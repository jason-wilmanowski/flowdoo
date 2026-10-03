from enum import StrEnum


class TraceStatus(StrEnum):
    """Lifecycle of a trace run."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
