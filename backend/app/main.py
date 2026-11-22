"""FastAPI application entry point."""

import asyncio
import os
import sys
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.catalog import router as catalog_router
from app.api.coordination import router as coordination_router
from app.api.core_v1 import router as core_v1_router
from app.api.health import router as health_router
from app.api.incidents import router as incidents_router
from app.api.safety import router as safety_router
from app.api.super_admin import router as super_admin_router
from app.api.telemetry import router as telemetry_router
from app.core.config import settings
from app.services.live_data import live_data

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    del app
    is_testing = bool(os.getenv("TESTING")) or "pytest" in sys.modules
    if not is_testing and not scheduler.running:
        scheduler.add_job(
            live_data.poll, "interval", minutes=30, id="open-telemetry-poll", replace_existing=True
        )
        scheduler.start()
        asyncio.create_task(live_data.poll())
    try:
        yield
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)


app = FastAPI(title="AapdaSetu API", lifespan=lifespan)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(coordination_router)
app.include_router(catalog_router)
app.include_router(telemetry_router)
app.include_router(core_v1_router)
app.include_router(incidents_router)
app.include_router(safety_router)
app.include_router(super_admin_router)


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    """Provide a small landing response for the API."""
    return {"name": "AapdaSetu API", "basin": settings.basin_name}
