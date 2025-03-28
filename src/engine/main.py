import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from engine.config import LOGGING_LEVEL
from engine.routes import router

logging.basicConfig(
    level=LOGGING_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

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

app.include_router(router)
