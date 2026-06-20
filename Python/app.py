import io
import os
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask_sqlalchemy import SQLAlchemy
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy import inspect, text
from werkzeug.security import check_password_hash


def loginRequired(function):
    @wraps(function)
    def decoratedFunction(*args, **kwargs):
        if "userId" not in session:
            flash("Bitte zuerst anmelden.", "warning")
            return redirect(url_for("login"))
        return function(*args, **kwargs)

    return decoratedFunction


# Set to True only when the whole database should be deleted on startup.
isResetDatabaseOnStartup = False

app = Flask(__name__)
app.secret_key = os.environ.get(
    "VEHICLE_MANAGER_SECRET_KEY",
    "CHANGE_THIS_TO_RANDOM_SECRET_KEY_123456",
)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "VEHICLE_MANAGER_DATABASE_URI",
    "sqlite:///vehicles.db",
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "connect_args": {"timeout": 5},
}

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    passwordHash = db.Column(db.String(200), nullable=False)


class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    brand = db.Column(db.String(100))
    model = db.Column(db.String(100))
    vin = db.Column(db.String(50))

    firstRegistration = db.Column(db.String(20))
    engineOil = db.Column(db.String(50))
    gearboxOil = db.Column(db.String(50))
    diffOil = db.Column(db.String(50))
    coolant = db.Column(db.String(50))
    fuel = db.Column(db.String(50))
    engineCode = db.Column(db.String(50))
    licensePlate = db.Column(db.String(20))

    orders = db.relationship(
        "Order",
        backref="vehicle",
        lazy=True,
        cascade="all, delete-orphan",
    )

    @property
    def displayName(self):
        return f"{self.brand or ''} {self.model or ''}".strip()


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200))
    description = db.Column(db.String(500))
    date = db.Column(db.DateTime, default=datetime.now)
    isClosed = db.Column(db.Boolean, nullable=False, default=False)
    closedAt = db.Column(db.DateTime, nullable=True)

    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicle.id"), nullable=False)

    costs = db.relationship(
        "Cost",
        backref="order",
        lazy=True,
        cascade="all, delete-orphan",
    )
    times = db.relationship(
        "WorkTime",
        backref="order",
        lazy=True,
        cascade="all, delete-orphan",
    )
    incomes = db.relationship(
        "Income",
        backref="order",
        lazy=True,
        cascade="all, delete-orphan",
    )


class Cost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200))
    amount = db.Column(db.Float)
    person = db.Column(db.String(100))
    date = db.Column(db.DateTime)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)


class WorkTime(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200))
    hours = db.Column(db.Float)
    person = db.Column(db.String(100))
    date = db.Column(db.DateTime)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)


class Income(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200))
    amount = db.Column(db.Float)
    person = db.Column(db.String(100))
    date = db.Column(db.DateTime)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)


def initializeDatabase():
    """Create new tables and add missing columns to older SQLite databases."""
    db.create_all()

    inspector = inspect(db.engine)
    if "order" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("order")}
    migrations = []

    if "isClosed" not in columns:
        migrations.append(
            'ALTER TABLE "order" '
            'ADD COLUMN "isClosed" BOOLEAN NOT NULL DEFAULT 0'
        )
    if "closedAt" not in columns:
        migrations.append(
            'ALTER TABLE "order" ADD COLUMN "closedAt" DATETIME'
        )

    if migrations:
        with db.engine.begin() as connection:
            for statement in migrations:
                connection.execute(text(statement))


def parseFormDate(value):
    if not value:
        return datetime.now()
    return datetime.fromisoformat(value)


def orderTotals(orderItem):
    totalCost = sum((item.amount or 0) for item in orderItem.costs)
    totalIncome = sum((item.amount or 0) for item in orderItem.incomes)
    totalHours = sum((item.hours or 0) for item in orderItem.times)
    return totalCost, totalIncome, totalHours, totalIncome - totalCost


def vehicleTotals(vehicleItem):
    totalCost = sum(
        (cost.amount or 0)
        for orderItem in vehicleItem.orders
        for cost in orderItem.costs
    )
    totalIncome = sum(
        (income.amount or 0)
        for orderItem in vehicleItem.orders
        for income in orderItem.incomes
    )
    totalHours = sum(
        (workTime.hours or 0)
        for orderItem in vehicleItem.orders
        for workTime in orderItem.times
    )
    return totalCost, totalIncome, totalHours, totalIncome - totalCost


def closedOrderRedirect(orderItem):
    flash(
        "Dieser Auftrag ist abgeschlossen und kann nicht mehr bearbeitet werden.",
        "warning",
    )
    return redirect(url_for("order", orderId=orderItem.id))


@app.template_filter("currency")
def currencyFilter(value):
    return f"{(value or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@app.template_filter("dateTime")
def dateTimeFilter(value):
    return value.strftime("%d.%m.%Y %H:%M") if value else "–"


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.passwordHash, password):
            session["userId"] = user.id
            flash("Erfolgreich angemeldet.", "success")
            return redirect(url_for("index"))

        flash("E-Mail-Adresse oder Passwort ist falsch.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Du wurdest abgemeldet.", "info")
    return redirect(url_for("login"))


@app.route("/")
@loginRequired
def index():
    vehicles = Vehicle.query.order_by(Vehicle.brand, Vehicle.model).all()
    openOrderCount = Order.query.filter_by(isClosed=False).count()
    closedOrderCount = Order.query.filter_by(isClosed=True).count()
    return render_template(
        "index.html",
        vehicles=vehicles,
        openOrderCount=openOrderCount,
        closedOrderCount=closedOrderCount,
    )


@app.route("/orders")
@loginRequired
def orders():
    showClosed = request.args.get("status") == "closed"
    orderItems = (
        Order.query.filter_by(isClosed=showClosed)
        .order_by(Order.date.desc(), Order.id.desc())
        .all()
    )
    return render_template(
        "orders.html",
        orders=orderItems,
        showClosed=showClosed,
        openCount=Order.query.filter_by(isClosed=False).count(),
        closedCount=Order.query.filter_by(isClosed=True).count(),
    )


@app.route("/add_vehicle", methods=["GET", "POST"])
@loginRequired
def addVehicle():
    if request.method == "POST":
        newVehicle = Vehicle(
            brand=request.form.get("brand", "").strip(),
            model=request.form.get("model", "").strip(),
            vin=request.form.get("vin", "").strip(),
            firstRegistration=request.form.get("firstRegistration", "").strip(),
            engineOil=request.form.get("engineOil", "").strip(),
            gearboxOil=request.form.get("gearboxOil", "").strip(),
            diffOil=request.form.get("diffOil", "").strip(),
            coolant=request.form.get("coolant", "").strip(),
            fuel=request.form.get("fuel", "").strip(),
            engineCode=request.form.get("engineCode", "").strip(),
            licensePlate=request.form.get("licensePlate", "").strip(),
        )
        db.session.add(newVehicle)
        db.session.commit()
        flash("Fahrzeug wurde angelegt.", "success")
        return redirect(url_for("vehicle", vehicleId=newVehicle.id))

    return render_template("add_vehicle.html")


@app.route("/vehicle/<int:vehicleId>")
@loginRequired
def vehicle(vehicleId):
    vehicleItem = Vehicle.query.get_or_404(vehicleId)
    openOrders = sorted(
        (item for item in vehicleItem.orders if not item.isClosed),
        key=lambda item: item.date or datetime.min,
        reverse=True,
    )
    closedOrders = sorted(
        (item for item in vehicleItem.orders if item.isClosed),
        key=lambda item: item.closedAt or item.date or datetime.min,
        reverse=True,
    )
    totalCost, totalIncome, totalHours, result = vehicleTotals(vehicleItem)

    return render_template(
        "vehicle.html",
        vehicle=vehicleItem,
        openOrders=openOrders,
        closedOrders=closedOrders,
        totalCost=totalCost,
        totalHours=totalHours,
        totalIncome=totalIncome,
        result=result,
    )


@app.route("/edit_vehicle/<int:vehicleId>", methods=["GET", "POST"])
@loginRequired
def editVehicle(vehicleId):
    vehicleItem = Vehicle.query.get_or_404(vehicleId)

    if request.method == "POST":
        vehicleItem.brand = request.form.get("brand", "").strip()
        vehicleItem.model = request.form.get("model", "").strip()
        vehicleItem.vin = request.form.get("vin", "").strip()
        vehicleItem.firstRegistration = request.form.get(
            "firstRegistration", ""
        ).strip()
        vehicleItem.engineOil = request.form.get("engineOil", "").strip()
        vehicleItem.gearboxOil = request.form.get("gearboxOil", "").strip()
        vehicleItem.diffOil = request.form.get("diffOil", "").strip()
        vehicleItem.coolant = request.form.get("coolant", "").strip()
        vehicleItem.fuel = request.form.get("fuel", "").strip()
        vehicleItem.engineCode = request.form.get("engineCode", "").strip()
        vehicleItem.licensePlate = request.form.get("licensePlate", "").strip()
        db.session.commit()
        flash("Fahrzeugdaten wurden gespeichert.", "success")
        return redirect(url_for("vehicle", vehicleId=vehicleItem.id))

    return render_template("edit_vehicle.html", vehicle=vehicleItem)


@app.route("/delete_vehicle/<int:vehicleId>", methods=["POST"])
@loginRequired
def deleteVehicle(vehicleId):
    vehicleItem = Vehicle.query.get_or_404(vehicleId)

    if any(orderItem.isClosed for orderItem in vehicleItem.orders):
        flash(
            "Das Fahrzeug enthält abgeschlossene Aufträge und kann deshalb "
            "nicht gelöscht werden.",
            "danger",
        )
        return redirect(url_for("editVehicle", vehicleId=vehicleItem.id))

    db.session.delete(vehicleItem)
    db.session.commit()
    flash("Fahrzeug wurde gelöscht.", "success")
    return redirect(url_for("index"))


@app.route("/vehicle/<int:vehicleId>/add_order", methods=["GET", "POST"])
@loginRequired
def addOrder(vehicleId):
    vehicleItem = Vehicle.query.get_or_404(vehicleId)

    if request.method == "POST":
        newOrder = Order(
            title=request.form.get("title", "").strip(),
            description=request.form.get("description", "").strip(),
            date=parseFormDate(request.form.get("date")),
            vehicle=vehicleItem,
        )
        db.session.add(newOrder)
        db.session.commit()
        flash("Auftrag wurde angelegt.", "success")
        return redirect(url_for("order", orderId=newOrder.id))

    return render_template("add_order.html", vehicle=vehicleItem)


@app.route("/order/<int:orderId>", methods=["GET", "POST"])
@loginRequired
def order(orderId):
    orderItem = Order.query.get_or_404(orderId)

    if request.method == "POST":
        if orderItem.isClosed:
            return closedOrderRedirect(orderItem)

        description = request.form.get("description", "").strip()
        person = request.form.get("person", "").strip()
        entryDate = parseFormDate(request.form.get("date"))

        if "cost_submit" in request.form:
            db.session.add(
                Cost(
                    description=description,
                    amount=float(request.form["amount"]),
                    person=person,
                    date=entryDate,
                    order=orderItem,
                )
            )
            message = "Ausgabe wurde hinzugefügt."
        elif "time_submit" in request.form:
            db.session.add(
                WorkTime(
                    description=description,
                    hours=float(request.form["hours"]),
                    person=person,
                    date=entryDate,
                    order=orderItem,
                )
            )
            message = "Arbeitszeit wurde hinzugefügt."
        elif "income_submit" in request.form:
            db.session.add(
                Income(
                    description=description,
                    amount=float(request.form["amount"]),
                    person=person,
                    date=entryDate,
                    order=orderItem,
                )
            )
            message = "Einnahme wurde hinzugefügt."
        else:
            flash("Unbekannte Aktion.", "danger")
            return redirect(url_for("order", orderId=orderItem.id))

        db.session.commit()
        flash(message, "success")
        return redirect(url_for("order", orderId=orderItem.id))

    totalCost, totalIncome, totalHours, result = orderTotals(orderItem)
    return render_template(
        "order.html",
        order=orderItem,
        costs=sorted(
            orderItem.costs,
            key=lambda item: item.date or datetime.min,
            reverse=True,
        ),
        times=sorted(
            orderItem.times,
            key=lambda item: item.date or datetime.min,
            reverse=True,
        ),
        incomes=sorted(
            orderItem.incomes,
            key=lambda item: item.date or datetime.min,
            reverse=True,
        ),
        totalCost=totalCost,
        totalIncome=totalIncome,
        totalHours=totalHours,
        result=result,
    )


@app.route("/order/<int:orderId>/edit", methods=["GET", "POST"])
@loginRequired
def editOrder(orderId):
    orderItem = Order.query.get_or_404(orderId)
    if orderItem.isClosed:
        return closedOrderRedirect(orderItem)

    if request.method == "POST":
        orderItem.title = request.form.get("title", "").strip()
        orderItem.description = request.form.get("description", "").strip()
        orderItem.date = parseFormDate(request.form.get("date"))
        db.session.commit()
        flash("Auftrag wurde gespeichert.", "success")
        return redirect(url_for("order", orderId=orderItem.id))

    return render_template("edit_order.html", order=orderItem)


@app.route("/order/<int:orderId>/close", methods=["POST"])
@loginRequired
def closeOrder(orderId):
    orderItem = Order.query.get_or_404(orderId)

    if orderItem.isClosed:
        flash("Der Auftrag ist bereits abgeschlossen.", "info")
    else:
        orderItem.isClosed = True
        orderItem.closedAt = datetime.now()
        db.session.commit()
        flash(
            "Auftrag abgeschlossen. Er ist ab jetzt schreibgeschützt.",
            "success",
        )

    return redirect(url_for("order", orderId=orderItem.id))


@app.route("/edit_cost/<int:costId>", methods=["GET", "POST"])
@loginRequired
def editCost(costId):
    cost = Cost.query.get_or_404(costId)
    if cost.order.isClosed:
        return closedOrderRedirect(cost.order)

    if request.method == "POST":
        cost.description = request.form.get("description", "").strip()
        cost.amount = float(request.form["amount"])
        cost.person = request.form.get("person", "").strip()
        cost.date = parseFormDate(request.form.get("date"))
        db.session.commit()
        flash("Ausgabe wurde gespeichert.", "success")
        return redirect(url_for("order", orderId=cost.order.id))

    return render_template("edit_cost.html", cost=cost)


@app.route("/edit_time/<int:timeId>", methods=["GET", "POST"])
@loginRequired
def editTime(timeId):
    workTime = WorkTime.query.get_or_404(timeId)
    if workTime.order.isClosed:
        return closedOrderRedirect(workTime.order)

    if request.method == "POST":
        workTime.description = request.form.get("description", "").strip()
        workTime.hours = float(request.form["hours"])
        workTime.person = request.form.get("person", "").strip()
        workTime.date = parseFormDate(request.form.get("date"))
        db.session.commit()
        flash("Arbeitszeit wurde gespeichert.", "success")
        return redirect(url_for("order", orderId=workTime.order.id))

    return render_template("edit_time.html", workTime=workTime)


@app.route("/edit_income/<int:incomeId>", methods=["GET", "POST"])
@loginRequired
def editIncome(incomeId):
    income = Income.query.get_or_404(incomeId)
    if income.order.isClosed:
        return closedOrderRedirect(income.order)

    if request.method == "POST":
        income.description = request.form.get("description", "").strip()
        income.amount = float(request.form["amount"])
        income.person = request.form.get("person", "").strip()
        income.date = parseFormDate(request.form.get("date"))
        db.session.commit()
        flash("Einnahme wurde gespeichert.", "success")
        return redirect(url_for("order", orderId=income.order.id))

    return render_template("edit_income.html", income=income)


@app.route("/delete_cost/<int:costId>", methods=["POST"])
@loginRequired
def deleteCost(costId):
    cost = Cost.query.get_or_404(costId)
    orderItem = cost.order
    if orderItem.isClosed:
        return closedOrderRedirect(orderItem)

    db.session.delete(cost)
    db.session.commit()
    flash("Ausgabe wurde gelöscht.", "success")
    return redirect(url_for("order", orderId=orderItem.id))


@app.route("/delete_time/<int:timeId>", methods=["POST"])
@loginRequired
def deleteTime(timeId):
    workTime = WorkTime.query.get_or_404(timeId)
    orderItem = workTime.order
    if orderItem.isClosed:
        return closedOrderRedirect(orderItem)

    db.session.delete(workTime)
    db.session.commit()
    flash("Arbeitszeit wurde gelöscht.", "success")
    return redirect(url_for("order", orderId=orderItem.id))


@app.route("/delete_income/<int:incomeId>", methods=["POST"])
@loginRequired
def deleteIncome(incomeId):
    income = Income.query.get_or_404(incomeId)
    orderItem = income.order
    if orderItem.isClosed:
        return closedOrderRedirect(orderItem)

    db.session.delete(income)
    db.session.commit()
    flash("Einnahme wurde gelöscht.", "success")
    return redirect(url_for("order", orderId=orderItem.id))


def safePdfDate(value):
    return value.strftime("%d.%m.%Y %H:%M") if value else "-"


@app.route("/order/<int:orderId>/print")
@loginRequired
def printOrder(orderId):
    orderItem = Order.query.get_or_404(orderId)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph(f"Auftrag: {orderItem.title}", styles["Title"]),
        Spacer(1, 10),
        Paragraph(f"Fahrzeug: {orderItem.vehicle.displayName}", styles["Normal"]),
        Paragraph(f"Datum: {safePdfDate(orderItem.date)}", styles["Normal"]),
        Paragraph(
            f"Status: {'Abgeschlossen' if orderItem.isClosed else 'Offen'}",
            styles["Normal"],
        ),
        Spacer(1, 10),
        Paragraph("Ausgaben", styles["Heading2"]),
    ]

    for item in orderItem.costs:
        elements.append(
            Paragraph(
                f"{safePdfDate(item.date)} - {item.description} - "
                f"{item.amount:.2f} EUR ({item.person})",
                styles["Normal"],
            )
        )

    elements.extend([Spacer(1, 10), Paragraph("Arbeitszeiten", styles["Heading2"])])
    for item in orderItem.times:
        elements.append(
            Paragraph(
                f"{safePdfDate(item.date)} - {item.description} - "
                f"{item.hours:.2f} h ({item.person})",
                styles["Normal"],
            )
        )

    elements.extend([Spacer(1, 10), Paragraph("Einnahmen", styles["Heading2"])])
    for item in orderItem.incomes:
        elements.append(
            Paragraph(
                f"{safePdfDate(item.date)} - {item.description} - "
                f"{item.amount:.2f} EUR ({item.person})",
                styles["Normal"],
            )
        )

    totalCost, totalIncome, totalHours, result = orderTotals(orderItem)
    elements.extend(
        [
            Spacer(1, 20),
            Paragraph("Zusammenfassung", styles["Heading2"]),
            Paragraph(f"Ausgaben: {totalCost:.2f} EUR", styles["Normal"]),
            Paragraph(f"Einnahmen: {totalIncome:.2f} EUR", styles["Normal"]),
            Paragraph(f"Ergebnis: {result:.2f} EUR", styles["Normal"]),
            Paragraph(f"Arbeitszeit: {totalHours:.2f} h", styles["Normal"]),
        ]
    )
    doc.build(elements)
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"auftrag_{orderItem.id}.pdf",
        mimetype="application/pdf",
    )


@app.route("/vehicle/<int:vehicleId>/print")
@loginRequired
def printVehicle(vehicleId):
    vehicleItem = Vehicle.query.get_or_404(vehicleId)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph(f"Fahrzeug: {vehicleItem.displayName}", styles["Title"]),
        Spacer(1, 10),
        Paragraph(f"FIN/VIN: {vehicleItem.vin or '-'}", styles["Normal"]),
        Spacer(1, 10),
    ]

    for orderItem in vehicleItem.orders:
        elements.extend(
            [
                Paragraph(
                    f"Auftrag: {orderItem.title} "
                    f"({'Abgeschlossen' if orderItem.isClosed else 'Offen'})",
                    styles["Heading2"],
                ),
                Paragraph("Ausgaben", styles["Heading3"]),
            ]
        )
        for item in orderItem.costs:
            elements.append(
                Paragraph(
                    f"{safePdfDate(item.date)} - {item.description} - "
                    f"{item.amount:.2f} EUR ({item.person})",
                    styles["Normal"],
                )
            )

        elements.append(Paragraph("Arbeitszeiten", styles["Heading3"]))
        for item in orderItem.times:
            elements.append(
                Paragraph(
                    f"{safePdfDate(item.date)} - {item.description} - "
                    f"{item.hours:.2f} h ({item.person})",
                    styles["Normal"],
                )
            )

        elements.append(Paragraph("Einnahmen", styles["Heading3"]))
        for item in orderItem.incomes:
            elements.append(
                Paragraph(
                    f"{safePdfDate(item.date)} - {item.description} - "
                    f"{item.amount:.2f} EUR ({item.person})",
                    styles["Normal"],
                )
            )
        elements.append(Spacer(1, 15))

    totalCost, totalIncome, totalHours, result = vehicleTotals(vehicleItem)
    elements.extend(
        [
            Paragraph("Fahrzeug-Zusammenfassung", styles["Heading2"]),
            Paragraph(f"Ausgaben: {totalCost:.2f} EUR", styles["Normal"]),
            Paragraph(f"Einnahmen: {totalIncome:.2f} EUR", styles["Normal"]),
            Paragraph(f"Ergebnis: {result:.2f} EUR", styles["Normal"]),
            Paragraph(f"Arbeitszeit: {totalHours:.2f} h", styles["Normal"]),
        ]
    )
    doc.build(elements)
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"fahrzeug_{vehicleItem.id}.pdf",
        mimetype="application/pdf",
    )


with app.app_context():
    initializeDatabase()


if __name__ == "__main__":
    with app.app_context():
        if isResetDatabaseOnStartup:
            print("Datenbank wird zurückgesetzt...")
            db.drop_all()
        initializeDatabase()

    app.run(host="0.0.0.0", port=5000, debug=True)
