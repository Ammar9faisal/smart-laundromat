from tests.conftest import FakeQuery, bearer


def test_summary_requires_admin(client, fake_auth):
    response = client.get("/api/admin/summary", headers=bearer("customer-token"))

    assert response.status_code == 403


def test_summary_counts(client, fake_auth):
    fake_auth.db.tables["machines"] = FakeQuery(
        data=[
            {"status": "AVAILABLE", "active": True},
            {"status": "IN_USE", "active": True},
            {"status": "OUT_OF_SERVICE", "active": True},
            {"status": "AVAILABLE", "active": False},
        ]
    )
    fake_auth.db.tables["reservations"] = FakeQuery(
        data=[{"status": "CONFIRMED"}, {"status": "CONFIRMED"}, {"status": "CANCELLED"}]
    )
    fake_auth.db.tables["payments"] = FakeQuery(
        data=[
            {"status": "SUCCEEDED", "amount": 4.5},
            {"status": "SUCCEEDED", "amount": 3.5},
            {"status": "FAILED", "amount": 4.5},
            {"status": "REFUNDED", "amount": 4.5},
        ]
    )

    response = client.get("/api/admin/summary", headers=bearer("admin-token"))

    assert response.status_code == 200
    assert response.json() == {
        "machines": {"total": 4, "active": 3, "available": 1, "out_of_service": 1},
        "reservations_by_status": {"CONFIRMED": 2, "CANCELLED": 1},
        "payments": {"succeeded": 2, "failed": 1, "refunded": 1, "revenue": 8.0},
    }


def test_admin_lists_all_machines_including_inactive(client, fake_auth):
    machines = [
        {"id": 1, "type": "WASHER", "capacity": 8, "price": 4.5, "status": "AVAILABLE", "active": True},
        {"id": 2, "type": "DRYER", "capacity": 10, "price": 3.5, "status": "AVAILABLE", "active": False},
    ]
    query = FakeQuery(data=machines)
    fake_auth.db.tables["machines"] = query

    response = client.get("/api/admin/machines", headers=bearer("admin-token"))

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert not query.called("eq", "active", True)
