"""Tank book backup integration tests using an isolated in-memory database."""

import io
import json
import os
from contextlib import redirect_stdout
from datetime import date
from decimal import Decimal
from pathlib import Path
import sys
import tempfile
import unittest


# The application initializes its database on import. Keep real data untouched.
os.environ["VEHICLE_MANAGER_DATABASE_URI"] = "sqlite:///:memory:"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import FuelEntry, Order, Vehicle, app, db
from databaseManager import exportJson, importJson


class FuelBackupTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.context = app.app_context()
        self.context.push()
        db.drop_all()
        db.create_all()
        self.vehicle = Vehicle(brand="BMW", model="E46", vin="FUEL-BACKUP-ONE")
        self.other_vehicle = Vehicle(brand="VW", model="Golf", vin="FUEL-BACKUP-TWO")
        self.vehicle.orders.append(Order(title="Bestehender Auftrag"))
        db.session.add_all([self.vehicle, self.other_vehicle])
        db.session.commit()
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "backup.json"

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()
        self.directory.cleanup()

    def add_entry(self, vehicle=None, **changes):
        fields = {
            "date": date(2025, 9, 14), "liters": Decimal("28.480"),
            "mileage": 216867, "price": Decimal("43.26"), "isFullTank": True,
        }
        fields.update(changes)
        entry = FuelEntry(**fields)
        (vehicle or self.vehicle).fuelEntries.append(entry)
        db.session.commit()
        return entry

    def export(self):
        with redirect_stdout(io.StringIO()):
            exportJson(self.path)
        return json.loads(self.path.read_text(encoding="utf-8"))

    def restore(self, data, replace=False):
        self.path.write_text(json.dumps(data), encoding="utf-8")
        with redirect_stdout(io.StringIO()):
            return importJson(self.path, replaceExisting=replace)

    def snapshot(self):
        db.session.expire_all()
        return [
            (
                entry.vehicle_id, entry.date, entry.liters, entry.mileage,
                entry.price, entry.isFullTank,
            )
            for entry in FuelEntry.query.order_by(FuelEntry.date, FuelEntry.id).all()
        ]

    def test_roundtrip_preserves_decimal_values_optional_fields_and_same_day_order(self):
        # Create out of date order; the two full tanks on the same day must retain
        # their order because reversing them would change interval consumption.
        self.add_entry(liters=Decimal("33.210"), mileage=217289, price=Decimal("47.99"))
        self.add_entry(liters=Decimal("59.660"), mileage=218065, price=Decimal("89.25"))
        self.add_entry(
            date=date(2025, 8, 29), liters=Decimal("31.340"), mileage=216143,
            price=None, isFullTank=True,
        )
        self.add_entry(
            date=date(2025, 9, 6), liters=Decimal("10.161"), mileage=None,
            price=Decimal("0.00"), isFullTank=False,
        )
        self.add_entry(
            vehicle=self.other_vehicle, liters=Decimal("0.001"), mileage=0,
            price=Decimal("0.01"), isFullTank=False,
        )
        original_vehicle_id = self.vehicle.id
        exported = self.export()
        first_vehicle = next(item for item in exported if item["vin"] == self.vehicle.vin)
        self.assertEqual(first_vehicle["fuelEntries"], [
            {"date": "2025-08-29", "liters": "31.340", "mileage": 216143,
             "price": None, "isFullTank": True},
            {"date": "2025-09-06", "liters": "10.161", "mileage": None,
             "price": "0.00", "isFullTank": False},
            {"date": "2025-09-14", "liters": "33.210", "mileage": 217289,
             "price": "47.99", "isFullTank": True},
            {"date": "2025-09-14", "liters": "59.660", "mileage": 218065,
             "price": "89.25", "isFullTank": True},
        ])
        self.assertTrue(self.restore(exported))
        imported = Vehicle.query.filter_by(vin="FUEL-BACKUP-ONE").order_by(Vehicle.id.desc()).first()
        self.assertNotEqual(imported.id, original_vehicle_id)
        self.assertEqual(
            [entry.mileage for entry in imported.fuelEntries],
            [216143, None, 217289, 218065],
        )
        self.assertEqual(imported.fuelEntries[1].liters, Decimal("10.161"))
        self.assertEqual(imported.fuelEntries[1].price, Decimal("0.00"))
        self.assertFalse(imported.fuelEntries[1].isFullTank)
        self.assertIsNone(imported.fuelEntries[0].price)
        self.assertEqual(FuelEntry.query.count(), 10)
        self.assertTrue(all(entry.vehicle_id == imported.id for entry in imported.fuelEntries))

    def test_old_export_without_tank_book_still_imports(self):
        data = [{"brand": "Legacy", "model": "Car", "orders": [{"title": "Alt"}]}]
        self.assertTrue(self.restore(data))
        imported = Vehicle.query.filter_by(brand="Legacy").one()
        self.assertEqual(imported.fuelEntries, [])
        self.assertEqual([order.title for order in imported.orders], ["Alt"])

    def test_import_accepts_required_fields_only_and_full_tank_without_mileage(self):
        self.assertTrue(self.restore([{
            "brand": "Imported", "fuelEntries": [
                {"date": "2025-01-01", "liters": "12.345"},
                {"date": "2025-01-02", "liters": 25, "isFullTank": True},
            ],
        }]))
        imported = Vehicle.query.filter_by(brand="Imported").one()
        first, second = imported.fuelEntries
        self.assertEqual(first.liters, Decimal("12.345"))
        self.assertFalse(first.isFullTank)
        self.assertIsNone(first.mileage)
        self.assertIsNone(first.price)
        self.assertTrue(second.isFullTank)
        self.assertIsNone(second.mileage)

    def test_successful_replacement_removes_old_fuel_entries(self):
        self.add_entry()
        self.add_entry(vehicle=self.other_vehicle)
        self.assertTrue(self.restore([{
            "brand": "Replacement", "fuelEntries": [
                {"date": "2025-12-31", "liters": "58.990", "mileage": 222896,
                 "price": "82.83", "isFullTank": True},
            ],
        }], replace=True))
        self.assertEqual(Vehicle.query.count(), 1)
        self.assertEqual(Order.query.count(), 0)
        self.assertEqual(FuelEntry.query.count(), 1)
        self.assertEqual(Vehicle.query.one().brand, "Replacement")
        self.assertEqual(FuelEntry.query.one().liters, Decimal("58.990"))

    def test_invalid_fuel_data_rolls_back_entire_import_and_replacement(self):
        self.add_entry()
        self.add_entry(vehicle=self.other_vehicle, liters=Decimal("35.000"))
        before = self.snapshot()
        original_vehicle_ids = {self.vehicle.id, self.other_vehicle.id}
        invalid_entries = [
            None, {}, "invalid", [None], ["invalid"], [{}],
        ]
        valid_entry = {
            "date": "2025-10-01", "liters": "59.660", "mileage": 218065,
            "price": "89.25", "isFullTank": True,
        }
        for changes in (
            {"date": ""}, {"date": "2025-02-29"}, {"date": 20250101},
            {"liters": None}, {"liters": "0"}, {"liters": "-1"},
            {"liters": "NaN"}, {"liters": "Infinity"}, {"liters": True},
            {"liters": "1.0001"}, {"liters": "10000000"},
            {"mileage": -1}, {"mileage": 1.5}, {"mileage": True},
            {"mileage": 2147483648}, {"price": "-0.01"},
            {"price": "NaN"}, {"price": "Infinity"}, {"price": True},
            {"price": "1.001"}, {"price": "10000000000"},
            {"isFullTank": "maybe"}, {"isFullTank": []},
        ):
            invalid_entries.append([{**valid_entry, **changes}])
        for replace in (False, True):
            for fuel_data in invalid_entries:
                with self.subTest(replace=replace, fuel_data=fuel_data):
                    # A valid vehicle preceding the invalid one must also roll back.
                    data = [
                        {"brand": "Valid", "fuelEntries": [valid_entry]},
                        {"brand": "Invalid", "fuelEntries": fuel_data},
                    ]
                    self.assertFalse(self.restore(data, replace=replace))
                    self.assertEqual({v.id for v in Vehicle.query.all()}, original_vehicle_ids)
                    self.assertEqual(Order.query.count(), 1)
                    self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    unittest.main()
