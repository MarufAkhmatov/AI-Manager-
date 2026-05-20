"""Idempotent admin seeding from environment variables.

Run inside the backend container by the entrypoint:

    python -m app.seed

Reads ADMIN_USERNAME / ADMIN_PASSWORD / ADMIN_ROLE (default role=admin).
No-op if the user already exists or the env vars are unset — safe to run
on every container start.
"""

from __future__ import annotations

import asyncio
import os
import uuid

from sqlalchemy import select

from app.db.models import User
from app.db.session import session_scope
from app.security.passwords import hash_password


async def seed_admin(username: str, password: str, role: str = "admin") -> None:
    async with session_scope() as session:
        existing = await session.scalar(select(User).where(User.username == username))
        if existing is not None:
            print(f"[seed] user {username!r} already exists ({existing.role}) — skipping")
            return
        session.add(
            User(
                id=uuid.uuid4(),
                username=username,
                password_hash=hash_password(password),
                role=role,
            )
        )
    print(f"[seed] created {role} user: {username}")


def main() -> None:
    username = os.environ.get("ADMIN_USERNAME")
    password = os.environ.get("ADMIN_PASSWORD")
    role = os.environ.get("ADMIN_ROLE", "admin")
    if not username or not password:
        print("[seed] ADMIN_USERNAME / ADMIN_PASSWORD not set — skipping admin seed")
        return
    if role not in {"admin", "analyst", "viewer"}:
        role = "admin"
    asyncio.run(seed_admin(username, password, role))


if __name__ == "__main__":
    main()
