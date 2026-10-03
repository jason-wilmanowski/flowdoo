from unittest.mock import patch

from odoo.tests import HttpCase, new_test_user, tagged

from ..tools import flags


@tagged("post_install", "-at_install")
class TestStatusEndpoint(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin_key = cls._api_key(cls.env.ref("base.user_admin"))
        cls.user = new_test_user(cls.env, login="flow_tracer_user", groups="base.group_user")
        cls.user_key = cls._api_key(cls.user)

    @classmethod
    def _api_key(cls, user):
        return (
            cls.env["res.users.apikeys"]
            .with_user(user)
            .sudo()
            ._generate(None, "flow_tracer tests", None)
        )

    def _status(self, key):
        return self.url_open(
            "/flow_tracer/v1/status",
            json={},
            method="POST",
            headers={"Authorization": f"bearer {key}", "X-Odoo-Database": self.env.cr.dbname},
        )

    def test_disabled_by_default(self):
        with patch.object(flags, "config", {}):
            response = self._status(self.admin_key)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["enabled"])
        self.assertEqual(body["odoo_version"], "19.0")
        self.assertEqual(body["addon_version"], "19.0.0.3.0")

    def test_enabled_by_server_config(self):
        for raw in ("True", "1", "yes", True):
            with self.subTest(raw=raw), patch.object(flags, "config", {flags.CONFIG_KEY: raw}):
                self.assertTrue(self._status(self.admin_key).json()["enabled"])
        for raw in ("False", "0", "", None):
            with self.subTest(raw=raw), patch.object(flags, "config", {flags.CONFIG_KEY: raw}):
                self.assertFalse(self._status(self.admin_key).json()["enabled"])

    def test_reports_admin_rights(self):
        self.assertTrue(self._status(self.admin_key).json()["is_admin"])
        self.assertFalse(self._status(self.user_key).json()["is_admin"])

    def test_requires_valid_api_key(self):
        response = self._status("not-a-key")

        self.assertEqual(response.status_code, 401)
