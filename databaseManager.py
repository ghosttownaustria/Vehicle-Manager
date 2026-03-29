import json
from app import app, db, User, Vehicle, Order, Cost, WorkTime, Income
from werkzeug.security import generate_password_hash
from datetime import datetime

def parseDate(dateValue):
    if dateValue is None:
        return datetime.utcnow()

    # Already datetime
    if isinstance(dateValue, datetime):
        return dateValue

    # String → datetime
    if isinstance(dateValue, str):
        try:
            return datetime.fromisoformat(dateValue)
        except:
            return datetime.utcnow()

    # Fallback
    return datetime.utcnow()

def clearScreen():
    print("\n" * 50)

def wait():
    input("\nPress Enter to continue...")

def listUsers():
    users = User.query.all()

    print("\n=== USERS ===")
    for u in users:
        print(f"{u.id} - {u.email}")

def addUser():
    print("\n=== ADD USER ===")
    email = input("Email: ")
    password = input("Password: ")

    user = User(
        email=email,
        passwordHash=generate_password_hash(password)
    )

    db.session.add(user)
    db.session.commit()

    print("User created.")

def deleteUser():
    listUsers()
    userId = int(input("\nUser ID to delete: "))

    user = User.query.get(userId)

    if user:
        db.session.delete(user)
        db.session.commit()
        print("User deleted.")

def listVehicles():
    vehicles = Vehicle.query.all()

    print("\n=== VEHICLES ===")
    for v in vehicles:
        print(f"{v.id} - {v.brand} {v.model} ({v.vin})")

def listOrders():
    orders = Order.query.all()

    print("\n=== ORDERS ===")
    for o in orders:
        print(f"{o.id} - {o.title} (Vehicle {o.vehicle_id})")

def listAllDetails():
    print("\n=== FULL DATABASE ===")

    for v in Vehicle.query.all():
        print(f"\nVehicle {v.id}: {v.brand} {v.model}")

        for o in v.orders:
            print(f"  Order {o.id}: {o.title}")

            for c in o.costs:
                print(f"    Cost: {c.description} - {c.amount}€")

            for t in o.times:
                print(f"    Time: {t.description} - {t.hours}h")

            for i in o.incomes:
                print(f"    Income: {i.description} - {i.amount}€")

def resetDatabase():
    confirm = input("Type YES to reset database: ")

    if confirm == "YES":
        db.drop_all()
        db.create_all()
        print("Database reset complete.")

def exportJson():
    data = []

    for v in Vehicle.query.all():
        vehicleData = {
            "brand": v.brand,
            "model": v.model,
            "vin": v.vin,
            "orders": []
        }

        for o in v.orders:
            orderData = {
                "title": o.title,
                "description": o.description,
                "costs": [],
                "times": [],
                "incomes": []
            }

            for c in o.costs:
                orderData["costs"].append({
                    "description": c.description,
                    "amount": c.amount,
                    "person": c.person,
                    "date": str(c.date)
                })

            for t in o.times:
                orderData["times"].append({
                    "description": t.description,
                    "hours": t.hours,
                    "person": t.person,
                    "date": str(t.date)
                })

            for i in o.incomes:
                orderData["incomes"].append({
                    "description": i.description,
                    "amount": i.amount,
                    "person": i.person,
                    "date": str(i.date)
                })

            vehicleData["orders"].append(orderData)

        data.append(vehicleData)

    with open("export.json", "w") as f:
        json.dump(data, f, indent=4)

    print("Exported to export.json")

def importJson():
    with open("export.json", "r") as f:
        data = json.load(f)

    for v in data:
        vehicle = Vehicle(
            brand=v["brand"],
            model=v["model"],
            vin=v["vin"]
        )

        db.session.add(vehicle)
        db.session.flush()

        for o in v["orders"]:
            order = Order(
                title=o["title"],
                description=o["description"],
                vehicle=vehicle
            )

            db.session.add(order)
            db.session.flush()

            for c in o["costs"]:
                db.session.add(Cost(
                    description=c["description"],
                    amount=c["amount"],
                    person=c["person"],
                    date=parseDate(c.get("date")),
                    order=order
                ))

            for t in o["times"]:
                db.session.add(WorkTime(
                    description=t["description"],
                    hours=t["hours"],
                    person=t["person"],
                    date=parseDate(t.get("date")),
                    order=order
                ))

            for i in o["incomes"]:
                db.session.add(Income(
                    description=i["description"],
                    amount=i["amount"],
                    person=i["person"],
                    date=parseDate(i.get("date")),
                    order=order
                ))

    db.session.commit()
    print("Import complete.")

def menu():
    while True:
        clearScreen()

        print("=== DATABASE MANAGER ===\n")
        print("1 - List Users")
        print("2 - Add User")
        print("3 - Delete User")
        print("4 - List Vehicles")
        print("5 - List Orders")
        print("6 - Full Overview")
        print("7 - Export JSON")
        print("8 - Import JSON")
        print("9 - Reset Database")
        print("0 - Exit")

        choice = input("\nSelect: ")

        if choice == "1": listUsers()
        elif choice == "2": addUser()
        elif choice == "3": deleteUser()
        elif choice == "4": listVehicles()
        elif choice == "5": listOrders()
        elif choice == "6": listAllDetails()
        elif choice == "7": exportJson()
        elif choice == "8": importJson()
        elif choice == "9": resetDatabase()
        elif choice == "0": break

        wait()

if __name__ == "__main__":
    with app.app_context():
        menu()