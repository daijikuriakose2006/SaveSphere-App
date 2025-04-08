"""
Supabase client configuration for SaveSphere app.
"""

import os
from supabase import create_client, Client

# Get Supabase URL and Key from environment variables
# These should be set in your environment or .env file
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# Initialize Supabase client lazily to avoid errors when environment variables are not set
_supabase_client = None

def get_supabase_client():
    """Get the Supabase client instance."""
    global _supabase_client
    
    if _supabase_client is None:
        if SUPABASE_URL and SUPABASE_KEY:
            _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        else:
            # Return dummy client for development/testing when credentials are not set
            from unittest.mock import MagicMock
            _supabase_client = MagicMock()
            print("WARNING: Using mock Supabase client because URL or KEY is not set")
    
    return _supabase_client 