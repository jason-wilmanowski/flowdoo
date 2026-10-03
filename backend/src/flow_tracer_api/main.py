"""ASGI entrypoint: ``uvicorn flow_tracer_api.main:app``."""

from flow_tracer_api.api.app import create_app

app = create_app()
