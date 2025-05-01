import logging
from datetime import datetime, timedelta
from io import StringIO
from typing import Dict, List

import pandas as pd
from bs4 import BeautifulSoup

from engine.classes import PedFluxCounterMeasurement
from engine.config import ETD_CACHE_TIMEOUT_S, ETD_MAX_PAX_PER_HOUR, ETD_PAGE_LOAD_INDICATOR_SELECTOR
from engine.simple_cache import SimpleCache
from scrapers.utils import scrape_urls

log = logging.getLogger(__name__)


async def poll_edintraveldata(sensor_descriptions: List[Dict]) -> List[PedFluxCounterMeasurement]:
    """Extract measurements from Edintraveldata.

    Wrapper function including caching for extracting measurements from Edintraveldata.
    """
    cache = SimpleCache('edintraveldata', ETD_CACHE_TIMEOUT_S)

    measurements = cache.read()
    current_dt = datetime.now()

    if measurements is None:
        measurements = {}
        hour_str = f'{current_dt.hour:02d}:00'

        # we extract the measurement from the previous day to mitigate the fact that some sensors
        # delay their reporting by some hours
        yesterday_date_str = (current_dt - timedelta(days=1)).strftime('%Y-%m-%d')

        urls = [
            s['source']
            + f'tfreport.asp?node=EDINBURGH_CYCLE&cosit={int(s["name"][3:]):012d}'
            + f'&reportdate={yesterday_date_str}&enddate={yesterday_date_str}&dimtype=2'
            for s in sensor_descriptions
        ]

        log.debug(f'going to check the following Edintraveldata URLs: \n{"\n".join(urls)}')
        htmls = await scrape_urls(urls, ETD_PAGE_LOAD_INDICATOR_SELECTOR)

        for sd, html in zip(sensor_descriptions, htmls):
            soup = BeautifulSoup(html, 'html.parser')
            table = soup.find('table', {'class': 'grid', 'id': 'gridTable'})
            if table is None:
                log.warning(
                    f'Could not find table in html returned for sensor {sd["name"]}'
                    f' for date {yesterday_date_str}, ignoring.'
                )
            else:
                df = pd.read_html(StringIO(str(table)))[0]
                measurement = df.loc[df['Time'] == hour_str, 'Ped'].iloc[0]
                if measurement == '-':
                    log.warning(f"Measurement for sensor {sd['name']} for time {hour_str} was '-'; ignoring.")
                else:
                    log.debug(f'Found measurement {measurement} pax per hour for {sd["name"]} for time {hour_str}')
                    measurements[sd['name']] = int(measurement)
        if len(measurements) > 0:
            # sanity check
            assert all([v >= 0 and v <= ETD_MAX_PAX_PER_HOUR for v in measurements.values()]), (
                f'ETD scraper produced nonsense values! {measurements}'
            )

            cache.write(measurements)

    return [
        PedFluxCounterMeasurement(sensor_name=k, datetime=current_dt, flow_pax_per_hour=v)
        for k, v in measurements.items()
    ]
