"""Extra routes for the MCP server, guarded exactly like the routes of flow_tracer."""

from odoo import http
from odoo.addons.flow_tracer.controllers.main import _check_access, _check_input, _entrypoint_errors
from odoo.addons.flow_tracer.tracing import run_trace
from odoo.http import request

from ..tools.introspect import describe_field, describe_method
from ..tools.raw_sql import recording


class FlowTracerMcpController(http.Controller):
    @http.route(
        "/flow_tracer_mcp/v1/method",
        type="json2",
        auth="bearer",
        methods=["POST"],
        readonly=True,
        save_session=False,
    )
    def method(self, model, method):
        _check_access()
        with _entrypoint_errors(model):
            return describe_method(request.env, model, method)

    @http.route(
        "/flow_tracer_mcp/v1/field",
        type="json2",
        auth="bearer",
        methods=["POST"],
        readonly=True,
        save_session=False,
    )
    def field(self, model, field):
        _check_access()
        with _entrypoint_errors(model):
            return describe_field(request.env, model, field)

    @http.route(
        "/flow_tracer_mcp/v1/trace",
        type="json2",
        auth="bearer",
        methods=["POST"],
        save_session=False,
    )
    def trace(self, trace_id, model, method, record_ids=(), context=None, kwargs=None):
        """The trace of flow_tracer, always a dry run, plus the direct SQL writes of the run."""
        _check_access()
        _check_input(trace_id, model, method, record_ids, context, kwargs, True)
        with _entrypoint_errors(model), recording() as writes:
            trace = run_trace(
                request.env,
                trace_id=trace_id,
                model=model,
                method=method,
                record_ids=list(record_ids),
                context=dict(context or {}),
                kwargs=dict(kwargs or {}),
                dry_run=True,
            )
        return {"trace": trace, "raw_sql_writes": writes}
