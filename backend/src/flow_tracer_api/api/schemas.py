"""HTTP-only response models (OpenAPI documentation of error bodies)."""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Body of every error response: ``HTTPException(detail=...)`` renders as this."""

    detail: str


def error_responses(*codes: int) -> dict[int | str, dict[str, object]]:
    return {code: {"model": ErrorResponse} for code in codes}
