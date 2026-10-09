import contextlib
import sys
from unittest.mock import patch

from odoo.tests import tagged

from ..tracing import monitor
from ..tracing.runner import SCHEMA_VERSION
from .common import TraceCase


@tagged("post_install", "-at_install")
class TestRecorder(TraceCase):
    """Reference flow available with `base` only: res.partner.create_company creates the
    parent company (create) and links the contact to it (write + constraint)."""

    def setUp(self):
        super().setUp()
        self.contact = self.admin_env["res.partner"].create(
            {"name": "Ada Lovelace", "company_name": "Analytical Engines Ltd"}
        )

    def test_payload_shape(self):
        payload = self.trace("res.partner", "create_company", self.contact.ids)

        self.assertEqual(payload["schema_version"], SCHEMA_VERSION)
        self.assertEqual(payload["odoo_version"], "19.0")
        self.assertTrue(payload["dry_run"])
        self.assertIsNone(payload["error"])
        self.assertEqual(
            payload["entrypoint"],
            {
                "model": "res.partner",
                "method": "create_company",
                "record_ids": self.contact.ids,
                "context": {},
                "kwargs": {},
            },
        )
        self.assertValidTree(payload)

    def test_entrypoint_and_override_chain(self):
        payload = self.trace("res.partner", "create_company", self.contact.ids)

        [entry] = self.find(payload, "res.partner", "create_company")
        self.assertEqual(entry["seq"], 1)
        self.assertIsNone(entry["parent_id"])
        self.assertEqual(entry["module"], "base")
        self.assertEqual(entry["record_ids"], self.contact.ids)
        self.assertEqual(entry["return_summary"], "True")

        # The write override chain: every addon layer calls super(), down to BaseModel.write
        # (module None). How many layers there are depends on the installed modules.
        chain = []
        parent_id = entry["id"]
        while True:
            layer = [
                s for s in self.find(payload, "res.partner", "write") if s["parent_id"] == parent_id
            ]
            if not layer:
                break
            chain.append(layer[0])
            parent_id = layer[0]["id"]
        self.assertIn("base", [s["module"] for s in chain])
        self.assertIsNone(chain[-1]["module"])
        self.assertFalse(chain[-1]["calls_super"])
        for upper, lower in zip(chain, chain[1:], strict=False):
            self.assertTrue(upper["calls_super"], upper["module"])
            self.assertEqual(upper["kind"], "orm_write")
            self.assertGreater(lower["mro_position"], upper["mro_position"])

    def test_field_changes_and_new_records(self):
        payload = self.trace("res.partner", "create_company", self.contact.ids)

        [parent_change] = [
            c
            for c in self.changes(payload, "res.partner", "parent_id")
            if c["record_id"] == self.contact.id
        ]
        self.assertIsNone(parent_change["old"])
        [company_id] = parent_change["new"]
        created = [
            c
            for c in self.changes(payload, "res.partner", "is_company")
            if c["record_id"] == company_id
        ]
        self.assertEqual(created[0]["old"], None)
        self.assertIs(created[0]["new"], True)
        self.assertTrue(self.find(payload, "res.partner", "_check_parent_id"))
        self.assertEqual(
            self.find(payload, "res.partner", "_check_parent_id")[0]["kind"], "constraint"
        )

    def test_dry_run_leaves_no_data(self):
        partners_before = self.env["res.partner"].search_count([])

        self.trace("res.partner", "create_company", self.contact.ids)

        self.env.invalidate_all()
        self.assertFalse(self.contact.parent_id)
        self.assertEqual(self.env["res.partner"].search_count([]), partners_before)

    def test_non_dry_run_keeps_the_changes(self):
        payload = self.trace("res.partner", "create_company", self.contact.ids, dry_run=False)

        self.assertFalse(payload["dry_run"])
        self.env.invalidate_all()
        self.assertEqual(self.contact.parent_id.name, "Analytical Engines Ltd")

    def test_exception_is_part_of_the_trace_and_rolled_back(self):
        def write_then_fail(records):
            records.write({"name": "renamed"})
            raise ValueError("boom")

        with patch.object(type(self.contact), "create_company", write_then_fail):
            payload = self.trace("res.partner", "create_company", self.contact.ids, dry_run=False)

        self.assertEqual(payload["error"], {"type": "builtins.ValueError", "message": "boom"})
        self.assertTrue(self.changes(payload, "res.partner", "name"))
        self.env.invalidate_all()
        self.assertEqual(self.contact.name, "Ada Lovelace")

    def test_commit_is_refused_during_dry_run(self):
        def committing(records):
            records.env.cr.commit()

        with patch.object(type(self.contact), "create_company", committing):
            payload = self.trace("res.partner", "create_company", self.contact.ids)

        self.assertEqual(
            payload["error"]["type"], "odoo.addons.flow_tracer.tracing.runner.DryRunCommitError"
        )

    def test_swallowed_commit_is_reported(self):
        # Odoo code with a broad except (e.g. mail.mail.send(auto_commit=True)) catches the
        # refusal and goes on; the trace must still say that a commit was blocked.
        def committing_quietly(records):
            with contextlib.suppress(Exception):  # what the code under trace does
                records.env.cr.commit()
            return True

        with patch.object(type(self.contact), "create_company", committing_quietly):
            payload = self.trace("res.partner", "create_company", self.contact.ids)

        self.assertEqual(payload["error"]["type"], "flow_tracer.CommitRefused")
        self.assertIn("1 time", payload["error"]["message"])

    def test_monitoring_is_released_after_each_trace(self):
        self.trace("res.partner", "create_company", self.contact.ids)

        self.assertFalse(monitor.MONITOR.active)
        self.assertIsNone(sys.monitoring.get_tool(sys.monitoring.PROFILER_ID))

    def test_busy_tool_id_is_reported(self):
        sys.monitoring.use_tool_id(sys.monitoring.PROFILER_ID, "someone else")
        try:
            with self.assertRaisesRegex(monitor.RecorderUnavailable, "in use by 'someone else'"):
                self.trace("res.partner", "create_company", self.contact.ids)
        finally:
            sys.monitoring.free_tool_id(sys.monitoring.PROFILER_ID)

    def test_step_limit_truncates_with_explicit_error(self):
        with patch("odoo.addons.flow_tracer.tracing.session.MAX_STEPS", 3):
            payload = self.trace("res.partner", "create_company", self.contact.ids)

        self.assertEqual(len(payload["steps"]), 3)
        self.assertEqual(payload["error"]["type"], "flow_tracer.TraceTruncated")
        self.assertValidTree(payload)

    def test_private_and_unknown_methods_are_refused(self):
        from odoo.exceptions import AccessError

        with self.assertRaises(AccessError):
            self.trace("res.partner", "_create_contact_parent_company", self.contact.ids)
        with self.assertRaises(AttributeError):
            self.trace("res.partner", "no_such_method", self.contact.ids)
        with self.assertRaises(KeyError):
            self.trace("no.such.model", "create_company", self.contact.ids)

    def test_entrypoint_echoes_the_kwargs_as_sent(self):
        # Odoo methods may change the values they get (res.partner.create adds defaults to
        # vals_list in some setups). The trace must report the call as it was requested,
        # otherwise the backend rejects it as an answer for a different run.
        partner_class = type(self.admin_env["res.partner"])
        original_write = partner_class.write

        def write_that_changes_vals(self, vals):
            vals["comment"] = "added by Odoo"
            return original_write(self, vals)

        sent = {"vals": {"name": "Ada King"}}
        with patch.object(partner_class, "write", write_that_changes_vals):
            payload = self.trace("res.partner", "write", self.contact.ids, kwargs=sent)

        self.assertIsNone(payload["error"])
        self.assertEqual(payload["entrypoint"]["kwargs"], {"vals": {"name": "Ada King"}})
        self.assertEqual(sent, {"vals": {"name": "Ada King"}})
