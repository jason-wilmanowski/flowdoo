from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp.server import MCPServer

from flow_tracer_api.integrations.odoo.client import OdooJson2Client
from flowdoo_mcp.config import get_settings
from flow_tracer_api.integrations.odoo.gateway import FlowTracerGateway


@dataclass
class AppContext:
    client: OdooJson2Client
    gateway: FlowTracerGateway


@asynccontextmanager
async def app_lifespan(server: MCPServer) -> AsyncIterator[AppContext]:
    settings = get_settings()
    async with OdooJson2Client(
        base_url=settings.odoo_url,
        database=settings.odoo_db,
        api_key=settings.odoo_api_key,
    ) as client:
        gateway = FlowTracerGateway(client=client, timeout_seconds=settings.flowdoo_timeout)
        yield AppContext(client=client, gateway=gateway)


mcp = MCPServer("flowdoo", lifespan=app_lifespan)