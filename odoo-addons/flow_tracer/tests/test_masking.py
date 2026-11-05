import uuid
from unittest.mock import patch

from odoo.tests import TransactionCase, tagged
from odoo.tools import config

from ..tracing import masking, values
from ..tracing.runner import run_trace


def extra_parts(parts):
    """Sets flow_tracer_masked_fields for the duration of a test."""
    return patch.dict(config.options, {masking.CONFIG_KEY: parts})


@tagged("post_install", "-at_install")
class TestMaskingRules(TransactionCase):
    def test_default_parts_cover_credentials(self):
        for name in ("password", "new_password", "access_token", "API_KEY", "totp_secret"):
            self.assertTrue(masking.is_sensitive(name), name)
        for name in ("name", "state", "partner_id", "amount_total"):
            self.assertFalse(masking.is_sensitive(name), name)

    def test_configured_parts_are_added(self):
        self.assertFalse(masking.is_sensitive("email"))
        with extra_parts(" Email , phone,,"):
            self.assertTrue(masking.is_sensitive("email_from"))
            self.assertTrue(masking.is_sensitive("mobile_phone"))
            self.assertIn("email", masking.masked_fields())
            self.assertIn("password", masking.masked_fields())

    def test_nested_values_are_masked_without_changing_the_original(self):
        original = {
            "password": "s3cret",
            "lines": [(0, 0, {"api_key": "k", "name": "A"})],
            "token": None,
        }

        result = masking.masked(original)

        self.assertEqual(result["password"], masking.MASKED)
        self.assertEqual(result["lines"][0][2], {"api_key": masking.MASKED, "name": "A"})
        self.assertIsNone(result["token"])
        self.assertEqual(original["password"], "s3cret")

    def test_long_lists_stay_complete(self):
        value = [{"token": "t"}] * 3 + list(range(40))

        result = masking.masked(value)

        self.assertEqual(len(result), 43)
        self.assertEqual(result[0], {"token": masking.MASKED})

    def test_an_empty_field_stays_empty(self):
        self.assertIsNone(masking.masked_field_value("password", None))
        self.assertEqual(masking.masked_field_value("password", "x"), masking.MASKED)
        self.assertEqual(masking.masked_field_value("name", "x"), "x")

    def test_a_sensitive_parameter_is_masked_as_a_whole(self):
        self.assertEqual(values.argument_summary("password", "s3cret"), "password='***'")
        self.assertEqual(values.argument_summary("password", None), "password=None")
        self.assertEqual(values.argument_summary("name", "Ada"), "name='Ada'")

    def test_summaries_hide_sensitive_keys(self):
        summary = values.summary({"name": "Ada", "password": "s3cret"})

        self.assertIn("Ada", summary)
        self.assertNotIn("s3cret", summary)

    def test_database_details_are_hidden(self):
        error = Exception(
            'violates "x"\nDETAIL:  Failing row contains (1, secret@example.com, 2).\n'
        )

        message = values.error_of(error)["message"]

        self.assertIn('violates "x"', message)
        self.assertNotIn("secret@example.com", message)


@tagged("post_install", "-at_install")
class TestMaskingInTraces(TransactionCase):
    def _trace(self, vals_list, **options):
        return run_trace(
            self.env,
            trace_id=str(uuid.uuid4()),
            model="res.partner",
            method="create",
            record_ids=[],
            context=options.get("context", {}),
            kwargs={"vals_list": vals_list},
        )

    def test_a_masked_field_leaves_no_value_in_the_trace(self):
        address = "secret.person@example.com"
        with extra_parts("email"):
            payload = self._trace([{"name": "Ada", "email": address}], context={"api_token": "t0k"})

        self.assertNotIn(address, str(payload))
        self.assertNotIn("t0k", str(payload))
        self.assertIn("email", payload["masked_fields"])
        self.assertEqual(payload["entrypoint"]["kwargs"]["vals_list"][0]["email"], masking.MASKED)
        self.assertEqual(payload["entrypoint"]["context"]["api_token"], masking.MASKED)
        changes = [c for s in payload["steps"] for c in s["changes"] if c["field"] == "email"]
        self.assertTrue(changes)
        self.assertEqual({c["new"] for c in changes}, {masking.MASKED})

    def test_unmasked_fields_keep_their_values(self):
        payload = self._trace([{"name": "Ada Lovelace"}])

        changes = [c for s in payload["steps"] for c in s["changes"] if c["field"] == "name"]
        self.assertEqual({c["new"] for c in changes}, {"Ada Lovelace"})

    def test_the_run_still_uses_the_real_value(self):
        with extra_parts("email"):
            payload = self._trace([{"name": "Ada", "email": "real@example.com"}])

        self.assertIsNone(payload["error"])

    def test_a_database_error_shows_no_row(self):
        payload = self._trace([{"email": "row@example.com"}])

        self.assertIn("res_partner_check_name", payload["error"]["message"])
        self.assertNotIn("row@example.com", payload["error"]["message"])
        failed = [step["error"]["message"] for step in payload["steps"] if step["error"]]
        self.assertTrue(failed)
        self.assertNotIn("row@example.com", str(failed))
