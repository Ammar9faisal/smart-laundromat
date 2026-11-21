import os
from dotenv import load_dotenv

load_dotenv()

#load environment variables from my .env file
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
