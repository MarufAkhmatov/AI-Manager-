"""Create the initial admin user.

Usage:
    python -m scripts.seed_admin --username admin --password 'something-strong'
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid

from sqlalchemy import select

# Allow running from repo root.
sys.path.insert(0, "backend")

from app.db.models import User  # noqa: E402
from app.db.session import session_scope  # noqa: E402
from app.security.passwords import hash_password  # noqa: E402


async def seed(username: str, password: str, role: str) -> None:
    async with session_scope() as session:
        existing = await session.scalar(select(User).where(User.username == username))
        if existing is not None:
            print(f"user {username!r} already exists ({existing.role})")
            return
        user = User(
            id=uuid.uuid4(),
            username=username,
            password_hash=hash_password(password),
            role=role,
        )
        session.add(user)
    print(f"created {role} user: {username}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--username", required=True)
    p.add_argument("--password", required=True)
    p.add_argument("--role", default="admin", choices=("admin", "analyst", "viewer"))
    args = p.parse_args()
    asyncio.run(seed(args.username, args.password, args.role))


if __name__ == "__main__":
    main()
