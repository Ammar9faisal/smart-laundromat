
from getpass import getpass
from supabase import create_client
from app.config import SUPABASE_URL, SUPABASE_KEY

client = create_client(SUPABASE_URL, SUPABASE_KEY)

email = input("Email: ")
password = getpass("Password: ")

response = client.auth.sign_in_with_password({
    "email": email,
    "password": password
})

if response.session:
    print("\nAccess token:")
    print(response.session.access_token)
else:
    print("No session returned")
