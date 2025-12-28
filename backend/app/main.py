import logging

from fastapi import FastAPI
from pythonjsonlogger import jsonlogger
from sqlalchemy import text

from .config import get_settings
from .db import engine
from .api.startups import router as startups_router
from .api.gmail import router as gmail_router
from .api.drive import router as drive_router
from .api.ingest import router as ingest_router
from .api.investor import router as investor_router
from .api.investor_voice import router as investor_voice_router
from .api.agent import router as agent_router
from .health import router as health_router

settings = get_settings()
logger = logging.getLogger(__name__)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level)
    root_logger.handlers = [handler]


configure_logging()

app = FastAPI(title=settings.app_name)
app.include_router(health_router)
app.include_router(startups_router)
app.include_router(gmail_router)
app.include_router(drive_router)
app.include_router(ingest_router)
app.include_router(investor_router)
app.include_router(investor_voice_router)
app.include_router(agent_router)


@app.on_event("startup")
def verify_database_connection() -> None:
    if not settings.db_check_on_startup:
        logger.info("Skipping database connection check on startup.")
        return
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Database connection check failed.")
