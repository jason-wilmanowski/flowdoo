from odoo.tests import BaseCase, tagged

from ..tracing import InvalidEntrypoint, describe_entrypoint
from ..tracing.signature import merged_parameters, summary_of
from .common import TraceCase


@tagged("post_install", "-at_install")
class TestEntrypoints(TraceCase):
    """Entrypoints with keyword arguments and model-level methods (like JSON-2)."""

    def setUp(self):
        super().setUp()
        self.contact = self.admin_env["res.partner"].create({"name": "Ada Lovelace"})

    def test_kwargs_are_passed_and_recorded(self):
        payload = self.trace(
            "res.partner", "write", self.contact.ids, kwargs={"vals": {"name": "Countess Ada"}}
        )

        self.assertIsNone(payload["error"])
        self.assertEqual(payload["entrypoint"]["kwargs"], {"vals": {"name": "Countess Ada"}})
        [change] = [
            c
            for c in self.changes(payload, "res.partner", "name")
            if c["record_id"] == self.contact.id
        ]
        self.assertEqual((change["old"], change["new"]), ("Ada Lovelace", "Countess Ada"))
        self.env.invalidate_all()
        self.assertEqual(self.contact.name, "Ada Lovelace")  # dry run

    def test_model_level_method_runs_without_ids(self):
        before = self.env["res.partner"].search_count([])

        payload = self.trace("res.partner", "name_create", [], kwargs={"name": "Grace Hopper"})

        self.assertIsNone(payload["error"])
        self.assertEqual(payload["entrypoint"]["record_ids"], [])
        [entry] = self.find(payload, "res.partner", "name_create")
        self.assertEqual(entry["record_ids"], [])
        self.assertTrue(self.find(payload, "res.partner", "create"))
        self.assertEqual(self.env["res.partner"].search_count([]), before)

    def test_invalid_calls_are_refused_before_running(self):
        cases = [
            ("name_create", self.contact.ids, {"name": "x"}, "model-level method"),
            ("write", self.contact.ids, {}, "missing a required argument: 'vals'"),
            (
                "write",
                self.contact.ids,
                {"vals": {}, "nope": 1},
                "unexpected keyword argument 'nope'",
            ),
        ]
        for method, ids, kwargs, message in cases:
            with (
                self.subTest(method=method, kwargs=kwargs),
                self.assertRaisesRegex(InvalidEntrypoint, message),
            ):
                self.trace("res.partner", method, ids, kwargs=kwargs)

    def test_describe_record_method(self):
        description = describe_entrypoint(self.admin_env, "res.partner", "write")

        self.assertEqual(description["model"], "res.partner")
        self.assertFalse(description["model_level"])
        self.assertTrue(description["module"])
        [vals] = description["parameters"]
        self.assertEqual(vals["name"], "vals")
        self.assertTrue(vals["required"])
        self.assertIsNone(vals["default"])

    def test_describe_model_level_method_with_doc(self):
        description = describe_entrypoint(self.admin_env, "res.partner", "name_create")

        self.assertTrue(description["model_level"])
        self.assertEqual([p["name"] for p in description["parameters"]], ["name"])
        self.assertTrue(description["summary"])

    def test_describe_reports_optional_parameters_with_default(self):
        description = describe_entrypoint(self.admin_env, "res.partner", "address_get")

        [adr_pref] = description["parameters"]
        self.assertFalse(adr_pref["required"])
        self.assertEqual(adr_pref["default"], "None")  # a default of None, not "no default"


@tagged("post_install", "-at_install")
class TestSignatureMerging(BaseCase):
    """Overrides that only pass **kwargs on must not hide the arguments further down."""

    def test_arguments_of_the_next_implementation_are_reachable(self):
        def sale_override(self, **kwargs):
            pass

        def mail_thread(self, *, body="", subject=None, partner_ids=None, **kwargs):
            pass

        def core(self, body, *, notify=True):
            pass

        merged = merged_parameters([sale_override, mail_thread, core])

        self.assertEqual(
            [(p["name"], p["required"], p["default"]) for p in merged],
            [
                ("body", False, "''"),
                ("subject", False, "None"),
                ("partner_ids", False, "None"),
                ("notify", False, "True"),
            ],
        )

    def test_collecting_stops_at_an_implementation_without_kwargs(self):
        def override(self, vals, **kwargs):
            pass

        def base(self, vals, check=False):
            pass

        def never_reached(self, vals, hidden=None):
            pass

        merged = merged_parameters([override, base, never_reached])

        self.assertEqual([p["name"] for p in merged], ["vals", "check"])
        self.assertTrue(merged[0]["required"])

    def test_open_kwargs_are_reported_where_the_chain_ends(self):
        def only(self, record_id, **options):
            pass

        merged = merged_parameters([only])

        self.assertEqual(
            [(p["name"], p["kind"]) for p in merged],
            [
                ("record_id", "positional_or_keyword"),
                ("options", "var_keyword"),
            ],
        )

    def test_summary_is_the_first_paragraph(self):
        doc = "Sends the selected emails immediately, ignoring their current\nstate.\n\nDetails."
        self.assertEqual(
            summary_of(doc), "Sends the selected emails immediately, ignoring their current state."
        )
        self.assertIsNone(summary_of("   "))
