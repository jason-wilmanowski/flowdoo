"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from flow_tracer_api.api.routes import health
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

    app = FastAPI(title="Odoo Flow Tracer API", version="0.1.0", lifespan=lifespan)
    app.include_router(health.router)
    return app
