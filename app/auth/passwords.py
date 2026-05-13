from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError


# One shared hasher. Default parameters are OWASP-recommended.

_hasher = PasswordHasher()


def hash_password(plaintext: str) -> str:
    """
    Returns an Argon2id hash string suitable for storing in users.password_hash.
    The salt is generated inside the call — never the same hash twice for
    the same input.
    """
    if not plaintext:
        raise ValueError("Cannot hash an empty password.")
    return _hasher.hash(plaintext)


def verify_password(stored_hash: str, plaintext: str) -> bool:
    """
    Returns True if 'plaintext' matches 'stored_hash', False otherwise.
    """
    if not stored_hash or not plaintext:
        return False
    try:
        _hasher.verify(stored_hash, plaintext)
        return True
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(stored_hash: str) -> bool:
    """
    True if the stored hash was made with weaker parameters than the current
    PasswordHasher defaults. Call after a successful verify_password() and,
    if True, re-hash and update the database with the stronger hash.

    This is how you transparently upgrade everyone's password security as
    hardware improves — without forcing them to reset their password.
    """
    try:
        return _hasher.check_needs_rehash(stored_hash)
    except InvalidHashError:
        return False