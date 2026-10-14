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
            data={"cost_id": [str(self.order.costs[0].id)], "workerName": ["Max", "Eva"], "workerHours": ["1", "0.5"], "workerTotal": ["60", "30"]},
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
                "cost_id": [str(self.order.costs[0].id)], "workerName": ["Max"], "workerHours": ["1.5"],
                "workerTotal": ["90"], "discountDescription": ["A", "B"],
                "discountType": ["percent", "amount"], "discountValue": ["5", "1,11"],
            },
        )
        self.assertTrue(response.data.startswith(b"%PDF"))


class ServicePlanTests(InvoiceTests):
    def test_service_plan_form_lists_intervals_and_checks(self):
        from app import ServiceInterval

        vehicle = self.order.vehicle
        vehicle.serviceIntervals.append(
            ServiceInterval(work="engine_oil", kilometers=15000, months=12)
        )
        db.session.commit()
        response = self.client.get(f"/vehicle/{vehicle.id}/serviceplan")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Ölwechsel".encode(), response.data)
        self.assertIn("Fahrzeugcheck".encode(), response.data)

    def test_only_due_intervals_are_preselected(self):
        from datetime import date

        from app import isServiceIntervalDue

        entry = type("Entry", (), {})()
        item = {"lastEntry": entry, "dueMileage": 20000, "dueDate": date(2030, 1, 1)}
        today = date(2026, 1, 1)
        self.assertFalse(isServiceIntervalDue(item, 15000, today))
        self.assertTrue(isServiceIntervalDue(item, 20000, today))
        self.assertTrue(isServiceIntervalDue(item, 100, date(2030, 1, 1)))
        self.assertTrue(isServiceIntervalDue({**item, "lastEntry": None}, 0, today))

    def test_service_plan_pdf_is_generated(self):
        from app import ServiceInterval

        vehicle = self.order.vehicle
        vehicle.serviceIntervals.append(
            ServiceInterval(work="inspection", kilometers=None, months=12)
        )
        db.session.commit()
        response = self.client.post(
            f"/vehicle/{vehicle.id}/serviceplan",
            data={
                "interval": ["inspection", "bogus"],
                "task": ["vehicle_check:0", "oil_service:2", "nope:9"],
                "extraTasks": "Scheibe tauschen\n\n",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data.startswith(b"%PDF"))

    def test_service_plan_pdf_without_selection(self):
        response = self.client.post(
            f"/vehicle/{self.order.vehicle.id}/serviceplan", data={}
        )
        self.assertTrue(response.data.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
