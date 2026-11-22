"""One-time trusted-operator command for creating the initial admin account."""

import os
import re
import sys

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.user import User
from app.services.auth import hash_password


def main() -> int:
    """Create an email-verified admin from explicitly configured environment values."""
    full_name = os.getenv("BOOTSTRAP_ADMIN_FULL_NAME", "").strip()
    username = os.getenv("BOOTSTRAP_ADMIN_USERNAME", "").strip().lower()
    email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")
    jwt_secret = os.getenv("AUTH_JWT_SECRET", "")
    if (
        not full_name
        or not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{2,31}", username)
        or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email)
    ):
        print(
            "Set BOOTSTRAP_ADMIN_FULL_NAME, a 3-32 character BOOTSTRAP_ADMIN_USERNAME "
            "(letters, numbers, dot, underscore, or hyphen), and a valid "
            "BOOTSTRAP_ADMIN_EMAIL.",
            file=sys.stderr,
        )
        return 2
    if len(password) < 12:
        print(
            "BOOTSTRAP_ADMIN_PASSWORD must contain at least 12 characters.",
            file=sys.stderr,
        )
        return 2
    if len(jwt_secret) < 32:
        print(
            "Set AUTH_JWT_SECRET to at least 32 characters before bootstrapping an admin.",
            file=sys.stderr,
        )
        return 2

    with SessionLocal() as db:
        existing_user = db.scalar(select(User).where(User.email == email))
        if existing_user is not None and existing_user.is_admin:
            if existing_user.username == username:
                print(f"Administrator username {username} is already configured.")
                return 0
            if existing_user.username is not None:
                print(
                    "The administrator already has a different username.",
                    file=sys.stderr,
                )
                return 1
            if db.scalar(select(User.id).where(User.username == username)) is not None:
                print("The bootstrap username already belongs to an account.", file=sys.stderr)
                return 1
            existing_user.username = username
            existing_user.is_super_admin = True
            db.commit()
            print(f"Username {username} assigned to the existing administrator.")
            return 0

        if db.scalar(select(User.id).where(User.is_admin.is_(True))) is not None:
            print("An administrator already exists; refusing to create another.", file=sys.stderr)
            return 1
        if existing_user is not None:
            print("The bootstrap email already belongs to an account.", file=sys.stderr)
            return 1
        if db.scalar(select(User.id).where(User.username == username)) is not None:
            print("The bootstrap username already belongs to an account.", file=sys.stderr)
            return 1

        user = User(
            full_name=full_name,
            email=email,
            username=username,
            password_hash=hash_password(password),
            is_responder=False,
            is_admin=True,
            is_super_admin=True,
            is_email_verified=True,
            responder_request_status="not_requested",
        )
        db.add(user)
        db.commit()

    print(
        f"Administrator account created with username {username}. "
        "Remove bootstrap credentials from .env."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
