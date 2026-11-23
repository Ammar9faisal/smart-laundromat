from datetime import datetime, timedelta, timezone

import pytest

from tests.conftest import CUSTOMER_ID, FakeQuery, api_error, bearer


def future(hours, minutes=0):
    start = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(days=2)
    return (start + timedelta(hours=hours, minutes=minutes)).isoformat()


RESERVATION = {
    "id": 7,
    "user_id": CUSTOMER_ID,
    "machine_id": 1,
    "start_time": "2030-01-10T10:00:00+00:00",
    "end_time": "2030-01-10T11:00:00+00:00",
    "status": "PENDING_PAYMENT",
    "price": 4.5,
    "expires_at": "2030-01-09T10:15:00+00:00",
    "version": 1,
    "created_at": "2030-01-09T10:00:00+00:00",
    "updated_at": "2030-01-09T10:00:00+00:00",
}


def booking(**overrides):
    return {"machine_id": 1, "start_time": future(10), "end_time": future(11), **overrides}


# --- Create -------------------------------------------------------------------

def test_create_reservation_requires_sign_in(client, fake_auth):
    response = client.post("/api/reservations", json=booking())

    assert response.status_code == 401


def test_customer_creates_reservation(client, fake_auth):
    fake_auth.db.rpcs["create_reservation"] = FakeQuery(data=RESERVATION)
    body = booking()

    response = client.post("/api/reservations", json=body, headers=bearer("customer-token"))

    assert response.status_code == 201
    assert response.json()["status"] == "PENDING_PAYMENT"
    name, params = fake_auth.db.rpc_calls[0]
    assert name == "create_reservation"
    assert params["p_machine_id"] == 1
    assert params["p_hold_minutes"] == 15
    # The user is never sent: the database takes it from the access token.
    assert "p_user_id" not in params
    # The call runs with the customer's own token (row level security applies).
    assert "customer-token" in fake_auth.user_client_tokens


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"start_time": future(11), "end_time": future(10)}, "end before start"),
        ({"start_time": future(10), "end_time": future(10, 10)}, "shorter than 15 minutes"),
        ({"start_time": future(10), "end_time": future(14)}, "longer than 3 hours"),
        ({"start_time": "2020-01-01T10:00:00+00:00", "end_time": "2020-01-01T11:00:00+00:00"}, "in the past"),
        ({"start_time": future(24 * 40), "end_time": future(24 * 40 + 1)}, "more than 30 days ahead"),
        ({"start_time": "2030-01-10T10:00:00", "end_time": "2030-01-10T11:00:00"}, "no time zone"),
        ({"machine_id": 0}, "invalid machine id"),
        ({"user_id": "00000000-0000-4000-8000-0000000000b2"}, "unexpected field"),
    ],
)
def test_create_reservation_validates_input(client, fake_auth, overrides, reason):
    fake_auth.db.rpcs["create_reservation"] = FakeQuery(data=RESERVATION)

    response = client.post(
        "/api/reservations", json=booking(**overrides), headers=bearer("customer-token")
    )

    assert response.status_code == 422, reason
    assert fake_auth.db.rpc_calls == []


@pytest.mark.parametrize(
    ("code", "status"),
    [("23P01", 409), ("LM001", 422), ("P0002", 404), ("22023", 422)],
)
def test_create_reservation_database_rules(client, fake_auth, code, status):
    message = "Machine 1 is already reserved for part of that time"
    fake_auth.db.rpcs["create_reservation"] = FakeQuery(error=api_error(code, message))

    response = client.post("/api/reservations", json=booking(), headers=bearer("customer-token"))

    assert response.status_code == status
    assert response.json() == {"detail": message}


# --- Read ---------------------------------------------------------------------

def test_list_my_reservations(client, fake_auth):
    query = FakeQuery(data=[RESERVATION])
    fake_auth.db.tables["reservations"] = query

    response = client.get(
        "/api/reservations?mine=true&status=PENDING_PAYMENT", headers=bearer("customer-token")
    )

    assert response.status_code == 200
    assert response.json()[0]["id"] == 7
    assert query.called("eq", "user_id", CUSTOMER_ID)
    assert query.called("eq", "status", "PENDING_PAYMENT")


def test_list_reservations_rejects_unknown_status(client, fake_auth):
    fake_auth.db.tables["reservations"] = FakeQuery(data=[])

    response = client.get("/api/reservations?status=LOST", headers=bearer("customer-token"))

    assert response.status_code == 422


def test_get_reservation(client, fake_auth):
    machine = {"id": 1, "type": "WASHER", "capacity": 8, "price": 4.5, "status": "AVAILABLE"}
    fake_auth.db.tables["reservations"] = FakeQuery(data=[{**RESERVATION, "machine": machine}])

    response = client.get("/api/reservations/7", headers=bearer("customer-token"))

    assert response.status_code == 200
    assert response.json()["machine"]["type"] == "WASHER"


def test_someone_elses_reservation_is_not_found(client, fake_auth):
    # Row level security returns no rows for another customer's reservation.
    fake_auth.db.tables["reservations"] = FakeQuery(data=[])

    response = client.get("/api/reservations/7", headers=bearer("customer-token"))

    assert response.status_code == 404


# --- Cancel -------------------------------------------------------------------

def test_cancel_reservation(client, fake_auth):
    fake_auth.db.rpcs["cancel_reservation"] = FakeQuery(data={**RESERVATION, "status": "CANCELLED"})

    response = client.delete("/api/reservations/7", headers=bearer("customer-token"))

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    assert fake_auth.db.rpc_calls[0] == ("cancel_reservation", {"p_reservation_id": 7})


@pytest.mark.parametrize(("code", "status"), [("LM002", 409), ("P0002", 404)])
def test_cancel_reservation_errors(client, fake_auth, code, status):
    fake_auth.db.rpcs["cancel_reservation"] = FakeQuery(error=api_error(code, "Not allowed"))

    response = client.delete("/api/reservations/7", headers=bearer("customer-token"))

    assert response.status_code == status
