from collections import Counter

from fastapi import APIRouter, Depends
from supabase import Client

from app.dependencies import get_admin_db
from app.errors import db_error
from app.schemas.admin import AdminSummary
from app.schemas.machines import Machine

router = APIRouter(
    prefix="/api/admin",
    tags=["Administration"]
)


@router.get("/machines", response_model=list[Machine])
def list_all_machines(db: Client = Depends(get_admin_db)):
    """Every machine, including deactivated ones."""
    try:
        response = db.table("machines").select("*").order("id").execute()
    except Exception as exc:
        raise db_error(exc, "Failed to retrieve machines")

    return response.data


@router.get("/summary", response_model=AdminSummary)
def get_summary(db: Client = Depends(get_admin_db)):
    """Counts for the admin dashboard (FR-35)."""
    try:
        machines = db.table("machines").select("status, active").execute().data
        reservations = db.table("reservations").select("status").execute().data
        payments = db.table("payments").select("status, amount").execute().data
    except Exception as exc:
        raise db_error(exc, "Failed to build summary")

    payment_counts = Counter(p["status"] for p in payments)
    revenue = sum(float(p["amount"]) for p in payments if p["status"] == "SUCCEEDED")

    return {
        "machines": {
            "total": len(machines),
            "active": sum(1 for m in machines if m["active"]),
            "available": sum(1 for m in machines if m["active"] and m["status"] == "AVAILABLE"),
            "out_of_service": sum(1 for m in machines if m["status"] == "OUT_OF_SERVICE"),
        },
        "reservations_by_status": dict(Counter(r["status"] for r in reservations)),
        "payments": {
            "succeeded": payment_counts.get("SUCCEEDED", 0),
            "failed": payment_counts.get("FAILED", 0),
            "refunded": payment_counts.get("REFUNDED", 0),
            "revenue": round(revenue, 2),
        },
    }
