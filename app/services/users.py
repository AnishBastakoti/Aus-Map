from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.auth.passwords import hash_password


class UserAlreadyExistsError(Exception):
    """Raised when trying to create a user with an email that's already taken."""


class UserNotFoundError(Exception):
    """Raised when a lookup by email/id returns nothing."""


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Return the User with this email, or None. Email lookup is case-insensitive."""
    normalized = email.strip().lower()
    stmt = select(User).where(User.email == normalized)
    return db.execute(stmt).scalar_one_or_none()


def create_user(
    db: Session,
    email: str,
    password: str,
    full_name: Optional[str] = None,
    is_active: bool = True,
) -> User:
    """
    Create a new user. Hashes the password, validates uniqueness, commits.

    Raises:
        UserAlreadyExistsError if a user with this email already exists.
        ValueError on empty email or password.

    Returns the newly created User (refreshed, with id and timestamps populated).
    """
    email = email.strip().lower()
    if not email:
        raise ValueError("Email is required.")
    if "@" not in email:
        raise ValueError("Email looks invalid (no @ sign).")
    if not password:
        raise ValueError("Password is required.")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")

    # Uniqueness check before insert. The DB has a UNIQUE constraint as a backstop,
    # but checking first gives a clean error message instead of a SQL violation.
    if get_user_by_email(db, email) is not None:
        raise UserAlreadyExistsError(f"A user with email '{email}' already exists.")

    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name.strip() if full_name else None,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)  # reload with DB-assigned values (id, created_at, etc.)
    return user