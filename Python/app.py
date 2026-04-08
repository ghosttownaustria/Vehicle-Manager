from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

from flask import send_file
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io

from functools import wraps


def loginRequired(f):
    @wraps(f)
    def decoratedFunction(*args, **kwargs):
        if "userId" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decoratedFunction

# ===============================
# DATABASE RESET SWITCH
# Set to True to completely reset the database on startup
# ===============================

isResetDatabaseOnStartup = False  # <-- set to True if you want to reset

app = Flask(__name__)
app.secret_key = "CHANGE_THIS_TO_RANDOM_SECRET_KEY_123456"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///vehicles.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    passwordHash = db.Column(db.String(200), nullable=False)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.passwordHash, password):
            session["userId"] = user.id
            return redirect(url_for("index"))

        return "Invalid credentials"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


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

    orders = db.relationship("Order", backref="vehicle", lazy=True)

    @property
    def displayName(self):
        return f"{self.brand} {self.model}"


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200))
    description = db.Column(db.String(500))
    date = db.Column(db.DateTime, default=datetime.utcnow)

    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicle.id"))

    costs = db.relationship("Cost", backref="order", lazy=True)
    times = db.relationship("WorkTime", backref="order", lazy=True)
    incomes = db.relationship("Income", backref="order", lazy=True)


class Cost(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    description = db.Column(db.String(200))
    amount = db.Column(db.Float)
    person = db.Column(db.String(100))
    date = db.Column(db.DateTime)

    order_id = db.Column(db.Integer, db.ForeignKey("order.id"))


class WorkTime(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    description = db.Column(db.String(200))
    hours = db.Column(db.Float)
    person = db.Column(db.String(100))
    date = db.Column(db.DateTime)

    order_id = db.Column(db.Integer, db.ForeignKey("order.id"))


class Income(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    description = db.Column(db.String(200))
    amount = db.Column(db.Float)
    person = db.Column(db.String(100))
    date = db.Column(db.DateTime)

    order_id = db.Column(db.Integer, db.ForeignKey("order.id"))


@app.route("/")
@loginRequired
def index():
    vehicles = Vehicle.query.all()
    return render_template("index.html", vehicles=vehicles)


@app.route("/add_vehicle", methods=["GET", "POST"])
@loginRequired
def addVehicle():

    if request.method == "POST":

        newVehicle = Vehicle(
            brand=request.form["brand"],
            model=request.form["model"],
            vin=request.form["vin"],

            firstRegistration=request.form["firstRegistration"],
            engineOil=request.form["engineOil"],
            gearboxOil=request.form["gearboxOil"],
            diffOil=request.form["diffOil"],
            coolant=request.form["coolant"],
            fuel=request.form["fuel"],
            engineCode=request.form["engineCode"],
            licensePlate=request.form["licensePlate"]
        )

        db.session.add(newVehicle)
        db.session.commit()

        return redirect(url_for("index"))

    # VERY IMPORTANT → return page if GET request
    return render_template("add_vehicle.html")


@app.route("/vehicle/<int:vehicleId>", methods=["GET", "POST"])
@loginRequired
def vehicle(vehicleId):
    vehicle = Vehicle.query.get_or_404(vehicleId)

    totalCost = sum(
        cost.amount
        for order in vehicle.orders
        for cost in order.costs
    )

    totalHours = sum(
        time.hours
        for order in vehicle.orders
        for time in order.times
    )

    totalIncome = sum(
        income.amount
        for order in vehicle.orders
        for income in order.incomes
    )

    result = totalIncome - totalCost

    if request.method == "POST":

        if "cost_submit" in request.form:
            description = request.form["cost_description"]
            amount = float(request.form["amount"])
            person = request.form["cost_person"]
            dateInput = request.form["cost_date"]

            if dateInput:
                dateValue = datetime.fromisoformat(dateInput)
            else:
                dateValue = datetime.utcnow()

        if "time_submit" in request.form:
            description = request.form["time_description"]
            hours = float(request.form["hours"])
            person = request.form["time_person"]
            dateInput = request.form["time_date"]

            if dateInput:
                dateValue = datetime.fromisoformat(dateInput)
            else:
                dateValue = datetime.utcnow()

            newTime = WorkTime(
                description=description,
                hours=hours,
                person=person,
                date=dateValue,
                vehicle=vehicle
            )

            db.session.add(newTime)

        db.session.commit()
        return redirect(url_for("vehicle", vehicleId=vehicle.id))

    totalCost = sum(
        cost.amount
        for order in vehicle.orders
        for cost in order.costs
    )

    totalHours = sum(
        time.hours
        for order in vehicle.orders
        for time in order.times
    )

    totalIncome = sum(
        income.amount
        for order in vehicle.orders
        for income in order.incomes
    )

    return render_template(
        "vehicle.html",
        vehicle=vehicle,
        totalCost=totalCost,
        totalHours=totalHours,
        totalIncome=totalIncome,
        result=result
    )


@app.route("/edit_vehicle/<int:vehicleId>", methods=["GET", "POST"])
@loginRequired
def editVehicle(vehicleId):

    vehicle = Vehicle.query.get_or_404(vehicleId)

    if request.method == "POST":

        vehicle.brand = request.form["brand"]
        vehicle.model = request.form["model"]
        vehicle.vin = request.form["vin"]

        vehicle.firstRegistration = request.form["firstRegistration"]
        vehicle.engineOil = request.form["engineOil"]
        vehicle.gearboxOil = request.form["gearboxOil"]
        vehicle.diffOil = request.form["diffOil"]
        vehicle.coolant = request.form["coolant"]
        vehicle.fuel = request.form["fuel"]
        vehicle.engineCode = request.form["engineCode"]
        vehicle.licensePlate = request.form["licensePlate"]

        db.session.commit()

        return redirect(url_for("vehicle", vehicleId=vehicle.id))

    return render_template("edit_vehicle.html", vehicle=vehicle)


@app.route("/edit_cost/<int:costId>", methods=["GET", "POST"])
@loginRequired
def editCost(costId):
    cost = Cost.query.get_or_404(costId)

    if request.method == "POST":
        cost.description = request.form["description"]
        cost.amount = float(request.form["amount"])
        cost.person = request.form["person"]

        dateInput = request.form["date"]
        if dateInput:
            cost.date = datetime.fromisoformat(dateInput)
        else:
            cost.date = datetime.utcnow()

        db.session.commit()
        return redirect(url_for("order", orderId=cost.order.id))

    return render_template("edit_cost.html", cost=cost)


@app.route("/edit_time/<int:timeId>", methods=["GET", "POST"])
@loginRequired
def editTime(timeId):
    workTime = WorkTime.query.get_or_404(timeId)

    if request.method == "POST":
        workTime.description = request.form["description"]
        workTime.hours = float(request.form["hours"])
        workTime.person = request.form["person"]

        dateInput = request.form["date"]
        if dateInput:
            workTime.date = datetime.fromisoformat(dateInput)
        else:
            workTime.date = datetime.utcnow()

        db.session.commit()
        return redirect(url_for("vehicle", vehicleId=workTime.vehicle.id))

    return render_template("edit_time.html", workTime=workTime)


@app.route("/delete_cost/<int:costId>", methods=["POST"])
@loginRequired
def deleteCost(costId):
    cost = Cost.query.get_or_404(costId)
    orderId = cost.order.id

    db.session.delete(cost)
    db.session.commit()

    return redirect(url_for("order", orderId=orderId))


@app.route("/delete_time/<int:timeId>", methods=["POST"])
@loginRequired
def deleteTime(timeId):
    workTime = WorkTime.query.get_or_404(timeId)
    vehicleId = workTime.vehicle.id

    db.session.delete(workTime)
    db.session.commit()

    return redirect(url_for("vehicle", vehicleId=vehicleId))


@app.route("/delete_vehicle/<int:vehicleId>", methods=["POST"])
@loginRequired
def deleteVehicle(vehicleId):
    vehicle = Vehicle.query.get_or_404(vehicleId)

    # Delete related entries first
    for order in vehicle.orders:

        for cost in order.costs:
            db.session.delete(cost)

        for time in order.times:
            db.session.delete(time)

        for income in order.incomes:
            db.session.delete(income)

        db.session.delete(order)

    for time in vehicle.times:
        db.session.delete(time)

    db.session.delete(vehicle)
    db.session.commit()

    return redirect(url_for("index"))



@app.route("/vehicle/<int:vehicleId>/add_order", methods=["GET", "POST"])
@loginRequired
def addOrder(vehicleId):

    vehicle = Vehicle.query.get_or_404(vehicleId)

    if request.method == "POST":

        newOrder = Order(
            title=request.form["title"],
            description=request.form["description"],
            vehicle=vehicle
        )

        db.session.add(newOrder)
        db.session.commit()

        return redirect(url_for("vehicle", vehicleId=vehicle.id))

    return render_template("add_order.html", vehicle=vehicle)


@app.route("/order/<int:orderId>", methods=["GET", "POST"])
@loginRequired
def order(orderId):

    order = Order.query.get_or_404(orderId)

    if request.method == "POST":

        # ADD COST
        if "cost_submit" in request.form:

            newCost = Cost(
                description=request.form["description"],
                amount=float(request.form["amount"]),
                person=request.form["person"],
                date=datetime.utcnow(),
                order=order
            )

            db.session.add(newCost)

        # ADD WORK TIME
        if "time_submit" in request.form:

            newTime = WorkTime(
                description=request.form["description"],
                hours=float(request.form["hours"]),
                person=request.form["person"],
                date=datetime.utcnow(),
                order=order
            )

            db.session.add(newTime)

        # ADD INCOME
        if "income_submit" in request.form:

            newIncome = Income(
                description=request.form["description"],
                amount=float(request.form["amount"]),
                person=request.form["person"],
                date=datetime.utcnow(),
                order=order
            )

            db.session.add(newIncome)

        db.session.commit()

        return redirect(url_for("order", orderId=order.id))

    totalCost = sum(c.amount for c in order.costs)
    totalIncome = sum(i.amount for i in order.incomes)
    totalHours = sum(t.hours for t in order.times)

    result = totalIncome - totalCost

    return render_template(
        "order.html",
        order=order,
        costs=order.costs,
        times=order.times,
        incomes=order.incomes,
        totalCost=totalCost,
        totalIncome=totalIncome,
        totalHours=totalHours,
        result=result
    )


@app.route("/order/<int:orderId>/print")
@loginRequired
def printOrder(orderId):

    order = Order.query.get_or_404(orderId)

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()

    elements = []

    # Titel
    elements.append(Paragraph(f"Order Report: {order.title}", styles["Title"]))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph(f"Vehicle: {order.vehicle.displayName}", styles["Normal"]))
    elements.append(Paragraph(f"Date: {order.date}", styles["Normal"]))
    elements.append(Spacer(1, 10))

    # Costs
    elements.append(Paragraph("Costs:", styles["Heading2"]))
    totalCost = 0

    for c in order.costs:
        elements.append(Paragraph(
            f"{c.date.strftime('%Y-%m-%d %H:%M')} - {c.description} - {c.amount}€ ({c.person})",
            styles["Normal"]
        ))
        totalCost += c.amount

    elements.append(Spacer(1, 10))

    # Work
    elements.append(Paragraph("Work Times:", styles["Heading2"]))
    totalHours = 0

    for t in order.times:
        elements.append(Paragraph(
            f"{t.date.strftime('%Y-%m-%d %H:%M')} - {t.description} - {t.hours}h ({t.person})",
            styles["Normal"]
        ))
        totalHours += t.hours

    elements.append(Spacer(1, 10))

    # Income
    elements.append(Paragraph("Income:", styles["Heading2"]))
    totalIncome = 0

    for i in order.incomes:
        elements.append(Paragraph(
            f"{i.date.strftime('%Y-%m-%d %H:%M')} - {i.description} - {i.amount}€ ({i.person})",
            styles["Normal"]
        ))
        totalIncome += i.amount

    elements.append(Spacer(1, 20))

    # Summary
    result = totalIncome - totalCost

    elements.append(Paragraph("Summary:", styles["Heading2"]))
    elements.append(Paragraph(f"Total Cost: {totalCost} €", styles["Normal"]))
    elements.append(Paragraph(f"Total Income: {totalIncome} €", styles["Normal"]))
    elements.append(Paragraph(f"Result: {result} €", styles["Normal"]))
    elements.append(Paragraph(f"Total Hours: {totalHours} h", styles["Normal"]))

    # PDF bauen
    doc.build(elements)

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"order_{order.id}.pdf",
        mimetype="application/pdf"
    )


@app.route("/vehicle/<int:vehicleId>/print")
@loginRequired
def printVehicle(vehicleId):

    vehicle = Vehicle.query.get_or_404(vehicleId)

    import io
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()

    elements = []

    # Titel
    elements.append(Paragraph(f"Vehicle Report: {vehicle.displayName}", styles["Title"]))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph(f"VIN: {vehicle.vin}", styles["Normal"]))
    elements.append(Spacer(1, 10))

    totalCost = 0
    totalIncome = 0
    totalHours = 0

    # Alle Orders durchgehen
    for order in vehicle.orders:

        elements.append(Paragraph(f"Order: {order.title}", styles["Heading2"]))
        elements.append(Spacer(1, 5))

        # Costs
        elements.append(Paragraph("Costs:", styles["Heading3"]))
        for c in order.costs:
            elements.append(Paragraph(
                f"{c.date.strftime('%Y-%m-%d %H:%M')} - {c.description} - {c.amount}€ ({c.person})",
                styles["Normal"]
            ))
            totalCost += c.amount

        elements.append(Spacer(1, 5))

        # Work Times
        elements.append(Paragraph("Work Times:", styles["Heading3"]))
        for t in order.times:
            elements.append(Paragraph(
                f"{t.date.strftime('%Y-%m-%d %H:%M')} - {t.description} - {t.hours}h ({t.person})",
                styles["Normal"]
            ))
            totalHours += t.hours

        elements.append(Spacer(1, 5))

        # Income
        elements.append(Paragraph("Income:", styles["Heading3"]))
        for i in order.incomes:
            elements.append(Paragraph(
                f"{i.date.strftime('%Y-%m-%d %H:%M')} - {i.description} - {i.amount}€ ({i.person})",
                styles["Normal"]
            ))
            totalIncome += i.amount

        elements.append(Spacer(1, 15))

    # Gesamtübersicht
    result = totalIncome - totalCost

    elements.append(Paragraph("Vehicle Summary", styles["Heading2"]))
    elements.append(Paragraph(f"Total Cost: {totalCost} €", styles["Normal"]))
    elements.append(Paragraph(f"Total Income: {totalIncome} €", styles["Normal"]))
    elements.append(Paragraph(f"Result: {result} €", styles["Normal"]))
    elements.append(Paragraph(f"Total Hours: {totalHours} h", styles["Normal"]))

    # PDF bauen
    doc.build(elements)

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"vehicle_{vehicle.id}.pdf",
        mimetype="application/pdf"
    )

if __name__ == "__main__":
    with app.app_context():

        if isResetDatabaseOnStartup:
            print("Resetting database...")
            db.drop_all()
            db.create_all()
            print("Database recreated.")
        else:
            db.create_all()

    # Make the app accessible in the local network
    app.run(host="0.0.0.0", port=5000, debug=True)