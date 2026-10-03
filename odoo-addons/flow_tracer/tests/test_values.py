import datetime

from odoo.tests import TransactionCase, tagged

from ..tracing import values


@tagged("post_install", "-at_install")
class TestValues(TransactionCase):
    def setUp(self):
        super().setUp()
        self.fields = self.env["res.partner"]._fields

    def test_field_values_follow_the_schema(self):
        f = self.fields
        cases = [
            (f["active"], False, False),
            (f["active"], True, True),
            (f["name"], False, None),
            (f["name"], None, None),
            (f["name"], "Ada", "Ada"),
            (f["parent_id"], 7, [7]),
            (f["category_id"], (3, 4), [3, 4]),
            (f["write_date"], datetime.datetime(2026, 10, 3, 12, 0), "2026-10-03 12:00:00"),
            (f["image_1920"], b"\x89PNG....", "<binary 8 bytes>"),
            (f["partner_latitude"], 1.5, 1.5),
        ]
        for field, raw, expected in cases:
            with self.subTest(field=field.name, raw=raw):
                self.assertEqual(values.field_value(field, raw), expected)

    def test_new_ids_are_left_out(self):
        new = self.env["res.partner"].new({"name": "draft"})
        mixed = self.env["res.partner"].browse([1, *new._ids])

        self.assertEqual(values.ids_of(mixed), [1])
        self.assertIsNone(values.field_value(self.fields["parent_id"], new.id))

    def test_texts_are_truncated_to_the_schema_limit(self):
        long_text = "x" * 5000

        self.assertEqual(
            len(values.field_value(self.fields["comment"], long_text)), values.SUMMARY_MAX
        )
        self.assertLessEqual(len(values.summary(list(range(10_000)))), values.SUMMARY_MAX)
        self.assertEqual(len(values.error_of(ValueError(long_text))["message"]), values.MESSAGE_MAX)

    def test_peek_never_loads_from_the_database(self):
        partner = self.env["res.partner"].create({"name": "cached"})
        self.env.invalidate_all()

        found = values.peek(self.env, "res.partner", partner.ids, ["name"])

        self.assertIs(found[(partner.id, "name")], values.MISSING)

    def test_read_columns_reads_the_table_without_flushing(self):
        partner = self.env["res.partner"].create({"name": "stored"})
        self.env.flush_all()
        partner.name = "pending"  # only in the ORM cache, not flushed

        found = values.read_columns(self.env, "res.partner", partner.ids, ["name", "category_id"])

        self.assertEqual(found, {(partner.id, "name"): "stored"})  # x2many has no column
