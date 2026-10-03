"""HTTP API of the addon, called by the Flowdoo backend.

Routes use Odoo 19's ``json2`` request type with ``auth="bearer"``: the backend sends
the same API key and ``X-Odoo-Database`` header it uses for ``/json/2``.
"""

from odoo import http, release
from odoo.http import request
from odoo.modules.module import get_manifest

from ..tools import is_enabled

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
        }
