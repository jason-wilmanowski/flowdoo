from enum import StrEnum


class Endpoint(StrEnum):
    ODOO_STATUS = "/odoo/status"
    GET_ENTRYPOINT = "/odoo/entrypoints/{model}/{method}"
    LIST_MODELS = "/odoo/models"
    GET_MODEL = "/odoo/models/{model}"
    TRACES = "/traces"  # POST starts a trace, GET lists them
    GET_TRACE = "/traces/{trace_id}"
