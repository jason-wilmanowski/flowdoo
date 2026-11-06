import uuid
from unittest.mock import patch

from odoo.addons.flow_tracer.tools import flags
from odoo.tests import HttpCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestRoutes(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin_key = cls._api_key(cls.env.ref("base.user_admin"))
        cls.user_key = cls._api_key(
            new_test_user(cls.env, login="mcp_user", groups="base.group_user")
        )
        cls.contact = cls.env["res.partner"].create({"name": "Ada", "company_name": "Engines Ltd"})

    @classmethod
    def _api_key(cls, user):
        return cls.env["res.users.apikeys"].with_user(user).sudo()._generate(None, "tests", None)

    def setUp(self):
        super().setUp()
        self.startPatcher(patch.object(flags, "config", {flags.CONFIG_KEY: "True"}))

    def _post(self, route, body, key=None):
        return self.url_open(
            f"/flow_tracer_mcp/v1/{route}",
            json=body,
            method="POST",
            headers={
                "Authorization": f"bearer {key or self.admin_key}",
                "X-Odoo-Database": self.env.cr.dbname,
            },
        )

    def test_method_route(self):
        answer = self._post("method", {"model": "res.partner", "method": "create_company"})

        self.assertEqual(answer.status_code, 200)
        self.assertTrue(answer.json()["implementations"])

    def test_field_route(self):
        answer = self._post("field", {"model": "res.partner", "field": "complete_name"})

        self.assertEqual(answer.status_code, 200)
        self.assertEqual(answer.json()["compute"], "_compute_complete_name")

    def test_unknown_names_are_not_found(self):
        self.assertEqual(
            self._post("method", {"model": "res.partner", "method": "nope"}).status_code, 404
        )
        self.assertEqual(self._post("field", {"model": "no.model", "field": "x"}).status_code, 404)

    def test_trace_route_is_a_dry_run_with_direct_sql(self):
        body = {
            "trace_id": str(uuid.uuid4()),
            "model": "res.partner",
            "method": "create_company",
            "record_ids": self.contact.ids,
        }

        answer = self._post("trace", body)

        self.assertEqual(answer.status_code, 200)
        payload = answer.json()
        self.assertTrue(payload["trace"]["dry_run"])
        self.assertIsInstance(payload["raw_sql_writes"], list)
        self.contact.invalidate_recordset()
        self.assertFalse(self.contact.parent_id)

    def test_routes_need_an_administrator(self):
        for route, body in (
            ("method", {"model": "res.partner", "method": "write"}),
            ("field", {"model": "res.partner", "field": "name"}),
        ):
            self.assertEqual(self._post(route, body, key=self.user_key).status_code, 403, route)

    def test_routes_are_off_without_the_switch(self):
        with patch.object(flags, "config", {}):
            answer = self._post("method", {"model": "res.partner", "method": "write"})

        self.assertEqual(answer.status_code, 403)
