import json
from collections.abc import Callable

import httpx
import pytest

from flow_tracer_api.integrations.odoo import (
    OdooAuthenticationError,
    OdooCallError,
    OdooDatabaseNotFoundError,
    OdooJson2Client,
    OdooUnreachableError,
)

API_KEY = "0123456789abcdef-secret"
ODOO_TRACEBACK = "Traceback (most recent call last): secret internals"


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> OdooJson2Client:
    return OdooJson2Client(
        base_url="http://odoo:8069/",
        database="dev",
        api_key=API_KEY,
        transport=httpx.MockTransport(handler),
    )


def _odoo_error(message: str, status: int) -> httpx.Response:
    body = {"name": "werkzeug.exceptions.X", "message": message, "debug": ODOO_TRACEBACK}
    return httpx.Response(status, json=body)


async def test_call_posts_json2_with_bearer_and_database_header() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[{"id": 1, "state": "installed"}])

    async with _client(handler) as client:
        result = await client.call(
            "ir.module.module", "search_read", domain=[["name", "=", "base"]], fields=["state"]
        )

    assert result == [{"id": 1, "state": "installed"}]
    [request] = seen
    assert request.method == "POST"
    assert request.url == "http://odoo:8069/json/2/ir.module.module/search_read"
    assert request.headers["Authorization"] == f"bearer {API_KEY}"
    assert request.headers["X-Odoo-Database"] == "dev"
    assert json.loads(request.content) == {"domain": [["name", "=", "base"]], "fields": ["state"]}


async def test_call_sends_ids_and_context_only_when_given() -> None:
    bodies: list[object] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json=True)

    async with _client(handler) as client:
        await client.call("res.users", "context_get")
        await client.call("sale.order", "action_confirm", ids=[7], context={"lang": "de_DE"})

    assert bodies == [{}, {"ids": [7], "context": {"lang": "de_DE"}}]


async def test_version_info_parses_jsonrpc_result() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/web/webclient/version_info"
        assert json.loads(request.content)["method"] == "call"
        result = {
            "server_version": "19.0-20260926",
            "server_version_info": [19, 0, 0, "final", 0, ""],
            "server_serie": "19.0",
            "protocol_version": 1,
        }
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": None, "result": result})

    async with _client(handler) as client:
        info = await client.version_info()

    assert info.server_serie == "19.0"
    assert info.server_version == "19.0-20260926"


async def test_version_info_jsonrpc_error_becomes_call_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        error = {"code": 200, "message": "Odoo Server Error", "data": {"message": "boom"}}
        return httpx.Response(200, json={"jsonrpc": "2.0", "error": error})

    async with _client(handler) as client:
        with pytest.raises(OdooCallError, match="version_info failed: boom"):
            await client.version_info()


@pytest.mark.parametrize(
    ("response", "error_type", "fragment"),
    [
        (_odoo_error("Invalid apikey", 401), OdooAuthenticationError, "rejected the API key"),
        (
            httpx.Response(404, text="<!DOCTYPE html>No database"),
            OdooDatabaseNotFoundError,
            "'dev'",
        ),
        (_odoo_error("the model 'x.y' does not exist", 404), OdooCallError, "does not exist"),
        (_odoo_error("Access Denied", 403), OdooCallError, "HTTP 403: Access Denied"),
        (_odoo_error("Internal error", 500), OdooCallError, "HTTP 500"),
    ],
)
async def test_http_errors_are_mapped_without_secrets(
    response: httpx.Response, error_type: type[Exception], fragment: str
) -> None:
    async with _client(lambda request: response) as client:
        with pytest.raises(error_type, match=fragment) as exc_info:
            await client.call("res.users", "context_get")

    message = str(exc_info.value)
    assert API_KEY not in message
    assert "Traceback" not in message


@pytest.mark.parametrize(
    ("exception", "fragment"),
    [
        (httpx.ConnectError("connection refused"), "Cannot reach Odoo: ConnectError"),
        (httpx.ReadTimeout("slow"), "did not answer in time"),
    ],
)
async def test_transport_failures_become_unreachable(exception: Exception, fragment: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise exception

    async with _client(handler) as client:
        with pytest.raises(OdooUnreachableError, match=fragment):
            await client.version_info()
