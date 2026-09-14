"""Tests for full-tank consumption calculations, independent of the database."""

from datetime import date
from decimal import Decimal
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fuelStatistics import buildFuelStatistics


def fill(entryId, liters="10", mileage=None, price=None, full=False, day=1):
    return SimpleNamespace(
        id=entryId, date=date(2026, 1, day), liters=Decimal(liters),
        mileage=mileage, price=Decimal(price) if price is not None else None,
        isFullTank=full,
    )


class FuelStatisticsTests(unittest.TestCase):
    def test_empty_statistics_have_no_rates(self):
        result = buildFuelStatistics([])
        self.assertEqual(result["rows"], [])
        self.assertEqual(result["summary"], {
            "count": 0, "totalLiters": Decimal("0"),
            "totalPrice": Decimal("0"), "missingPriceCount": 0,
            "averagePricePerLiter": None, "distance": 0,
            "intervalLiters": Decimal("0"), "averageConsumption": None,
            "averageCentsPerKm": None, "intervalCount": 0,
        })

    def test_partial_fills_are_counted_until_next_full_tank_with_mileage(self):
        entries = [
            fill(1, "50", 1000, "75", True),
            fill(2, "12.11", price="17.70"),
            fill(3, "59.66", 2198, "89.25", True),
        ]
        result = buildFuelStatistics(entries)
        self.assertTrue(result["rows"][0]["isBaseline"])
        self.assertIsNone(result["rows"][1]["interval"])
        interval = result["rows"][2]["interval"]
        self.assertEqual(interval["distance"], 1198)
        self.assertEqual(interval["liters"], Decimal("71.77"))
        self.assertEqual(interval["price"], Decimal("106.95"))
        self.assertEqual(interval["consumption"], Decimal("7177") / 1198)
        self.assertEqual(interval["centsPerKm"], Decimal("10695") / 1198)
        self.assertFalse(result["rows"][2]["isBaseline"])

    def test_full_tank_without_mileage_remains_in_the_interval(self):
        entries = [
            fill(1, "30", 1000, "45", True),
            fill(2, "10", 1100, "15"),
            fill(3, "20", price="30", full=True),
            fill(4, "15", 1300, "22.50"),
            fill(5, "5", 1500, "7.50", True),
        ]
        result = buildFuelStatistics(entries)
        self.assertIsNone(result["rows"][2]["interval"])
        self.assertFalse(result["rows"][2]["isBaseline"])
        self.assertEqual(result["rows"][-1]["interval"]["liters"], Decimal("50"))
        self.assertEqual(result["summary"]["averageConsumption"], Decimal("10"))
        self.assertEqual(result["summary"]["averageCentsPerKm"], Decimal("15"))

    def test_chronological_sort_uses_id_for_same_day_and_preserves_input(self):
        entries = [
            fill(4, "40", 1900, full=True, day=2),
            fill(3, "20", 1400, full=True),
            fill(1, "40", 1000, full=True),
            fill(2, "10"),
        ]
        original = list(entries)
        result = buildFuelStatistics(iter(entries))
        self.assertEqual([row["entry"].id for row in result["rows"]], [1, 2, 3, 4])
        self.assertEqual(result["rows"][2]["interval"]["liters"], Decimal("30"))
        self.assertEqual(result["rows"][3]["interval"]["liters"], Decimal("40"))
        self.assertEqual(entries, original)

    def test_unmeasured_beginning_and_unfinished_end_only_affect_totals(self):
        entries = [
            fill(1, "10", 900, "10"),
            fill(2, "20", price="20", full=True),
            fill(3, "30", 1000, "30", True),
            fill(4, "40", 1500, "40", True),
            fill(5, "50", 2000, "50"),
        ]
        summary = buildFuelStatistics(entries)["summary"]
        self.assertEqual(summary["totalLiters"], Decimal("150"))
        self.assertEqual(summary["totalPrice"], Decimal("150"))
        self.assertEqual(summary["intervalLiters"], Decimal("40"))
        self.assertEqual(summary["distance"], 500)
        self.assertEqual(summary["intervalCount"], 1)
        self.assertEqual(summary["averageConsumption"], Decimal("8"))

    def test_missing_price_keeps_consumption_but_disables_cost_rate(self):
        entries = [
            fill(1, "50", 1000, "100", True),
            fill(2, "20"),
            fill(3, "30", 1500, "60", True),
            fill(4, "40", 2000, "80", True),
        ]
        result = buildFuelStatistics(entries)
        interval = result["rows"][2]["interval"]
        self.assertIsNone(interval["price"])
        self.assertIsNone(interval["centsPerKm"])
        self.assertEqual(interval["consumption"], Decimal("10"))
        self.assertEqual(result["rows"][3]["interval"]["centsPerKm"], Decimal("16"))
        summary = result["summary"]
        self.assertIsNone(summary["averageCentsPerKm"])
        self.assertEqual(summary["averageConsumption"], Decimal("9"))
        self.assertEqual(summary["totalPrice"], Decimal("240"))
        self.assertEqual(summary["missingPriceCount"], 1)
        self.assertEqual(summary["averagePricePerLiter"], Decimal("2"))

    def test_missing_prices_outside_completed_intervals_do_not_disable_cost_rate(self):
        entries = [
            fill(1, "10"),
            fill(2, "50", 1000, full=True),
            fill(3, "40", 1500, "60", True),
            fill(4, "10"),
        ]
        summary = buildFuelStatistics(entries)["summary"]
        self.assertEqual(summary["averageCentsPerKm"], Decimal("12"))
        self.assertEqual(summary["averagePricePerLiter"], Decimal("1.5"))
        self.assertEqual(summary["missingPriceCount"], 3)

    def test_without_full_tanks_and_readings_no_consumption_is_available(self):
        scenarios = [
            [fill(1, mileage=1000), fill(2, mileage=1500)],
            [fill(1, full=True), fill(2, full=True)],
            [fill(1, mileage=1000, full=True), fill(2, full=True)],
        ]
        for entries in scenarios:
            with self.subTest(entries=entries):
                summary = buildFuelStatistics(entries)["summary"]
                self.assertEqual(summary["distance"], 0)
                self.assertIsNone(summary["averageConsumption"])
                self.assertIsNone(summary["averageCentsPerKm"])

    def test_zero_and_negative_distances_restart_from_new_baseline(self):
        for mileage in [1000, 900]:
            with self.subTest(mileage=mileage):
                entries = [
                    fill(1, "40", 1000, "60", True),
                    fill(2, "20", mileage, "30", True),
                    fill(3, "30", mileage + 300, "45", True),
                ]
                result = buildFuelStatistics(entries)
                self.assertIsNone(result["rows"][1]["interval"])
                self.assertTrue(result["rows"][1]["isBaseline"])
                self.assertEqual(result["summary"]["intervalCount"], 1)
                self.assertEqual(result["summary"]["distance"], 300)
                self.assertEqual(result["summary"]["intervalLiters"], Decimal("30"))

    def test_regressing_intermediate_mileage_invalidates_interval_then_recovers(self):
        entries = [
            fill(1, "50", 1000, "75", True),
            fill(2, "10", 1300, "15"),
            fill(3, "10", 1200, "15"),
            fill(4, "30", 1500, "45", True),
            fill(5, "40", 2000, "60", True),
        ]
        result = buildFuelStatistics(entries)
        self.assertIsNone(result["rows"][3]["interval"])
        self.assertTrue(result["rows"][3]["isBaseline"])
        self.assertEqual(result["summary"]["intervalCount"], 1)
        self.assertEqual(result["summary"]["distance"], 500)
        self.assertEqual(result["summary"]["averageConsumption"], Decimal("8"))

    def test_intermediate_reading_above_final_mileage_invalidates_interval(self):
        result = buildFuelStatistics([
            fill(1, "40", 1000, full=True),
            fill(2, "10", 2000),
            fill(3, "40", 1500, full=True),
        ])
        self.assertEqual(result["summary"]["intervalCount"], 0)
        self.assertIsNone(result["summary"]["averageConsumption"])

    def test_consumption_and_cost_means_are_distance_weighted(self):
        result = buildFuelStatistics([
            fill(1, "50", 1000, "100", True),
            fill(2, "10", 1100, "20", True),
            fill(3, "45", 2000, "90", True),
        ])
        summary = result["summary"]
        self.assertEqual(summary["distance"], 1000)
        self.assertEqual(summary["intervalLiters"], Decimal("55"))
        self.assertEqual(summary["averageConsumption"], Decimal("5.5"))
        self.assertEqual(summary["averageCentsPerKm"], Decimal("11"))

    def test_zero_price_is_known_and_float_values_are_converted_exactly(self):
        entries = [fill(1, "40", 0, full=True), fill(2, "1", 100, "0", True)]
        entries[1].liters = 0.1
        result = buildFuelStatistics(entries)
        self.assertEqual(result["summary"]["totalLiters"], Decimal("40.1"))
        self.assertEqual(result["summary"]["averageConsumption"], Decimal("0.1"))
        self.assertEqual(result["summary"]["averageCentsPerKm"], Decimal("0"))
        self.assertEqual(result["summary"]["averagePricePerLiter"], Decimal("0"))
        self.assertEqual(result["summary"]["missingPriceCount"], 1)


if __name__ == "__main__":
    unittest.main()
