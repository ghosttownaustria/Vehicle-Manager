"""Calculate fuel consumption between recorded full tanks without storing it."""

from decimal import Decimal


def _decimal(value):
    """Keep database decimals exact and avoid binary-float conversion artifacts."""
    return value if isinstance(value, Decimal) else Decimal(str(value))


def buildFuelStatistics(entries):
    """Return chronological rows and distance-weighted fuel statistics.

    Entries expose id, date, liters, mileage, price and isFullTank attributes.
    A full tank with an odometer reading starts a measuring interval. All fuel
    after it, including the next full tank with a reading, belongs to that
    interval. The starting fill and unfinished intervals do not contribute to
    consumption. Full tanks without readings are included as intermediate fills.

    A decreasing recorded odometer reading invalidates its entire interval.
    Each full tank with a reading becomes the next baseline, allowing recovery
    after corrected readings. isBaseline marks rows that start a measurement
    without closing a valid interval. Missing prices never count as zero when
    calculating costs per kilometer or the average price per liter.
    """
    zero = Decimal("0")
    hundred = Decimal("100")
    rows = []
    summary = {
        "count": 0,
        "totalLiters": zero,
        "totalPrice": zero,
        "missingPriceCount": 0,
        "averagePricePerLiter": None,
        "distance": 0,
        "intervalLiters": zero,
        "averageConsumption": None,
        "averageCentsPerKm": None,
        "intervalCount": 0,
    }
    pricedLiters = zero
    intervalTotalPrice = zero
    completedPricesKnown = True
    baseline = None
    previousMileage = None
    pendingLiters = zero
    pendingPrice = zero
    pendingPricesKnown = True
    pendingMileageValid = True

    for entry in sorted(entries, key=lambda item: (item.date, item.id)):
        liters = _decimal(entry.liters)
        price = _decimal(entry.price) if entry.price is not None else None
        summary["count"] += 1
        summary["totalLiters"] += liters
        if price is None:
            summary["missingPriceCount"] += 1
        else:
            summary["totalPrice"] += price
            pricedLiters += liters

        row = {"entry": entry, "interval": None, "isBaseline": False}
        rows.append(row)
        isBoundary = entry.isFullTank and entry.mileage is not None

        if baseline is not None:
            pendingLiters += liters
            if price is None:
                pendingPricesKnown = False
            else:
                pendingPrice += price
            if entry.mileage is not None:
                if entry.mileage < previousMileage:
                    pendingMileageValid = False
                previousMileage = entry.mileage

            if isBoundary:
                distance = entry.mileage - baseline.mileage
                if distance > 0 and pendingMileageValid:
                    row["interval"] = {
                        "distance": distance,
                        "liters": pendingLiters,
                        "price": pendingPrice if pendingPricesKnown else None,
                        "consumption": pendingLiters * hundred / distance,
                        "centsPerKm": (
                            pendingPrice * hundred / distance
                            if pendingPricesKnown else None
                        ),
                    }
                    summary["distance"] += distance
                    summary["intervalLiters"] += pendingLiters
                    summary["intervalCount"] += 1
                    intervalTotalPrice += pendingPrice
                    completedPricesKnown &= pendingPricesKnown

        if isBoundary:
            row["isBaseline"] = row["interval"] is None
            baseline = entry
            previousMileage = entry.mileage
            pendingLiters = zero
            pendingPrice = zero
            pendingPricesKnown = True
            pendingMileageValid = True

    if pricedLiters > 0:
        summary["averagePricePerLiter"] = summary["totalPrice"] / pricedLiters
    if summary["distance"] > 0:
        summary["averageConsumption"] = (
            summary["intervalLiters"] * hundred / summary["distance"]
        )
        if completedPricesKnown:
            summary["averageCentsPerKm"] = (
                intervalTotalPrice * hundred / summary["distance"]
            )

    return {"rows": rows, "summary": summary}
