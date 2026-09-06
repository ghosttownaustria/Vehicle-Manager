"""Estimate current mileage from recorded service history without storing it."""

from datetime import date


def projectMileage(entries, today=None):
    """Return a current-mileage estimate, or None without a usable past interval.

    For multiple entries on one day, use the last recorded entry. Daily mileage
    is weighted by the duration of each interval. Decreasing odometer readings
    are treated as corrections and excluded from the average.
    """
    if today is None:
        today = date.today()

    samplesByDate = {}
    for entry in sorted(entries, key=lambda item: (item["date"], item["id"])):
        samplesByDate[date.fromisoformat(entry["date"])] = entry["mileage"]

    samples = list(samplesByDate.items())
    if len(samples) < 2 or samples[-1][0] >= today:
        return None

    totalMileage = 0
    totalDays = 0
    for (previousDate, previousMileage), (sampleDate, sampleMileage) in zip(
        samples, samples[1:]
    ):
        difference = sampleMileage - previousMileage
        if difference >= 0:
            totalMileage += difference
            totalDays += (sampleDate - previousDate).days

    if not totalDays:
        return None

    latestDate, latestMileage = samples[-1]
    dailyMileage = totalMileage / totalDays
    projectedMileage = latestMileage + dailyMileage * (today - latestDate).days
    return {
        "date": today.isoformat(),
        "mileage": round(projectedMileage),
        "dailyMileage": dailyMileage,
    }
