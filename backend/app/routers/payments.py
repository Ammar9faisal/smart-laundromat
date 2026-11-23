import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from supabase import Client

from app.dependencies import AuthContext, get_current_user, get_service_db, get_user_db
from app.errors import db_error
from app.schemas.payments import Payment, PaymentCreate, PaymentFailed, PaymentStatus
from app.services.payment_gateway import SimulatedPaymentGateway, get_payment_gateway

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/payments",
    tags=["Payments"]
)

CURRENCY = "CAD"


def _payment_response(payment: dict, created: bool) -> JSONResponse:
    """201 for a new successful payment, 200 when an earlier result is replayed,
    402 when the (simulated) card was declined."""
    body = Payment.model_validate(payment).model_dump(mode="json")

    if payment["status"] == "FAILED":
        detail = payment.get("failure_reason") or "Payment failed"
        return JSONResponse(status_code=402, content={"detail": detail, "payment": body})

    return JSONResponse(status_code=201 if created else 200, content=body)


@router.post(
    "",
    status_code=201,
    response_model=Payment,
    responses={
        200: {"model": Payment, "description": "Repeated request: the original payment"},
        402: {"model": PaymentFailed, "description": "The simulated card was declined"},
    },
)
def create_payment(
    body: PaymentCreate,
    auth: AuthContext = Depends(get_current_user),
    db: Client = Depends(get_user_db),
    service_db: Client = Depends(get_service_db),
    gateway: SimulatedPaymentGateway = Depends(get_payment_gateway),
):
    """Pay for a PENDING_PAYMENT reservation with a simulated card (FR-18 to FR-22).

    A successful payment confirms the reservation. A declined payment is still
    recorded, and the reservation stays PENDING_PAYMENT so the customer can try
    again until the hold expires.
    """
    user_id = str(auth.user.id)

    # Same idempotency key as an earlier request: return that result (FR-21).
    if body.idempotency_key:
        try:
            existing = (
                db.table("payments")
                .select("*")
                .eq("idempotency_key", body.idempotency_key)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            raise db_error(exc, "Failed to process payment")

        if existing.data:
            payment = existing.data[0]
            if payment["reservation_id"] != body.reservation_id:
                raise HTTPException(
                    status_code=409,
                    detail="Idempotency key was already used for another reservation",
                )
            return _payment_response(payment, created=False)

    # The customer can only see their own reservations, so someone else's is a 404.
    try:
        found = (
            db.table("reservations")
            .select("id, status, price, expires_at")
            .eq("id", body.reservation_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise db_error(exc, "Failed to process payment")

    if not found.data:
        raise HTTPException(status_code=404, detail=f"Reservation {body.reservation_id} not found")

    reservation = found.data[0]

    # Checked before charging so a customer is never charged for a reservation
    # that cannot be confirmed. record_payment checks again inside its transaction.
    if reservation["status"] != "PENDING_PAYMENT":
        raise HTTPException(
            status_code=409,
            detail=f"Reservation is {reservation['status'].lower()} and cannot be paid",
        )

    expires_at = datetime.fromisoformat(reservation["expires_at"])
    if expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=409, detail="The hold on this reservation has expired")

    result = gateway.charge(
        amount=float(reservation["price"]),
        currency=CURRENCY,
        payment_method=body.payment_method,
    )

    try:
        recorded = service_db.rpc(
            "record_payment",
            {
                "p_user_id": user_id,
                "p_reservation_id": body.reservation_id,
                "p_succeeded": result.succeeded,
                "p_provider_ref": result.provider_ref,
                "p_failure_reason": result.failure_reason,
                "p_idempotency_key": body.idempotency_key,
                "p_currency": CURRENCY,
            },
        ).execute()
    except Exception as exc:
        raise db_error(exc, "Failed to record payment")

    payment = recorded.data
    event = "PaymentCompleted" if result.succeeded else "PaymentFailed"
    logger.info(
        "%s payment=%s reservation=%s user=%s",
        event, payment["id"], body.reservation_id, user_id,
    )
    return _payment_response(payment, created=True)


@router.get("", response_model=list[Payment])
def list_payments(
    auth: AuthContext = Depends(get_current_user),
    db: Client = Depends(get_user_db),
    mine: bool = Query(
        default=False,
        description="Only the caller's payments (customers only ever see their own)",
    ),
    reservation_id: int | None = Query(default=None, gt=0),
    status: PaymentStatus | None = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    """Customers see their own payments; administrators see everyone's (FR-34)."""
    try:
        query = db.table("payments").select("*")
        if mine:
            query = query.eq("user_id", str(auth.user.id))
        if reservation_id:
            query = query.eq("reservation_id", reservation_id)
        if status:
            query = query.eq("status", status)

        response = query.order("created_at", desc=True).limit(limit).execute()
    except Exception as exc:
        raise db_error(exc, "Failed to retrieve payments")

    return response.data


@router.get("/{payment_id}", response_model=Payment)
def get_payment(
    payment_id: int,
    db: Client = Depends(get_user_db),
):
    try:
        response = (
            db.table("payments")
            .select("*")
            .eq("id", payment_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise db_error(exc, "Failed to retrieve payment")

    if not response.data:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found")

    return response.data[0]
