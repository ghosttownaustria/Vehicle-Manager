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

    def test_non_billable_time_is_unchecked_on_invoice(self):
        self.order.times.append(
            WorkTime(description="Kulanz", hours=2, isBillable=False)
        )
        db.session.commit()
        html = self.client.get(f"/order/{self.order.id}/invoice").get_data(as_text=True)
        rows = [row for row in html.split("<tr>") if 'data-hours="' in row]
        self.assertEqual(len(rows), 2)
        self.assertIn(" checked", rows[0])
        self.assertNotIn(" checked", rows[1])
        self.assertIn('name="workerHours" value="1.5"', html)

    def test_order_page_shows_actual_and_billable_hours(self):
        self.order.times.append(
            WorkTime(description="Kulanz", hours=2, isBillable=False)
        )
        db.session.commit()
        html = self.client.get(f"/order/{self.order.id}").get_data(as_text=True)
        self.assertIn("Arbeitszeit (tatsächlich)", html)
        self.assertIn("Arbeitszeit (verrechnet)", html)
        self.assertIn("3,50 h tatsächlich · 1,50 h verrechnet", html)

    def test_new_work_time_is_billable_by_default(self):
        self.assertTrue(self.order.times[0].isBillable)

    def test_price_uses_per_unit_discount(self):
        cost = self.order.costs[0]
        cost.discount = 2
        self.assertAlmostEqual(cost.price, 3 * (15 - 2 * 1.2))

    def test_cost_form_stores_gross_prices_and_discount(self):
        response = self.client.post(
            f"/order/{self.order.id}",
            data={
                "cost_submit": "1", "description": "Filter", "quantity": "2",
                "amount": "11,90", "saleAmount": "23.80", "discount": "1,80",
            },
        )
        self.assertEqual(response.status_code, 302)
        cost = Cost.query.filter_by(description="Filter").one()
        self.assertEqual((cost.amount, cost.saleAmount, cost.discount), (11.9, 23.8, 1.8))
        self.assertEqual(cost.listPrice, 47.6)
        self.assertEqual(cost.price, 43.27)
        self.assertEqual(cost.discountTotal, 4.33)

    def test_invoice_rows_show_list_price_and_discount_line(self):
        from pdfReports import invoiceRows

        cost = self.order.costs[0]
        cost.discount = 2
        rows = invoiceRows([cost], [], [("Rabatt Oel", False, 7.2, "all", 720)], 0)
        self.assertEqual(rows[0][3:], ("15,00 €", "45,00 €"))
        self.assertIn(("sum", "Summe Teile", "", "", "45,00 €"), rows)
        self.assertIn(("row", "Rabatt Oel", "", "", "-7,20 €"), rows)

    def test_invoice_pdf_includes_position_discount(self):
        self.order.costs[0].discount = 2
        db.session.commit()
        response = self.client.post(
            f"/order/{self.order.id}/invoice",
            data={"cost_id": [str(self.order.costs[0].id)]},
        )
        self.assertTrue(response.data.startswith(b"%PDF"))

    def test_invoice_pdf_is_generated(self):
        response = self.client.post(
            f"/order/{self.order.id}/invoice",
            data={"cost_id": [str(self.order.costs[0].id)], "workerName": ["Max", "Eva"], "workerHours": ["1", "0.5"], "workerTotal": ["60", "30"]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data.startswith(b"%PDF"))

    def test_discounts_and_cent_rounding(self):
        from pdfReports import calculateInvoiceDiscounts

        lines, rounding = calculateInvoiceDiscounts(
            40, 60, [("Stammkunde", True, 10, "all"), ("Kulanz", False, 2.66, "all")]
        )
        self.assertEqual(lines, [("Stammkunde", 1000), ("Kulanz", 266)])
        self.assertEqual(rounding, 4)
        self.assertEqual(calculateInvoiceDiscounts(12.34, 0, [])[1], 4)

    def test_percent_discount_scope(self):
        from pdfReports import calculateInvoiceDiscounts

        lines, _ = calculateInvoiceDiscounts(
            40, 60, [("T", True, 10, "parts"), ("A", True, 10, "work")]
        )
        self.assertEqual(lines, [("T", 400), ("A", 600)])

    def test_invoice_pdf_with_discounts(self):
        response = self.client.post(
            f"/order/{self.order.id}/invoice",
            data={
                "cost_id": [str(self.order.costs[0].id)], "workerName": ["Max"], "workerHours": ["1.5"],
                "workerTotal": ["90"], "discountDescription": ["A", "B"],
                "discountType": ["percent", "amount"], "discountScope": ["parts", "all"], "discountValue": ["5", "1,11"],
            },
        )
        self.assertTrue(response.data.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
