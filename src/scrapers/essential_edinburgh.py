import logging
from datetime import date, datetime, timedelta
from typing import Callable, Dict, List, Tuple

import cv2
import numpy as np
import requests
from bs4 import BeautifulSoup

from engine import config
from engine.classes import PedFluxCounterMeasurement
from engine.simple_cache import SimpleCache
from scrapers.utils import scrape_urls

log = logging.getLogger(__name__)

WORKDAYS_PER_WEEK = 5
HOURS_PER_DAY = 24
WEEKS_PER_YEAR = 52


def get_pixel_to_data_transform(
    pix_1: Tuple[float], data_1: Tuple[float], pix_2: Tuple[float], data_2: Tuple[float]
) -> Callable:
    """Compute scale and offset for x and y axes."""
    pix_x1, pix_y1 = pix_1
    data_x1, data_y1 = data_1
    pix_x2, pix_y2 = pix_2
    data_x2, data_y2 = data_2

    scale_x = (data_x2 - data_x1) / (pix_x2 - pix_x1)
    offset_x = data_x1 - pix_x1 * scale_x

    scale_y = (data_y2 - data_y1) / (pix_y2 - pix_y1)
    offset_y = data_y1 - pix_y1 * scale_y

    def transform(xs, ys):
        data_xs = xs * scale_x + offset_x
        data_ys = ys * scale_y + offset_y
        return data_xs, data_ys

    return transform


def extract_lines_from_graphs(image_bytes: bytes) -> List:
    """Extract the lines from Essential Edinburgh's graphs.

    We are assuming here that the lines are all different
    colours from each other, and also a different colour from the axes.

    Returns a tuple containing the line's coordinates in pixel space.
    """
    # Load the image
    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)

    # Remove the axes and title (note this works for both princes and rose street)
    bottom = config.EE_PIXELS_FROM_BOTTOM_COVERING_AXES
    top = config.EE_PIXELS_FROM_TOP_COVERING_TITLE
    left = config.EE_PIXELS_FROM_LEFT_COVERING_AXES
    img = img[top : (img.shape[0] - bottom), left:, :]

    # reduce colour depth to 2 bit
    # TODO: This algorithm fails to separate the grey line in the Rose St
    # image from the axes, so it is not picked up.
    factor = 256 // 2
    img = ((img // factor) * factor).astype(np.uint8)

    # Find unique colours
    unique_colours = np.unique(img.reshape(-1, 3), axis=0)
    log.debug(f'found {len(unique_colours)} unique 2-bit colours in the image')

    #  Sort them by the number of pixels matching them
    sorted_unique_colours = sorted(unique_colours, key=lambda x: np.all(img == x, axis=2).ravel().sum(), reverse=True)

    # The lines in the image will be the three most prevelant unique colors,
    # but not the most prevelant (that's the background)
    line_colours = sorted_unique_colours[1:4]

    for c in line_colours:
        log.debug(f'extracting data for line with colour {c}')
        # create mask for this line colour as uint8 image
        mask = (np.all(img == c, axis=2) * 255).astype(np.uint8)

        # remove noise via connected component filtering
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
        log.debug(f'found {num_labels} line segments')
        filtered = np.zeros_like(mask)
        for i in range(1, num_labels):  # start at 1 to exclude background
            if stats[i, cv2.CC_STAT_AREA] >= config.EE_CONNECTED_COMPONENT_FILTERING_THRESH:
                filtered[labels == i] = 1

        # extract x and y values from filtered mask
        ys, xs = np.nonzero(filtered)

        # aggregate y values per x
        x_to_ys = {}
        for x, y in zip(xs, ys):
            if x not in x_to_ys:
                x_to_ys[x] = []
            x_to_ys[x].append(y)

        # obtain mean y per x (the centre of the line)
        x_vals = np.array(sorted(x_to_ys.keys()))
        y_vals = [np.mean(x_to_ys[x]) for x in x_vals]

        # fill missing x_vals via linear interpolation
        pixel_space_results_x = np.arange(x_vals.min(), x_vals.max() + 1)
        pixel_space_results_y = np.interp(pixel_space_results_x, x_vals, y_vals)

        return pixel_space_results_x, pixel_space_results_y


def scrape_dashboard() -> Dict[str, List[Tuple[int]]]:
    """Extract Footfall measurements from Essential Edinburgh.

    We scrape the Princes St and Rose St figures from
    https://www.essentialedinburgh.co.uk/stats/ and
    process them to extract the data.

    Note that this website specifically prevents reproduction
    of the figures, so we may not simply re-report the data!
    """
    log.info('commencing scrape of Essential Edinburgh.')

    images_to_find = [
        {'name': 'EE001', 'src_pattern': 'PS-52-Week_Update', 'image_bytes': None, 'df': None},
        {'name': 'EE002', 'src_pattern': 'RoseSt-52-Week_Update', 'image_bytes': None, 'df': None},
    ]

    html = scrape_urls(['https://www.essentialedinburgh.co.uk/stats/'], config.EE_PAGE_LOAD_INDICATOR_SELECTOR)[0]
    soup = BeautifulSoup(html, 'html.parser')

    found_all_figures = False
    for image_source in [i.get('src') for i in soup.find_all('img')]:
        for image_dict in images_to_find:
            if image_dict['src_pattern'] in image_source:
                response = requests.get(image_source)
                assert response.ok, f'Failed to retrieve {image_dict["name"]} image'
                image_dict['image_bytes'] = response.content
                log.debug(f'retrieved {image_dict["name"]} figure')

        if all([x['image_bytes'] is not None for x in images_to_find]):
            log.info('retrieved all figures')
            found_all_figures = True
            break

    if found_all_figures:
        # generate the image space -> data space transforms
        transform_lines_to_data = {
            'EE001': get_pixel_to_data_transform(**config.EE_PRINCES_IMG_TO_DATA_CALIB),
            'EE002': get_pixel_to_data_transform(**config.EE_ROSE_IMG_TO_DATA_CALIB),
        }

        results = {
            img['name']: transform_lines_to_data[img['name']](extract_lines_from_graphs(img['image_bytes']))
            for img in image_dict
        }

        log.info('extracted data from all figures')
    else:
        log.warning('Failed to extract necessary figures from Essential Edinburgh page, using hard-coded fallbacks...')
        results = {
            'EE001': [(np.array([1]), np.array([config.EE_FALLBACK_PRINCES_FOOTFALL_PAX_PER_WEEK]))],
            'EE002': [(np.array([1]), np.array([config.EE_FALLBACK_ROSE_FOOTFALL_PAX_PER_WEEK]))],
        }

    return results


def monday_of_week(week: int, year: int = date.today().year) -> date:
    jan_1 = date(year, 1, 1)
    jan_1_weekday = jan_1.weekday()
    # Shift to first Monday *before or on* Jan 1
    first_monday = jan_1 - timedelta(days=jan_1_weekday)
    # Add (week - 1) * 7 days
    return first_monday + timedelta(weeks=week - 1)


def extract_most_recent_measurements(all_measurements: Dict[str, List[Tuple[int]]]) -> Dict[str, int]:
    """We only care about the most recent measurement at the moment.

    This may change later on.
    """
    most_recent_measurements = {k: None for k in all_measurements.keys()}

    for k, results in all_measurements.items():
        max_x_vals = np.array([int(x[0].max()) for x in results])

        # If all the results have 52 x values then
        # we're in the last week of December or the first week of January,
        # so just average those two from all past years.
        if np.all(max_x_vals == WEEKS_PER_YEAR):
            christmas_and_new_years_measurements = [x[1][0] for x in results] + [x[1][-1] for x in results]
            most_recent_measurements[k] = int(np.mean(christmas_and_new_years_measurements))
            log.info(f'most recent measurement for {k} was approximated from christmas and new year figures')
        else:
            # find the result set with the smallest x value, and return its last y value
            # this should represent the end of the line that stops in the middle of the year
            sorted_results = sorted(results, key=lambda x: x[0].max())
            most_recent_measurements[k] = int(sorted_results[0][1][-1])
            most_recent_measurement_week = int(max_x_vals.min())
            most_recent_measurement_week_monday = monday_of_week(most_recent_measurement_week)
            log.info(
                f'most recent measurement for {k} was from '
                f'week {most_recent_measurement_week} commencing on {most_recent_measurement_week_monday}, '
                f'and so is up to {(date.today() - most_recent_measurement_week_monday).days} days old'
            )

        log.info(f'most recent measurement for {k} was {most_recent_measurements[k]} pax per week')

    return most_recent_measurements


def correct_for_diurnal_and_day_of_week(
    most_recent_measurements_pax_per_week: Dict[str, int], dt: datetime
) -> Dict[str, int]:
    """Correct Essential Edinburgh measurements for time of day and day of week.

    Essential Edinburgh gives us one figure for the week,
    so we need to add diurnal and weekday versus weekend effects.

    We are making a very strong assumption here
    about the pattern of pedestrian use of Princes and Rose St!

    Note that this function accepts pax per week and returns pax per hour!
    """
    if dt.weekday() < WORKDAYS_PER_WEEK:
        diurnal_model = np.array(config.EE_WEEKDAY_DIURNAL)
    else:
        diurnal_model = np.array(config.EE_WEEKEND_DIURNAL)

    assert len(diurnal_model) == HOURS_PER_DAY, 'Diurnal model needs to have length 24'

    # normalise
    diurnal_model = diurnal_model / sum(diurnal_model)

    log.debug(f'day -> hour diurnal correction is {diurnal_model[dt.hour]:.4f}')

    return {k: v / 7 * diurnal_model[dt.hour] for k, v in most_recent_measurements_pax_per_week.items()}


def poll_essential_edinburgh() -> List[PedFluxCounterMeasurement]:
    """Extract measurements from Essential Edinburgh.

    Wrapper function including caching
    for extracting measurements from Essential Edinburgh.
    """
    cache = SimpleCache('essential_edinburgh', config.EE_CACHE_TIMEOUT_S)

    weekly_measurements_pax_per_week = cache.read()

    if weekly_measurements_pax_per_week is None:
        # scrape the website and cache the result
        all_measurements_pax_per_week = scrape_dashboard()
        weekly_measurements_pax_per_week = extract_most_recent_measurements(all_measurements_pax_per_week)
        cache.write(weekly_measurements_pax_per_week)

    # Adjust the results for the current time of day / week.
    # This happens hourly while the scrape happens weekly.
    # The calculation here is trivial, so we don't bother to cache it.
    current_dt = datetime.now()
    corrected_measurements_pax_per_hour = correct_for_diurnal_and_day_of_week(
        weekly_measurements_pax_per_week, current_dt
    )

    # sanity check
    assert all([v >= 0 and v <= config.EE_MAX_PAX_PER_HOUR for v in corrected_measurements_pax_per_hour.values()]), (
        f'EE scraper produced nonsense values! {corrected_measurements_pax_per_hour}'
    )

    return [
        PedFluxCounterMeasurement(sensor_name=k, datetime=current_dt, flow_pax_per_hour=v)
        for k, v in corrected_measurements_pax_per_hour.items()
    ]
