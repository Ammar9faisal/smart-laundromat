import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client

from app.config import RESERVATION_HOLD_MINUTES
from app.dependencies import AuthContext, get_current_user, get_user_db
from app.errors import db_error
from app.schemas.reservations import Reservation, ReservationCreate, ReservationStatus

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/reservations",
    tags=["Reservations"]
)

RESERVATION_COLUMNS = "*, machine:machines(id, type, capacity, price, status)"


@router.post("", response_model=Reservation, status_code=201)
def create_reservation(
    body: ReservationCreate,
    auth: AuthContext = Depends(get_current_user),
    db: Client = Depends(get_user_db),
):
    """Reserve a machine for a time slot (FR-12, FR-13, FR-17).

    The reservation starts as PENDING_PAYMENT and holds the slot for a limited
    time. Overlapping reservations are rejected with 409 by the database, so
    the rule also holds for simultaneous requests.
    """
    try:
        response = db.rpc(
            "create_reservation",
            {
                "p_machine_id": body.machine_id,
                "p_start_time": body.start_time.isoformat(),
                "p_end_time": body.end_time.isoformat(),
                "p_hold_minutes": RESERVATION_HOLD_MINUTES,
            },
        ).execute()
    except Exception as exc:
        raise db_error(exc, "Failed to create reservation")

    reservation = response.data
    logger.info(
        "ReservationCreated id=%s machine=%s user=%s",
        reservation["id"], reservation["machine_id"], auth.user.id,
    )
    return reservation


@router.get("", response_model=list[Reservation])
def list_reservations(
    auth: AuthContext = Depends(get_current_user),
    db: Client = Depends(get_user_db),
    mine: bool = Query(
        default=False,
        description="Only the caller's reservations (customers only ever see their own)",
    ),
    status: ReservationStatus | None = None,
    machine_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=100, ge=1, le=500),
):
    """Customers see their own reservations; administrators see everyone's (FR-4, FR-34)."""
    try:
        query = db.table("reservations").select(RESERVATION_COLUMNS)
        if mine:
            query = query.eq("user_id", str(auth.user.id))
        if status:
            query = query.eq("status", status)
        if machine_id:
            query = query.eq("machine_id", machine_id)

        response = query.order("start_time", desc=True).limit(limit).execute()
    except Exception as exc:
        raise db_error(exc, "Failed to retrieve reservations")

    return response.data


@router.get("/{reservation_id}", response_model=Reservation)
def get_reservation(
    reservation_id: int,
    db: Client = Depends(get_user_db),
):
    try:
        response = (
            db.table("reservations")
            .select(RESERVATION_COLUMNS)
            .eq("id", reservation_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise db_error(exc, "Failed to retrieve reservation")

    # Row level security hides other customers' reservations, so they are
    # reported as not found.
    if not response.data:
        raise HTTPException(status_code=404, detail=f"Reservation {reservation_id} not found")

    return response.data[0]


@router.delete("/{reservation_id}", response_model=Reservation)
def cancel_reservation(
    reservation_id: int,
    auth: AuthContext = Depends(get_current_user),
    db: Client = Depends(get_user_db),
):
    """Cancel a future reservation (FR-15). A successful payment is refunded when
    the cancellation is more than 15 minutes before the start time (FR-19)."""
    try:
        response = db.rpc(
            "cancel_reservation",
            {"p_reservation_id": reservation_id},
        ).execute()
    except Exception as exc:
        raise db_error(exc, "Failed to cancel reservation")

    logger.info("ReservationCancelled id=%s user=%s", reservation_id, auth.user.id)
    return response.data
