"""Print the backend's OpenAPI document as JSON.

Builds the FastAPI app with dummy settings: no server, no database, no Odoo connection is
needed (the engine is only created in the app's lifespan, which does not run here).
Run through the backend's environment: uv run --project ../backend python scripts/dump_openapi.py
"""

import json
import sys

from pydantic import SecretStr

from flow_tracer_api.core.config import Settings
from flow_tracer_api.main import create_app

settings = Settings(
    database_url=SecretStr("postgresql+asyncpg://openapi:unused@localhost/unused"),
    frontend_url="http://localhost:5173",
    _env_file=None,
)
json.dump(create_app(settings).openapi(), sys.stdout, indent=2, sort_keys=True)
sys.stdout.write("\n")
