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
from pdfReports import buildOrderPdf, buildVehiclePdf
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


orderAttachedVehicle = db.Table(
    "order_attached_vehicle",
    db.Column(
        "order_id",
        db.Integer,
        db.ForeignKey("order.id"),
        primary_key=True,
    ),
    db.Column(
        "vehicle_id",
        db.Integer,
        db.ForeignKey("vehicle.id"),
        primary_key=True,
    ),
)


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
    lastOpenedAt = db.Column(db.DateTime, nullable=True)

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
    lastOpenedAt = db.Column(db.DateTime, nullable=True)

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
    attachedVehicles = db.relationship(
        "Vehicle",
        secondary=orderAttachedVehicle,
        lazy=True,
        backref=db.backref("attachedToOrders", lazy=True),
    )


class Cost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200))
    amount = db.Column(db.Float)
    saleAmount = db.Column(db.Float, nullable=False, default=0)
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
    tableNames = set(inspector.get_table_names())
    migrations = []

    if "vehicle" in tableNames:
        vehicleColumns = {
            column["name"] for column in inspector.get_columns("vehicle")
        }
        if "lastOpenedAt" not in vehicleColumns:
            migrations.append(
                'ALTER TABLE "vehicle" ADD COLUMN "lastOpenedAt" DATETIME'
            )

    if "order" in tableNames:
        orderColumns = {
            column["name"] for column in inspector.get_columns("order")
        }
        if "isClosed" not in orderColumns:
            migrations.append(
                'ALTER TABLE "order" '
                'ADD COLUMN "isClosed" BOOLEAN NOT NULL DEFAULT 0'
            )
        if "closedAt" not in orderColumns:
            migrations.append(
                'ALTER TABLE "order" ADD COLUMN "closedAt" DATETIME'
            )
        if "lastOpenedAt" not in orderColumns:
            migrations.append(
                'ALTER TABLE "order" ADD COLUMN "lastOpenedAt" DATETIME'
            )

    if "cost" in tableNames:
        costColumns = {
            column["name"] for column in inspector.get_columns("cost")
        }
        if "saleAmount" not in costColumns:
            migrations.append(
                'ALTER TABLE "cost" ADD COLUMN "saleAmount" FLOAT NOT NULL DEFAULT 0'
            )

    if migrations:
        with db.engine.begin() as connection:
            for statement in migrations:
                connection.execute(text(statement))


def parseFormDate(value):
    if not value:
        return datetime.now()
    return datetime.fromisoformat(value)


def parseFormAmount(value):
    if value is None or str(value).strip() == "":
        return 0
    return float(str(value).replace(",", "."))


def parseFormInteger(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def directOrderTotals(orderItem):
    totalCost = sum((item.amount or 0) for item in orderItem.costs)
    totalIncome = sum((item.amount or 0) for item in orderItem.incomes)
    totalHours = sum((item.hours or 0) for item in orderItem.times)
    return totalCost, totalIncome, totalHours, totalIncome - totalCost


def addTotals(firstTotals, secondTotals):
    return tuple(
        first + second for first, second in zip(firstTotals, secondTotals)
    )


def ownVehicleTotals(vehicleItem):
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


def orderTotals(orderItem):
    totals = directOrderTotals(orderItem)
    for attachedVehicle in orderItem.attachedVehicles:
        totals = addTotals(totals, ownVehicleTotals(attachedVehicle))
    return totals


def vehicleTotals(vehicleItem):
    totalCost, totalIncome, totalHours, _ = ownVehicleTotals(vehicleItem)
    attachedVehicleIds = set()

    for orderItem in vehicleItem.orders:
        for attachedVehicle in orderItem.attachedVehicles:
            if attachedVehicle.id in attachedVehicleIds:
                continue
            attachedVehicleIds.add(attachedVehicle.id)
            (
                attachedCost,
                attachedIncome,
                attachedHours,
                _,
            ) = ownVehicleTotals(attachedVehicle)
            totalCost += attachedCost
            totalIncome += attachedIncome
            totalHours += attachedHours

    return totalCost, totalIncome, totalHours, totalIncome - totalCost


def totalsSummary(item, totals):
    totalCost, totalIncome, totalHours, result = totals
    return {
        "item": item,
        "totalCost": totalCost,
        "totalIncome": totalIncome,
        "totalHours": totalHours,
        "result": result,
    }


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
    vehicles = Vehicle.query.order_by(
        Vehicle.lastOpenedAt.desc().nullslast(),
        Vehicle.brand,
        Vehicle.model,
        Vehicle.id,
    ).all()
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
        .order_by(
            Order.lastOpenedAt.desc().nullslast(),
            Order.date.desc(),
            Order.id.desc(),
        )
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
    vehicleItem.lastOpenedAt = datetime.now()
    db.session.commit()

    openOrders = sorted(
        (item for item in vehicleItem.orders if not item.isClosed),
        key=lambda item: (
            item.lastOpenedAt or datetime.min,
            item.date or datetime.min,
            item.id,
        ),
        reverse=True,
    )
    closedOrders = sorted(
        (item for item in vehicleItem.orders if item.isClosed),
        key=lambda item: (
            item.lastOpenedAt or datetime.min,
            item.closedAt or item.date or datetime.min,
            item.id,
        ),
        reverse=True,
    )
    attachedOrders = sorted(
        vehicleItem.attachedToOrders,
        key=lambda item: (
            item.lastOpenedAt or datetime.min,
            item.date or datetime.min,
            item.id,
        ),
        reverse=True,
    )
    totalCost, totalIncome, totalHours, result = vehicleTotals(vehicleItem)

    return render_template(
        "vehicle.html",
        vehicle=vehicleItem,
        openOrders=openOrders,
        closedOrders=closedOrders,
        attachedOrders=attachedOrders,
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

    if any(orderItem.isClosed for orderItem in vehicleItem.attachedToOrders):
        flash(
            "Das Fahrzeug ist an abgeschlossene Auftraege angehaengt und "
            "kann deshalb nicht geloescht werden.",
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

        if "cost_submit" in request.form:
            db.session.add(
                Cost(
                    description=request.form.get("description", "").strip(),
                    amount=parseFormAmount(request.form.get("amount")),
                    saleAmount=parseFormAmount(
                        request.form.get("saleAmount")
                    ),
                    person=request.form.get("person", "").strip(),
                    date=parseFormDate(request.form.get("date")),
                    order=orderItem,
                )
            )
            message = "Ausgabe wurde hinzugefügt."
        elif "time_submit" in request.form:
            db.session.add(
                WorkTime(
                    description=request.form.get("description", "").strip(),
                    hours=parseFormAmount(request.form.get("hours")),
                    person=request.form.get("person", "").strip(),
                    date=parseFormDate(request.form.get("date")),
                    order=orderItem,
                )
            )
            message = "Arbeitszeit wurde hinzugefügt."
        elif "income_submit" in request.form:
            db.session.add(
                Income(
                    description=request.form.get("description", "").strip(),
                    amount=parseFormAmount(request.form.get("amount")),
                    person=request.form.get("person", "").strip(),
                    date=parseFormDate(request.form.get("date")),
                    order=orderItem,
                )
            )
            message = "Einnahme wurde hinzugefügt."
        elif "attach_vehicle_submit" in request.form:
            attachedVehicleId = parseFormInteger(
                request.form.get("attached_vehicle_id")
            )
            attachedVehicle = (
                Vehicle.query.get(attachedVehicleId)
                if attachedVehicleId
                else None
            )
            if not attachedVehicle:
                flash("Fahrzeug zum Anhaengen wurde nicht gefunden.", "danger")
                return redirect(url_for("order", orderId=orderItem.id))
            if attachedVehicle.id == orderItem.vehicle_id:
                flash(
                    "Das Hauptfahrzeug ist bereits mit diesem Auftrag verbunden.",
                    "warning",
                )
                return redirect(url_for("order", orderId=orderItem.id))
            if attachedVehicle in orderItem.attachedVehicles:
                flash("Dieses Fahrzeug ist bereits angehaengt.", "info")
                return redirect(url_for("order", orderId=orderItem.id))

            orderItem.attachedVehicles.append(attachedVehicle)
            message = "Fahrzeug wurde an den Auftrag angehaengt."
        else:
            flash("Unbekannte Aktion.", "danger")
            return redirect(url_for("order", orderId=orderItem.id))

        db.session.commit()
        flash(message, "success")
        return redirect(url_for("order", orderId=orderItem.id))

    orderItem.lastOpenedAt = datetime.now()
    db.session.commit()

    totalCost, totalIncome, totalHours, result = orderTotals(orderItem)
    directCost = sum((item.amount or 0) for item in orderItem.costs)
    directIncome = sum((item.amount or 0) for item in orderItem.incomes)
    directHours = sum((item.hours or 0) for item in orderItem.times)
    attachedVehicleSummaries = [
        totalsSummary(attachedVehicle, ownVehicleTotals(attachedVehicle))
        for attachedVehicle in sorted(
            orderItem.attachedVehicles,
            key=lambda item: (item.brand or "", item.model or "", item.id),
        )
    ]
    attachedVehicleIds = {
        attachedVehicle.id for attachedVehicle in orderItem.attachedVehicles
    }
    attachableVehicles = [
        vehicleItem
        for vehicleItem in Vehicle.query.order_by(
            Vehicle.brand,
            Vehicle.model,
            Vehicle.id,
        ).all()
        if vehicleItem.id != orderItem.vehicle_id
        and vehicleItem.id not in attachedVehicleIds
    ]
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
        directCost=directCost,
        directIncome=directIncome,
        directHours=directHours,
        attachedVehicleSummaries=attachedVehicleSummaries,
        attachableVehicles=attachableVehicles,
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


@app.route("/order/<int:orderId>/detach_vehicle/<int:vehicleId>", methods=["POST"])
@loginRequired
def detachVehicleFromOrder(orderId, vehicleId):
    orderItem = Order.query.get_or_404(orderId)
    if orderItem.isClosed:
        return closedOrderRedirect(orderItem)

    attachedVehicle = Vehicle.query.get_or_404(vehicleId)
    if attachedVehicle in orderItem.attachedVehicles:
        orderItem.attachedVehicles.remove(attachedVehicle)
        db.session.commit()
        flash("Fahrzeug wurde vom Auftrag geloest.", "success")
    else:
        flash("Dieses Fahrzeug ist nicht an den Auftrag angehaengt.", "info")

    return redirect(url_for("order", orderId=orderItem.id))


@app.route("/edit_cost/<int:costId>", methods=["GET", "POST"])
@loginRequired
def editCost(costId):
    cost = Cost.query.get_or_404(costId)
    if cost.order.isClosed:
        return closedOrderRedirect(cost.order)

    if request.method == "POST":
        cost.description = request.form.get("description", "").strip()
        cost.amount = parseFormAmount(request.form.get("amount"))
        cost.saleAmount = parseFormAmount(request.form.get("saleAmount"))
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
        workTime.hours = parseFormAmount(request.form.get("hours"))
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
        income.amount = parseFormAmount(request.form.get("amount"))
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


@app.route("/order/<int:orderId>/print")
@loginRequired
def printOrder(orderId):
    orderItem = Order.query.get_or_404(orderId)
    buffer = buildOrderPdf(orderItem, orderTotals(orderItem))
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
    buffer = buildVehiclePdf(vehicleItem, vehicleTotals(vehicleItem))
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
