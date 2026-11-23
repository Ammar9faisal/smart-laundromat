from datetime import datetime, timedelta, timezone

import pytest

from app import dependencies
from app.main import app
from tests.conftest import CUSTOMER_ID, FakeQuery, api_error, bearer

HOLD_ENDS = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()

PENDING = {"id": 7, "status": "PENDING_PAYMENT", "price": 4.5, "expires_at": HOLD_ENDS}


def payment(status="SUCCEEDED", **overrides):
    return {
        "id": 11,
        "reservation_id": 7,
        "user_id": CUSTOMER_ID,
        "amount": 4.5,
        "currency": "CAD",
        "status": status,
        "provider": "SIMULATED",
        "provider_ref": "sim_abc",
        "failure_reason": None if status != "FAILED" else "Your card was declined.",
        "idempotency_key": None,
        "created_at": "2030-01-09T10:01:00+00:00",
        "updated_at": "2030-01-09T10:01:00+00:00",
        **overrides,
    }


@pytest.fixture
def pending_reservation(fake_auth):
    fake_auth.db.tables["reservations"] = FakeQuery(data=[PENDING])
    fake_auth.db.tables["payments"] = FakeQuery(data=[])
    return fake_auth


def pay(client, **body):
    return client.post(
        "/api/payments",
        json={"reservation_id": 7, "payment_method": "pm_card_visa", **body},
        headers=bearer("customer-token"),
    )


def test_payment_requires_sign_in(client, fake_auth, service_db):
    response = client.post(
        "/api/payments", json={"reservation_id": 7, "payment_method": "pm_card_visa"}
    )

    assert response.status_code == 401


def test_successful_payment(client, pending_reservation, service_db):
    service_db.rpcs["record_payment"] = FakeQuery(data=payment())

    response = pay(client)

    assert response.status_code == 201
    assert response.json()["status"] == "SUCCEEDED"
    name, params = service_db.rpc_calls[0]
    assert name == "record_payment"
    # The user comes from the verified token, never from the request body.
    assert params["p_user_id"] == CUSTOMER_ID
    assert params["p_succeeded"] is True
    assert params["p_provider_ref"].startswith("sim_")
    assert params["p_currency"] == "CAD"


def test_declined_payment_is_recorded_and_returns_402(client, pending_reservation, service_db):
    service_db.rpcs["record_payment"] = FakeQuery(data=payment("FAILED"))

    response = pay(client, payment_method="pm_card_chargeDeclined")

    assert response.status_code == 402
    assert response.json()["detail"] == "Your card was declined."
    assert response.json()["payment"]["status"] == "FAILED"
    params = service_db.rpc_calls[0][1]
    assert params["p_succeeded"] is False
    assert params["p_failure_reason"] == "Your card was declined."


@pytest.mark.parametrize(
    "body",
    [
        {"payment_method": "4242424242424242"},
        {"payment_method": "pm_card_visa", "card_number": "4242424242424242"},
        {"payment_method": "pm_card_visa", "cvv": "123"},
        {"payment_method": "pm_card_visa", "idempotency_key": "short"},
        {"payment_method": "pm_card_visa", "amount": 0.01},
    ],
)
def test_payment_rejects_card_details_and_bad_input(client, pending_reservation, service_db, body):
    response = pay(client, **body)

    assert response.status_code == 422
    assert service_db.rpc_calls == []


def test_paying_someone_elses_reservation_is_not_found(client, fake_auth, service_db):
    fake_auth.db.tables["reservations"] = FakeQuery(data=[])
    fake_auth.db.tables["payments"] = FakeQuery(data=[])

    response = pay(client)

    assert response.status_code == 404
    assert service_db.rpc_calls == []


def test_paying_a_confirmed_reservation_is_rejected_before_charging(client, fake_auth, service_db):
    fake_auth.db.tables["reservations"] = FakeQuery(data=[{**PENDING, "status": "CONFIRMED"}])
    fake_auth.db.tables["payments"] = FakeQuery(data=[])

    response = pay(client)

    assert response.status_code == 409
    assert service_db.rpc_calls == []


def test_paying_after_the_hold_expired_is_rejected(client, fake_auth, service_db):
    expired = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    fake_auth.db.tables["reservations"] = FakeQuery(data=[{**PENDING, "expires_at": expired}])
    fake_auth.db.tables["payments"] = FakeQuery(data=[])

    response = pay(client)

    assert response.status_code == 409
    assert service_db.rpc_calls == []


def test_repeated_idempotency_key_returns_original_payment(client, fake_auth, service_db):
    original = payment(idempotency_key="order-7-attempt-1")
    fake_auth.db.tables["payments"] = FakeQuery(data=[original])
    fake_auth.db.tables["reservations"] = FakeQuery(data=[PENDING])

    response = pay(client, idempotency_key="order-7-attempt-1")

    assert response.status_code == 200
    assert response.json()["id"] == 11
    assert service_db.rpc_calls == []


def test_idempotency_key_for_another_reservation_is_rejected(client, fake_auth, service_db):
    other = payment(reservation_id=99, idempotency_key="order-7-attempt-1")
    fake_auth.db.tables["payments"] = FakeQuery(data=[other])
    fake_auth.db.tables["reservations"] = FakeQuery(data=[PENDING])

    response = pay(client, idempotency_key="order-7-attempt-1")

    assert response.status_code == 409


def test_state_change_during_payment_returns_409(client, pending_reservation, service_db):
    service_db.rpcs["record_payment"] = FakeQuery(
        error=api_error("LM002", "Reservation 7 is confirmed and cannot be paid")
    )

    response = pay(client)

    assert response.status_code == 409
    assert response.json()["detail"] == "Reservation 7 is confirmed and cannot be paid"


def test_payments_unavailable_without_secret_key(client, pending_reservation, monkeypatch):
    monkeypatch.setattr(dependencies, "get_service_client", lambda: None)
    app.dependency_overrides.pop(dependencies.get_service_db, None)

    response = pay(client)

    assert response.status_code == 503


def test_list_my_payments(client, fake_auth):
    query = FakeQuery(data=[payment()])
    fake_auth.db.tables["payments"] = query

    response = client.get("/api/payments?mine=true&reservation_id=7", headers=bearer("customer-token"))

    assert response.status_code == 200
    assert response.json()[0]["id"] == 11
    assert query.called("eq", "user_id", CUSTOMER_ID)
    assert query.called("eq", "reservation_id", 7)


def test_get_payment_not_visible_returns_404(client, fake_auth):
    fake_auth.db.tables["payments"] = FakeQuery(data=[])

    response = client.get("/api/payments/11", headers=bearer("customer-token"))

    assert response.status_code == 404
