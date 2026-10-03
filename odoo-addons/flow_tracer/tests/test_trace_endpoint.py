import uuid
from unittest.mock import patch

from odoo.tests import HttpCase, new_test_user, tagged

from ..tools import flags


@tagged("post_install", "-at_install")
class TestTraceEndpoint(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        admin = cls.env.ref("base.user_admin")
        cls.admin_key = cls._api_key(admin)
        cls.user_key = cls._api_key(
            new_test_user(cls.env, login="tracer_user", groups="base.group_user")
        )
        cls.contact = cls.env["res.partner"].create({"name": "Ada", "company_name": "Engines Ltd"})

    @classmethod
    def _api_key(cls, user):
        return cls.env["res.users.apikeys"].with_user(user).sudo()._generate(None, "tests", None)

    def setUp(self):
        super().setUp()
        self.startPatcher(patch.object(flags, "config", {flags.CONFIG_KEY: "True"}))

    def _trace(self, key=None, **body):
        payload = {
            "trace_id": str(uuid.uuid4()),
            "model": "res.partner",
            "method": "create_company",
            "record_ids": self.contact.ids,
            **body,
        }
        return self.url_open(
            "/flow_tracer/v1/trace",
            json=payload,
            method="POST",
            headers={
                "Authorization": f"bearer {key or self.admin_key}",
                "X-Odoo-Database": self.env.cr.dbname,
            },
        )

    def test_records_a_dry_run(self):
        response = self._trace()

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["entrypoint"]["method"], "create_company")
        self.assertTrue(body["dry_run"])
        self.assertIsNone(body["error"])
        self.assertTrue(body["steps"])
        self.env.invalidate_all()
        self.assertFalse(self.contact.parent_id)

    def test_disabled_server_refuses(self):
        with patch.object(flags, "config", {}):
            response = self._trace()

        self.assertEqual(response.status_code, 403)
        self.assertIn("flow_tracer is disabled", response.text)

    def test_requires_admin_group(self):
        response = self._trace(key=self.user_key)

        self.assertEqual(response.status_code, 403)
        self.assertIn("Settings (Administration)", response.text)

    def test_rejects_invalid_input(self):
        cases = [
            {"trace_id": "not-a-uuid"},
            {"record_ids": [0]},
            {"record_ids": "1"},
            {"context": []},
            {"dry_run": "yes"},
            {"model": ""},
        ]
        for body in cases:
            with self.subTest(body=body):
                self.assertEqual(self._trace(**body).status_code, 400)

    def test_unknown_model_and_private_method(self):
        self.assertEqual(self._trace(model="no.such.model").status_code, 404)
        self.assertEqual(self._trace(method="no_such_method").status_code, 404)
        self.assertEqual(self._trace(method="_create_contact_parent_company").status_code, 403)

    def test_status_reports_recorder_availability(self):
        response = self.url_open(
            "/flow_tracer/v1/status",
            json={},
            method="POST",
            headers={
                "Authorization": f"bearer {self.admin_key}",
                "X-Odoo-Database": self.env.cr.dbname,
            },
        )

        self.assertTrue(response.json()["recorder_available"])
