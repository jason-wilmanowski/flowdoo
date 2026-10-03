"""Errors raised by the service layer.

Every error carries a ``message`` and a ``status_code``, both set where the service
raises it. Endpoints catch ``ServiceError`` and turn it into an ``HTTPException``.
``http.HTTPStatus`` (stdlib) keeps the service layer free of FastAPI imports.
"""

from http import HTTPStatus


class ServiceError(Exception):
    def __init__(self, message: str, status_code: HTTPStatus) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class TraceNotFoundError(ServiceError):
    """The requested trace does not exist (any more)."""


class OdooGatewayUnavailableError(ServiceError):
    """No Odoo connection is configured, so no trace can be started."""


class NonDryRunNotAllowedError(ServiceError):
    """``dry_run=false`` was requested but is not enabled for this setup."""
