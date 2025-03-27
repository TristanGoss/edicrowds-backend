import logging
import json

from importlib.resources import files
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from trade_secrets.main import hello_secret_world
    TRADE_SECRETS_PRESENT = True
except ImportError:
    TRADE_SECRETS_PRESENT = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://edinburghcrowds.co.uk",
        "http://localhost:5173",  # for local development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/nowcast")
def get_nowcast():
    if TRADE_SECRETS_PRESENT:
        hello_secret_world()
    logger.info("Nowcast requested, returning mock data")
    data_path = files("engine") / "mock_nowcast.json"
    with data_path.open("r", encoding="utf-8") as f:
        return json.load(f)
