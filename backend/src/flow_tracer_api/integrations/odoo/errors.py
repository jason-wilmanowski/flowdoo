"""Errors of the Odoo client. Messages never contain the API key or Odoo tracebacks."""


class OdooClientError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class OdooUnreachableError(OdooClientError):
    """No HTTP connection (wrong URL, Odoo down, timeout)."""


class OdooAuthenticationError(OdooClientError):
    """The API key was rejected."""


class OdooDatabaseNotFoundError(OdooClientError):
    """Odoo answered, but the configured database is not served."""


class OdooCallError(OdooClientError):
    """Odoo executed the request and returned an error (e.g. unknown model, access error)."""
