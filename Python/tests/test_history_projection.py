"""Tests for the mileage estimate, independent of Flask and the database."""

from copy import deepcopy
from datetime import date
from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from historyProjection import projectMileage


def sample(entryId, sampleDate, mileage):
    return {"id": entryId, "date": sampleDate, "mileage": mileage}


class MileageProjectionTests(unittest.TestCase):
    def test_irregular_intervals_use_duration_weighted_daily_mileage(self):
        entries = [
            sample(3, "2026-01-11", 2000),
            sample(1, "2026-01-01", 1000),
            sample(2, "2026-01-03", 1400),
        ]
        self.assertEqual(projectMileage(entries, date(2026, 1, 21)), {
            "date": "2026-01-21", "mileage": 3000, "dailyMileage": 100,
        })

    def test_same_day_uses_greatest_id_even_when_not_greatest_mileage(self):
        entries = [
            sample(4, "2026-01-11", 2000),
            sample(1, "2026-01-01", 1000),
            sample(3, "2026-01-11", 9000),
            sample(2, "2026-01-01", 1500),
        ]
        self.assertEqual(projectMileage(entries, date(2026, 1, 21)), {
            "date": "2026-01-21", "mileage": 2500, "dailyMileage": 50,
        })

    def test_zero_usage_produces_horizontal_projection(self):
        entries = [
            sample(1, "2026-01-01", 1500),
            sample(2, "2026-01-11", 1500),
        ]
        self.assertEqual(projectMileage(entries, date(2026, 1, 21)), {
            "date": "2026-01-21", "mileage": 1500, "dailyMileage": 0,
        })

    def test_zero_usage_interval_contributes_to_average_duration(self):
        entries = [
            sample(1, "2026-01-01", 1000),
            sample(2, "2026-01-11", 1000),
            sample(3, "2026-01-21", 2000),
        ]
        self.assertEqual(projectMileage(entries, date(2026, 1, 31)), {
            "date": "2026-01-31", "mileage": 2500, "dailyMileage": 50,
        })

    def test_negative_interval_is_skipped_and_projection_uses_latest_reading(self):
        entries = [
            sample(1, "2026-01-01", 1000),
            sample(2, "2026-01-11", 2000),
            sample(3, "2026-01-21", 1500),
        ]
        self.assertEqual(projectMileage(entries, date(2026, 1, 31)), {
            "date": "2026-01-31", "mileage": 2500, "dailyMileage": 100,
        })

    def test_only_negative_intervals_have_no_projection(self):
        entries = [
            sample(1, "2026-01-01", 2000),
            sample(2, "2026-01-11", 1000),
            sample(3, "2026-01-21", 500),
        ]
        self.assertIsNone(projectMileage(entries, date(2026, 1, 31)))

    def test_at_least_two_distinct_dates_are_required(self):
        for entries in [
            [],
            [sample(1, "2026-01-01", 1000)],
            [sample(1, "2026-01-01", 1000), sample(2, "2026-01-01", 2000)],
        ]:
            with self.subTest(entries=entries):
                self.assertIsNone(projectMileage(entries, date(2026, 1, 31)))

    def test_latest_reading_today_or_in_future_has_no_projection(self):
        for latest in ["2026-01-31", "2026-02-01"]:
            with self.subTest(latest=latest):
                entries = [sample(1, "2026-01-01", 1000), sample(2, latest, 2000)]
                self.assertIsNone(projectMileage(entries, date(2026, 1, 31)))

    def test_projected_mileage_is_rounded(self):
        entries = [
            sample(1, "2026-01-01", 1000),
            sample(2, "2026-01-04", 1002),
        ]
        projection = projectMileage(entries, date(2026, 1, 5))
        self.assertEqual(projection["mileage"], 1003)
        self.assertAlmostEqual(projection["dailyMileage"], 2 / 3)

    def test_entries_are_not_mutated(self):
        entries = [
            sample(2, "2026-01-11", 2000),
            sample(1, "2026-01-01", 1000),
        ]
        original = deepcopy(entries)
        projectMileage(entries, date(2026, 1, 21))
        self.assertEqual(entries, original)


if __name__ == "__main__":
    unittest.main()
