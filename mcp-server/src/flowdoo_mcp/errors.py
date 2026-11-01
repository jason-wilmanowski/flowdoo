from collections.abc import Iterator
from contextlib import contextmanager

from flow_tracer_api.integrations.odoo.errors import OdooClientError
from mcp.server.mcpserver.exceptions import ToolError


@contextmanager
def odoo_errors_as_tool_errors() -> Iterator[None]:
    """Show Odoo's error messages to the model; they never contain credentials.

    Any other exception counts as a crash, and the model would only see a generic error.
    """
    try:
        yield
    except OdooClientError as exc:
        raise ToolError(exc.message) from exc
