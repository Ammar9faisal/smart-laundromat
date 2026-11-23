"""Integration tests against the real Supabase project.

These create two temporary customers and a temporary machine, exercise the API
end to end, and delete everything they created afterwards. They are skipped
unless RUN_INTEGRATION_TESTS=1 is set, and need SUPABASE_URL, SUPABASE_KEY and
SUPABASE_SECRET_KEY in backend/.env. Run them from backend/:

    RUN_INTEGRATION_TESTS=1 python -m pytest integration_tests
"""

import os
import secrets
import uuid

import pytest
from dotenv import load_dotenv

load_dotenv()

from fastapi.testclient import TestClient  # noqa: E402
from supabase import create_client  # noqa: E402

from app.config import SUPABASE_KEY, SUPABASE_SECRET_KEY, SUPABASE_URL  # noqa: E402
from app.main import app  # noqa: E402


def pytest_collection_modifyitems(config, items):
    if os.environ.get("RUN_INTEGRATION_TESTS") != "1":
        reason = "set RUN_INTEGRATION_TESTS=1 to run tests against Supabase"
    elif not SUPABASE_SECRET_KEY:
        reason = "SUPABASE_SECRET_KEY is required in backend/.env"
    else:
        return

    for item in items:
        item.add_marker(pytest.mark.skip(reason=reason))


@pytest.fixture(scope="session")
def service():
    return create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


def _create_customer(service, label):
    email = f"integration-{label}-{uuid.uuid4().hex[:8]}@example.com"
    password = secrets.token_urlsafe(16)
    created = service.auth.admin.create_user(
        {
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"full_name": f"Integration {label}"},
        }
    )
    session = create_client(SUPABASE_URL, SUPABASE_KEY).auth.sign_in_with_password(
        {"email": email, "password": password}
    )
    return {"id": created.user.id, "token": session.session.access_token}


@pytest.fixture(scope="session")
def customers(service):
    """Two temporary customers; removed with all their data at the end."""
    users = [_create_customer(service, "a"), _create_customer(service, "b")]
    yield users

    for user in users:
        service.table("payments").delete().eq("user_id", user["id"]).execute()
        service.table("reservations").delete().eq("user_id", user["id"]).execute()
        service.table("profiles").delete().eq("id", user["id"]).execute()
        service.auth.admin.delete_user(user["id"])


@pytest.fixture(scope="session")
def machine(service, customers):
    """A temporary washer. Depends on customers so it is removed after their
    reservations are gone."""
    row = (
        service.table("machines")
        .insert({"type": "WASHER", "capacity": 7, "price": 4.25, "status": "AVAILABLE"})
        .execute()
        .data[0]
    )
    yield row

    service.table("reservations").delete().eq("machine_id", row["id"]).execute()
    service.table("machines").delete().eq("id", row["id"]).execute()


def auth_header(user):
    return {"Authorization": f"Bearer {user['token']}"}
