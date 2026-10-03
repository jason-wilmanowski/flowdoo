"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from flow_tracer_api.api.routes import health, odoo, traces
from flow_tracer_api.core.config import Settings, get_settings
from flow_tracer_api.core.db import create_engine, create_session_factory
from flow_tracer_api.core.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine(settings)
        app.state.engine = engine
        app.state.session_factory = create_session_factory(engine)
        try:
            yield
        finally:
            await engine.dispose()

    app = FastAPI(title="Flowdoo - Odoo Workflow Tracer", version="0.1.0", lifespan=lifespan)
    # Only the configured frontend origins; no cookies or auth headers are used.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type"],
        allow_credentials=False,
    )
    app.include_router(health.router)
    app.include_router(traces.router)
    app.include_router(odoo.router)
    return app
