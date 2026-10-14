"""Tests for per-vehicle service intervals (kilometers and months)."""

import os
import sys
import unittest
from datetime import date
from pathlib import Path

os.environ["VEHICLE_MANAGER_DATABASE_URI"] = "sqlite:///:memory:"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import ServiceHistoryEntry, User, Vehicle, addMonths, app, db


class ServiceIntervalTests(unittest.TestCase):
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
        db.session.add_all([admin, self.vehicle])
        db.session.commit()
        self.client = app.test_client()
        with self.client.session_transaction() as session:
            session["userId"] = admin.id

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def editVehicle(self, **intervals):
        data = {"brand": "VW", "model": "Golf", "vin": "TEST-ONE", **intervals}
        return self.client.post(f"/edit_vehicle/{self.vehicle.id}", data=data)

    def test_intervals_are_saved_and_shown_in_form(self):
        response = self.editVehicle(
            intervalKm_engine_oil="15000", intervalMonths_engine_oil="12",
            intervalMonths_brake_fluid="24",
        )
        self.assertEqual(response.status_code, 302)
        stored = {item.work: (item.kilometers, item.months) for item in self.vehicle.serviceIntervals}
        self.assertEqual(stored, {"engine_oil": (15000, 12), "brake_fluid": (None, 24)})

        page = self.client.get(f"/edit_vehicle/{self.vehicle.id}").get_data(as_text=True)
        self.assertIn('name="intervalKm_engine_oil" value="15000"', page)

    def test_resaving_and_changing_single_field_intervals(self):
        self.editVehicle(intervalKm_engine_oil="15000")
        self.assertEqual(self.editVehicle(intervalKm_engine_oil="15000").status_code, 302)
        self.assertEqual(self.editVehicle(intervalMonths_engine_oil="12").status_code, 302)
        stored = [(item.work, item.kilometers, item.months) for item in self.vehicle.serviceIntervals]
        self.assertEqual(stored, [("engine_oil", None, 12)])

    def test_clearing_fields_removes_interval(self):
        self.editVehicle(intervalKm_engine_oil="15000")
        self.editVehicle(intervalKm_engine_oil="")
        self.assertEqual(self.vehicle.serviceIntervals, [])

    def test_invalid_value_is_rejected_without_saving(self):
        response = self.editVehicle(intervalKm_engine_oil="abc")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.vehicle.serviceIntervals, [])

    def test_vehicle_page_shows_next_due(self):
        db.session.add(ServiceHistoryEntry(
            vehicle_id=self.vehicle.id, date=date(2025, 1, 31), mileage=100000,
            categories=["service"], works=["engine_oil"],
        ))
        db.session.commit()
        self.editVehicle(intervalKm_engine_oil="15000", intervalMonths_engine_oil="1")
        page = self.client.get(f"/vehicle/{self.vehicle.id}").get_data(as_text=True)
        self.assertIn("115.000 km", page)
        self.assertIn("28.02.2025", page)

    def test_add_months_clamps_day(self):
        self.assertEqual(addMonths(date(2025, 1, 31), 1), date(2025, 2, 28))
        self.assertEqual(addMonths(date(2025, 11, 15), 3), date(2026, 2, 15))


if __name__ == "__main__":
    unittest.main()
