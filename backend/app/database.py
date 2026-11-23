#setup supabase client to connect to the database
from supabase import create_client, Client, ClientOptions
from app.config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_SECRET_KEY

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

def get_user_client(access_token: str) -> Client:
    return create_client(
        SUPABASE_URL,
        SUPABASE_KEY,
        options=ClientOptions(
            headers={
                "Authorization": f"Bearer {access_token}"
            }
        )
    )

_service_client: Client | None = None

def get_service_client() -> Client | None:
    """Client using the secret key. It bypasses row level security, so it is
    only used for operations restricted to the backend (recording payments).
    Returns None when SUPABASE_SECRET_KEY is not configured."""
    global _service_client

    if not SUPABASE_SECRET_KEY:
        return None

    if _service_client is None:
        _service_client = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

    return _service_client
