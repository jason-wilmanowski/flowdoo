"""Server-side switch for the addon (CLAUDE.md section 6: off unless explicitly enabled).

Set ``flow_tracer_enabled = True`` in the [options] section of the Odoo configuration
file. Odoo 19 keeps unknown options as raw strings (``tools.config._load_file_options``)
and logs "unknown option 'flow_tracer_enabled' ... stored as-is" at startup; that
warning is expected.
"""

from odoo.tools import config

CONFIG_KEY = "flow_tracer_enabled"
_TRUE_VALUES = {"1", "true", "yes", "on"}


def is_enabled():
    value = config.get(CONFIG_KEY)
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in _TRUE_VALUES
