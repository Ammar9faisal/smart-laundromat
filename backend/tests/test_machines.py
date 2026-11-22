from app.routers import machines as machines_router

from tests.conftest import FakeClient, FakeQuery

MACHINES = [
    {"id": 1, "type": "WASHER", "capacity": 8, "price": 4.5, "status": "AVAILABLE", "active": True},
    {"id": 2, "type": "DRYER", "capacity": 10, "price": 3.5, "status": "AVAILABLE", "active": True},
]


def test_list_machines_returns_active_machines(client, monkeypatch):
    query = FakeQuery(data=MACHINES)
    monkeypatch.setattr(machines_router, "supabase", FakeClient({"machines": query}))

    response = client.get("/api/machines/")

    assert response.status_code == 200
    assert response.json() == MACHINES
    assert query.called("eq", "active", True)


def test_list_machines_is_public(client, monkeypatch):
    monkeypatch.setattr(
        machines_router, "supabase", FakeClient({"machines": FakeQuery(data=[])})
    )

    response = client.get("/api/machines/")

    assert response.status_code == 200
    assert response.json() == []


def test_list_machines_database_error_returns_500(client, monkeypatch):
    query = FakeQuery(error=RuntimeError("connection refused"))
    monkeypatch.setattr(machines_router, "supabase", FakeClient({"machines": query}))

    response = client.get("/api/machines/")

    assert response.status_code == 500
    assert response.json() == {"detail": "Failed to retrieve machines"}
