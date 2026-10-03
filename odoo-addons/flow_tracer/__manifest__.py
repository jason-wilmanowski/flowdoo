{
    "name": "Flowdoo Flow Tracer",
    "summary": "Record Odoo workflows step by step for the Flowdoo tracer (development only)",
    "description": """
Flowdoo Flow Tracer
===================

Recorder side of Flowdoo: runs an entrypoint such as sale.order.action_confirm, records
the calls and field changes across models and modules and returns the trace to the
Flowdoo backend.

Development databases only. All endpoints are disabled unless the server
configuration contains ``flow_tracer_enabled = True``; tracing additionally requires
the Settings (Administration) group.
""",
    "version": "19.0.0.1.0",
    "category": "Hidden/Tools",
    "author": "Flowdoo",
    "website": "https://github.com/jason-wilmanowski/flowdoo",
    "depends": ["base"],
    "data": [],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
