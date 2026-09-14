"""Fuel-entry integration tests against an isolated in-memory database."""

from contextlib import contextmanager
from datetime import date
from decimal import Decimal
import os
from pathlib import Path
import sys
import unittest


# Importing app initializes its database; never touch the installation's data.
os.environ["VEHICLE_MANAGER_DATABASE_URI"] = "sqlite:///:memory:"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flask import template_rendered

from app import FuelEntry, Order, User, Vehicle, app, db, initializeDatabase


@contextmanager
def captured_templates():
    contexts = []

    def record(sender, template, context, **extra):
        contexts.append((template.name, context))

    template_rendered.connect(record, app)
    try:
        yield contexts
    finally:
        template_rendered.disconnect(record, app)


class FuelEntryTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.context = app.app_context()
        self.context.push()
        db.drop_all()
        db.create_all()
        self.admin = User(
            name="Admin", email="admin@example.test", passwordHash="unused",
            role="admin", isAdmin=True,
        )
        self.technician = User(
            name="Techniker", email="technician@example.test", passwordHash="unused",
            role="technician",
        )
        self.customer = User(
            name="Kunde", email="customer@example.test", passwordHash="unused",
            role="customer",
        )
        self.vehicle = Vehicle(brand="BMW", model="E46", vin="FUEL-ONE")
        self.other_vehicle = Vehicle(brand="VW", model="Golf", vin="FUEL-TWO")
        self.vehicle.assignedUsers.append(self.customer)
        db.session.add_all([
            self.admin, self.technician, self.customer,
            self.vehicle, self.other_vehicle,
        ])
        db.session.commit()
        self.client = app.test_client()
        self.login(self.admin)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def login(self, user):
        with self.client.session_transaction() as session:
            session.clear()
            if user is not None:
                session["userId"] = user.id

    def form_data(self, **changes):
        data = {
            "date": "2024-02-29", "liters": "31,340", "mileage": "216143",
            "price": "45,00", "isFullTank": "on",
        }
        data.update(changes)
        return data

    def add_url(self, vehicle=None):
        return f"/vehicle/{(vehicle or self.vehicle).id}/fuel/add"

    def entry_url(self, entry, action, vehicle=None):
        return f"/vehicle/{(vehicle or self.vehicle).id}/fuel/{entry.id}/{action}"

    def create_entry(self, vehicle=None, **changes):
        response = self.client.post(self.add_url(vehicle), data=self.form_data(**changes))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            f"/vehicle/{(vehicle or self.vehicle).id}#fuel-statistics",
        )
        return FuelEntry.query.order_by(FuelEntry.id.desc()).first()

    def snapshot(self, entry):
        db.session.expire_all()
        return (
            entry.vehicle_id, entry.date, entry.liters,
            entry.mileage, entry.price, entry.isFullTank,
        )

    def statistics(self, vehicle=None, **filters):
        with captured_templates() as templates:
            response = self.client.get(
                f"/vehicle/{(vehicle or self.vehicle).id}", query_string=filters,
            )
        self.assertEqual(response.status_code, 200)
        context = next(context for name, context in templates if name == "vehicle.html")
        return context["fuelStatistics"], response.get_data(as_text=True)

    def invalid_changes(self):
        for field, values in (
            ("date", ("", "2025-02-29", "2024-13-01", "20240229", "29.02.2024")),
            ("liters", (
                "", "0", "-1", "NaN", "Infinity", "1e2", "0.0001",
                "10000000", "1.000,50", "1" * 26,
            )),
            ("mileage", (
                "-1", "1.5", "1,5", "NaN", "Infinity", "1e3",
                "2147483648", "216.143", "1" * 26,
            )),
            ("price", (
                "-0.01", "NaN", "Infinity", "1e2", "1.001",
                "10000000000", "1.000,50", "1" * 26,
            )),
        ):
            for value in values:
                yield {field: value}

    def test_only_date_and_liters_are_required_and_accept_decimal_comma(self):
        self.assertEqual(self.client.get(self.add_url()).status_code, 200)
        response = self.client.post(
            self.add_url(), data={"date": "2024-02-29", "liters": "31,34"},
        )
        self.assertEqual(response.status_code, 302)
        entry = FuelEntry.query.one()
        self.assertEqual(entry.date, date(2024, 2, 29))
        self.assertEqual(entry.liters, Decimal("31.340"))
        self.assertIsNone(entry.mileage)
        self.assertIsNone(entry.price)
        self.assertFalse(entry.isFullTank)
        self.assertEqual(entry.vehicle_id, self.vehicle.id)
        self.assertIn(entry, self.vehicle.fuelEntries)

    def test_optional_zero_values_and_full_tank_without_mileage_are_allowed(self):
        entry = self.create_entry(liters="0.001", mileage="0", price="0")
        self.assertEqual(entry.liters, Decimal("0.001"))
        self.assertEqual(entry.mileage, 0)
        self.assertEqual(entry.price, Decimal("0.00"))
        self.assertTrue(entry.isFullTank)
        without_mileage = self.create_entry(mileage="", price="")
        self.assertIsNone(without_mileage.mileage)
        self.assertIsNone(without_mileage.price)
        self.assertTrue(without_mileage.isFullTank)

    def test_largest_supported_values_roundtrip_without_silent_rounding(self):
        entry = self.create_entry(
            liters="9999999.999", mileage="2147483647", price="9999999999.99",
        )
        self.assertEqual(entry.liters, Decimal("9999999.999"))
        self.assertEqual(entry.mileage, 2147483647)
        self.assertEqual(entry.price, Decimal("9999999999.99"))

    def test_edit_preserves_initial_values_and_can_clear_optional_fields(self):
        entry = self.create_entry()
        with captured_templates() as templates:
            response = self.client.get(self.entry_url(entry, "edit"))
        self.assertEqual(response.status_code, 200)
        context = next(c for name, c in templates if name == "fuel_entry_form.html")
        self.assertEqual(context["formValues"], {
            "date": "2024-02-29", "liters": "31.340", "mileage": "216143",
            "price": "45.00", "isFullTank": True,
        })
        response = self.client.post(
            self.entry_url(entry, "edit"),
            data={"date": "2025-03-01", "liters": "42,5"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.snapshot(entry), (
            self.vehicle.id, date(2025, 3, 1), Decimal("42.500"), None, None, False,
        ))
        self.assertEqual(FuelEntry.query.count(), 1)
        response = self.client.post(self.entry_url(entry, "delete"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], f"/vehicle/{self.vehicle.id}#fuel-statistics")
        self.assertEqual(FuelEntry.query.count(), 0)

    def test_invalid_add_preserves_input_and_creates_no_records(self):
        for changes in self.invalid_changes():
            with self.subTest(changes=changes), captured_templates() as templates:
                data = self.form_data(**changes)
                response = self.client.post(self.add_url(), data=data)
                self.assertEqual(response.status_code, 400)
                context = next(c for name, c in templates if name == "fuel_entry_form.html")
                self.assertTrue(context["formErrors"])
                self.assertEqual(context["formValues"], {**data, "isFullTank": True})
                self.assertEqual(FuelEntry.query.count(), 0)

    def test_invalid_edit_does_not_partially_mutate_existing_record(self):
        entry = self.create_entry()
        before = self.snapshot(entry)
        for changes in self.invalid_changes():
            with self.subTest(changes=changes), captured_templates() as templates:
                data = self.form_data(date="2026-01-01", liters="99", price="199")
                data.update(changes)
                response = self.client.post(self.entry_url(entry, "edit"), data=data)
                self.assertEqual(response.status_code, 400)
                context = next(c for name, c in templates if name == "fuel_entry_form.html")
                self.assertEqual(context["formValues"], {**data, "isFullTank": True})
                self.assertEqual(self.snapshot(entry), before)
                self.assertEqual(FuelEntry.query.count(), 1)

    def test_invalid_full_tank_flag_and_missing_required_fields_are_rejected(self):
        for data in (
            {"date": "2024-02-29"}, {"liters": "10"},
            self.form_data(isFullTank="maybe"),
        ):
            with self.subTest(data=data):
                self.assertEqual(self.client.post(self.add_url(), data=data).status_code, 400)
                self.assertEqual(FuelEntry.query.count(), 0)

    def test_statistics_recalculate_after_backdated_add_edit_and_delete(self):
        baseline = self.create_entry(date="2026-01-01", liters="50", mileage="1000")
        endpoint = self.create_entry(date="2026-01-03", liters="30", mileage="1500", price="45")
        stats, html = self.statistics()
        self.assertIn('id="fuel-statistics"', html)
        self.assertEqual(stats["summary"]["averageConsumption"], Decimal("6"))
        self.assertEqual(stats["summary"]["distance"], 500)

        partial = self.create_entry(
            date="2026-01-02", liters="10", mileage="", price="15", isFullTank="",
        )
        stats, _ = self.statistics(q="no service history matches")
        self.assertEqual([row["entry"].id for row in stats["rows"]], [baseline.id, partial.id, endpoint.id])
        self.assertEqual(stats["summary"]["averageConsumption"], Decimal("8"))
        self.assertEqual(stats["summary"]["averageCentsPerKm"], Decimal("12"))

        response = self.client.post(self.entry_url(partial, "edit"), data=self.form_data(
            date="2026-01-02", liters="20", mileage="", price="30", isFullTank="",
        ))
        self.assertEqual(response.status_code, 302)
        stats, _ = self.statistics()
        self.assertEqual(stats["summary"]["averageConsumption"], Decimal("10"))
        self.assertEqual(stats["summary"]["averageCentsPerKm"], Decimal("15"))

        self.assertEqual(self.client.post(self.entry_url(partial, "delete")).status_code, 302)
        stats, _ = self.statistics()
        self.assertEqual(stats["summary"]["averageConsumption"], Decimal("6"))
        self.assertEqual(stats["summary"]["averageCentsPerKm"], Decimal("9"))

        response = self.client.post(self.entry_url(endpoint, "edit"), data=self.form_data(
            date="2026-01-03", liters="30", mileage="1600", price="45",
        ))
        self.assertEqual(response.status_code, 302)
        stats, _ = self.statistics()
        self.assertEqual(stats["summary"]["distance"], 600)
        self.assertEqual(stats["summary"]["averageConsumption"], Decimal("5"))

        self.assertEqual(self.client.post(self.entry_url(baseline, "delete")).status_code, 302)
        stats, _ = self.statistics()
        self.assertIsNone(stats["summary"]["averageConsumption"])
        self.assertEqual(stats["summary"]["intervalCount"], 0)

    def test_vehicle_statistics_only_include_its_own_entries(self):
        first = self.create_entry(date="2026-01-01", mileage="1000", liters="40")
        second = self.create_entry(date="2026-01-02", mileage="1500", liters="30")
        foreign = self.create_entry(vehicle=self.other_vehicle, liters="999", mileage="20000")
        stats, _ = self.statistics()
        self.assertEqual([row["entry"].id for row in stats["rows"]], [first.id, second.id])
        self.assertEqual(stats["summary"]["totalLiters"], Decimal("70"))
        other_stats, _ = self.statistics(self.other_vehicle)
        self.assertEqual([row["entry"].id for row in other_stats["rows"]], [foreign.id])
        self.assertEqual(other_stats["summary"]["totalLiters"], Decimal("999"))

    def test_customer_can_read_assigned_vehicle_but_cannot_change_fuel_entries(self):
        entry = self.create_entry()
        before = self.snapshot(entry)
        self.login(self.customer)
        stats, html = self.statistics()
        self.assertEqual(stats["summary"]["count"], 1)
        self.assertNotIn(self.add_url(), html)
        self.assertNotIn(self.entry_url(entry, "edit"), html)
        self.assertNotIn(self.entry_url(entry, "delete"), html)
        for method, url in (
            ("get", self.add_url()), ("post", self.add_url()),
            ("get", self.entry_url(entry, "edit")),
            ("post", self.entry_url(entry, "edit")),
            ("post", self.entry_url(entry, "delete")),
        ):
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url, data=self.form_data(liters="99"))
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.headers["Location"], "/")
                self.assertEqual(FuelEntry.query.count(), 1)
                self.assertEqual(self.snapshot(entry), before)
        response = self.client.get(f"/vehicle/{self.other_vehicle.id}")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")

    def test_technician_can_add_edit_delete_and_view_fuel_entries(self):
        self.login(self.technician)
        entry = self.create_entry()
        stats, html = self.statistics()
        self.assertEqual(stats["summary"]["count"], 1)
        self.assertIn(self.add_url(), html)
        response = self.client.post(self.entry_url(entry, "edit"), data=self.form_data(liters="42.5"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.snapshot(entry)[2], Decimal("42.500"))
        self.assertEqual(self.client.post(self.entry_url(entry, "delete")).status_code, 302)
        self.assertEqual(FuelEntry.query.count(), 0)

    def test_anonymous_requests_require_login_without_mutation(self):
        entry = self.create_entry()
        before = self.snapshot(entry)
        self.login(None)
        for method, url in (
            ("get", f"/vehicle/{self.vehicle.id}"),
            ("get", self.add_url()), ("post", self.add_url()),
            ("get", self.entry_url(entry, "edit")),
            ("post", self.entry_url(entry, "edit")),
            ("post", self.entry_url(entry, "delete")),
        ):
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url, data=self.form_data(liters="99"))
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.headers["Location"].startswith("/login"))
                self.assertEqual(self.snapshot(entry), before)
        self.assertEqual(FuelEntry.query.count(), 1)

    def test_entry_id_cannot_be_used_through_another_vehicle(self):
        entry = self.create_entry()
        before = self.snapshot(entry)
        for method, action in (("get", "edit"), ("post", "edit"), ("post", "delete")):
            with self.subTest(method=method, action=action):
                response = getattr(self.client, method)(
                    self.entry_url(entry, action, self.other_vehicle),
                    data=self.form_data(liters="99"),
                )
                self.assertEqual(response.status_code, 404)
                self.assertEqual(self.snapshot(entry), before)
                self.assertEqual(FuelEntry.query.count(), 1)

    def test_delete_rejects_get_without_deleting(self):
        entry = self.create_entry()
        self.assertEqual(self.client.get(self.entry_url(entry, "delete")).status_code, 405)
        self.assertEqual(FuelEntry.query.count(), 1)

    def test_startup_adds_fuel_table_and_preserves_existing_data(self):
        vehicle_id = self.vehicle.id
        order = Order(title="Existing service order", vehicle=self.vehicle)
        db.session.add(order)
        db.session.commit()
        order_id = order.id
        db.session.remove()
        FuelEntry.__table__.drop(db.engine)

        initializeDatabase()
        initializeDatabase()

        self.assertEqual(Vehicle.query.count(), 2)
        self.assertEqual(User.query.count(), 3)
        self.assertEqual(Order.query.count(), 1)
        self.assertEqual(db.session.get(Order, order_id).title, "Existing service order")
        self.vehicle = db.session.get(Vehicle, vehicle_id)
        self.assertEqual(self.vehicle.vin, "FUEL-ONE")
        self.assertEqual(FuelEntry.query.count(), 0)
        entry = self.create_entry()
        self.assertEqual(entry.vehicle_id, vehicle_id)

    def test_vehicle_deletion_cascades_only_to_its_own_fuel_entries(self):
        self.create_entry()
        self.create_entry(date="2025-01-01")
        foreign = self.create_entry(vehicle=self.other_vehicle)
        foreign_id = foreign.id
        foreign_snapshot = self.snapshot(foreign)
        response = self.client.post(f"/delete_vehicle/{self.vehicle.id}")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Vehicle.query.count(), 1)
        self.assertEqual(FuelEntry.query.count(), 1)
        self.assertEqual(self.snapshot(db.session.get(FuelEntry, foreign_id)), foreign_snapshot)


if __name__ == "__main__":
    unittest.main()
