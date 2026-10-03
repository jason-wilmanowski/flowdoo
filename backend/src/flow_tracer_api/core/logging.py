"""Logging setup for the API process."""

import logging

from flow_tracer_api.core.config import LogLevel

_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logging(level: LogLevel) -> None:
    """Configure root logging once. Never log credentials or trace payloads at INFO."""
    logging.basicConfig(level=level, format=_FORMAT, force=True)
