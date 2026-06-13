import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("SUPABASE_URL", "")
key: str = os.environ.get("SUPABASE_KEY", "")

print(f"[DEBUG] SUPABASE_URL={'SET ('+str(len(url))+' chars)' if url else 'MISSING'}")
print(f"[DEBUG] All env keys with SUPA: {[k for k in os.environ if 'SUPA' in k]}")

supabase: Client = create_client(url, key)
