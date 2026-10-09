from http import HTTPStatus
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from flow_tracer_api.api.dependencies import get_odoo_client
from flow_tracer_api.core.config import get_settings
from flow_tracer_api.integrations.odoo import OdooCallError, OdooClientError, OdooUnreachableError
from flow_tracer_api.main import create_app
from flow_tracer_api.services import ModelLookupError, OdooGatewayUnavailableError, OdooRequestError
from flow_tracer_api.services.ports import OdooClient
from flow_tracer_api.services.registry_service import RegistryService
from tests.unit.test_odoo_connection_service import FakeOdooClient
from tests.unit.test_odoo_status_api import CONFIGURED, _settings

PARTNER = {
    "model": "res.partner",
    "description": "Contact",
    "module": "base",
    "modules": ["account", "base"],
    "abstract": False,
    "transient": False,
    "parents": ["mail.thread"],
    "delegates": {},
}
LIST = {
    "models": [
        {
            **PARTNER,
            "field_count": 2,
            "relations": [{"field": "parent_id", "type": "many2one", "target": "res.partner"}],
        }
    ]
}
DETAIL = {
    **PARTNER,
    "fields": [
        {
            "name": "parent_id",
            "type": "many2one",
            "string": "Related Company",
            "module": "base",
            "target": "res.partner",
            "inverse": None,
            "required": False,
            "readonly": False,
            "stored": True,
            "compute": None,
            "related": None,
            "selection": None,
        }
    ],
}


class RegistryClient(FakeOdooClient):
    def __init__(self, error: OdooClientError | None = None, answer: Any = None) -> None:
        super().__init__()
        self.error = error
        self.answer = answer
        self.posted: list[tuple[str, dict[str, Any]]] = []

    async def post(self, path: str, payload: dict[str, Any], **_: Any) -> Any:
        self.posted.append((path, payload))
        if self.error is not None:
            raise self.error
        if self.answer is not None:
            return self.answer
        return LIST if path.endswith("/models") else DETAIL


def _service(client: RegistryClient | None) -> RegistryService:
    typed: OdooClient | None = client
    return RegistryService(typed)


async def test_lists_and_describes_models() -> None:
    client = RegistryClient()

    listing = await _service(client).list_models()
    detail = await _service(client).describe_model("res.partner")

    assert client.posted == [
        ("/flow_tracer/v1/models", {}),
        ("/flow_tracer/v1/model", {"model": "res.partner"}),
    ]
    assert listing.models[0].relations[0].target == "res.partner"
    assert detail.fields[0].name == "parent_id"


async def test_unknown_model_is_passed_on() -> None:
    client = RegistryClient(error=OdooCallError("The model 'no.such' does not exist", 404))

    with pytest.raises(ModelLookupError) as exc_info:
        await _service(client).describe_model("no.such")

    assert exc_info.value.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.parametrize("error", [OdooCallError("boom", 500), OdooUnreachableError("down")])
async def test_other_failures_are_bad_gateway(error: OdooClientError) -> None:
    with pytest.raises(OdooRequestError) as exc_info:
        await _service(RegistryClient(error=error)).list_models()

    assert exc_info.value.status_code == HTTPStatus.BAD_GATEWAY


async def test_unusable_answer_is_bad_gateway() -> None:
    with pytest.raises(
        OdooRequestError, match=r"Unexpected answer from flow_tracer \(model registry\)"
    ):
        await _service(RegistryClient(answer={"models": [{"model": "x"}]})).list_models()


async def test_not_configured_is_503() -> None:
    with pytest.raises(OdooGatewayUnavailableError):
        await _service(None).list_models()


async def test_model_endpoints() -> None:
    settings = _settings(**CONFIGURED)
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_odoo_client] = lambda: RegistryClient()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        listing = await client.get("/odoo/models")
        detail = await client.get("/odoo/models/res.partner")

    assert listing.status_code == 200
    assert listing.json() == LIST
    assert detail.status_code == 200
    assert detail.json() == DETAIL


async def test_model_endpoint_passes_404_on() -> None:
    settings = _settings(**CONFIGURED)
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_odoo_client] = lambda: RegistryClient(
        error=OdooCallError("The model 'no.such' does not exist", 404)
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/odoo/models/no.such")

    assert response.status_code == 404
    assert response.json() == {"detail": "The model 'no.such' does not exist"}
