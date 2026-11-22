#setup supabase client to connect to the database
from supabase import create_client, Client, ClientOptions
from app.config import SUPABASE_URL, SUPABASE_KEY

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
