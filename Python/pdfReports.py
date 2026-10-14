import io
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


PAGE_WIDTH, PAGE_HEIGHT = A4
CONTENT_WIDTH = PAGE_WIDTH - (36 * mm)
FRAME_PADDING = 6  # default reportlab frame padding in points
TABLE_WIDTH = CONTENT_WIDTH - (2 * FRAME_PADDING)
TEXT_GRAY = colors.HexColor("#666666")


def formatCurrency(value):
    value = value or 0
    formatted = (
        f"{abs(value):,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )
    return f"{'-' if value < 0 else ''}{formatted} €"


def formatHours(value):
    value = value or 0
    formatted = (
        f"{value:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )
    return f"{formatted} h"


def formatDate(value):
    return value.strftime("%d.%m.%Y %H:%M") if value else "–"


def pdfStyles():
    styles = getSampleStyleSheet()
    return {
        "body": ParagraphStyle(
            "GhostTownBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=10,
            textColor=colors.black,
        ),
        "body_right": ParagraphStyle(
            "GhostTownBodyRight",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=10,
            alignment=TA_RIGHT,
            textColor=colors.black,
        ),
        "small": ParagraphStyle(
            "GhostTownSmall",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=8.5,
            textColor=TEXT_GRAY,
        ),
        "small_right": ParagraphStyle(
            "GhostTownSmallRight",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=8.5,
            alignment=TA_RIGHT,
            textColor=TEXT_GRAY,
        ),
        "bold": ParagraphStyle(
            "GhostTownBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=colors.black,
        ),
        "bold_right": ParagraphStyle(
            "GhostTownBoldRight",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            alignment=TA_RIGHT,
            textColor=colors.black,
        ),
        "vehicle": ParagraphStyle(
            "GhostTownVehicle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=13,
            textColor=colors.black,
        ),
        "vehicle_right": ParagraphStyle(
            "GhostTownVehicleRight",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            alignment=TA_RIGHT,
            textColor=colors.black,
        ),
        "order_title": ParagraphStyle(
            "GhostTownOrderTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=13,
            textColor=colors.black,
        ),
        "section": ParagraphStyle(
            "GhostTownSection",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=colors.black,
        ),
    }


def createDocument(buffer, title, vehicle, documentKind, documentHeading):
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title=title,
        author="Ghost Town",
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=25 * mm,
        bottomMargin=25 * mm,
    )
    document.vehicle = vehicle
    document.documentKind = documentKind
    document.documentHeading = documentHeading or ""
    return document


def fitWidths(fractions):
    """Turn width fractions into column widths that fit the frame."""
    return [TABLE_WIDTH * fraction for fraction in fractions]


def plainTableStyle(headerRow=0, lastRow=None):
    """Invoice look: no fills, black rules around the header row."""
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        ("LINEABOVE", (0, headerRow), (-1, headerRow), 0.75, colors.black),
        ("LINEBELOW", (0, headerRow), (-1, headerRow), 0.75, colors.black),
    ]
    if lastRow is not None:
        commands.append(("LINEBELOW", (0, lastRow), (-1, lastRow), 0.75, colors.black))
    return commands


def safeText(value, fallback="–"):
    text = str(value).strip() if value is not None else ""
    return escape(text) if text else fallback


def orderBanner(order, styles):
    status = "Abgeschlossen" if order.isClosed else "Offen"
    statusDetails = f"{status}<br/>{formatDate(order.date)}"
    data = [
        [
            Paragraph(safeText(order.title, "Auftrag"), styles["order_title"]),
            Paragraph(statusDetails, styles["small_right"]),
        ]
    ]
    if order.description:
        data.append([Paragraph(safeText(order.description), styles["body"]), ""])

    table = Table(data, colWidths=fitWidths([0.72, 0.28]), hAlign="LEFT")
    tableStyle = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LINEBELOW", (0, -1), (-1, -1), 0.75, colors.black),
    ]
    if len(data) > 1:
        tableStyle.append(("SPAN", (0, 1), (-1, 1)))
    table.setStyle(TableStyle(tableStyle))
    return table


def detailCell(description, date, styles):
    return Paragraph(
        f"{safeText(description)}"
        f"<br/><font size='7' color='#666666'>{formatDate(date)}</font>",
        styles["body"],
    )


def amountCell(value, styles, forceNegative=False, bold=False):
    displayValue = -abs(value or 0) if forceNegative else (value or 0)
    return Paragraph(
        formatCurrency(displayValue),
        styles["bold_right"] if bold else styles["body_right"],
    )


def hoursCell(value, styles, bold=False):
    return Paragraph(
        formatHours(value),
        styles["bold_right"] if bold else styles["body_right"],
    )


def directOrderTotals(order):
    totalCost = sum(item.purchaseTotal for item in order.costs)
    totalIncome = sum((item.amount or 0) for item in order.incomes)
    totalHours = sum((item.hours or 0) for item in order.times)
    return totalCost, totalIncome, totalHours, totalIncome - totalCost


def ownVehicleTotals(vehicle):
    totalCost = sum(
        cost.purchaseTotal
        for order in vehicle.orders
        for cost in order.costs
    )
    totalIncome = sum(
        (income.amount or 0)
        for order in vehicle.orders
        for income in order.incomes
    )
    totalHours = sum(
        (workTime.hours or 0)
        for order in vehicle.orders
        for workTime in order.times
    )
    return totalCost, totalIncome, totalHours, totalIncome - totalCost


def orderTotals(order):
    totalCost, totalIncome, totalHours, _ = directOrderTotals(order)
    for vehicle in order.attachedVehicles:
        vehicleCost, vehicleIncome, vehicleHours, _ = ownVehicleTotals(vehicle)
        totalCost += vehicleCost
        totalIncome += vehicleIncome
        totalHours += vehicleHours
    return totalCost, totalIncome, totalHours, totalIncome - totalCost


def sectionTable(title, headers, rows, fractions, styles, emptyText, rightColumns=()):
    columnCount = len(headers)
    data = [
        [Paragraph(safeText(title), styles["section"])] + [""] * (columnCount - 1),
        [
            Paragraph(
                safeText(header, "&nbsp;"),
                styles["body_right" if column in rightColumns else "body"],
            )
            for column, header in enumerate(headers)
        ],
    ]
    if rows:
        data.extend(rows)
    else:
        data.append(
            [Paragraph(safeText(emptyText), styles["small"])]
            + [""] * (columnCount - 1)
        )

    table = Table(data, colWidths=fitWidths(fractions), repeatRows=2, hAlign="LEFT")
    tableStyle = plainTableStyle(headerRow=1, lastRow=len(data) - 1)
    tableStyle.extend(
        [
            ("SPAN", (0, 0), (-1, 0)),
            ("TOPPADDING", (0, 0), (-1, 0), 4),
            ("VALIGN", (0, 2), (-1, -1), "TOP"),
        ]
    )
    if not rows:
        tableStyle.append(("SPAN", (0, 2), (-1, 2)))
    table.setStyle(TableStyle(tableStyle))
    return table


def costTable(costs, styles):
    rows = [
        [
            detailCell(item.description, item.date, styles),
            Paragraph(safeText(item.person), styles["body"]),
            Paragraph(f"{item.quantity or 0:g}", styles["body_right"]),
            amountCell(item.amount, styles, forceNegative=True),
            amountCell(item.saleAmount, styles),
            amountCell(item.price, styles),
        ]
        for item in sorted(costs, key=lambda item: item.date or datetime.min)
    ]
    return sectionTable(
        "Positionen",
        ["Beschreibung", "Person", "Menge", "EK", "VK", "Preis"],
        rows,
        [
            0.32,
            0.18,
            0.10,
            0.13,
            0.13,
            0.14,
        ],
        styles,
        "Keine Positionen erfasst",
        rightColumns=(2, 3, 4, 5),
    )


def timeTable(times, styles):
    rows = [
        [
            detailCell(item.description, item.date, styles),
            Paragraph(safeText(item.person), styles["body"]),
            hoursCell(item.hours, styles),
        ]
        for item in sorted(times, key=lambda item: item.date or datetime.min)
    ]
    return sectionTable(
        "Arbeitszeiten",
        ["Beschreibung", "Person", "Stunden"],
        rows,
        [0.57, 0.23, 0.20],
        styles,
        "Keine Arbeitszeiten erfasst",
        rightColumns=(2,),
    )


def incomeTable(incomes, styles):
    rows = [
        [
            detailCell(item.description, item.date, styles),
            Paragraph(safeText(item.person), styles["body"]),
            amountCell(item.amount, styles),
        ]
        for item in sorted(incomes, key=lambda item: item.date or datetime.min)
    ]
    return sectionTable(
        "Einnahmen",
        ["Beschreibung", "Person", "Betrag"],
        rows,
        [0.57, 0.23, 0.20],
        styles,
        "Keine Einnahmen erfasst",
        rightColumns=(2,),
    )


def attachedVehicleTable(vehicles, styles):
    rows = []
    for vehicle in sorted(
        vehicles,
        key=lambda item: (item.brand or "", item.model or "", item.id),
    ):
        totalCost, totalIncome, totalHours, result = ownVehicleTotals(vehicle)
        rows.append(
            [
                Paragraph(safeText(vehicle.displayName), styles["body"]),
                Paragraph(
                    safeText(vehicle.vin or vehicle.licensePlate),
                    styles["body"],
                ),
                amountCell(totalCost, styles, forceNegative=True),
                amountCell(totalIncome, styles),
                hoursCell(totalHours, styles),
                amountCell(result, styles),
            ]
        )

    return sectionTable(
        "Angehängte Fahrzeuge",
        ["Fahrzeug", "FIN/VIN", "EK", "Einnahmen", "Stunden", "Ergebnis"],
        rows,
        [
            0.25,
            0.20,
            0.13,
            0.17,
            0.11,
            0.14,
        ],
        styles,
        "Keine Fahrzeuge angehängt",
        rightColumns=(2, 3, 4, 5),
    )


def summaryTable(totalCost, totalIncome, totalHours, result, styles, title):
    data = [
        [Paragraph(safeText(title), styles["section"]), ""],
        [Paragraph("EK", styles["body"]), amountCell(totalCost, styles, forceNegative=True)],
        [Paragraph("Einnahmen", styles["body"]), amountCell(totalIncome, styles)],
        [Paragraph("Ergebnis", styles["bold"]), amountCell(result, styles, bold=True)],
        [Paragraph("Arbeitszeit", styles["bold"]), hoursCell(totalHours, styles, bold=True)],
    ]
    table = Table(data, colWidths=fitWidths([0.75, 0.25]), hAlign="LEFT")
    tableStyle = plainTableStyle(headerRow=0, lastRow=len(data) - 1)
    tableStyle.extend(
        [
            ("SPAN", (0, 0), (-1, 0)),
            ("TOPPADDING", (0, 0), (-1, 0), 4),
        ]
    )
    table.setStyle(TableStyle(tableStyle))
    return table


def buildOrderPdf(order, totals):
    styles = pdfStyles()
    buffer = io.BytesIO()
    document = createDocument(
        buffer,
        f"Auftrag {order.title}",
        order.vehicle,
        "Auftrag",
        order.title,
    )
    totalCost, totalIncome, totalHours, result = totals

    elements = [
        orderBanner(order, styles),
        Spacer(1, 4 * mm),
    ]
    if order.attachedVehicles:
        elements.extend(
            [
                attachedVehicleTable(order.attachedVehicles, styles),
                Spacer(1, 4 * mm),
            ]
        )
    elements.extend(
        [
            costTable(order.costs, styles),
            Spacer(1, 4 * mm),
            timeTable(order.times, styles),
            Spacer(1, 4 * mm),
            incomeTable(order.incomes, styles),
            Spacer(1, 5 * mm),
            summaryTable(
                totalCost,
                totalIncome,
                totalHours,
                result,
                styles,
                "Zusammenfassung",
            ),
        ]
    )
    document.build(
        elements,
        onFirstPage=drawDocumentPage,
        onLaterPages=drawDocumentPage,
    )
    buffer.seek(0)
    return buffer


def toCents(value):
    return int(round((value or 0) * 100))


def calculateInvoiceDiscounts(subtotal, discounts):
    """Return discount lines (description, cents) and the cent rounding in cents.

    Each discount is (description, isPercent, value). Percentages refer to the
    subtotal before any discount. The rounding always cuts the final total
    down to a full ten cents.
    """
    subtotalCents = toCents(subtotal)
    lines = []
    for description, isPercent, value in discounts:
        cents = (
            int(round(subtotalCents * value / 100))
            if isPercent
            else toCents(value)
        )
        lines.append((description, cents))
    totalCents = subtotalCents - sum(cents for _, cents in lines)
    return lines, totalCents % 10


def formatNumber(value):
    return f"{value or 0:.1f}".replace(".", ",")


def invoiceRows(costs, workers, discounts, roundingCents):
    """Build invoice rows as (kind, description, quantity, price, total) tuples.

    Kinds: "row" (plain line), "sum" (bold subtotal) and "gap" (empty spacer).
    """
    rows = []
    if costs:
        for item in costs:
            rows.append(
                (
                    "row",
                    item.description,
                    formatNumber(item.quantity),
                    formatCurrency(item.saleAmount),
                    formatCurrency(item.price),
                )
            )
        rows.append(
            ("sum", "Summe Teile", "", "", formatCurrency(sum(i.price for i in costs)))
        )
        rows.append(("gap", "", "", "", ""))
    if workers:
        for name, hours, hoursTotal in workers:
            rows.append(
                (
                    "row",
                    f"Arbeitsstunden {name}".strip(),
                    formatNumber(hours),
                    formatCurrency(hoursTotal / hours if hours > 0 else 0),
                    formatCurrency(hoursTotal),
                )
            )
        rows.append(
            (
                "sum",
                "Summe Arbeitsstunden",
                "",
                "",
                formatCurrency(sum(total for _, _, total in workers)),
            )
        )
        rows.append(("gap", "", "", "", ""))
    deductionCents = 0
    for description, isPercent, value, cents in discounts:
        deductionCents += cents
        rows.append(
            (
                "row",
                description,
                f"{value:g} %".replace(".", ",") if isPercent else "",
                "",
                formatCurrency(-cents / 100),
            )
        )
    deductionCents += roundingCents
    rows.append(("row", "Centausgleich", "", "", formatCurrency(-roundingCents / 100)))
    rows.append(("sum", "Summe Sonstige", "", "", formatCurrency(-deductionCents / 100)))
    return rows


def invoiceTable(rows, total, styles):
    data = [
        [
            Paragraph(text, styles["body_right" if column else "body"])
            for column, text in enumerate(
                ["Beschreibung", "AW/Menge", "Preis", "Endpreis"]
            )
        ]
    ]
    for kind, description, quantity, price, amount in rows:
        style = "bold" if kind == "sum" else "body"
        rightStyle = "bold_right" if kind == "sum" else "body_right"
        data.append(
            [
                Paragraph(safeText(description, "&nbsp;"), styles[style]),
                Paragraph(quantity, styles[rightStyle]),
                Paragraph(price, styles[rightStyle]),
                Paragraph(amount, styles[rightStyle]),
            ]
        )
    data.append(
        [
            Paragraph("Summe Gesamt", styles["bold"]),
            "",
            "",
            Paragraph(formatCurrency(total), styles["bold_right"]),
        ]
    )
    lastRow = len(data) - 1
    table = Table(
        data,
        colWidths=[
            TABLE_WIDTH * 0.55,
            TABLE_WIDTH * 0.15,
            TABLE_WIDTH * 0.15,
            TABLE_WIDTH * 0.15,
        ],
        repeatRows=1,
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 1.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
                ("LINEABOVE", (0, 0), (-1, 0), 0.75, colors.black),
                ("LINEBELOW", (0, 0), (-1, 0), 0.75, colors.black),
                ("LINEABOVE", (0, lastRow), (-1, lastRow), 0.75, colors.black),
                ("TOPPADDING", (0, lastRow), (-1, lastRow), 4),
                ("LINEBELOW", (0, lastRow), (-1, lastRow), 0.75, colors.black),
            ]
        )
    )
    return table


def drawDocumentPage(pdfCanvas, document):
    pdfCanvas.saveState()
    left = (18 * mm) + FRAME_PADDING
    right = PAGE_WIDTH - (18 * mm) - FRAME_PADDING
    titleY = PAGE_HEIGHT - (20 * mm)
    pdfCanvas.setFont("Helvetica-Bold", 11)
    pdfCanvas.drawString(left, titleY, document.documentKind)
    pdfCanvas.drawRightString(right, titleY, document.documentHeading)

    footerY = 15 * mm
    pdfCanvas.setFont("Helvetica", 9)
    pdfCanvas.drawString(left, footerY, document.vehicle.displayName or "")
    pdfCanvas.drawRightString(right, footerY, document.vehicle.vin or "")
    pdfCanvas.restoreState()


def buildInvoicePdf(order, costs, workers, discounts=()):
    """workers is a list of (displayName, hours, hoursTotal) tuples."""
    styles = pdfStyles()
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title=f"Rechnung {order.title}",
        author="Ghost Town",
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=25 * mm,
        bottomMargin=25 * mm,
    )
    document.vehicle = order.vehicle
    document.documentKind = "Rechnung"
    document.documentHeading = order.title or ""

    subtotal = sum(item.price for item in costs) + sum(
        total for _, _, total in workers
    )
    discountLines, roundingCents = calculateInvoiceDiscounts(subtotal, discounts)
    discountRows = [
        (description, isPercent, value, cents)
        for (description, isPercent, value), (_, cents) in zip(
            discounts, discountLines
        )
    ]
    totalCents = (
        toCents(subtotal) - sum(cents for _, cents in discountLines) - roundingCents
    )
    rows = invoiceRows(costs, workers, discountRows, roundingCents)
    document.build(
        [invoiceTable(rows, totalCents / 100, styles)],
        onFirstPage=drawDocumentPage,
        onLaterPages=drawDocumentPage,
    )
    buffer.seek(0)
    return buffer


def buildVehiclePdf(vehicle, totals):
    styles = pdfStyles()
    buffer = io.BytesIO()
    document = createDocument(
        buffer,
        f"Fahrzeug {vehicle.displayName}",
        vehicle,
        "Fahrzeug",
        vehicle.licensePlate,
    )
    totalCost, totalIncome, totalHours, result = totals

    elements = []

    orderedOrders = sorted(
        vehicle.orders,
        key=lambda order: order.date or datetime.min,
        reverse=True,
    )
    if not orderedOrders:
        elements.append(
            sectionTable(
                "Aufträge",
                ["Beschreibung", "Status", "Datum"],
                [],
                [
                    0.57,
                    0.20,
                    0.23,
                ],
                styles,
                "Keine Aufträge vorhanden",
            )
        )

    for index, order in enumerate(orderedOrders):
        if index:
            elements.append(Spacer(1, 6 * mm))
        elements.extend(
            [
                orderBanner(order, styles),
                Spacer(1, 3 * mm),
            ]
        )
        if order.costs:
            elements.extend([costTable(order.costs, styles), Spacer(1, 3 * mm)])
        if order.times:
            elements.extend([timeTable(order.times, styles), Spacer(1, 3 * mm)])
        if order.incomes:
            elements.extend(
                [incomeTable(order.incomes, styles), Spacer(1, 3 * mm)]
            )
        if order.attachedVehicles:
            elements.extend(
                [
                    attachedVehicleTable(order.attachedVehicles, styles),
                    Spacer(1, 3 * mm),
                ]
            )

        orderCost, orderIncome, orderHours, orderResult = orderTotals(order)
        elements.append(
            summaryTable(
                orderCost,
                orderIncome,
                orderHours,
                orderResult,
                styles,
                f"Auftragssumme: {order.title}",
            )
        )

    if orderedOrders:
        elements.append(Spacer(1, 7 * mm))

    elements.append(
        summaryTable(
            totalCost,
            totalIncome,
            totalHours,
            result,
            styles,
            "Gesamtsumme Fahrzeug",
        )
    )
    document.build(
        elements,
        onFirstPage=drawDocumentPage,
        onLaterPages=drawDocumentPage,
    )
    buffer.seek(0)
    return buffer


class CheckBox(Flowable):
    """Empty square that can be ticked by hand."""

    SIZE = 3.4 * mm

    def wrap(self, availableWidth, availableHeight):
        return self.SIZE, self.SIZE

    def draw(self):
        self.canv.setLineWidth(0.7)
        self.canv.rect(0, 0, self.SIZE, self.SIZE)


def formatKilometers(value):
    return f"{value:,}".replace(",", ".") + " km"


def formatDateOnly(value):
    return value.strftime("%d.%m.%Y") if value else "–"


def servicePlanIntervalText(item):
    parts = []
    if item["kilometers"]:
        parts.append(formatKilometers(item["kilometers"]))
    if item["months"]:
        parts.append(f"{item['months']} Monate")
    return " / ".join(parts)


def servicePlanLastText(item):
    lastEntry = item["lastEntry"]
    if lastEntry is None:
        return "–"
    return f"{formatDateOnly(lastEntry.date)}<br/>{formatKilometers(lastEntry.mileage)}"


def servicePlanDueText(item):
    parts = []
    if item["dueMileage"]:
        parts.append(formatKilometers(item["dueMileage"]))
    if item["dueDate"]:
        parts.append(formatDateOnly(item["dueDate"]))
    return "<br/>".join(parts) if parts else "–"


def servicePlanIntervalTable(intervals, styles):
    rows = [
        [
            CheckBox(),
            Paragraph(safeText(item["label"]), styles["body"]),
            Paragraph(servicePlanIntervalText(item), styles["body"]),
            Paragraph(servicePlanLastText(item), styles["body"]),
            Paragraph(servicePlanDueText(item), styles["body"]),
        ]
        for item in intervals
    ]
    return sectionTable(
        "Wartung nach Intervall",
        ["OK", "Arbeit", "Intervall", "Zuletzt", "Fällig"],
        rows,
        [
            0.06,
            0.30,
            0.24,
            0.20,
            0.20,
        ],
        styles,
        "Keine Intervalle ausgewählt",
    )


def servicePlanTaskTable(title, tasks, styles):
    rows = [
        [
            CheckBox(),
            Paragraph(safeText(task), styles["body"]),
        ]
        for task in tasks
    ]
    return sectionTable(
        title,
        ["OK", "Arbeit"],
        rows,
        [0.06, 0.94],
        styles,
        "",
    )


def servicePlanSignatureTable(styles):
    labels = ["Datum", "Kilometerstand", "Unterschrift"]
    data = [[Paragraph(label, styles["small"]) for label in labels]]
    table = Table(
        data,
        colWidths=[TABLE_WIDTH / 3] * 3,
        rowHeights=[16 * mm],
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("LINEBELOW", (0, 0), (0, 0), 0.5, colors.black),
                ("LINEBELOW", (1, 0), (1, 0), 0.5, colors.black),
                ("LINEBELOW", (2, 0), (2, 0), 0.5, colors.black),
                ("RIGHTPADDING", (0, 0), (-2, 0), 8 * mm),
            ]
        )
    )
    return table


def buildServicePlanPdf(vehicle, intervals, taskGroups, currentMileage=None):
    """intervals: interval overview dicts, taskGroups: [(title, [task])]."""
    styles = pdfStyles()
    buffer = io.BytesIO()
    document = createDocument(
        buffer,
        f"Serviceplan {vehicle.displayName}",
        vehicle,
        "Serviceplan",
        vehicle.licensePlate,
    )

    mileageText = (
        f"Letzter bekannter Kilometerstand: {formatKilometers(currentMileage)}"
        if currentMileage is not None
        else "Kein Kilometerstand erfasst"
    )
    elements = [
        Paragraph(
            f"Erstellt am {datetime.now().strftime('%d.%m.%Y')} · {mileageText}",
            styles["small"],
        ),
        Spacer(1, 4 * mm),
    ]
    if intervals:
        elements.extend([servicePlanIntervalTable(intervals, styles), Spacer(1, 5 * mm)])
    for title, tasks in taskGroups:
        elements.extend([servicePlanTaskTable(title, tasks, styles), Spacer(1, 5 * mm)])
    elements.append(servicePlanSignatureTable(styles))

    document.build(
        elements,
        onFirstPage=drawDocumentPage,
        onLaterPages=drawDocumentPage,
    )
    buffer.seek(0)
    return buffer
