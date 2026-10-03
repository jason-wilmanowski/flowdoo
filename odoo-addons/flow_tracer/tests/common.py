import uuid

from odoo.tests import TransactionCase

from ..tracing import run_trace


class TraceCase(TransactionCase):
    """Helpers to run and inspect traces in tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin_env = cls.env(user=cls.env.ref("base.user_admin").id)

    def trace(self, model, method, record_ids, *, dry_run=True, context=None, env=None):
        return run_trace(
            env or self.admin_env,
            trace_id=str(uuid.uuid4()),
            model=model,
            method=method,
            record_ids=list(record_ids),
            context=context or {},
            dry_run=dry_run,
        )

    def assertValidTree(self, payload):
        """Rules of schema v0.1.0 that JSON Schema itself cannot express."""
        steps = payload["steps"]
        ids = [s["id"] for s in steps]
        self.assertEqual(len(ids), len(set(ids)), "step ids must be unique")
        seqs = [s["seq"] for s in steps]
        self.assertEqual(seqs, list(range(1, len(steps) + 1)), "seq must be 1..n")
        known = set(ids)
        for step in steps:
            self.assertTrue(step["parent_id"] is None or step["parent_id"] in known)

    @staticmethod
    def find(payload, model, method, module=None):
        return [
            s
            for s in payload["steps"]
            if s["model"] == model
            and s["method"] == method
            and (module is None or s["module"] == module)
        ]

    @staticmethod
    def changes(payload, model, field):
        return [
            c
            for s in payload["steps"]
            for c in s["changes"]
            if c["model"] == model and c["field"] == field
        ]
