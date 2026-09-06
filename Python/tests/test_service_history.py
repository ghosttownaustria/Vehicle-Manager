"""Integration tests using an isolated database; run with unittest discover."""

import io
import json
import os
from contextlib import contextmanager, redirect_stdout
from datetime import date
from pathlib import Path
import sys
import tempfile
import unittest


# app initializes its database during import. Never use the installation's DB.
os.environ["VEHICLE_MANAGER_DATABASE_URI"] = "sqlite:///:memory:"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flask import template_rendered

from app import (
    Order, ServiceHistoryEntry, User, Vehicle, app, db, initializeDatabase,
    serviceHistoryOrder,
)
from databaseManager import exportJson, importJson


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


class ServiceHistoryTests(unittest.TestCase):
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
            name="Techniker", email="technician@example.test",
            passwordHash="unused", role="technician",
        )
        self.customer = User(
            name="Kunde", email="customer@example.test", passwordHash="unused",
            role="customer",
        )
        self.vehicle = Vehicle(brand="VW", model="Golf", vin="TEST-ONE")
        self.other_vehicle = Vehicle(brand="Audi", model="A4", vin="TEST-TWO")
        self.vehicle.assignedUsers.append(self.customer)
        self.first_order = Order(title="Inspektion", vehicle=self.vehicle)
        self.second_order = Order(
            title="Abgeschlossene Reparatur", vehicle=self.vehicle, isClosed=True,
        )
        self.other_order = Order(title="Fremder Auftrag", vehicle=self.other_vehicle)
        db.session.add_all([
            self.admin, self.technician, self.customer, self.vehicle,
            self.other_vehicle, self.first_order, self.second_order, self.other_order,
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
            "date": "2024-02-29",
            "mileage": "125000",
            "description": "Ölwechsel und Reparatur durchgeführt.",
            "categories": ["service", "repair"],
            "works": ["engine_oil", "oil_filter", "air_filter"],
            "orderIds": [str(self.first_order.id), str(self.second_order.id)],
        }
        data.update(changes)
        return data

    def add_url(self, vehicle=None):
        return f"/vehicle/{(vehicle or self.vehicle).id}/history/add"

    def entry_url(self, entry, action, vehicle=None):
        return f"/vehicle/{(vehicle or self.vehicle).id}/history/{entry.id}/{action}"

    def create_entry(self, **changes):
        response = self.client.post(self.add_url(), data=self.form_data(**changes))
        self.assertEqual(response.status_code, 302)
        return ServiceHistoryEntry.query.order_by(ServiceHistoryEntry.id.desc()).first()

    def snapshot(self, entry):
        db.session.expire_all()
        return (
            entry.date, entry.mileage, entry.description,
            tuple(entry.categories), tuple(entry.works),
            tuple(sorted(order.id for order in entry.orders)),
        )

    def history_ids(self, **filters):
        with captured_templates() as templates:
            response = self.client.get(
                f"/vehicle/{self.vehicle.id}", query_string=filters,
            )
        self.assertEqual(response.status_code, 200)
        context = next(context for name, context in templates if name == "vehicle.html")
        return [entry.id for entry in context["historyEntries"]]

    def test_create_edit_delete_with_multiple_categories_works_and_orders(self):
        self.assertEqual(self.client.get(self.add_url()).status_code, 200)
        entry = self.create_entry()
        self.assertEqual(entry.date, date(2024, 2, 29))
        self.assertEqual(entry.mileage, 125000)
        self.assertEqual(set(entry.categories), {"service", "repair"})
        self.assertEqual(set(entry.works), {"engine_oil", "oil_filter", "air_filter"})
        self.assertEqual(
            {order.id for order in entry.orders},
            {self.first_order.id, self.second_order.id},
        )
        self.assertIn(entry, self.vehicle.serviceHistory)
        self.assertEqual(self.client.get(self.entry_url(entry, "edit")).status_code, 200)

        response = self.client.post(
            self.entry_url(entry, "edit"),
            data=self.form_data(
                date="2025-03-10", mileage="130000", description="Reifen montiert",
                categories=["tires"], works=[], orderIds=[str(self.first_order.id)],
            ),
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.snapshot(entry), (
            date(2025, 3, 10), 130000, "Reifen montiert", ("tires",), (),
            (self.first_order.id,),
        ))
        response = self.client.post(self.entry_url(entry, "delete"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ServiceHistoryEntry.query.count(), 0)
        self.assertEqual(Order.query.count(), 3)

    def test_invalid_create_is_rejected_without_saving_and_retains_description(self):
        invalid_values = [
            {"date": ""}, {"date": "2025-02-29"},
            {"mileage": ""}, {"mileage": "-1"}, {"mileage": "1.5"},
            {"mileage": "2147483648"}, {"categories": []},
            {"categories": ["unknown"]}, {"categories": ["service", "unknown"]},
            {"works": ["unknown"]}, {"orderIds": ["invalid"]},
            {"orderIds": ["999999"]},
            {"orderIds": [str(self.first_order.id), str(self.other_order.id)]},
        ]
        for changes in invalid_values:
            with self.subTest(changes=changes):
                response = self.client.post(
                    self.add_url(),
                    data=self.form_data(description="Meine Beschreibung bleibt", **changes),
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn("Meine Beschreibung bleibt", response.get_data(as_text=True))
                self.assertEqual(ServiceHistoryEntry.query.count(), 0)

    def test_invalid_edit_does_not_partially_change_existing_entry(self):
        entry = self.create_entry()
        before = self.snapshot(entry)
        for changes in (
            {"mileage": "-1"},
            {"orderIds": [str(self.other_order.id)]},
            {"works": ["unknown"]},
        ):
            with self.subTest(changes=changes):
                response = self.client.post(
                    self.entry_url(entry, "edit"),
                    data=self.form_data(
                        date="2026-01-01", description="Nicht speichern", **changes,
                    ),
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(self.snapshot(entry), before)

    def test_optional_works_and_orders_and_mileage_boundaries(self):
        for mileage in ("0", "2147483647"):
            with self.subTest(mileage=mileage):
                entry = self.create_entry(
                    mileage=mileage, categories=["other"], works=[], orderIds=[],
                    description="",
                )
                self.assertEqual(entry.mileage, int(mileage))
                self.assertEqual(entry.works, [])
                self.assertEqual(entry.orders, [])

    def test_duplicate_selections_are_stored_once(self):
        entry = self.create_entry(
            categories=["service", "service", "repair"],
            works=["engine_oil", "engine_oil"],
            orderIds=[str(self.first_order.id), str(self.first_order.id)],
        )
        self.assertEqual(len(entry.categories), 2)
        self.assertEqual(entry.works, ["engine_oil"])
        self.assertEqual([order.id for order in entry.orders], [self.first_order.id])

    def test_timeline_filters_combine_and_do_not_include_other_vehicles(self):
        mixed = self.create_entry(
            date="2024-01-01", description="Ölwechsel: Ölfilter 100%_ erledigt. Straße",
        )
        repair = self.create_entry(
            date="2025-01-01", categories=["repair"], works=["air_filter"],
            description="Luftfilter erneuert",
        )
        tires = self.create_entry(
            date="2026-01-01", categories=["tires"], works=[],
            description="Sommerreifen montiert",
        )
        response = self.client.post(
            self.add_url(self.other_vehicle),
            data=self.form_data(description="Ölwechsel fremd", orderIds=[]),
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.history_ids(), [tires.id, repair.id, mixed.id])
        self.assertEqual(self.history_ids(category="repair"), [repair.id, mixed.id])
        self.assertEqual(self.history_ids(work="oil_filter"), [mixed.id])
        self.assertEqual(
            self.history_ids(category="service", work="oil_filter", q="ÖLFILTER"),
            [mixed.id],
        )
        self.assertEqual(self.history_ids(category="tires", work="oil_filter"), [])
        self.assertEqual(self.history_ids(q="nicht enthalten"), [])
        for term in ("ölwechsel", "STRASSE", "%", "_"):
            with self.subTest(term=term):
                self.assertEqual(self.history_ids(q=term), [mixed.id])

    def test_filters_preserve_full_vehicle_curve_even_without_matching_points(self):
        first = self.create_entry(date="2024-01-01", mileage="80000")
        last = self.create_entry(
            date="2026-01-01", mileage="125000", categories=["tires"],
            works=["tire_change"], description="Sommerreifen montiert",
        )
        self.client.post(
            self.add_url(self.other_vehicle),
            data=self.form_data(mileage="999999", orderIds=[]),
        )
        expected_curve = [
            {"id": last.id, "date": "2026-01-01", "mileage": 125000},
            {"id": first.id, "date": "2024-01-01", "mileage": 80000},
        ]
        for filters, visible_ids in (
            ({}, [last.id, first.id]),
            ({"category": "service"}, [first.id]),
            ({"work": "tire_change"}, [last.id]),
            ({"category": "tires", "work": "tire_change", "q": "Sommer"}, [last.id]),
            ({"q": "kein passender Eintrag"}, []),
        ):
            with self.subTest(filters=filters), captured_templates() as templates:
                response = self.client.get(
                    f"/vehicle/{self.vehicle.id}", query_string=filters,
                )
                self.assertEqual(response.status_code, 200)
                context = next(context for name, context in templates if name == "vehicle.html")
                self.assertEqual(context["historyCurvePoints"], expected_curve)
                self.assertEqual([item.id for item in context["historyEntries"]], visible_ids)
                self.assertIn("data-history-chart", response.get_data(as_text=True))

    def test_customer_can_read_assigned_vehicle_but_cannot_modify_history(self):
        entry = self.create_entry()
        before = self.snapshot(entry)
        self.login(self.customer)
        self.assertEqual(self.history_ids(), [entry.id])
        for method, url in (
            ("get", self.add_url()), ("post", self.add_url()),
            ("get", self.entry_url(entry, "edit")),
            ("post", self.entry_url(entry, "edit")),
            ("post", self.entry_url(entry, "delete")),
        ):
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url, data=self.form_data())
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.headers["Location"], "/")
                self.assertEqual(ServiceHistoryEntry.query.count(), 1)
                self.assertEqual(self.snapshot(entry), before)
        response = self.client.get(f"/vehicle/{self.other_vehicle.id}")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")

    def test_technician_can_manage_history(self):
        self.login(self.technician)
        entry = self.create_entry(categories=["inspection"], works=["spark_plugs"])
        response = self.client.post(
            self.entry_url(entry, "edit"), data=self.form_data(description="Geprüft"),
        )
        self.assertEqual(response.status_code, 302)
        db.session.expire_all()
        self.assertEqual(entry.description, "Geprüft")
        self.assertEqual(
            self.client.post(self.entry_url(entry, "delete")).status_code, 302,
        )
        self.assertEqual(ServiceHistoryEntry.query.count(), 0)

    def test_login_required_for_history_routes(self):
        entry = self.create_entry()
        self.login(None)
        for method, url in (
            ("get", self.add_url()), ("post", self.add_url()),
            ("get", self.entry_url(entry, "edit")),
            ("post", self.entry_url(entry, "edit")),
            ("post", self.entry_url(entry, "delete")),
        ):
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url, data=self.form_data())
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.headers["Location"].startswith("/login"))
        self.assertEqual(ServiceHistoryEntry.query.count(), 1)

    def test_entry_cannot_be_accessed_through_a_different_vehicle(self):
        entry = self.create_entry()
        before = self.snapshot(entry)
        for method, action in (("get", "edit"), ("post", "edit"), ("post", "delete")):
            with self.subTest(method=method, action=action):
                response = getattr(self.client, method)(
                    self.entry_url(entry, action, self.other_vehicle),
                    data=self.form_data(description="Nicht speichern", orderIds=[]),
                )
                self.assertEqual(response.status_code, 404)
                self.assertEqual(self.snapshot(entry), before)

    def test_history_delete_requires_post(self):
        entry = self.create_entry()
        self.assertEqual(
            self.client.get(self.entry_url(entry, "delete")).status_code, 405,
        )
        self.assertEqual(ServiceHistoryEntry.query.count(), 1)

    def test_order_deletion_keeps_history_and_other_order_links(self):
        entry = self.create_entry()
        db.session.delete(self.first_order)
        db.session.commit()
        db.session.expire_all()
        self.assertEqual(ServiceHistoryEntry.query.count(), 1)
        self.assertEqual([order.id for order in entry.orders], [self.second_order.id])

    def test_vehicle_deletion_removes_history_and_orders_without_affecting_others(self):
        self.create_entry()
        self.second_order.isClosed = False
        db.session.commit()
        response = self.client.post(f"/delete_vehicle/{self.vehicle.id}")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ServiceHistoryEntry.query.count(), 0)
        self.assertEqual(Vehicle.query.count(), 1)
        self.assertEqual([order.id for order in Order.query.all()], [self.other_order.id])

    def test_initialization_adds_history_tables_and_preserves_existing_data(self):
        original_vehicle_id = self.vehicle.id
        original_order_ids = {self.first_order.id, self.second_order.id, self.other_order.id}
        db.session.remove()
        serviceHistoryOrder.drop(db.engine)
        ServiceHistoryEntry.__table__.drop(db.engine)

        initializeDatabase()
        initializeDatabase()  # Repeated application startups must remain safe.

        self.assertEqual(Vehicle.query.count(), 2)
        self.assertEqual({order.id for order in Order.query.all()}, original_order_ids)
        self.assertEqual(User.query.count(), 3)
        self.assertEqual(db.session.get(Vehicle, original_vehicle_id).vin, "TEST-ONE")
        self.assertEqual(ServiceHistoryEntry.query.count(), 0)
        entry = self.create_entry()
        self.assertEqual(entry.vehicle_id, original_vehicle_id)
        self.assertEqual(len(entry.orders), 2)

    def test_backup_roundtrip_remaps_order_ids_and_preserves_history(self):
        self.create_entry()
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            file_path = Path(directory) / "backup.json"
            exportJson(file_path)
            exported = json.loads(file_path.read_text(encoding="utf-8"))
            exported_vehicle = next(item for item in exported if item["vin"] == "TEST-ONE")
            self.assertEqual(len(exported_vehicle["serviceHistory"]), 1)
            self.assertEqual(
                set(exported_vehicle["serviceHistory"][0]["orderIds"]),
                {order["exportId"] for order in exported_vehicle["orders"]},
            )
            self.assertTrue(importJson(file_path))
        imported = Vehicle.query.filter_by(vin="TEST-ONE").order_by(Vehicle.id.desc()).first()
        self.assertNotEqual(imported.id, self.vehicle.id)
        self.assertEqual(len(imported.serviceHistory), 1)
        entry = imported.serviceHistory[0]
        self.assertEqual(entry.date, date(2024, 2, 29))
        self.assertEqual(entry.mileage, 125000)
        self.assertEqual(entry.description, "Ölwechsel und Reparatur durchgeführt.")
        self.assertEqual(set(entry.categories), {"service", "repair"})
        self.assertEqual(set(entry.works), {"engine_oil", "oil_filter", "air_filter"})
        self.assertEqual({order.id for order in entry.orders}, {order.id for order in imported.orders})
        self.assertTrue(all(order.vehicle_id == imported.id for order in entry.orders))
        self.assertTrue(any(order.isClosed for order in entry.orders))

    def test_old_export_without_history_still_imports(self):
        data = [{"brand": "Old", "model": "Vehicle", "orders": [{"title": "Legacy order"}]}]
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            file_path = Path(directory) / "old.json"
            file_path.write_text(json.dumps(data), encoding="utf-8")
            self.assertTrue(importJson(file_path))
        imported = Vehicle.query.filter_by(brand="Old").one()
        self.assertEqual(imported.serviceHistory, [])
        self.assertEqual([order.title for order in imported.orders], ["Legacy order"])

    def test_invalid_history_restore_rolls_back_replacement(self):
        entry = self.create_entry()
        before = self.snapshot(entry)
        original_vehicle_id = self.vehicle.id
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            file_path = Path(directory) / "backup.json"
            exportJson(file_path)
            valid_data = json.loads(file_path.read_text(encoding="utf-8"))
            for changes in (
                {"date": "2025-02-29"}, {"mileage": -1},
                {"categories": ["unknown"]}, {"works": ["unknown"]},
                {"orderIds": [999999]}, {"orderIds": [self.other_order.id]},
            ):
                with self.subTest(changes=changes):
                    data = json.loads(json.dumps(valid_data))
                    data[0]["serviceHistory"][0].update(changes)
                    file_path.write_text(json.dumps(data), encoding="utf-8")
                    self.assertFalse(importJson(file_path, replaceExisting=True))
                    self.assertEqual(Vehicle.query.count(), 2)
                    self.assertEqual(Order.query.count(), 3)
                    self.assertEqual(ServiceHistoryEntry.query.count(), 1)
                    restored_entry = ServiceHistoryEntry.query.one()
                    self.assertEqual(restored_entry.vehicle_id, original_vehicle_id)
                    self.assertEqual(self.snapshot(restored_entry), before)


if __name__ == "__main__":
    unittest.main()
