"""Entrypoint of the API: builds the FastAPI app, its middleware and routers.

Started as an application factory, so importing this module needs no configuration:
``uvicorn flow_tracer_api.main:create_app --factory``.
"""

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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(traces.router)
    app.include_router(odoo.router)
    return app
