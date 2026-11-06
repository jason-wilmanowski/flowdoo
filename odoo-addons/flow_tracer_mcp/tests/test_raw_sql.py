from odoo.sql_db import Cursor
from odoo.tests import TransactionCase, tagged

from ..tools import raw_sql


@tagged("post_install", "-at_install")
class TestRawSqlRecording(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner = self.env["res.partner"].create({"name": "Ada"})
        self.env.flush_all()

    def test_a_direct_write_is_recorded_with_its_code_but_no_values(self):
        with raw_sql.recording() as writes:
            self.env.cr.execute(
                "UPDATE res_partner SET comment = %s WHERE id = %s",
                ["secret note", self.partner.id],
            )

        self.assertEqual(len(writes), 1)
        write = writes[0]
        self.assertEqual(
            (write["operation"], write["table"], write["columns"]),
            ("UPDATE", "res_partner", ["comment"]),
        )
        self.assertEqual(
            write["method"], "test_a_direct_write_is_recorded_with_its_code_but_no_values"
        )
        self.assertTrue(write["file"].endswith("tests/test_raw_sql.py"), write["file"])
        self.assertNotIn("secret note", str(writes))

    def test_writes_of_the_orm_are_left_out(self):
        with raw_sql.recording() as writes:
            self.partner.write({"comment": "through the ORM"})
            self.env.flush_all()

        self.assertEqual(writes, [])

    def test_reads_are_left_out(self):
        with raw_sql.recording() as writes:
            self.env.cr.execute("SELECT id FROM res_partner WHERE id = %s", [self.partner.id])

        self.assertEqual(writes, [])

    def test_the_cursor_is_restored_afterwards(self):
        original = Cursor.execute

        with raw_sql.recording():
            self.assertIsNot(Cursor.execute, original)

        self.assertIs(Cursor.execute, original)

    def test_the_cursor_is_restored_after_an_error(self):
        original = Cursor.execute

        with self.assertRaises(ValueError), raw_sql.recording():
            raise ValueError

        self.assertIs(Cursor.execute, original)

    def test_columns_of_the_common_statements(self):
        self.assertEqual(raw_sql._columns('UPDATE t SET "a" = %s, b = %s WHERE id = 1'), ["a", "b"])
        self.assertEqual(raw_sql._columns("INSERT INTO t (a, b) VALUES (%s, %s)"), ["a", "b"])
        self.assertEqual(raw_sql._columns("DELETE FROM t WHERE amount = 0"), [])
        self.assertIsNotNone(raw_sql.WRITE.match("DELETE FROM t WHERE amount = 0"))
        self.assertIsNone(raw_sql.WRITE.match("SELECT 1"))
