import io
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


PAGE_WIDTH, PAGE_HEIGHT = A4
CONTENT_WIDTH = PAGE_WIDTH - (36 * mm)
TABLE_GRAY = colors.HexColor("#d9d9d9")
TEXT_GRAY = colors.HexColor("#666666")
NEGATIVE_RED = colors.HexColor("#ff0000")


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
        "negative": ParagraphStyle(
            "GhostTownNegative",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=10,
            alignment=TA_RIGHT,
            textColor=NEGATIVE_RED,
        ),
        "negative_bold": ParagraphStyle(
            "GhostTownNegativeBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            alignment=TA_RIGHT,
            textColor=NEGATIVE_RED,
        ),
    }


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._savedPageStates = []
        self._printedAt = datetime.now()

    def showPage(self):
        self._savedPageStates.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        pageCount = len(self._savedPageStates)
        for state in self._savedPageStates:
            self.__dict__.update(state)
            self.drawFooter(pageCount)
            super().showPage()
        super().save()

    def drawFooter(self, pageCount):
        self.saveState()
        self.setFillColor(colors.black)
        self.setFont("Helvetica", 7.5)
        self.drawString(
            18 * mm,
            11 * mm,
            f"Seite {self._pageNumber} von {pageCount}",
        )
        self.drawRightString(
            PAGE_WIDTH - (18 * mm),
            11 * mm,
            f"Druckdatum: {self._printedAt.strftime('%d.%m.%Y %H:%M')}",
        )
        self.restoreState()


def drawFourPointStar(pdfCanvas, centerX, centerY, size=5):
    path = pdfCanvas.beginPath()
    path.moveTo(centerX, centerY + size)
    path.lineTo(centerX + size * 0.28, centerY + size * 0.28)
    path.lineTo(centerX + size, centerY)
    path.lineTo(centerX + size * 0.28, centerY - size * 0.28)
    path.lineTo(centerX, centerY - size)
    path.lineTo(centerX - size * 0.28, centerY - size * 0.28)
    path.lineTo(centerX - size, centerY)
    path.lineTo(centerX - size * 0.28, centerY + size * 0.28)
    path.close()
    pdfCanvas.drawPath(path, fill=1, stroke=0)


def drawBrandHeader(pdfCanvas, document):
    pdfCanvas.saveState()
    title = "Ghost Town"
    titleY = PAGE_HEIGHT - (18 * mm)
    pdfCanvas.setFillColor(colors.black)
    pdfCanvas.setFont("Times-Bold", 24)
    pdfCanvas.drawCentredString(PAGE_WIDTH / 2, titleY, title)

    titleWidth = pdfCanvas.stringWidth(title, "Times-Bold", 24)
    starOffset = (titleWidth / 2) + (10 * mm)
    starY = titleY + 7
    drawFourPointStar(pdfCanvas, (PAGE_WIDTH / 2) - starOffset, starY, 6)
    drawFourPointStar(pdfCanvas, (PAGE_WIDTH / 2) + starOffset, starY, 6)

    vehicle = document.vehicle
    vehicleY = PAGE_HEIGHT - (29 * mm)
    pdfCanvas.setFont("Helvetica-Bold", 11)
    pdfCanvas.drawString(
        18 * mm,
        vehicleY,
        vehicle.displayName or "Unbenanntes Fahrzeug",
    )
    pdfCanvas.setFont("Helvetica-Bold", 9)
    pdfCanvas.drawRightString(
        PAGE_WIDTH - (18 * mm),
        vehicleY,
        vehicle.vin or "Keine FIN/VIN",
    )
    pdfCanvas.restoreState()


def createDocument(buffer, title, vehicle):
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title=title,
        author="Ghost Town",
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=39 * mm,
        bottomMargin=20 * mm,
    )
    document.vehicle = vehicle
    return document


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
        data.append(
            [
                Paragraph(safeText(order.description), styles["body"]),
                "",
            ]
        )

    table = Table(
        data,
        colWidths=[CONTENT_WIDTH * 0.72, CONTENT_WIDTH * 0.28],
    )
    tableStyle = [
        ("BACKGROUND", (0, 0), (-1, 0), TABLE_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, 0), 5),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
    ]
    if len(data) > 1:
        tableStyle.extend(
            [
                ("SPAN", (0, 1), (-1, 1)),
                ("TOPPADDING", (0, 1), (-1, 1), 5),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 5),
            ]
        )
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
    if displayValue < 0:
        style = styles["negative_bold"] if bold else styles["negative"]
    else:
        style = styles["bold_right"] if bold else styles["body_right"]
    return Paragraph(formatCurrency(displayValue), style)


def hoursCell(value, styles, bold=False):
    return Paragraph(
        formatHours(value),
        styles["bold_right"] if bold else styles["body_right"],
    )


def directOrderTotals(order):
    totalCost = sum((item.amount or 0) for item in order.costs)
    totalIncome = sum((item.amount or 0) for item in order.incomes)
    totalHours = sum((item.hours or 0) for item in order.times)
    return totalCost, totalIncome, totalHours, totalIncome - totalCost


def ownVehicleTotals(vehicle):
    totalCost = sum(
        (cost.amount or 0)
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


def sectionTable(title, headers, rows, widths, styles, emptyText):
    columnCount = len(headers)
    data = [
        [Paragraph(safeText(title), styles["section"])]
        + [""] * (columnCount - 1),
        [Paragraph(safeText(header), styles["bold"]) for header in headers],
    ]
    if rows:
        data.extend(rows)
    else:
        data.append(
            [Paragraph(safeText(emptyText), styles["small"])]
            + [""] * (columnCount - 1)
        )

    table = Table(
        data,
        colWidths=widths,
        repeatRows=2,
        hAlign="LEFT",
    )
    tableStyle = [
        ("SPAN", (0, 0), (-1, 0)),
        ("BACKGROUND", (0, 1), (-1, 1), TABLE_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
        ("TOPPADDING", (0, 1), (-1, 1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 4),
        ("ALIGN", (-1, 1), (-1, -1), "RIGHT"),
    ]

    for rowIndex in range(2, len(data)):
        if (rowIndex - 2) % 2 == 0:
            tableStyle.append(
                ("BACKGROUND", (0, rowIndex), (-1, rowIndex), TABLE_GRAY)
            )
        tableStyle.extend(
            [
                ("TOPPADDING", (0, rowIndex), (-1, rowIndex), 2.5),
                ("BOTTOMPADDING", (0, rowIndex), (-1, rowIndex), 2.5),
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
            amountCell(item.amount, styles, forceNegative=True),
            amountCell(item.saleAmount, styles),
        ]
        for item in sorted(costs, key=lambda item: item.date or datetime.min)
    ]
    return sectionTable(
        "Ausgaben",
        ["Beschreibung", "Person", "EK", "VK"],
        rows,
        [
            CONTENT_WIDTH * 0.48,
            CONTENT_WIDTH * 0.22,
            CONTENT_WIDTH * 0.15,
            CONTENT_WIDTH * 0.15,
        ],
        styles,
        "Keine Ausgaben erfasst",
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
        [CONTENT_WIDTH * 0.57, CONTENT_WIDTH * 0.23, CONTENT_WIDTH * 0.20],
        styles,
        "Keine Arbeitszeiten erfasst",
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
        [CONTENT_WIDTH * 0.57, CONTENT_WIDTH * 0.23, CONTENT_WIDTH * 0.20],
        styles,
        "Keine Einnahmen erfasst",
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
            CONTENT_WIDTH * 0.25,
            CONTENT_WIDTH * 0.20,
            CONTENT_WIDTH * 0.13,
            CONTENT_WIDTH * 0.17,
            CONTENT_WIDTH * 0.11,
            CONTENT_WIDTH * 0.14,
        ],
        styles,
        "Keine Fahrzeuge angehängt",
    )


def summaryTable(totalCost, totalIncome, totalHours, result, styles, title):
    data = [
        [
            Paragraph(safeText(title), styles["section"]),
            "",
        ],
        [
            Paragraph("EK", styles["body"]),
            amountCell(totalCost, styles, forceNegative=True),
        ],
        [
            Paragraph("Einnahmen", styles["body"]),
            amountCell(totalIncome, styles),
        ],
        [
            Paragraph("Ergebnis", styles["bold"]),
            amountCell(result, styles, bold=True),
        ],
        [
            Paragraph("Arbeitszeit", styles["bold"]),
            hoursCell(totalHours, styles, bold=True),
        ],
    ]
    table = Table(
        data,
        colWidths=[CONTENT_WIDTH * 0.75, CONTENT_WIDTH * 0.25],
    )
    table.setStyle(
        TableStyle(
            [
                ("SPAN", (0, 0), (-1, 0)),
                ("BACKGROUND", (0, 1), (-1, 1), TABLE_GRAY),
                ("BACKGROUND", (0, 3), (-1, 3), TABLE_GRAY),
                ("BACKGROUND", (0, 4), (-1, 4), TABLE_GRAY),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, 0), 6),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
                ("TOPPADDING", (0, 1), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
            ]
        )
    )
    return table


def buildOrderPdf(order, totals):
    styles = pdfStyles()
    buffer = io.BytesIO()
    document = createDocument(
        buffer,
        f"Auftrag {order.title}",
        order.vehicle,
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
        onFirstPage=drawBrandHeader,
        onLaterPages=drawBrandHeader,
        canvasmaker=NumberedCanvas,
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
                    CONTENT_WIDTH * 0.57,
                    CONTENT_WIDTH * 0.20,
                    CONTENT_WIDTH * 0.23,
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
        onFirstPage=drawBrandHeader,
        onLaterPages=drawBrandHeader,
        canvasmaker=NumberedCanvas,
    )
    buffer.seek(0)
    return buffer
