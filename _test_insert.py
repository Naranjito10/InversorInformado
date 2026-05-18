"""Prueba de insert minimal para diagnosticar el trigger de Supabase."""
from datetime import datetime, timezone
from scraper.db import get_client

client = get_client()
now = datetime.now(timezone.utc).isoformat()

# Insert minimal sin raw_data para ver si el trigger falla
payload_minimal = {
    "url": "https://test.fotocasa.es/test-diagnostic-001",
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

print("Intentando insert minimal (sin raw_data)...")
try:
    res = client.table("listings").insert(payload_minimal).execute()
    print("OK:", res.data)
    # Clean up test row
    client.table("listings").delete().eq("url", "https://test.fotocasa.es/test-diagnostic-001").execute()
    print("Test row eliminado.")
except Exception as e:
    print(f"FAILED: {e}")

# Now check if raw_data column exists by trying to insert with it
print("\nComprobando si columna raw_data existe...")
payload_with_raw = {**payload_minimal, "raw_data": {"test": True}}
payload_with_raw["url"] = "https://test.fotocasa.es/test-diagnostic-002"
try:
    res2 = client.table("listings").insert(payload_with_raw).execute()
    print("raw_data columna: EXISTE")
    client.table("listings").delete().eq("url", "https://test.fotocasa.es/test-diagnostic-002").execute()
except Exception as e:
    print(f"raw_data columna error: {e}")
