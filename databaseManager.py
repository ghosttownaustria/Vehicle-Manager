import json
from datetime import datetime

from app import app, db, Vehicle, Cost, WorkTime, User


BACKUP_FILE = "database_backup.json"


def exportDatabase():
    with app.app_context():

        data = {
            "users": [],
            "vehicles": [],
            "costs": [],
            "workTimes": []
        }

        for user in User.query.all():
            data["users"].append({
                "id": user.id,
                "email": user.email,
                "passwordHash": user.passwordHash
            })

        for vehicle in Vehicle.query.all():
            data["vehicles"].append({
                "id": vehicle.id,
                "brand": vehicle.brand,
                "model": vehicle.model,
                "vin": vehicle.vin
            })

        for cost in Cost.query.all():
            data["costs"].append({
                "id": cost.id,
                "description": cost.description,
                "amount": cost.amount,
                "person": cost.person,
                "date": cost.date.isoformat(),
                "vehicle_id": cost.vehicle_id
            })

        for time in WorkTime.query.all():
            data["workTimes"].append({
                "id": time.id,
                "description": time.description,
                "hours": time.hours,
                "person": time.person,
                "date": time.date.isoformat(),
                "vehicle_id": time.vehicle_id
            })

        with open(BACKUP_FILE, "w") as f:
            json.dump(data, f, indent=4)

        print("Database exported to", BACKUP_FILE)


def importDatabase():
    with app.app_context():

        with open(BACKUP_FILE, "r") as f:
            data = json.load(f)

        print("Importing database...")

        for userData in data["users"]:
            user = User(
                id=userData["id"],
                email=userData["email"],
                passwordHash=userData["passwordHash"]
            )
            db.session.add(user)

        for vehicleData in data["vehicles"]:
            vehicle = Vehicle(
                id=vehicleData["id"],
                brand=vehicleData["brand"],
                model=vehicleData["model"],
                vin=vehicleData["vin"]
            )
            db.session.add(vehicle)

        for costData in data["costs"]:
            cost = Cost(
                id=costData["id"],
                description=costData["description"],
                amount=costData["amount"],
                person=costData["person"],
                date=datetime.fromisoformat(costData["date"]),
                vehicle_id=costData["vehicle_id"]
            )
            db.session.add(cost)

        for timeData in data["workTimes"]:
            workTime = WorkTime(
                id=timeData["id"],
                description=timeData["description"],
                hours=timeData["hours"],
                person=timeData["person"],
                date=datetime.fromisoformat(timeData["date"]),
                vehicle_id=timeData["vehicle_id"]
            )
            db.session.add(workTime)

        db.session.commit()

        print("Import complete")


def resetDatabase():
    with app.app_context():

        confirm = input("Type YES to reset the database: ")

        if confirm != "YES":
            print("Cancelled")
            return

        db.drop_all()
        db.create_all()

        print("Database reset complete")


def deleteDatabaseFile():
    import os

    if os.path.exists("vehicles.db"):
        os.remove("vehicles.db")
        print("Database file deleted")
    else:
        print("Database file not found")


def menu():

    while True:

        print("\n=== DATABASE MANAGER ===")
        print("1 - Export database")
        print("2 - Import database")
        print("3 - Reset database")
        print("4 - Delete database file")
        print("5 - Exit")

        choice = input("Select option: ")

        if choice == "1":
            exportDatabase()

        elif choice == "2":
            importDatabase()

        elif choice == "3":
            resetDatabase()

        elif choice == "4":
            deleteDatabaseFile()

        elif choice == "5":
            break

        else:
            print("Invalid option")


if __name__ == "__main__":
    menu()