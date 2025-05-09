import os
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

# Initialize Supabase client
def get_supabase_client():
    """
    Create and return a Supabase client instance.
    Raises an exception if environment variables are not properly set.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_ANON_KEY must be set in the environment variables"
        )
    
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# Default client instance
try:
    supabase = get_supabase_client()
except Exception as e:
    print(f"Warning: Could not initialize Supabase client: {e}")
    supabase = None