import argparse
import getpass
import sys

from app.database import SessionLocal
from app.services.users import create_user, UserAlreadyExistsError


def cmd_create_admin() -> int:
    """
    Interactively create a new user. Returns process exit code.
    """
    print("Create admin user")
    print("=================")

    email = input("Email: ").strip()
    if not email:
        print("ERROR: Email required.", file=sys.stderr)
        return 1

    full_name = input("Full name (optional, press Enter to skip): ").strip() or None

    # getpass hides what the user types — never echo passwords
    password = getpass.getpass("Password (min 8 chars): ")
    password_confirm = getpass.getpass("Confirm password:    ")

    if password != password_confirm:
        print("ERROR: Passwords do not match.", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        user = create_user(
            db,
            email=email,
            password=password,
            full_name=full_name,
            is_active=True,
        )
        print()
        print(f"  Created user {user.email}")
        print(f"  ID:         {user.id}")
        print(f"  Created at: {user.created_at}")
        return 0
    except UserAlreadyExistsError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="Aus-Map administrative CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("create-admin", help="Create a new admin user")

    args = parser.parse_args()

    if args.command == "create-admin":
        return cmd_create_admin()
    else:
        # argparse will catch unknown commands before we get here, but be defensive
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())