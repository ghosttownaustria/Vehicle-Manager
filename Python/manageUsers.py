from app import ROLE_ADMIN, ROLE_OPTIONS, User, app, db, parseRole
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
        print(
            f"ID: {user.id} | Name: {user.displayName} | "
            f"Email: {user.email} | Role: {user.roleLabel}"
        )

    print()


def createUser():
    print("\nCreate New User")
    print("----------------")

    name = input("Name: ").strip()
    email = input("Email: ").strip()

    if not email:
        print("Email must not be empty!\n")
        return

    if User.query.filter_by(email=email).first():
        print("User already exists!\n")
        return

    password = getpass.getpass("Password: ")
    confirmPassword = getpass.getpass("Confirm Password: ")

    if not password:
        print("Password must not be empty!\n")
        return

    if password != confirmPassword:
        print("Passwords do not match!\n")
        return

    hashedPassword = generate_password_hash(password)
    print("Roles:")
    for value, label in ROLE_OPTIONS:
        print(f"  {value} - {label}")
    role = parseRole(input("Role [customer]: ").strip() or "customer")

    newUser = User(
        name=name or email,
        email=email,
        passwordHash=hashedPassword,
        isAdmin=role == ROLE_ADMIN,
        role=role,
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
