from unittest import SkipTest

from odoo.tests import tagged

from .common import TraceCase


@tagged("post_install", "-at_install")
class TestSaleOrderConfirmReference(TraceCase):
    """Reference test of CLAUDE.md section 9: sale.order.action_confirm.

    Needs `sale_stock`, which this addon does not depend on; the test is skipped (with a
    reason) in databases without it, e.g. the test Odoo's `odoo_trace` database has it.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if "stock.picking" not in cls.env or "sale.order" not in cls.env:
            raise SkipTest("needs sale_stock installed")
        env = cls.admin_env
        product = env["product.product"].create(
            {"name": "Traced chair", "type": "consu", "is_storable": True}
        )
        partner = env["res.partner"].create({"name": "Traced customer"})
        cls.order = env["sale.order"].create(
            {
                "partner_id": partner.id,
                "order_line": [(0, 0, {"product_id": product.id, "product_uom_qty": 2})],
            }
        )

    def test_action_confirm_is_recorded_and_rolled_back(self):
        payload = self.trace("sale.order", "action_confirm", self.order.ids)

        self.assertIsNone(payload["error"])
        self.assertValidTree(payload)

        [entry] = self.find(payload, "sale.order", "action_confirm", "sale")
        self.assertEqual(entry["seq"], 1)

        # sale_stock overrides _action_confirm and calls super() into sale
        [stock_confirm] = self.find(payload, "sale.order", "_action_confirm", "sale_stock")
        self.assertTrue(stock_confirm["calls_super"])
        [sale_confirm] = self.find(payload, "sale.order", "_action_confirm", "sale")
        self.assertEqual(sale_confirm["parent_id"], stock_confirm["id"])
        self.assertGreater(sale_confirm["mro_position"], stock_confirm["mro_position"])

        modules = {s["module"] for s in payload["steps"]}
        self.assertTrue({"sale", "sale_stock", "stock"} <= modules)

        state = [
            c
            for c in self.changes(payload, "sale.order", "state")
            if c["record_id"] == self.order.id
        ]
        self.assertEqual((state[0]["old"], state[0]["new"]), ("draft", "sale"))
        self.assertTrue(self.find(payload, "stock.picking", "create"))

        self.env.invalidate_all()
        self.assertEqual(self.order.state, "draft")
        self.assertFalse(self.order.picking_ids)
