import uuid


class ServiceError(Exception):
    """Base class for errors the API layer translates into HTTP responses."""


class TraceNotFoundError(ServiceError):
    def __init__(self, trace_id: uuid.UUID) -> None:
        super().__init__(f"Trace {trace_id} not found")
        self.trace_id = trace_id


class NonDryRunNotAllowedError(ServiceError):
    def __init__(self) -> None:
        super().__init__(
            "dry_run=false is disabled. It writes to the Odoo database and is only allowed "
            "when explicitly enabled for a development setup."
        )
