
from dataclasses import dataclass

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.database import supabase, get_user_client

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
