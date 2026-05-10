from werkzeug.security import check_password_hash, generate_password_hash
from typing import Optional, Union


def hash_password(password: str) -> str:
    """Generate a Werkzeug password hash."""
    return generate_password_hash(password)


def verify_password(stored_hash: Optional[Union[str, bytes]], password: str) -> bool:
    """
    Verify password against stored hash.

    Matches the repo's existing behavior in `models/user.py`:
    - If stored value isn't a recognized hash prefix, treat it as plain text.
    """
    if stored_hash is None:
        return False

    try:
        if isinstance(stored_hash, bytes):
            password_hash_str = stored_hash.decode("utf-8")
        else:
            password_hash_str = stored_hash

        if not password_hash_str.startswith(("$2b$", "$2a$", "$2y$", "scrypt:", "pbkdf2:")):
            return password_hash_str == password

        return check_password_hash(password_hash_str, password)
    except Exception:
        return False

