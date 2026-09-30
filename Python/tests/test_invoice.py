"""Tests for invoice printing and quantity-aware purchase totals."""

import os
import sys
import unittest
from pathlib import Path

os.environ["VEHICLE_MANAGER_DATABASE_URI"] = "sqlite:///:memory:"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import Cost, Order, User, Vehicle, WorkTime, app, db, directOrderTotals


class InvoiceTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.context = app.app_context()
        self.context.push()
        db.drop_all()
        db.create_all()
        admin = User(
            name="Admin", email="admin@example.test", passwordHash="unused",
            role="admin", isAdmin=True,
        )
        vehicle = Vehicle(brand="VW", model="Golf", vin="TEST-ONE")
        self.order = Order(title="Inspektion", vehicle=vehicle)
        self.order.costs.append(
            Cost(description="Oel", amount=10, quantity=3, saleAmount=15)
        )
        self.order.times.append(WorkTime(description="Wechsel", hours=1.5))
        db.session.add_all([admin, vehicle, self.order])
        db.session.commit()
        self.client = app.test_client()
        with self.client.session_transaction() as session:
            session["userId"] = admin.id

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_purchase_total_uses_quantity(self):
        self.assertEqual(directOrderTotals(self.order)[0], 30)

    def test_invoice_form_renders(self):
        response = self.client.get(f"/order/{self.order.id}/invoice")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b">EK<", response.data)

    def test_invoice_pdf_is_generated(self):
        response = self.client.post(
            f"/order/{self.order.id}/invoice",
            data={"cost_id": [str(self.order.costs[0].id)], "hours": "1.5", "hoursTotal": "90"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data.startswith(b"%PDF"))

    def test_discounts_and_cent_rounding(self):
        from pdfReports import calculateInvoiceDiscounts

        lines, rounding = calculateInvoiceDiscounts(
            100, [("Stammkunde", True, 10), ("Kulanz", False, 2.66)]
        )
        self.assertEqual(lines, [("Stammkunde", 1000), ("Kulanz", 266)])
        self.assertEqual(rounding, 4)
        self.assertEqual(calculateInvoiceDiscounts(12.34, [])[1], 4)

    def test_invoice_pdf_with_discounts(self):
        response = self.client.post(
            f"/order/{self.order.id}/invoice",
            data={
                "cost_id": [str(self.order.costs[0].id)], "hours": "1.5",
                "hoursTotal": "90", "discountDescription": ["A", "B"],
                "discountType": ["percent", "amount"], "discountValue": ["5", "1,11"],
            },
        )
        self.assertTrue(response.data.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
