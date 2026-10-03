from http import HTTPStatus
from typing import Any

import pytest

from flow_tracer_api.integrations.odoo import OdooCallError, OdooClientError, OdooUnreachableError
from flow_tracer_api.services import (
    EntrypointLookupError,
    OdooGatewayUnavailableError,
    OdooRequestError,
)
from flow_tracer_api.services.entrypoint_service import EntrypointService
from flow_tracer_api.services.ports import OdooClient
from tests.unit.test_odoo_connection_service import FakeOdooClient

SIGNATURE = {
    "model": "res.partner",
    "method": "write",
    "model_level": False,
    "module": "base",
    "summary": "Update the records.",
    "parameters": [
        {
            "name": "vals",
            "kind": "positional_or_keyword",
            "required": True,
            "default": None,
            "annotation": None,
        }
    ],
}


class SignatureClient(FakeOdooClient):
    def __init__(self, answer: Any = None, error: OdooClientError | None = None) -> None:
        super().__init__()
        self.answer = SIGNATURE if answer is None else answer
        self.error = error
        self.posted: list[tuple[str, dict[str, Any]]] = []

    async def post(self, path: str, payload: dict[str, Any], **_: Any) -> Any:
        self.posted.append((path, payload))
        if self.error is not None:
            raise self.error
        return self.answer


def _service(client: SignatureClient | None) -> EntrypointService:
    typed: OdooClient | None = client
    return EntrypointService(typed)


async def test_describe_asks_the_addon() -> None:
    client = SignatureClient()

    signature = await _service(client).describe("res.partner", "write")

    assert client.posted == [
        ("/flow_tracer/v1/signature", {"model": "res.partner", "method": "write"})
    ]
    assert signature.model_level is False
    assert [p.name for p in signature.parameters] == ["vals"]
    assert signature.parameters[0].required is True


@pytest.mark.parametrize("status", [400, 403, 404])
async def test_request_errors_are_passed_on(status: int) -> None:
    client = SignatureClient(error=OdooCallError(f"refused with HTTP {status}", status))

    with pytest.raises(EntrypointLookupError) as exc_info:
        await _service(client).describe("res.partner", "nope")

    assert exc_info.value.status_code == status
    assert exc_info.value.message == f"refused with HTTP {status}"


@pytest.mark.parametrize(
    "error",
    [OdooCallError("boom", 500), OdooCallError("no status"), OdooUnreachableError("down")],
)
async def test_odoo_failures_are_bad_gateway(error: OdooClientError) -> None:
    with pytest.raises(OdooRequestError) as exc_info:
        await _service(SignatureClient(error=error)).describe("res.partner", "write")

    assert exc_info.value.status_code == HTTPStatus.BAD_GATEWAY


async def test_unusable_answer_is_bad_gateway() -> None:
    with pytest.raises(OdooRequestError, match="Unexpected signature answer"):
        await _service(SignatureClient(answer={"model": "x"})).describe("x", "y")


async def test_not_configured_is_503() -> None:
    with pytest.raises(OdooGatewayUnavailableError) as exc_info:
        await _service(None).describe("res.partner", "write")

    assert exc_info.value.status_code == HTTPStatus.SERVICE_UNAVAILABLE
