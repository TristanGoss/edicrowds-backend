"""Single point of configuration."""

import logging

LOGGING_LEVEL = logging.DEBUG

CACHE_ROOT = '/tmp/engine_cache'  # note must be mounted as docker volume so that cached scrapes persist over restarts

NOWCAST_CACHE_TIMEOUT_S = 15 * 60  # Return the cached nowcast unless it's more than 15 minutes old

AVERAGE_WALKING_SPEED_MPS = 1.3  # For conversion of pex flux measurements to ped density

PLAYWRIGHT_POLL_JITTER_S = 2  # jitter requests when submitting many
PLAYWRIGHT_LOAD_TIMEOUT_S = 20  # give up waiting for the page to load if it takes longer than this
PLAYWRIGHT_USER_AGENTS = [
    # Chrome on Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    # Firefox on Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
    # Safari on Mac
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_2) AppleWebKit/605.1.15 '
    '(KHTML, like Gecko) Version/16.3 Safari/605.1.15',
    # Firefox on Ubuntu
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0'
    # Opera on Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.6099.110 Safari/537.36 OPR/106.0.4998.70'
    # Opera on Ubuntu
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.6099.110 Safari/537.36 OPR/106.0.4998.70',
]
PLAYWRIGHT_VIEWPORTS = [
    {'width': 1920, 'height': 1080},
    {'width': 1366, 'height': 768},
    {'width': 1536, 'height': 864},
]
PLAYWRIGHT_LOCALES = ['en-US', 'en-GB']

ETD_PAGE_LOAD_INDICATOR_SELECTOR = '#gridTable'
ETD_CACHE_TIMEOUT_S = 60 * 60  # The site offers real-time measurements, but we only poll it once an hour
ETD_MAX_PAX_PER_HOUR = 1e3

EE_PAGE_LOAD_INDICATOR_SELECTOR = '.visualizer-chart-loaded'
EE_CACHE_TIMEOUT_S = 7 * 24 * 60 * 60  # The site only provides a weekly measurement
EE_PIXELS_FROM_BOTTOM_COVERING_AXES = 100
EE_PIXELS_FROM_TOP_COVERING_TITLE = 50
EE_PIXELS_FROM_LEFT_COVERING_AXES = 60
EE_CONNECTED_COMPONENT_FILTERING_THRESH = 10
EE_PRINCES_IMG_TO_DATA_CALIB = {
    'pix_1': (24, 205),
    'data_1': (1, 250e3),
    'pix_2': (820, 51),
    'data_2': (52, 400e3),
}
EE_ROSE_IMG_TO_DATA_CALIB = {
    'pix_1': (24, 157),
    'data_1': (1, 60e3),
    'pix_2': (820, 52),
    'data_2': (52, 100e3),
}
# from weekdays in March 2025, CEC045
EE_WEEKDAY_DIURNAL = [
    18,
    17,
    7,
    4,
    0,
    4,
    863,
    76,
    602,
    417,
    380,
    362,
    867,
    89,
    386,
    305,
    417,
    555,
    1179,
    246,
    171,
    108,
    79,
    65,
]
# from weekends in March 2025, CEC045
EE_WEEKEND_DIURNAL = [
    23,
    19,
    7,
    7,
    5,
    0,
    460,
    24,
    54,
    130,
    186,
    219,
    193,
    158,
    125,
    114,
    137,
    111,
    523,
    95,
    74,
    31,
    46,
    23,
]
EE_MAX_PAX_PER_HOUR = 50e3
