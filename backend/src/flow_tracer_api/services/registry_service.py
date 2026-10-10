"""The model registry of the connected Odoo, for the overview (flow_tracer addon)."""

from flow_tracer_api.schemas import ModelDetail, ModelList
from flow_tracer_api.services.addon_calls import ask_addon
from flow_tracer_api.services.errors import ModelLookupError
from flow_tracer_api.services.ports import OdooClient

MODELS_ROUTE = "/flow_tracer/v1/models"
MODEL_ROUTE = "/flow_tracer/v1/model"


class RegistryService:
    def __init__(self, client: OdooClient | None) -> None:
        self._client = client

    async def list_models(self) -> ModelList:
        return await ask_addon(
            self._client,
            MODELS_ROUTE,
            {},
            target="model registry",
            answer_type=ModelList,
            refused=ModelLookupError,
        )

    async def describe_model(self, model: str) -> ModelDetail:
        return await ask_addon(
            self._client,
            MODEL_ROUTE,
            {"model": model},
            target=f"{model} model",
            answer_type=ModelDetail,
            refused=ModelLookupError,
        )
