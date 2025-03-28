"""Single point of configuration."""
import logging

LOGGING_LEVEL=logging.DEBUG

CACHE_ROOT = "/tmp/engine_cache"  # note must be mounted as docker volume so that cached scrapes persist over restarts

NOWCAST_CACHE_TIMEOUT_S = 15 * 60  # Return the cached nowcast unless it's more than 15 minutes old

AVERAGE_WALKING_SPEED_MPS = 1.3  # For conversion of pex flux measurements to ped density

PLAYWRIGHT_POLL_JITTER_S = 2
PLAYWRIGHT_RENDER_WAIT_S = 10
PLAYWRIGHT_USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",

    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",

    # Safari on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_2) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/16.3 Safari/605.1.15",

    # Firefox on Ubuntu
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0"

    # Opera on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.6099.110 Safari/537.36 OPR/106.0.4998.70"

    # Opera on Ubuntu
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.6099.110 Safari/537.36 OPR/106.0.4998.70"
]
PLAYWRIGHT_VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
]
PLAYWRIGHT_LOCALES = ["en-US", "en-GB"]


ETD_CACHE_TIMEOUT_S = 60 * 60  # The site offers real-time measurements, but we only poll it once an hour

EE_CACHE_TIMEOUT_S = 7 * 24 * 60 * 60  # The site only provides a weekly measurement
EE_PIXELS_FROM_BOTTOM_COVERING_AXES = 100
EE_PIXELS_FROM_TOP_COVERING_TITLE = 50
EE_PIXELS_FROM_LEFT_COVERING_AXES = 60
EE_CONNECTED_COMPONENT_FILTERING_THRESH = 10
EE_PRINCES_IMG_TO_DATA_CALIB = {
    'pix_x1': 24,
    'data_x1': 1,
    'pix_x2': 820,
    'data_x2': 52,
    'pix_y1': 205,
    'data_y1': 250e3,
    'pix_y2': 51,
    'data_y2': 400e3
}
EE_ROSE_IMG_TO_DATA_CALIB = {
    'pix_x1': 25,
    'data_x1': 1,
    'pix_x2': 820,
    'data_x2': 52,
    'pix_y1': 157,
    'data_y1': 60e3,
    'pix_y2': 52,
    'data_y2': 100e3
}
# from 3rd-7th March 2025, CEC045
# TODO: Refine model
EE_WEEKDAY_DIURNAL = [0, 0, 0, 0, 0, 0, 36, 0, 7, 3, 6, 6, 41, 17, 14, 11, 17, 21, 53, 10, 5, 1, 2, 2]
# from 8th-9th March 2025, CEC045
# TODO: Refine model
EE_WEEKEND_DIURNAL = [1, 2, 0, 0, 1, 0, 53, 0, 6, 22, 28, 20, 16, 25, 17, 18, 18, 14, 48, 16, 6, 4, 5, 2]
