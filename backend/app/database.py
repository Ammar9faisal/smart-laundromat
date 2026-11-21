#setup supabase client to connect to the database
from supabase import create_client, Client
from app.config import SUPABASE_URL, SUPABASE_KEY

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)
