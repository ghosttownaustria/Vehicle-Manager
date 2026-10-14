"""Tests for order-bound service plans and the history entry created on close."""

import os
import sys
import unittest
from datetime import date
from pathlib import Path

os.environ["VEHICLE_MANAGER_DATABASE_URI"] = "sqlite:///:memory:"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import (
    Order, ServiceHistoryEntry, ServiceInterval, ServicePlanItem, User, Vehicle,
    app, db, isServiceIntervalDue,
)


class ServicePlanTests(unittest.TestCase):
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
        self.vehicle = Vehicle(brand="VW", model="Golf", vin="TEST-ONE")
        self.vehicle.serviceIntervals.append(
            ServiceInterval(work="engine_oil", kilometers=15000, months=12)
        )
        self.order = Order(title="Inspektion", vehicle=self.vehicle)
        db.session.add_all([admin, self.vehicle, self.order])
        db.session.commit()
        self.client = app.test_client()
        with self.client.session_transaction() as session:
            session["userId"] = admin.id
        self.planUrl = f"/order/{self.order.id}/serviceplan"

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def savePlan(self):
        return self.client.post(
            self.planUrl,
            data={
                "interval": ["engine_oil", "bogus"],
                "task": ["vehicle_check:0", "oil_service:2", "nope:9"],
                "extraTasks": "Scheibe tauschen\n\n",
            },
        )

    def test_only_due_intervals_are_preselected(self):
        entry = object()
        item = {"lastEntry": entry, "dueMileage": 20000, "dueDate": date(2030, 1, 1)}
        today = date(2026, 1, 1)
        self.assertFalse(isServiceIntervalDue(item, 15000, today))
        self.assertTrue(isServiceIntervalDue(item, 20000, today))
        self.assertTrue(isServiceIntervalDue(item, 100, date(2030, 1, 1)))
        self.assertTrue(isServiceIntervalDue({**item, "lastEntry": None}, 0, today))

    def test_form_lists_intervals_and_checks(self):
        response = self.client.get(self.planUrl)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Ölwechsel".encode(), response.data)
        self.assertIn("Fahrzeugcheck".encode(), response.data)

    def test_saving_stores_only_known_lines_on_the_order(self):
        self.assertEqual(self.savePlan().status_code, 302)
        items = db.session.get(Order, self.order.id).servicePlanItems
        self.assertEqual(
            [(item.kind, item.key) for item in items],
            [
                ("interval", "engine_oil"),
                ("task", "vehicle_check:0"),
                ("task", "oil_service:2"),
                ("task", "extra:0"),
            ],
        )

    def test_empty_selection_is_rejected(self):
        self.client.post(self.planUrl, data={})
        self.assertEqual(db.session.get(Order, self.order.id).servicePlanItems, [])

    def test_editing_keeps_done_state_of_remaining_lines(self):
        self.savePlan()
        first = db.session.get(Order, self.order.id).servicePlanItems[0]
        self.client.post(
            f"/order/{self.order.id}/serviceplan/check", data={"done": [str(first.id)]}
        )
        self.client.post(self.planUrl, data={"interval": ["engine_oil"], "task": ["vehicle_check:1"]})
        items = db.session.get(Order, self.order.id).servicePlanItems
        self.assertEqual([(item.key, item.isDone) for item in items],
                         [("engine_oil", True), ("vehicle_check:1", False)])

    def test_checking_off_lines(self):
        self.savePlan()
        items = db.session.get(Order, self.order.id).servicePlanItems
        self.client.post(
            f"/order/{self.order.id}/serviceplan/check",
            data={"done": [str(items[1].id)]},
        )
        done = [item.isDone for item in db.session.get(Order, self.order.id).servicePlanItems]
        self.assertEqual(done, [False, True, False, False])

    def test_order_page_shows_plan(self):
        self.savePlan()
        response = self.client.get(f"/order/{self.order.id}")
        self.assertIn("Ölstand prüfen".encode(), response.data)
        self.assertIn("0 von 4 erledigt".encode(), response.data)

    def test_pdf_is_generated_from_saved_plan(self):
        self.savePlan()
        response = self.client.get(f"/order/{self.order.id}/serviceplan/pdf")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data.startswith(b"%PDF"))

    def test_closing_redirects_to_prefilled_history_entry(self):
        self.savePlan()
        items = db.session.get(Order, self.order.id).servicePlanItems
        self.client.post(
            f"/order/{self.order.id}/serviceplan/check",
            data={"done": [str(items[0].id), str(items[2].id)]},
        )
        response = self.client.post(f"/order/{self.order.id}/close")
        self.assertEqual(response.status_code, 302)
        self.assertIn(f"fromOrder={self.order.id}", response.headers["Location"])

        form = self.client.get(response.headers["Location"])
        html = form.get_data(as_text=True)
        self.assertIn('value="engine_oil" checked', html)
        self.assertIn('value="oil_filter" checked', html)
        self.assertNotIn('value="wheel_change" checked', html)
        self.assertIn(f'value="{self.order.id}" checked', html)

    def test_closing_without_plan_stays_on_order(self):
        response = self.client.post(f"/order/{self.order.id}/close")
        self.assertEqual(response.headers["Location"], f"/order/{self.order.id}")

    def test_closed_order_plan_is_read_only(self):
        self.savePlan()
        self.client.post(f"/order/{self.order.id}/close")
        self.client.post(self.planUrl, data={"interval": ["engine_oil"]})
        self.assertEqual(len(db.session.get(Order, self.order.id).servicePlanItems), 4)
        self.assertEqual(
            self.client.get(f"/order/{self.order.id}/serviceplan/pdf").status_code, 200
        )

    def test_saving_history_entry_from_prefill(self):
        self.savePlan()
        items = db.session.get(Order, self.order.id).servicePlanItems
        self.client.post(
            f"/order/{self.order.id}/serviceplan/check", data={"done": [str(items[0].id)]}
        )
        self.client.post(f"/order/{self.order.id}/close")
        response = self.client.post(
            f"/vehicle/{self.vehicle.id}/history/add?fromOrder={self.order.id}",
            data={
                "date": "2026-10-14", "mileage": "123456", "categories": ["service"],
                "works": ["engine_oil"], "orderIds": [str(self.order.id)],
                "description": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        entry = ServiceHistoryEntry.query.one()
        self.assertEqual([order.id for order in entry.orders], [self.order.id])


if __name__ == "__main__":
    unittest.main()
