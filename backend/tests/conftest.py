"""Shared fixtures for the backend test suite.

The unit tests never contact Supabase. The Supabase clients used by the app are
replaced with small fakes that return canned data, so the tests run offline and
cannot change the shared development database.
"""

import os
from types import SimpleNamespace

import pytest

# app.config reads these when the app is imported. Setting them before the
# import also means a developer's real backend/.env is never used by tests
# (load_dotenv does not override variables that are already set).
os.environ["SUPABASE_URL"] = "https://test-project.supabase.co"
os.environ["SUPABASE_KEY"] = "sb_publishable_test_key"

from fastapi.testclient import TestClient  # noqa: E402

from app import dependencies  # noqa: E402
from app.main import app  # noqa: E402
from app.routers import auth as auth_router  # noqa: E402


class FakeQuery:
    """Stands in for a supabase-py query builder.

    Every builder method (select, eq, single, ...) is recorded and returns the
    same object, so call chains work. execute() returns the canned data or
    raises the configured error.
    """

    def __init__(self, data=None, error=None):
        self.data = data
        self.error = error
        self.calls = []

    def __getattr__(self, name):
        def builder_method(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return self

        return builder_method

    def execute(self):
        if self.error is not None:
            raise self.error
        return SimpleNamespace(data=self.data)

    def called(self, name, *args):
        return any(c[0] == name and c[1] == args for c in self.calls)


class FakeClient:
    """Stands in for a supabase-py Client with one FakeQuery per table."""

    def __init__(self, tables=None):
        self.tables = tables or {}

    def table(self, name):
        return self.tables[name]


CUSTOMER_ID = "00000000-0000-4000-8000-0000000000a1"
ADMIN_ID = "00000000-0000-4000-8000-0000000000c3"

VALID_TOKENS = {
    "customer-token": SimpleNamespace(id=CUSTOMER_ID, email="customer@example.com"),
    "admin-token": SimpleNamespace(id=ADMIN_ID, email="admin@example.com"),
}

PROFILES = {
    CUSTOMER_ID: {
        "id": CUSTOMER_ID,
        "full_name": "Test Customer",
        "role": "customer",
        "created_at": "2026-11-22T15:37:46+00:00",
    },
    ADMIN_ID: {
        "id": ADMIN_ID,
        "full_name": "Test Admin",
        "role": "admin",
        "created_at": "2026-11-22T15:57:21+00:00",
    },
}


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def fake_auth(monkeypatch):
    """Replaces Supabase Auth and the user-scoped client.

    Tokens listed in VALID_TOKENS are accepted; anything else is rejected the
    way Supabase rejects an invalid or expired token. Profile lookups return
    the matching entry from PROFILES. The returned object records which tokens
    were used to build user-scoped clients.
    """

    state = SimpleNamespace(user_client_tokens=[], profile_error=None)

    def get_user(token):
        if token not in VALID_TOKENS:
            raise RuntimeError("invalid JWT")
        return SimpleNamespace(user=VALID_TOKENS[token])

    def get_user_client(token):
        state.user_client_tokens.append(token)
        user = VALID_TOKENS[token]
        return FakeClient(
            {"profiles": FakeQuery(data=PROFILES[user.id], error=state.profile_error)}
        )

    monkeypatch.setattr(
        dependencies, "supabase", SimpleNamespace(auth=SimpleNamespace(get_user=get_user))
    )
    monkeypatch.setattr(dependencies, "get_user_client", get_user_client)
    monkeypatch.setattr(auth_router, "get_user_client", get_user_client)
    return state


def bearer(token):
    return {"Authorization": f"Bearer {token}"}
