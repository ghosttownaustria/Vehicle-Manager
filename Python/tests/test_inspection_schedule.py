"""Tests for the Austrian §57a inspection schedule."""

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from inspectionSchedule import buildInspectionStatus, parseRegistrationMonth


def dueMonth(registration, lastInspection=None):
    return buildInspectionStatus(registration, lastInspection, date(2020, 1, 1))["dueMonth"]


class InspectionScheduleTests(unittest.TestCase):
    def test_registration_formats_ignore_day(self):
        for text in ("05/2018", "5.2018", "2018-05", "15.05.2018", "2018-05-15"):
            self.assertEqual(parseRegistrationMonth(text), (2018, 5), text)
        for text in ("", None, "abc", "13/2018", "2018"):
            self.assertIsNone(parseRegistrationMonth(text), text)

    def test_first_inspection_after_three_years(self):
        self.assertEqual(dueMonth("05/2018"), "05/2021")

    def test_second_after_five_years_then_yearly(self):
        self.assertEqual(dueMonth("05/2018", date(2021, 5, 3)), "05/2023")
        self.assertEqual(dueMonth("05/2018", date(2023, 5, 31)), "05/2024")
        self.assertEqual(dueMonth("05/2018", date(2024, 5, 1)), "05/2025")

    def test_one_month_early_counts_for_the_due_month(self):
        self.assertEqual(dueMonth("05/2018", date(2021, 4, 20)), "05/2023")

    def test_too_early_does_not_count(self):
        self.assertEqual(dueMonth("05/2018", date(2021, 3, 20)), "05/2021")

    def test_late_inspection_keeps_schedule(self):
        self.assertEqual(dueMonth("05/2018", date(2021, 8, 1)), "05/2023")

    def test_overdue_and_unknown(self):
        status = buildInspectionStatus("05/2018", None, date(2021, 6, 1))
        self.assertTrue(status["isOverdue"])
        self.assertFalse(buildInspectionStatus("05/2018", None, date(2021, 5, 31))["isOverdue"])
        self.assertIsNone(buildInspectionStatus("unbekannt", None, date(2021, 6, 1)))


if __name__ == "__main__":
    unittest.main()
