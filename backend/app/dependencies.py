
from dataclasses import dataclass

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client

from app.database import supabase, get_user_client, get_service_client

security = HTTPBearer()

@dataclass
class AuthContext:
    user: object
    token: str

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> AuthContext:
    token = credentials.credentials

    try:
        response = supabase.auth.get_user(token)

        if response.user is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid access token"
            )

        return AuthContext(
            user=response.user,
            token=token
        )

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token"
        )

def require_admin(
    auth: AuthContext = Depends(get_current_user)
) -> AuthContext:
    client = get_user_client(auth.token)

    try:
        result = (
            client.table("profiles")
            .select("role")
            .eq("id", str(auth.user.id))
            .single()
            .execute()
        )
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Unable to verify account role"
        )

    if result.data["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Administrator access required"
        )

    return auth

def get_user_db(
    auth: AuthContext = Depends(get_current_user)
) -> Client:
    """Supabase client acting as the signed-in user, so row level security
    decides which rows they can read."""
    return get_user_client(auth.token)

def get_admin_db(
    auth: AuthContext = Depends(require_admin)
) -> Client:
    """Supabase client for an administrator (role checked by require_admin)."""
    return get_user_client(auth.token)

def get_service_db() -> Client:
    client = get_service_client()

    if client is None:
        raise HTTPException(
            status_code=503,
            detail="Payments are not configured on the server"
        )

    return client
