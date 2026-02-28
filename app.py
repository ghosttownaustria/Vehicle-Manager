from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# ===============================
# DATABASE RESET SWITCH
# Set to True to completely reset the database on startup
# ===============================

isResetDatabaseOnStartup = False  # <-- set to True if you want to reset

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///vehicles.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    vin = db.Column(db.String(50), nullable=False)

    costs = db.relationship("Cost", backref="vehicle", lazy=True)
    times = db.relationship("WorkTime", backref="vehicle", lazy=True)

    @property
    def displayName(self):
        return f"{self.brand} {self.model}"


class Cost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200))
    amount = db.Column(db.Float)
    person = db.Column(db.String(100))
    date = db.Column(db.DateTime, nullable=False)

    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicle.id"), nullable=False)


class WorkTime(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200))
    hours = db.Column(db.Float)
    person = db.Column(db.String(100))
    date = db.Column(db.DateTime, nullable=False)

    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicle.id"), nullable=False)


@app.route("/")
def index():
    vehicles = Vehicle.query.all()
    return render_template("index.html", vehicles=vehicles)


@app.route("/add_vehicle", methods=["GET", "POST"])
def addVehicle():
    if request.method == "POST":
        brand = request.form["brand"]
        model = request.form["model"]
        vin = request.form["vin"]

        newVehicle = Vehicle(
            brand=brand,
            model=model,
            vin=vin
        )

        db.session.add(newVehicle)
        db.session.commit()
        return redirect(url_for("index"))

    return render_template("add_vehicle.html")


@app.route("/vehicle/<int:vehicleId>", methods=["GET", "POST"])
def vehicle(vehicleId):
    vehicle = Vehicle.query.get_or_404(vehicleId)

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

            newCost = Cost(
                description=description,
                amount=amount,
                person=person,
                date=dateValue,
                vehicle=vehicle
            )

            db.session.add(newCost)

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

    totalCost = sum(c.amount for c in vehicle.costs)
    totalHours = sum(t.hours for t in vehicle.times)

    return render_template(
        "vehicle.html",
        vehicle=vehicle,
        totalCost=totalCost,
        totalHours=totalHours
    )


@app.route("/edit_vehicle/<int:vehicleId>", methods=["GET", "POST"])
def editVehicle(vehicleId):
    vehicle = Vehicle.query.get_or_404(vehicleId)

    if request.method == "POST":
        vehicle.brand = request.form["brand"]
        vehicle.model = request.form["model"]
        vehicle.vin = request.form["vin"]

        db.session.commit()
        return redirect(url_for("vehicle", vehicleId=vehicle.id))

    return render_template("edit_vehicle.html", vehicle=vehicle)


@app.route("/edit_cost/<int:costId>", methods=["GET", "POST"])
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
        return redirect(url_for("vehicle", vehicleId=cost.vehicle.id))

    return render_template("edit_cost.html", cost=cost)


@app.route("/edit_time/<int:timeId>", methods=["GET", "POST"])
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
def deleteCost(costId):
    cost = Cost.query.get_or_404(costId)
    vehicleId = cost.vehicle.id

    db.session.delete(cost)
    db.session.commit()

    return redirect(url_for("vehicle", vehicleId=vehicleId))


@app.route("/delete_time/<int:timeId>", methods=["POST"])
def deleteTime(timeId):
    workTime = WorkTime.query.get_or_404(timeId)
    vehicleId = workTime.vehicle.id

    db.session.delete(workTime)
    db.session.commit()

    return redirect(url_for("vehicle", vehicleId=vehicleId))


@app.route("/delete_vehicle/<int:vehicleId>", methods=["POST"])
def deleteVehicle(vehicleId):
    vehicle = Vehicle.query.get_or_404(vehicleId)

    # Delete related entries first
    for cost in vehicle.costs:
        db.session.delete(cost)

    for time in vehicle.times:
        db.session.delete(time)

    db.session.delete(vehicle)
    db.session.commit()

    return redirect(url_for("index"))


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