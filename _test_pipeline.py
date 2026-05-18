"""Diagnostico: traza el pipeline completo de un item de Fotocasa hasta Supabase."""
from scraper.http_client import fetch_html
from scraper.scrapers.fotocasa import FotocasaScraper
from scraper.normalizer import normalize
from scraper.db import get_client, upsert_listing

url = "https://www.fotocasa.es/es/comprar/viviendas/barcelona-capital/eixample/l"
html = fetch_html(url, use_js=True)
items = list(FotocasaScraper().parse_search_page(html, url))
print(f"[1] parse_search_page: {len(items)} items")
if not items:
    print("ERROR: 0 items parsed")
    exit(1)

raw = items[0]
print(f"[2] raw item keys: {list(raw.keys())}")
print(f"    url={raw.get('url')}, precio={raw.get('precio_venta')}, metros={raw.get('metros_cuadrados')}")

try:
    listing = normalize("fotocasa", raw)
    print(f"[3] normalize OK: url={listing.url}, precio={listing.precio_venta}, metros={listing.metros_cuadrados}")
except Exception as e:
    print(f"[3] normalize FAILED: {e}")
    exit(1)

db_dict = listing.to_db_dict()
print(f"[4] to_db_dict keys: {list(db_dict.keys())}")

# Try direct insert to Supabase and see the actual error
client = get_client()
try:
    from datetime import datetime, timezone
    db_dict["primera_deteccion"] = datetime.now(timezone.utc).isoformat()
    db_dict["ultima_actualizacion"] = datetime.now(timezone.utc).isoformat()
    db_dict["veces_visto"] = 1
    db_dict["activo"] = True
    res = client.table("listings").insert(db_dict).execute()
    print(f"[5] INSERT OK: {res.data}")
except Exception as e:
    print(f"[5] INSERT FAILED: {e}")
    # Show which fields might conflict
    print(f"    Fields sent: {list(db_dict.keys())}")
