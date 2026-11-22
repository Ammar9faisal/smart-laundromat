
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import (
    AuthContext,
    get_current_user,
    require_admin
)
from app.database import get_user_client

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)

@router.get("/me")
def get_my_profile(
    auth: AuthContext = Depends(get_current_user)
):
    client = get_user_client(auth.token)

    try:
        response = (
            client.table("profiles")
            .select("id, full_name, role, created_at")
            .eq("id", str(auth.user.id))
            .single()
            .execute()
        )
        return {
            **response.data,
            "email": auth.user.email
        }
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve profile"
        )

@router.get("/admin-test")
def admin_test(
    auth: AuthContext = Depends(require_admin)
):
    return {
        "message": "Admin access granted",
        "user_id": str(auth.user.id)
    }
