"""FastAPI application: middleware, error handlers and module routers."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text

from app import __version__, models
from app.core.config import get_settings
from app.core.db import engine
from app.core.errors import register_error_handlers
from app.modules.admin.router import router as admin_config_router
from app.modules.auth.router import router as auth_router
from app.modules.delivery.router import router as delivery_router
from app.modules.drivers.router import router as driver_router
from app.modules.files.router import router as files_router
from app.modules.hubs.router import router as hubs_router
from app.modules.incidents.router import driver_router as driver_incidents_router
from app.modules.incidents.router import hub_router as hub_incidents_router
from app.modules.orders.hub_router import router as hub_orders_router
from app.modules.partner.router import router as partner_router
from app.modules.rbac.router import router as roles_router
from app.modules.realtime.router import router as realtime_router
from app.modules.reports.router import router as reports_router
from app.modules.routing.router import router as routes_router
from app.modules.sim.router import demo_router as sim_demo_router
from app.modules.sim.router import router as sim_router
from app.modules.sim.router import track_router as sim_track_router
from app.modules.users.router import admin_router as admin_users_router
from app.modules.users.router import me_router
from app.worker.runner import worker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


class HealthOut(BaseModel):
    status: str
    database: str
    version: str
    demo_mode: bool


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if get_settings().worker_enabled:
        worker.start()
    yield
    await worker.stop()
    await engine.dispose()


async def health() -> JSONResponse:
    """Liveness + database check. Used by Docker/Render health checks and the web app."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("select 1"))
        database_ok = True
    except Exception:
        database_ok = False
    body = HealthOut(
        status="ok" if database_ok else "degraded",
        database="ok" if database_ok else "unavailable",
        version=__version__,
        demo_mode=get_settings().demo_mode,
    )
    return JSONResponse(body.model_dump(), status_code=200 if database_ok else 503)


def create_app() -> FastAPI:
    settings = get_settings()
    # Every model must be loaded so cross-module foreign keys (orders -> route_stops,
    # delivery_attempt_files -> files, ...) resolve; configure() also fails fast on mapping errors.
    models.Base.registry.configure()
    app = FastAPI(
        title="H4T Xpress API",
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)

    app.add_api_route("/health", health, methods=["GET"], include_in_schema=False)
    app.include_router(realtime_router)

    api = APIRouter(prefix="/api/v1")
    api.add_api_route("/health", health, methods=["GET"], response_model=HealthOut, tags=["system"])
    for router in (
        auth_router,
        me_router,
        hubs_router,
        driver_router,
        delivery_router,
        driver_incidents_router,
        hub_orders_router,
        hub_incidents_router,
        routes_router,
        reports_router,
        files_router,
        admin_users_router,
        admin_config_router,
        roles_router,
        partner_router,
        sim_router,
        sim_track_router,
        sim_demo_router,
    ):
        api.include_router(router)
    app.include_router(api)
    return app


app = create_app()
