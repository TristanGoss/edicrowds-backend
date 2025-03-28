
import os
import json
from datetime import datetime
import logging
from pathlib import Path

from importlib.resources import files
from fastapi import APIRouter

from engine.config import NOWCAST_CACHE_TIMEOUT_S
from engine.sensors import poll_all_sensors
from engine.simple_cache import SimpleCache

try:
    from trade_secrets.model import generate_nowcast
    TRADE_SECRETS_AVAILABLE = True
except ImportError:
    TRADE_SECRETS_AVAILABLE = False

router = APIRouter()

log = logging.getLogger(__name__)


@router.get("/nowcast")
def get_nowcast() -> dict:
    """Return the current nowcast, generating it if needed."""

    cache = SimpleCache('nowcast', NOWCAST_CACHE_TIMEOUT_S)
    nowcast = cache.read()

    if nowcast is None:
        if TRADE_SECRETS_AVAILABLE:
            nowcast = generate_nowcast(poll_all_sensors())
        else:
            log.warning("Nowcast requested, but trade secrets are not present, so returning mock data")
            data_path = files("engine") / "mock_nowcast.json"
            with data_path.open("r", encoding="utf-8") as f:
                nowcast = json.load(f)

        cache.write(nowcast)

    return nowcast
