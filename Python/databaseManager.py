import argparse
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy.exc import OperationalError, SQLAlchemyError
from werkzeug.security import generate_password_hash

from app import (
    Cost,
    Income,
    Order,
    User,
    Vehicle,
    WorkTime,
    app,
    db,
    initializeDatabase,
)


DEFAULT_EXPORT_FILE = Path(__file__).with_name("export.json")


def parseDate(dateValue, fallback=None):
    fallback = fallback or datetime.now()
    if dateValue is None or dateValue == "":
        return fallback
    if isinstance(dateValue, datetime):
        return dateValue
    if isinstance(dateValue, str):
        normalized = dateValue.strip()
        if not normalized or normalized.lower() == "none":
            return fallback
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(normalized)
            return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
        except ValueError:
            return fallback
    return fallback


def parseBoolean(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "ja", "closed"}
    return bool(value)


def clearScreen():
    print("\n" * 3)


def wait():
    input("\nEnter drücken, um zum Menü zurückzukehren...")


def listUsers():
    print("\n=== BENUTZER ===")
    for user in User.query.order_by(User.email).all():
        print(f"{user.id} - {user.email}")


def addUser():
    print("\n=== BENUTZER ANLEGEN ===")
    email = input("E-Mail: ").strip()
    password = input("Passwort: ")
    db.session.add(
        User(
            email=email,
            passwordHash=generate_password_hash(password),
        )
    )
    db.session.commit()
    print("Benutzer wurde angelegt.")


def deleteUser():
    listUsers()
    try:
        userId = int(input("\nZu löschende Benutzer-ID: "))
    except ValueError:
        print("Ungültige ID.")
        return

    user = db.session.get(User, userId)
    if not user:
        print("Benutzer wurde nicht gefunden.")
        return

    db.session.delete(user)
    db.session.commit()
    print("Benutzer wurde gelöscht.")


def listVehicles():
    print("\n=== FAHRZEUGE ===")
    for vehicle in Vehicle.query.order_by(Vehicle.brand, Vehicle.model).all():
        print(
            f"{vehicle.id} - {vehicle.displayName} "
            f"({vehicle.vin or 'keine FIN/VIN'})"
        )


def listOrders():
    print("\n=== AUFTRÄGE ===")
    for order in Order.query.order_by(Order.date.desc()).all():
        status = "geschlossen" if order.isClosed else "offen"
        print(
            f"{order.id} - {order.title} "
            f"(Fahrzeug {order.vehicle_id}, {status})"
        )


def listAllDetails():
    print("\n=== DATENBANKÜBERSICHT ===")
    for vehicle in Vehicle.query.order_by(Vehicle.brand, Vehicle.model).all():
        print(f"\nFahrzeug {vehicle.id}: {vehicle.displayName}")
        for order in vehicle.orders:
            status = "geschlossen" if order.isClosed else "offen"
            print(f"  Auftrag {order.id}: {order.title} [{status}]")
            for cost in order.costs:
                print(f"    Ausgabe: {cost.description} - {cost.amount:.2f} €")
            for workTime in order.times:
                print(
                    f"    Arbeitszeit: {workTime.description} - "
                    f"{workTime.hours:.2f} h"
                )
            for income in order.incomes:
                print(
                    f"    Einnahme: {income.description} - "
                    f"{income.amount:.2f} €"
                )


def resetDatabase():
    confirm = input(
        "Zum vollständigen Löschen der Datenbank RESET eingeben: "
    ).strip()
    if confirm != "RESET":
        print("Abgebrochen.")
        return

    db.drop_all()
    initializeDatabase()
    print("Datenbank wurde zurückgesetzt.")


def exportJson(filePath=DEFAULT_EXPORT_FILE):
    filePath = Path(filePath)
    data = []

    for vehicle in Vehicle.query.order_by(Vehicle.id).all():
        vehicleData = {
            "brand": vehicle.brand,
            "model": vehicle.model,
            "vin": vehicle.vin,
            "firstRegistration": vehicle.firstRegistration,
            "engineOil": vehicle.engineOil,
            "gearboxOil": vehicle.gearboxOil,
            "diffOil": vehicle.diffOil,
            "coolant": vehicle.coolant,
            "fuel": vehicle.fuel,
            "engineCode": vehicle.engineCode,
            "licensePlate": vehicle.licensePlate,
            "orders": [],
        }

        for order in vehicle.orders:
            orderData = {
                "title": order.title,
                "description": order.description,
                "date": order.date.isoformat() if order.date else None,
                "isClosed": bool(order.isClosed),
                "closedAt": (
                    order.closedAt.isoformat() if order.closedAt else None
                ),
                "costs": [],
                "times": [],
                "incomes": [],
            }

            for cost in order.costs:
                orderData["costs"].append(
                    {
                        "description": cost.description,
                        "amount": cost.amount,
                        "person": cost.person,
                        "date": cost.date.isoformat() if cost.date else None,
                    }
                )

            for workTime in order.times:
                orderData["times"].append(
                    {
                        "description": workTime.description,
                        "hours": workTime.hours,
                        "person": workTime.person,
                        "date": (
                            workTime.date.isoformat() if workTime.date else None
                        ),
                    }
                )

            for income in order.incomes:
                orderData["incomes"].append(
                    {
                        "description": income.description,
                        "amount": income.amount,
                        "person": income.person,
                        "date": income.date.isoformat() if income.date else None,
                    }
                )

            vehicleData["orders"].append(orderData)
        data.append(vehicleData)

    filePath.write_text(
        json.dumps(data, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"{len(data)} Fahrzeuge wurden nach {filePath} exportiert.")


def importJson(filePath=DEFAULT_EXPORT_FILE, replaceExisting=False):
    """Import old and new exports without requiring new status fields."""
    filePath = Path(filePath)
    if not filePath.exists():
        print(f"Datei nicht gefunden: {filePath}")
        return False

    try:
        data = json.loads(filePath.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"Importdatei konnte nicht gelesen werden: {error}")
        return False

    if not isinstance(data, list):
        print("Ungültiges Format: Die oberste JSON-Ebene muss eine Liste sein.")
        return False

    vehicleCount = len(data)
    orderCount = 0
    entryCount = 0
    print(f"Import gestartet: {vehicleCount} Fahrzeuge aus {filePath.name}")

    try:
        if replaceExisting:
            print("Vorhandene Fahrzeuge und Aufträge werden entfernt...")
            for vehicle in Vehicle.query.all():
                db.session.delete(vehicle)
            db.session.flush()

        # Relationship assignment sets all foreign keys during the final flush.
        # Avoiding a flush for every single order keeps large old exports fast.
        with db.session.no_autoflush:
            for index, vehicleData in enumerate(data, start=1):
                if not isinstance(vehicleData, dict):
                    raise ValueError(
                        f"Fahrzeug-Eintrag {index} ist kein JSON-Objekt."
                    )

                vehicle = Vehicle(
                    brand=vehicleData.get("brand", ""),
                    model=vehicleData.get("model", ""),
                    vin=vehicleData.get("vin", ""),
                    firstRegistration=vehicleData.get("firstRegistration", ""),
                    engineOil=vehicleData.get("engineOil", ""),
                    gearboxOil=vehicleData.get("gearboxOil", ""),
                    diffOil=vehicleData.get("diffOil", ""),
                    coolant=vehicleData.get("coolant", ""),
                    fuel=vehicleData.get("fuel", ""),
                    engineCode=vehicleData.get("engineCode", ""),
                    licensePlate=vehicleData.get("licensePlate", ""),
                )
                db.session.add(vehicle)

                for orderData in vehicleData.get("orders", []):
                    isClosed = parseBoolean(
                        orderData.get(
                            "isClosed",
                            orderData.get("closed", False),
                        )
                    )
                    orderDate = parseDate(orderData.get("date"))
                    order = Order(
                        title=orderData.get("title", ""),
                        description=orderData.get("description", ""),
                        date=orderDate,
                        isClosed=isClosed,
                        closedAt=(
                            parseDate(
                                orderData.get("closedAt"),
                                fallback=orderDate,
                            )
                            if isClosed
                            else None
                        ),
                        vehicle=vehicle,
                    )
                    db.session.add(order)
                    orderCount += 1

                    for costData in orderData.get("costs", []):
                        order.costs.append(
                            Cost(
                                description=costData.get("description", ""),
                                amount=float(costData.get("amount", 0) or 0),
                                person=costData.get("person", ""),
                                date=parseDate(costData.get("date")),
                            )
                        )
                        entryCount += 1

                    for timeData in orderData.get("times", []):
                        order.times.append(
                            WorkTime(
                                description=timeData.get("description", ""),
                                hours=float(timeData.get("hours", 0) or 0),
                                person=timeData.get("person", ""),
                                date=parseDate(timeData.get("date")),
                            )
                        )
                        entryCount += 1

                    for incomeData in orderData.get("incomes", []):
                        order.incomes.append(
                            Income(
                                description=incomeData.get("description", ""),
                                amount=float(incomeData.get("amount", 0) or 0),
                                person=incomeData.get("person", ""),
                                date=parseDate(incomeData.get("date")),
                            )
                        )
                        entryCount += 1

                print(
                    f"  [{index}/{vehicleCount}] "
                    f"{vehicle.displayName or 'Unbenanntes Fahrzeug'}"
                )

        db.session.commit()
    except OperationalError as error:
        db.session.rollback()
        print(
            "Datenbank ist gesperrt oder nicht erreichbar. Bitte die laufende "
            "Vehicle-Manager-App kurz beenden und den Import erneut starten."
        )
        print(f"Technische Meldung: {error.orig}")
        return False
    except (SQLAlchemyError, ValueError, TypeError, KeyError) as error:
        db.session.rollback()
        print(f"Import abgebrochen, es wurden keine neuen Daten gespeichert: {error}")
        return False

    print(
        f"Import abgeschlossen: {vehicleCount} Fahrzeuge, "
        f"{orderCount} Aufträge und {entryCount} Buchungen."
    )
    return True


def menu():
    while True:
        clearScreen()
        print("=== DATABASE MANAGER ===\n")
        print("1 - Benutzer auflisten")
        print("2 - Benutzer anlegen")
        print("3 - Benutzer löschen")
        print("4 - Fahrzeuge auflisten")
        print("5 - Aufträge auflisten")
        print("6 - Vollständige Übersicht")
        print("7 - JSON exportieren")
        print("8 - JSON importieren")
        print("9 - Datenbank zurücksetzen")
        print("0 - Beenden")

        choice = input("\nAuswahl: ").strip()

        if choice == "1":
            listUsers()
        elif choice == "2":
            addUser()
        elif choice == "3":
            deleteUser()
        elif choice == "4":
            listVehicles()
        elif choice == "5":
            listOrders()
        elif choice == "6":
            listAllDetails()
        elif choice == "7":
            path = input(
                f"Datei [{DEFAULT_EXPORT_FILE}]: "
            ).strip() or str(DEFAULT_EXPORT_FILE)
            exportJson(path)
        elif choice == "8":
            path = input(
                f"Importdatei [{DEFAULT_EXPORT_FILE}]: "
            ).strip() or str(DEFAULT_EXPORT_FILE)
            replace = (
                input("Vorhandene Fahrzeuge vorher löschen? [j/N]: ")
                .strip()
                .lower()
                == "j"
            )
            importJson(path, replaceExisting=replace)
        elif choice == "9":
            resetDatabase()
        elif choice == "0":
            break
        else:
            print("Ungültige Auswahl.")

        wait()


def parseArguments():
    parser = argparse.ArgumentParser(description="Vehicle Manager Datenbank")
    parser.add_argument(
        "--import",
        dest="importFile",
        metavar="DATEI",
        help="JSON-Datei importieren und danach beenden",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Beim Import vorhandene Fahrzeuge ersetzen",
    )
    parser.add_argument(
        "--export",
        dest="exportFile",
        metavar="DATEI",
        help="JSON-Datei exportieren und danach beenden",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parseArguments()
    with app.app_context():
        initializeDatabase()
        if arguments.importFile:
            importJson(arguments.importFile, replaceExisting=arguments.replace)
        elif arguments.exportFile:
            exportJson(arguments.exportFile)
        else:
            menu()
