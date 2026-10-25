from typing import Any

from flowdoo_mcp.endpoints import Endpoint
from flowdoo_mcp.server import call_api, mcp


@mcp.tool()
async def odoo_status() -> dict[str, Any]:
    """Check whether Flowdoo can reach the user's Odoo and is ready to trace.

    Call this first, before any other Flowdoo tool. `ok` is true only if everything works:
    Odoo reachable, version 19.0, API key valid, the flow_tracer addon installed and
    switched on, the recorder available and the key's user an administrator. `problems`
    says what blocks tracing, `warnings` what could not be verified or should be known
    (e.g. a database that is not neutralised, so mails and crons stay active).
    """
    result: dict[str, Any] = await call_api("GET", Endpoint.ODOO_STATUS)
    return result
