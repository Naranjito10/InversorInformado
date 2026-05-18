import json, re

with open("_fotocasa_live.html", encoding="utf-8") as f:
    html = f.read()

pattern = r'<script[^>]*id="__initial_props__"[^>]*>(.*?)</script>'
data = json.loads(re.search(pattern, html, re.DOTALL).group(1))

real_estates = data["initialSearch"]["result"]["realEstates"]
v2_items = data["initialSearch"]["result"]["resultsV2"]["items"]
v2_index = {it["realEstateAdId"]: it for it in v2_items if it.get("realEstateAdId")}

print(f"{'='*70}")
print(f"FOTOCASA — Eixample, Barcelona | {len(real_estates)} anuncios")
print(f"{'='*70}\n")

for i, raw in enumerate(real_estates, 1):
    detail = raw.get("detail") or {}
    path = detail.get("es-ES") or detail.get("es") or ""
    url = f"https://www.fotocasa.es{path}"
    precio_raw = raw.get("rawPrice")
    precio_str = f"{precio_raw:,}".replace(",", ".") + " €" if precio_raw else raw.get("price", "—")
    addr = raw.get("address") or {}
    barrio = addr.get("neighborhood") or addr.get("district") or "—"
    muni = (addr.get("municipality") or "").strip() or "—"
    v2 = v2_index.get(raw.get("realEstateAdId") or "")
    feats = (v2.get("features") or {}) if v2 else {}
    metros = feats.get("surface") or "—"
    rooms = feats.get("rooms") or "—"
    banos = feats.get("bathrooms") or "—"
    planta = feats.get("floor")
    planta_str = f"Planta {planta}" if planta is not None else "—"
    coords = raw.get("coordinates") or {}
    lat = coords.get("latitude")
    lon = coords.get("longitude")
    desc = (raw.get("description") or "")[:120].replace("\n", " ")
    precio_m2 = round(precio_raw / metros) if precio_raw and isinstance(metros, int) and metros > 0 else None

    print(f"[{i:02d}] {precio_str:<18}  {metros}m²  {rooms} hab  {banos} baños  {planta_str}")
    print(f"     {barrio}, {muni}")
    if precio_m2:
        print(f"     Precio/m²: {precio_m2:,} €/m²".replace(",", "."))
    if desc:
        print(f"     {desc}...")
    print(f"     {url}")
    print()
