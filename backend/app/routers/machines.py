
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import AwareDatetime
from supabase import Client

from app.database import supabase
from app.dependencies import get_admin_db
from app.errors import db_error
from app.schemas.machines import (
    Machine,
    MachineAvailability,
    MachineCreate,
    MachineStatus,
    MachineStatusUpdate,
    MachineType,
    MachineUpdate,
    to_db_values,
)


router = APIRouter(    #setup router for machines
    prefix="/api/machines",
    tags=["Machines"]
)

MACHINE_COLUMNS = "id, type, capacity, price, status, active"


@router.get("/", response_model=list[Machine]) #define a GET endpoint to retrieve active machines
def get_machines(
    type: MachineType | None = None,
    status: MachineStatus | None = None,
    min_capacity: int | None = Query(default=None, gt=0),
):
    """List active machines, optionally filtered by type, status and minimum capacity."""
    try:
        query = (
            supabase.table("machines")
            .select("*")
            .eq("active", True) #active machines only which are available for use
        )
        if type:
            query = query.eq("type", type)
        if status:
            query = query.eq("status", status)
        if min_capacity:
            query = query.gte("capacity", min_capacity)

        response = query.order("id").execute()

        return response.data

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve machines"
        )


@router.get("/available", response_model=list[Machine])
def get_available_machines(
    start_time: AwareDatetime,
    end_time: AwareDatetime,
    type: MachineType | None = None,
):
    """Active, in-service machines with no reservation overlapping the window."""
    if end_time <= start_time:
        raise HTTPException(status_code=422, detail="end_time must be after start_time")

    try:
        response = supabase.rpc(
            "get_available_machines",
            {
                "p_start_time": start_time.isoformat(),
                "p_end_time": end_time.isoformat(),
                "p_type": type,
            },
        ).execute()
    except Exception as exc:
        raise db_error(exc, "Failed to check machine availability")

    return response.data


def _find_active_machine(machine_id: int) -> dict:
    try:
        response = (
            supabase.table("machines")
            .select(MACHINE_COLUMNS)
            .eq("id", machine_id)
            .eq("active", True)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise db_error(exc, "Failed to retrieve machine")

    if not response.data:
        raise HTTPException(status_code=404, detail=f"Machine {machine_id} not found")

    return response.data[0]


@router.get("/{machine_id}", response_model=Machine)
def get_machine(machine_id: int):
    return _find_active_machine(machine_id)


@router.get("/{machine_id}/availability", response_model=MachineAvailability)
def get_machine_availability(
    machine_id: int,
    from_time: AwareDatetime = Query(alias="from"),
    to_time: AwareDatetime = Query(alias="to"),
):
    """Busy time ranges for one machine between `from` and `to` (at most 31 days)."""
    if to_time <= from_time:
        raise HTTPException(status_code=422, detail="'to' must be after 'from'")

    _find_active_machine(machine_id)

    try:
        response = supabase.rpc(
            "get_machine_busy_slots",
            {
                "p_machine_id": machine_id,
                "p_from": from_time.isoformat(),
                "p_to": to_time.isoformat(),
            },
        ).execute()
    except Exception as exc:
        raise db_error(exc, "Failed to retrieve availability")

    return {
        "machine_id": machine_id,
        "from_time": from_time,
        "to_time": to_time,
        "busy": response.data,
    }


# --- Administration (FR-10, FR-33) -----------------------------------------

@router.post("/", response_model=Machine, status_code=201)
def create_machine(
    machine: MachineCreate,
    db: Client = Depends(get_admin_db),
):
    try:
        response = (
            db.table("machines")
            .insert(to_db_values(machine, only_sent=False))
            .execute()
        )
    except Exception as exc:
        raise db_error(exc, "Failed to create machine")

    return response.data[0]


def _update_machine(db: Client, machine_id: int, values: dict) -> dict:
    try:
        response = (
            db.table("machines")
            .update(values)
            .eq("id", machine_id)
            .execute()
        )
    except Exception as exc:
        raise db_error(exc, "Failed to update machine")

    if not response.data:
        raise HTTPException(status_code=404, detail=f"Machine {machine_id} not found")

    return response.data[0]


@router.patch("/{machine_id}", response_model=Machine)
def update_machine(
    machine_id: int,
    changes: MachineUpdate,
    db: Client = Depends(get_admin_db),
):
    return _update_machine(db, machine_id, to_db_values(changes))


@router.patch("/{machine_id}/status", response_model=Machine)
def update_machine_status(
    machine_id: int,
    body: MachineStatusUpdate,
    db: Client = Depends(get_admin_db),
):
    return _update_machine(db, machine_id, {"status": body.status})


@router.delete("/{machine_id}", status_code=204)
def deactivate_machine(
    machine_id: int,
    db: Client = Depends(get_admin_db),
):
    """Soft delete: the machine is marked inactive so past reservations keep it."""
    _update_machine(db, machine_id, {"active": False})
    return Response(status_code=204)
