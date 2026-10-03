"""HTTP API of the addon, called by the Flowdoo backend.

Routes use Odoo 19's ``json2`` request type with ``auth="bearer"``: the backend sends
the same API key and ``X-Odoo-Database`` header it uses for ``/json/2``. The controller
only checks access and input; recording lives in ``tracing``.
"""

import uuid

from odoo import http, release
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.modules.module import get_manifest
from werkzeug.exceptions import BadRequest, Forbidden, NotFound, ServiceUnavailable

from ..tools import is_enabled
from ..tracing import RECORDER_AVAILABLE, RecorderUnavailable, run_trace

ADMIN_GROUP = "base.group_system"


class FlowTracerController(http.Controller):
    @http.route(
        "/flow_tracer/v1/status",
        type="json2",
        auth="bearer",
        methods=["POST"],
        readonly=True,
        save_session=False,
    )
    def status(self):
        """Tell the backend whether this Odoo can be used for tracing.

        Always answers (also when disabled), so the backend can report *why* tracing is
        not possible instead of a bare 404.
        """
        return {
            "addon_version": get_manifest("flow_tracer")["version"],
            "odoo_version": release.serie,
            "enabled": is_enabled(),
            "is_admin": request.env.user.has_group(ADMIN_GROUP),
            "recorder_available": RECORDER_AVAILABLE,
        }

    @http.route(
        "/flow_tracer/v1/trace",
        type="json2",
        auth="bearer",
        methods=["POST"],
        save_session=False,
    )
    def trace(self, trace_id, model, method, record_ids=(), context=None, dry_run=True):
        """Run ``model.method`` on ``record_ids`` under the recorder; returns the trace.

        A run that raises still answers 200: the exception is part of the trace.
        """
        if not is_enabled():
            raise Forbidden(
                "flow_tracer is disabled: set flow_tracer_enabled = True in the server config"
            )
        if not request.env.user.has_group(ADMIN_GROUP):
            raise Forbidden("Tracing requires the Settings (Administration) group")
        _check_input(trace_id, model, method, record_ids, context, dry_run)
        try:
            return run_trace(
                request.env,
                trace_id=trace_id,
                model=model,
                method=method,
                record_ids=list(record_ids),
                context=dict(context or {}),
                dry_run=dry_run,
            )
        except KeyError as exc:
            raise NotFound(f"The model {model!r} does not exist") from exc
        except AttributeError as exc:
            raise NotFound(str(exc)) from exc
        except AccessError as exc:
            raise Forbidden(str(exc)) from exc
        except RecorderUnavailable as exc:
            raise ServiceUnavailable(str(exc)) from exc


def _check_input(trace_id, model, method, record_ids, context, dry_run):
    try:
        uuid.UUID(str(trace_id))
    except ValueError as exc:
        raise BadRequest("trace_id must be a UUID") from exc
    if not isinstance(model, str) or not model or not isinstance(method, str) or not method:
        raise BadRequest("model and method must be non-empty strings")
    if not isinstance(record_ids, (list, tuple)) or not all(
        isinstance(i, int) and not isinstance(i, bool) and i > 0 for i in record_ids
    ):
        raise BadRequest("record_ids must be a list of positive integers")
    if context is not None and not isinstance(context, dict):
        raise BadRequest("context must be an object")
    if not isinstance(dry_run, bool):
        raise BadRequest("dry_run must be a boolean")
