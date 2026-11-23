"""End-to-end checks of the reservation and payment rules against Supabase."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app
from integration_tests.conftest import auth_header


def slot(days, hour, hours=1):
    day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    start = day + timedelta(days=days, hours=hour)
    return start.isoformat(), (start + timedelta(hours=hours)).isoformat()


def test_booking_payment_and_cancellation(client, customers, machine):
    a, b = customers
    start, end = slot(days=3, hour=9)
    booking = {"machine_id": machine["id"], "start_time": start, "end_time": end}

    # Customer A reserves the slot.
    response = client.post("/api/reservations", json=booking, headers=auth_header(a))
    assert response.status_code == 201, response.text
    reservation = response.json()
    assert reservation["status"] == "PENDING_PAYMENT"
    assert reservation["price"] == 4.25

    # Customer B cannot book an overlapping slot.
    overlap_start, overlap_end = slot(days=3, hour=9, hours=2)
    response = client.post(
        "/api/reservations",
        json={"machine_id": machine["id"], "start_time": overlap_start, "end_time": overlap_end},
        headers=auth_header(b),
    )
    assert response.status_code == 409, response.text

    # Customer B cannot see or cancel A's reservation.
    assert client.get(f"/api/reservations/{reservation['id']}", headers=auth_header(b)).status_code == 404
    assert client.delete(f"/api/reservations/{reservation['id']}", headers=auth_header(b)).status_code == 404

    # The slot shows as busy.
    response = client.get(
        f"/api/machines/{machine['id']}/availability", params={"from": start, "to": end}
    )
    assert response.status_code == 200
    assert len(response.json()["busy"]) == 1

    # A declined card is recorded and leaves the reservation unpaid.
    response = client.post(
        "/api/payments",
        json={"reservation_id": reservation["id"], "payment_method": "pm_card_chargeDeclined"},
        headers=auth_header(a),
    )
    assert response.status_code == 402, response.text
    response = client.get(f"/api/reservations/{reservation['id']}", headers=auth_header(a))
    assert response.json()["status"] == "PENDING_PAYMENT"

    # A successful payment confirms it.
    pay = {
        "reservation_id": reservation["id"],
        "payment_method": "pm_card_visa",
        "idempotency_key": f"integration-{reservation['id']}-1",
    }
    response = client.post("/api/payments", json=pay, headers=auth_header(a))
    assert response.status_code == 201, response.text
    payment = response.json()
    assert payment["status"] == "SUCCEEDED"
    assert payment["amount"] == 4.25

    response = client.get(f"/api/reservations/{reservation['id']}", headers=auth_header(a))
    assert response.json()["status"] == "CONFIRMED"

    # Repeating the request returns the same payment instead of charging again.
    response = client.post("/api/payments", json=pay, headers=auth_header(a))
    assert response.status_code == 200
    assert response.json()["id"] == payment["id"]

    # Paying again with a new key is rejected.
    response = client.post(
        "/api/payments", json={**pay, "idempotency_key": f"integration-{reservation['id']}-2"},
        headers=auth_header(a),
    )
    assert response.status_code == 409

    # Cancelling days ahead refunds the payment and frees the slot.
    response = client.delete(f"/api/reservations/{reservation['id']}", headers=auth_header(a))
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "CANCELLED"

    response = client.get(
        "/api/payments", params={"reservation_id": reservation["id"]}, headers=auth_header(a)
    )
    statuses = sorted(p["status"] for p in response.json())
    assert statuses == ["FAILED", "REFUNDED"]

    response = client.post("/api/reservations", json=booking, headers=auth_header(b))
    assert response.status_code == 201, response.text


def test_fifty_simultaneous_bookings_for_one_slot(customers, machine):
    """NF-3: only one of many simultaneous requests for the same slot succeeds."""
    start, end = slot(days=4, hour=14)
    booking = {"machine_id": machine["id"], "start_time": start, "end_time": end}

    def attempt(i):
        user = customers[i % 2]
        with TestClient(app) as client:
            return client.post("/api/reservations", json=booking, headers=auth_header(user)).status_code

    with ThreadPoolExecutor(max_workers=50) as pool:
        codes = list(pool.map(attempt, range(50)))

    assert codes.count(201) == 1, codes
    assert codes.count(409) == 49, codes


def test_customers_cannot_manage_machines(client, customers, machine):
    a, _ = customers

    response = client.patch(
        f"/api/machines/{machine['id']}/status",
        json={"status": "OUT_OF_SERVICE"},
        headers=auth_header(a),
    )
    assert response.status_code == 403

    response = client.post(
        "/api/machines/", json={"type": "DRYER", "capacity": 9, "price": "3.00"},
        headers=auth_header(a),
    )
    assert response.status_code == 403
