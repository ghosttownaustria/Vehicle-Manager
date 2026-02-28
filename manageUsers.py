from app import app, db, User
from werkzeug.security import generate_password_hash
import getpass
import sys


def printHeader():
    print("\n==============================")
    print("   Vehicle App - User Admin")
    print("==============================\n")


def listUsers():
    users = User.query.all()

    if not users:
        print("No users found.\n")
        return

    print("Existing Users:")
    print("------------------------------")

    for user in users:
        print(f"ID: {user.id} | Email: {user.email}")

    print()


def createUser():
    print("\nCreate New User")
    print("----------------")

    email = input("Email: ").strip()

    if User.query.filter_by(email=email).first():
        print("User already exists!\n")
        return

    password = getpass.getpass("Password: ")
    confirmPassword = getpass.getpass("Confirm Password: ")

    if password != confirmPassword:
        print("Passwords do not match!\n")
        return

    hashedPassword = generate_password_hash(password)

    newUser = User(
        email=email,
        passwordHash=hashedPassword
    )

    db.session.add(newUser)
    db.session.commit()

    print("User created successfully.\n")


def deleteUser():
    print("\nDelete User")
    print("----------------")

    listUsers()

    try:
        userId = int(input("Enter User ID to delete: "))
    except ValueError:
        print("Invalid ID.\n")
        return

    user = User.query.get(userId)

    if not user:
        print("User not found.\n")
        return

    confirm = input(f"Really delete {user.email}? (yes/no): ")

    if confirm.lower() != "yes":
        print("Cancelled.\n")
        return

    db.session.delete(user)
    db.session.commit()

    print("User deleted successfully.\n")


def mainMenu():
    while True:
        printHeader()
        print("1 - List Users")
        print("2 - Create User")
        print("3 - Delete User")
        print("0 - Exit\n")

        choice = input("Select option: ").strip()

        if choice == "1":
            listUsers()
        elif choice == "2":
            createUser()
        elif choice == "3":
            deleteUser()
        elif choice == "0":
            print("Exiting...")
            sys.exit()
        else:
            print("Invalid option.\n")


if __name__ == "__main__":
    with app.app_context():
        mainMenu()