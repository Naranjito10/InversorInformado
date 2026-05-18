"""Consulta los triggers y FK constraints del schema de Supabase."""
from scraper.db import get_client

client = get_client()

# Query triggers via pg_trigger / information_schema using RPC
# Supabase permite queries SQL via RPC si hay una función, o via postgrest /rpc
# Usamos una tabla de sistema accesible
try:
    # information_schema.triggers
    res = client.rpc("query_triggers", {}).execute()
    print("RPC triggers:", res)
except Exception as e:
    print(f"RPC failed: {e}")

# Try via raw postgrest query on pg_trigger (may not be accessible)
try:
    res = client.table("pg_trigger").select("*").execute()
    print("pg_trigger:", res.data[:3])
except Exception as e:
    print(f"pg_trigger access: {e}")

# Check if there's a way to see the trigger via listings table meta
# Try inserting into price_history directly to see FK direction
try:
    import uuid
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    fake_id = str(uuid.uuid4())
    res = client.table("price_history").insert({
        "listing_id": fake_id,
        "precio": 100000,
        "fecha": now,
    }).execute()
    print("price_history insert with fake id:", res.data)
except Exception as e:
    print(f"price_history insert error: {e}")
