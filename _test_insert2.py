"""Test: insert con id explícito para ver si el trigger necesita que esté presente."""
import uuid
from datetime import datetime, timezone
from scraper.db import get_client

client = get_client()
now = datetime.now(timezone.utc).isoformat()
listing_id = str(uuid.uuid4())

payload = {
    "id": listing_id,
    "url": f"https://test.fotocasa.es/test-diag-{listing_id[:8]}",
    "fuente": "fotocasa",
    "precio_venta": 300000,
    "metros_cuadrados": 80,
    "barrio": "Eixample",
    "municipio": "Barcelona",
    "primera_deteccion": now,
    "ultima_actualizacion": now,
    "veces_visto": 1,
    "activo": True,
    "bajada_precio": False,
}

print(f"Insert con id={listing_id}...")
try:
    res = client.table("listings").insert(payload).execute()
    print("OK:", res.data)
    client.table("listings").delete().eq("id", listing_id).execute()
    print("Test row eliminado.")
except Exception as e:
    print(f"FAILED: {e}")
