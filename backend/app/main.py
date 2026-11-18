"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.config import settings
from app.core.database import init_db

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Run database table initialization on startup."""
    try:
        init_db()
        logger.info("Database tables initialized successfully.")
    except Exception as err:
        logger.warning("Database initialization on startup deferred: %s", err)
    yield


app = FastAPI(title="AapdaSetu API", lifespan=lifespan)
app.include_router(health_router)


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    """Provide a small landing response for the API."""
    return {"name": "AapdaSetu API", "basin": settings.basin_name}

