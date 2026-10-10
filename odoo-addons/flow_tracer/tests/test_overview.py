from unittest.mock import patch

from odoo.tests import HttpCase, TransactionCase, new_test_user, tagged

from ..overview import describe_model, list_models
from ..tools import flags


@tagged("post_install", "-at_install")
class TestRegistry(TransactionCase):
    """Works with `base` only, so it runs in any test database."""

    def test_lists_every_model_with_relations_and_inheritance(self):
        models = {m["model"]: m for m in list_models(self.env)}

        self.assertEqual(set(models), set(self.env.registry.models))
        partner = models["res.partner"]
        self.assertEqual(partner["module"], "base")
        self.assertIn("base", partner["modules"])
        self.assertEqual(partner["field_count"], len(self.env["res.partner"]._fields))
        self.assertIn(
            {"field": "parent_id", "type": "many2one", "target": "res.partner"},
            partner["relations"],
        )
        # res.users delegates to res.partner (_inherits), it does not extend it
        self.assertEqual(models["res.users"]["delegates"], {"res.partner": "partner_id"})
        self.assertTrue(models["base"]["abstract"])

    def test_modules_are_the_layers_of_the_model_itself(self):
        model = describe_model(self.env, "res.partner")
        mro_modules = [
            getattr(cls, "_module", None)
            for cls in type(self.env["res.partner"]).__mro__
            if getattr(cls, "_module", None)
        ]
        # most derived first, the defining module last, no mixin modules in between
        self.assertEqual(model["modules"][-1], "base")
        self.assertTrue(set(model["modules"]) <= set(mro_modules))
        self.assertNotIn("res.partner", model["parents"])
        self.assertNotIn("base", model["parents"])

    def test_describes_fields(self):
        fields = {f["name"]: f for f in describe_model(self.env, "res.partner")["fields"]}

        self.assertEqual(fields["name"]["type"], "char")
        self.assertEqual(fields["name"]["module"], "base")
        self.assertEqual(fields["parent_id"]["target"], "res.partner")
        self.assertEqual(fields["child_ids"]["inverse"], "parent_id")
        self.assertTrue(fields["display_name"]["compute"])
        self.assertFalse(fields["display_name"]["stored"])
        self.assertIsInstance(fields["type"]["selection"], list)

    def test_unknown_model_raises_key_error(self):
        with self.assertRaises(KeyError):
            describe_model(self.env, "no.such.model")


@tagged("post_install", "-at_install")
class TestOverviewEndpoints(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        keys = cls.env["res.users.apikeys"]
        cls.admin_key = (
            keys.with_user(cls.env.ref("base.user_admin")).sudo()._generate(None, "tests", None)
        )
        user = new_test_user(cls.env, login="overview_user", groups="base.group_user")
        cls.user_key = keys.with_user(user).sudo()._generate(None, "tests", None)

    def setUp(self):
        super().setUp()
        self.startPatcher(patch.object(flags, "config", {flags.CONFIG_KEY: "True"}))

    def _post(self, route, body, key=None):
        return self.url_open(
            route,
            json=body,
            method="POST",
            headers={
                "Authorization": f"bearer {key or self.admin_key}",
                "X-Odoo-Database": self.env.cr.dbname,
            },
        )

    def test_models_and_model(self):
        listing = self._post("/flow_tracer/v1/models", {})
        self.assertEqual(listing.status_code, 200, listing.text)
        self.assertIn("res.partner", {m["model"] for m in listing.json()["models"]})

        detail = self._post("/flow_tracer/v1/model", {"model": "res.partner"})
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(detail.json()["model"], "res.partner")

    def test_unknown_model_is_404_and_bad_input_is_400(self):
        self.assertEqual(self._post("/flow_tracer/v1/model", {"model": "no.such"}).status_code, 404)
        self.assertEqual(self._post("/flow_tracer/v1/model", {"model": ""}).status_code, 400)

    def test_needs_the_settings_group(self):
        response = self._post("/flow_tracer/v1/models", {}, key=self.user_key)
        self.assertEqual(response.status_code, 403)
