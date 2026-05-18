import json, re

with open("_fotocasa_live.html", encoding="utf-8") as f:
    html = f.read()

pattern = r'<script[^>]*id="__initial_props__"[^>]*>(.*?)</script>'
data = json.loads(re.search(pattern, html, re.DOTALL).group(1))

res = data["initialSearch"]["result"]["realEstates"][0]
v2 = data["initialSearch"]["result"]["resultsV2"]["items"][0]

print("realEstates[0].detail:", res.get("detail"))
print("realEstates[0].realEstateAdId:", res.get("realEstateAdId"))
print("v2.realEstateAdId:", v2.get("realEstateAdId"))
print("v2.detailUrl:", v2.get("detailUrl"))
print("v2.features:", v2.get("features"))

# Show first 3 items from realEstates with key fields
print("\n--- First 3 realEstates ---")
for i, r in enumerate(data["initialSearch"]["result"]["realEstates"][:3]):
    print(f"[{i}] id={r.get('realEstateAdId')} price={r.get('price')} "
          f"desc={str(r.get('description',''))[:60]}")
    addr = r.get("address", {})
    print(f"     dist={addr.get('district')} barrio={addr.get('neighborhood')} muni={addr.get('municipality')}")
