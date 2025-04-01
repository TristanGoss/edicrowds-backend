import asyncio
import json
import logging
from contextlib import asynccontextmanager
from importlib.resources import files

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from engine.config import LOGGING_LEVEL, NOWCAST_CACHE_TIMEOUT_S
from engine.sensors import poll_all_sensors
from engine.simple_cache import SimpleCache

try:
    from trade_secrets.model import generate_nowcast

    TRADE_SECRETS_AVAILABLE = True
except ImportError:
    TRADE_SECRETS_AVAILABLE = False

NOWCAST_CACHE = SimpleCache('nowcast', NOWCAST_CACHE_TIMEOUT_S)
LAST_CACHE_READ_TIME_CACHE = SimpleCache('had_users_since_cache', NOWCAST_CACHE_TIMEOUT_S)

logging.basicConfig(
    level=LOGGING_LEVEL,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)

log = logging.getLogger(__name__)


def refresh_cached_nowcast() -> dict:
    if TRADE_SECRETS_AVAILABLE:
        nowcast = generate_nowcast(poll_all_sensors())
    else:
        log.warning('Nowcast requested, but trade secrets are not present, so returning mock data')
        data_path = files('engine') / 'mock_nowcast.json'
        with data_path.open('r', encoding='utf-8') as f:
            nowcast = json.load(f)

    NOWCAST_CACHE.write(nowcast)
    return nowcast


async def nowcast_cache_autorefresh():
    log.debug('Cache autorefresh watchdog started')
    while True:
        await asyncio.sleep(NOWCAST_CACHE_TIMEOUT_S)
        if LAST_CACHE_READ_TIME_CACHE.read() is not None:
            # nowcast cache was hit before timeout, so automatically refresh cache
            # (assuming new users are coming and they don't want to wait!)
            log.info('A user accessed the cache since it was last generated, so regenerating to keep it warm...')
            refresh_cached_nowcast()


@asynccontextmanager
async def lifespan_manager(_: FastAPI):
    """Create an async task that automatically refreshes the cache.

    The cache is refreshed every NOWCAST_CACHE_TIMEOUT_S, but only if it was accessed during the last refresh period.
    This keeps the cache warm if it's actually being used.
    """
    watchdog = asyncio.create_task(nowcast_cache_autorefresh())
    try:
        yield
    finally:
        watchdog.cancel()
        try:
            await watchdog
        except asyncio.CancelledError:
            log.debug('Cache autorefresh watchdog shutdown')


app = FastAPI(lifespan=lifespan_manager)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'https://edinburghcrowds.co.uk',
        'http://localhost:5173',  # for local development
    ],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/nowcast')
def get_nowcast() -> dict:
    """Return the current nowcast, generating it if needed."""
    nowcast = NOWCAST_CACHE.read()

    if nowcast is None:
        # we need to generate a fresh nowcast for this user
        nowcast = refresh_cached_nowcast()
    else:
        # A user hit the route while the cache was present.
        # This will prompt an automatic cache refresh later.
        LAST_CACHE_READ_TIME_CACHE.write('_')

    return nowcast
