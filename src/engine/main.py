import asyncio
import json
import logging
import re
from contextlib import asynccontextmanager
from datetime import datetime
from importlib.resources import files
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request

from engine import config
from engine.sensors import poll_all_sensors
from engine.simple_cache import SimpleCache

try:
    from trade_secrets.model import generate_nowcast

    TRADE_SECRETS_AVAILABLE = True
except ImportError:
    TRADE_SECRETS_AVAILABLE = False

NOWCAST_CACHE = SimpleCache('nowcast', config.NOWCAST_CACHE_TIMEOUT_S)

logging.basicConfig(
    level=config.LOGGING_LEVEL,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)

log = logging.getLogger(__name__)


async def refresh_cached_nowcast() -> dict:
    if TRADE_SECRETS_AVAILABLE:
        nowcast = generate_nowcast(await poll_all_sensors())
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
        await asyncio.sleep(config.NOWCAST_CACHE_TIMEOUT_S)
        uk_time = datetime.now(ZoneInfo('Europe/London'))
        if (
            config.NOWCAST_CACHE_AUTO_REFRESH_FIRST_HOUR <= uk_time.hour <= config.NOWCAST_CACHE_AUTO_REFRESH_LAST_HOUR
        ) and (
            config.NOWCAST_CACHE_AUTO_REFRESH_FIRST_WEEKDAY
            <= uk_time.weekday()
            <= config.NOWCAST_CACHE_AUTO_REFRESH_LAST_WEEKDAY
        ):
            # Only refresh the cache during UK working hours to save hammering the data sources.
            log.info('Autorefreshing cache...')
            try:
                await refresh_cached_nowcast()
            except (RuntimeError, TypeError, KeyError) as e:
                log.error(f'Cache autorefresh failed with error {e}')
            log.info('Cache autorefresh complete.')
        else:
            log.debug(
                'Cache autorefresh watchdog triggered, but did not autorefresh cache '
                f'as the hour is {uk_time.hour} and the day of the week is {uk_time.weekday()}'
            )


@asynccontextmanager
async def lifespan_manager(_: FastAPI):
    """Create an async task that automatically refreshes the cache.

    The cache is refreshed every NOWCAST_CACHE_TIMEOUT_S, but only between 0800 and 1800 UK time.
    This prevents us hammering the sites too much while keeping the site fast.
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


def is_vercel_preview_deployment(url: str) -> bool:
    return bool(re.fullmatch(r'https://edicrowds-frontend-[a-z0-9\-]+-tristan-goss-projects\.vercel\.app', url))


@app.middleware('http')
async def dynamic_cors_middleware(request: Request, call_next):
    """Custom CORS Middleware to support vercel preview deployments.

    Allows access if it's a local Vite dev server,
    the production build, or a vercel preview URL.
    """
    origin = request.headers.get('origin')
    response = await call_next(request)
    if origin and (
        origin
        in {
            'https://www.edinburghcrowds.co.uk',
            'http://localhost:5173',
        }
        or is_vercel_preview_deployment(origin)
    ):
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = '*'
        response.headers['Access-Control-Allow-Headers'] = '*'
    return response


@app.get('/nowcast')
async def get_nowcast() -> dict:
    """Return the current nowcast, generating it if needed."""
    nowcast = NOWCAST_CACHE.read()
    if nowcast is None:
        # we need to generate a fresh nowcast for this user
        nowcast = await refresh_cached_nowcast()

    return nowcast
