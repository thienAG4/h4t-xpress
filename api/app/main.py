from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text

from app import __version__
from app.core.config import get_settings
from app.core.db import engine


class HealthOut(BaseModel):
    status: str
    database: str
    version: str
    demo_mode: bool


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
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

    app.add_api_route("/health", health, methods=["GET"], include_in_schema=False)

    api = APIRouter(prefix="/api/v1")
    api.add_api_route("/health", health, methods=["GET"], response_model=HealthOut, tags=["system"])
    app.include_router(api)
    return app


app = create_app()
