# -*- coding: utf-8 -*-
"""
Seed a minimal public demo dataset.

Usage:
    .venv/Scripts/python.exe examples/seed_demo.py

This script creates:
- tenant: demo-school
- user: demo_student / Demo@123456
- student portrait: 00000000-0000-4000-8000-000000000001
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from app.core.database import SessionLocal, init_db  # noqa: E402
from app.core.security_context import reset_context, set_current_user  # noqa: E402
from app.models.db_models import Tenant, User  # noqa: E402
from app.routers.auth import _hash_password  # noqa: E402
from app.services.student_graph_service import student_graph_service  # noqa: E402

DEMO_TENANT_ID = "demo-school"
DEMO_TENANT_NAME = "公开演示学校"
DEMO_USERNAME = "demo_student"
DEMO_PASSWORD = "Demo@123456"
DEMO_STUDENT_ID = "00000000-0000-4000-8000-000000000001"


def load_demo_portrait() -> dict:
    portrait_path = BASE_DIR / "examples" / "demo_portrait.json"
    with portrait_path.open("r", encoding="utf-8") as portrait_file:
        return json.load(portrait_file)


def upsert_demo_user() -> None:
    with SessionLocal() as db_session:
        tenant = db_session.get(Tenant, DEMO_TENANT_ID)
        if tenant is None:
            db_session.add(Tenant(id=DEMO_TENANT_ID, name=DEMO_TENANT_NAME))

        user = db_session.query(User).filter(User.username == DEMO_USERNAME).first()
        if user is None:
            db_session.add(
                User(
                    id=str(uuid.uuid4()),
                    username=DEMO_USERNAME,
                    password_hash=_hash_password(DEMO_PASSWORD),
                    tenant_id=DEMO_TENANT_ID,
                    role="student",
                    student_id=DEMO_STUDENT_ID,
                    class_id=None,
                )
            )
        else:
            user.password_hash = _hash_password(DEMO_PASSWORD)
            user.tenant_id = DEMO_TENANT_ID
            user.role = "student"
            user.student_id = DEMO_STUDENT_ID

        db_session.commit()


def main() -> None:
    init_db()
    upsert_demo_user()
    set_current_user(
        {
            "username": DEMO_USERNAME,
            "role": "student",
            "tenant_id": DEMO_TENANT_ID,
            "student_id": DEMO_STUDENT_ID,
        }
    )
    try:
        student_id = student_graph_service.save_student(load_demo_portrait())
    finally:
        reset_context()

    print("Demo data is ready.")
    print(f"  username: {DEMO_USERNAME}")
    print(f"  password: {DEMO_PASSWORD}")
    print(f"  tenant:   {DEMO_TENANT_ID}")
    print(f"  student:  {student_id}")


if __name__ == "__main__":
    main()
