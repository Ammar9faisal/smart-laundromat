import os
from dotenv import load_dotenv

load_dotenv()

#load environment variables from my .env file
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

# Secret key for the server-side client. Only used for operations customers must
# not be able to perform themselves (recording payment outcomes). Optional so the
# rest of the API still runs without it; payment endpoints return 503 instead.
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY")

# How long an unpaid reservation holds its time slot (FR-16).
RESERVATION_HOLD_MINUTES = int(os.environ.get("RESERVATION_HOLD_MINUTES", "15"))
