"""Describe an entrypoint before tracing it (flow_tracer addon, /flow_tracer/v1/signature)."""

from flow_tracer_api.schemas import EntrypointSignature
from flow_tracer_api.services.common.addon_calls import ask_addon
from flow_tracer_api.services.common.errors import EntrypointLookupError
from flow_tracer_api.services.common.ports import OdooClient

SIGNATURE_ROUTE = "/flow_tracer/v1/signature"


class EntrypointService:
    def __init__(self, client: OdooClient | None) -> None:
        self._client = client

    async def describe(self, model: str, method: str) -> EntrypointSignature:
        return await ask_addon(
            self._client,
            SIGNATURE_ROUTE,
            {"model": model, "method": method},
            target=f"{model}.{method} signature",
            answer_type=EntrypointSignature,
            refused=EntrypointLookupError,
        )
