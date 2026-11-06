from odoo.tests import TransactionCase, tagged

from ..tools.introspect import describe_field, describe_method


@tagged("post_install", "-at_install")
class TestDescribeMethod(TransactionCase):
    def test_lists_every_implementation_most_derived_first(self):
        answer = describe_method(self.env, "res.partner", "write")

        implementations = answer["implementations"]
        self.assertGreater(len(implementations), 1)
        self.assertEqual(
            [item["position"] for item in implementations], list(range(len(implementations)))
        )
        self.assertTrue(implementations[0]["calls_super"])
        self.assertFalse(implementations[-1]["calls_super"])
        self.assertIn("vals", answer["signature"])
        self.assertFalse(answer["private"])

    def test_gives_file_and_line_of_addon_code(self):
        first = describe_method(self.env, "res.partner", "write")["implementations"][0]

        self.assertTrue(first["file"].endswith(".py"))
        self.assertFalse(first["file"].startswith("/"), first["file"])
        self.assertGreater(first["line"], 0)

    def test_private_methods_can_be_described(self):
        answer = describe_method(self.env, "res.partner", "_compute_display_name")

        self.assertTrue(answer["private"])
        self.assertTrue(answer["implementations"])

    def test_an_unknown_method_raises(self):
        with self.assertRaises(AttributeError):
            describe_method(self.env, "res.partner", "no_such_method")


@tagged("post_install", "-at_install")
class TestDescribeField(TransactionCase):
    def test_a_computed_field_shows_its_method_and_dependencies(self):
        answer = describe_field(self.env, "res.partner", "complete_name")

        self.assertTrue(answer["stored"])
        self.assertEqual(answer["compute"], "_compute_complete_name")
        self.assertIn("name", answer["depends_on"])

    def test_a_field_shows_the_stored_fields_it_recomputes(self):
        answer = describe_field(self.env, "res.partner", "name")

        self.assertIsNone(answer["compute"])
        self.assertIn("res.partner.complete_name", answer["recomputes"])

    def test_an_unknown_field_raises(self):
        with self.assertRaises(AttributeError):
            describe_field(self.env, "res.partner", "no_such_field")
