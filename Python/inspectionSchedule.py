"""Austrian §57a KFG inspection schedule ("Pickerl") for passenger cars.

Inspections fall due in fixed months counted from the first registration:
after 3 years, after 5 years, then every year. Only month and year matter;
the inspection is valid until the end of the due month and may be done one
month early without moving the schedule.
"""

import re

FIRST_INSPECTION_MONTHS = 36
SECOND_INSPECTION_MONTHS = 60
YEARLY_INSPECTION_MONTHS = 12
MAX_SCHEDULE_YEARS = 100

# Accepts "05/2018", "5.2018", "2018-05", "15.05.2018" and "2018-05-15"; any day is ignored.
_MONTH_FIRST = re.compile(r"^(?:\d{1,2}[./-])?(\d{1,2})[./-](\d{4})$")
_YEAR_FIRST = re.compile(r"^(\d{4})[./-](\d{1,2})(?:[./-]\d{1,2})?$")


def parseRegistrationMonth(text):
    """Return (year, month) from a free-text first registration, or None."""
    value = (text or "").strip()
    match = _MONTH_FIRST.match(value)
    if match:
        month, year = int(match.group(1)), int(match.group(2))
    else:
        match = _YEAR_FIRST.match(value)
        if not match:
            return None
        year, month = int(match.group(1)), int(match.group(2))
    if not 1 <= month <= 12 or year < 1900:
        return None
    return year, month


def monthIndex(year, month):
    return year * 12 + month - 1


def formatMonthIndex(index):
    return f"{index % 12 + 1:02d}/{index // 12}"


def inspectionDueMonthIndexes(registration):
    """Yield the month indexes (year * 12 + month - 1) at which inspections fall due."""
    start = monthIndex(*registration)
    yield start + FIRST_INSPECTION_MONTHS
    offset = SECOND_INSPECTION_MONTHS
    for _ in range(MAX_SCHEDULE_YEARS):
        yield start + offset
        offset += YEARLY_INSPECTION_MONTHS


def nextInspectionDue(registration, lastInspectionDate=None):
    """Return the next due month index, or None without a valid registration."""
    if registration is None:
        return None
    minimum = None
    if lastInspectionDate is not None:
        # An inspection counts for the due month it is done in or one month before.
        minimum = monthIndex(lastInspectionDate.year, lastInspectionDate.month) + 1
    return next(
        (due for due in inspectionDueMonthIndexes(registration)
         if minimum is None or due > minimum),
        None,
    )


def buildInspectionStatus(registrationText, lastInspectionDate, today):
    """Return the due month and whether it is overdue, or None if unknown."""
    due = nextInspectionDue(parseRegistrationMonth(registrationText), lastInspectionDate)
    if due is None:
        return None
    return {
        "dueMonth": formatMonthIndex(due),
        "isOverdue": due < monthIndex(today.year, today.month),
        "isDueSoon": due <= monthIndex(today.year, today.month) + 2,
    }
