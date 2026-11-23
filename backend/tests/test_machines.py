from app.routers import machines as machines_router

from tests.conftest import FakeClient, FakeQuery, api_error, bearer

MACHINES = [
    {"id": 1, "type": "WASHER", "capacity": 8, "price": 4.5, "status": "AVAILABLE", "active": True},
    {"id": 2, "type": "DRYER", "capacity": 10, "price": 3.5, "status": "AVAILABLE", "active": True},
]

FROM = "2030-01-10T00:00:00+00:00"
TO = "2030-01-11T00:00:00+00:00"


def use_public_db(monkeypatch, tables=None, rpcs=None):
    """Replace the publishable-key client used by the public machine endpoints."""
    fake = FakeClient(tables or {}, rpcs or {})
    monkeypatch.setattr(machines_router, "supabase", fake)
    return fake


# --- Public endpoints ---------------------------------------------------------

def test_list_machines_returns_active_machines(client, monkeypatch):
    query = FakeQuery(data=MACHINES)
    use_public_db(monkeypatch, {"machines": query})

    response = client.get("/api/machines/")

    assert response.status_code == 200
    assert response.json() == MACHINES
    assert query.called("eq", "active", True)


def test_list_machines_is_public(client, monkeypatch):
    use_public_db(monkeypatch, {"machines": FakeQuery(data=[])})

    response = client.get("/api/machines/")

    assert response.status_code == 200
    assert response.json() == []


def test_list_machines_applies_filters(client, monkeypatch):
    query = FakeQuery(data=[MACHINES[0]])
    use_public_db(monkeypatch, {"machines": query})

    response = client.get("/api/machines/?type=WASHER&status=AVAILABLE&min_capacity=8")

    assert response.status_code == 200
    assert query.called("eq", "type", "WASHER")
    assert query.called("eq", "status", "AVAILABLE")
    assert query.called("gte", "capacity", 8)


def test_list_machines_rejects_unknown_type(client, monkeypatch):
    use_public_db(monkeypatch, {"machines": FakeQuery(data=[])})

    response = client.get("/api/machines/?type=BLENDER")

    assert response.status_code == 422


def test_list_machines_database_error_returns_500(client, monkeypatch):
    query = FakeQuery(error=RuntimeError("connection refused"))
    use_public_db(monkeypatch, {"machines": query})

    response = client.get("/api/machines/")

    assert response.status_code == 500
    assert response.json() == {"detail": "Failed to retrieve machines"}


def test_get_machine(client, monkeypatch):
    query = FakeQuery(data=[MACHINES[0]])
    use_public_db(monkeypatch, {"machines": query})

    response = client.get("/api/machines/1")

    assert response.status_code == 200
    assert response.json() == MACHINES[0]
    assert query.called("eq", "id", 1)


def test_get_missing_machine_returns_404(client, monkeypatch):
    use_public_db(monkeypatch, {"machines": FakeQuery(data=[])})

    response = client.get("/api/machines/99")

    assert response.status_code == 404


def test_machine_availability_lists_busy_slots(client, monkeypatch):
    busy = [{"start_time": "2030-01-10T10:00:00+00:00", "end_time": "2030-01-10T11:00:00+00:00"}]
    fake = use_public_db(
        monkeypatch,
        {"machines": FakeQuery(data=[MACHINES[0]])},
        {"get_machine_busy_slots": FakeQuery(data=busy)},
    )

    response = client.get("/api/machines/1/availability", params={"from": FROM, "to": TO})

    assert response.status_code == 200
    body = response.json()
    assert body["machine_id"] == 1
    assert len(body["busy"]) == 1
    name, params = fake.rpc_calls[0]
    assert name == "get_machine_busy_slots"
    assert params["p_machine_id"] == 1


def test_machine_availability_requires_time_zone(client, monkeypatch):
    use_public_db(monkeypatch, {"machines": FakeQuery(data=[MACHINES[0]])})

    response = client.get(
        "/api/machines/1/availability",
        params={"from": "2030-01-10T00:00:00", "to": "2030-01-11T00:00:00"},
    )

    assert response.status_code == 422


def test_machine_availability_rejects_reversed_window(client, monkeypatch):
    use_public_db(monkeypatch, {"machines": FakeQuery(data=[MACHINES[0]])})

    response = client.get("/api/machines/1/availability", params={"from": TO, "to": FROM})

    assert response.status_code == 422


def test_machine_availability_window_too_long_returns_422(client, monkeypatch):
    use_public_db(
        monkeypatch,
        {"machines": FakeQuery(data=[MACHINES[0]])},
        {"get_machine_busy_slots": FakeQuery(error=api_error("22023", "Availability window cannot be longer than 31 days"))},
    )

    response = client.get(
        "/api/machines/1/availability",
        params={"from": FROM, "to": "2030-03-01T00:00:00+00:00"},
    )

    assert response.status_code == 422
    assert "31 days" in response.json()["detail"]


def test_available_machines_for_a_window(client, monkeypatch):
    fake = use_public_db(monkeypatch, rpcs={"get_available_machines": FakeQuery(data=[MACHINES[1]])})

    response = client.get(
        "/api/machines/available",
        params={"start_time": FROM, "end_time": TO, "type": "DRYER"},
    )

    assert response.status_code == 200
    assert response.json() == [MACHINES[1]]
    assert fake.rpc_calls[0][1]["p_type"] == "DRYER"


# --- Administration -----------------------------------------------------------

NEW_MACHINE = {"type": "WASHER", "capacity": 12, "price": "6.25"}


def test_create_machine_requires_sign_in(client, fake_auth):
    response = client.post("/api/machines/", json=NEW_MACHINE)

    assert response.status_code == 401


def test_create_machine_rejects_customers(client, fake_auth):
    response = client.post("/api/machines/", json=NEW_MACHINE, headers=bearer("customer-token"))

    assert response.status_code == 403


def test_admin_creates_machine(client, fake_auth):
    created = {"id": 3, "type": "WASHER", "capacity": 12, "price": 6.25, "status": "AVAILABLE", "active": True}
    query = FakeQuery(data=[created])
    fake_auth.db.tables["machines"] = query

    response = client.post("/api/machines/", json=NEW_MACHINE, headers=bearer("admin-token"))

    assert response.status_code == 201
    assert response.json() == created
    name, args, _ = next(c for c in query.calls if c[0] == "insert")
    assert args[0] == {"type": "WASHER", "capacity": 12, "price": 6.25, "status": "AVAILABLE", "active": True}


def test_create_machine_validates_input(client, fake_auth):
    fake_auth.db.tables["machines"] = FakeQuery(data=[])

    for bad in (
        {"type": "WASHER", "capacity": 0, "price": 5},
        {"type": "WASHER", "capacity": 8, "price": -1},
        {"type": "WASHER", "capacity": 8, "price": 5.123},
        {"type": "OVEN", "capacity": 8, "price": 5},
        {"type": "WASHER", "capacity": 8, "price": 5, "id": 1},
    ):
        response = client.post("/api/machines/", json=bad, headers=bearer("admin-token"))
        assert response.status_code == 422, bad


def test_admin_changes_machine_status(client, fake_auth):
    updated = {**MACHINES[0], "status": "OUT_OF_SERVICE"}
    query = FakeQuery(data=[updated])
    fake_auth.db.tables["machines"] = query

    response = client.patch(
        "/api/machines/1/status",
        json={"status": "OUT_OF_SERVICE"},
        headers=bearer("admin-token"),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "OUT_OF_SERVICE"
    assert query.called("update", {"status": "OUT_OF_SERVICE"})
    assert query.called("eq", "id", 1)


def test_status_change_rejects_unknown_status(client, fake_auth):
    fake_auth.db.tables["machines"] = FakeQuery(data=[])

    response = client.patch(
        "/api/machines/1/status", json={"status": "BROKEN"}, headers=bearer("admin-token")
    )

    assert response.status_code == 422


def test_update_missing_machine_returns_404(client, fake_auth):
    fake_auth.db.tables["machines"] = FakeQuery(data=[])

    response = client.patch("/api/machines/99", json={"capacity": 9}, headers=bearer("admin-token"))

    assert response.status_code == 404


def test_update_requires_at_least_one_field(client, fake_auth):
    fake_auth.db.tables["machines"] = FakeQuery(data=[])

    response = client.patch("/api/machines/1", json={}, headers=bearer("admin-token"))

    assert response.status_code == 422


def test_admin_updates_only_sent_fields(client, fake_auth):
    query = FakeQuery(data=[{**MACHINES[0], "price": 5.0}])
    fake_auth.db.tables["machines"] = query

    response = client.patch("/api/machines/1", json={"price": "5.00"}, headers=bearer("admin-token"))

    assert response.status_code == 200
    assert query.called("update", {"price": 5.0})


def test_deactivate_machine_is_a_soft_delete(client, fake_auth):
    query = FakeQuery(data=[{**MACHINES[0], "active": False}])
    fake_auth.db.tables["machines"] = query

    response = client.delete("/api/machines/1", headers=bearer("admin-token"))

    assert response.status_code == 204
    assert query.called("update", {"active": False})
    assert not query.called("delete")


def test_customer_cannot_deactivate_machine(client, fake_auth):
    fake_auth.db.tables["machines"] = FakeQuery(data=[])

    response = client.delete("/api/machines/1", headers=bearer("customer-token"))

    assert response.status_code == 403
