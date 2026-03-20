import logging

from api import router
from fastapi import FastAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

app = FastAPI(title="IdentifAI API")
app.include_router(router)
