import json, re

with open("_fotocasa_live.html", encoding="utf-8") as f:
    html = f.read()

pattern = r'<script[^>]*id="__initial_props__"[^>]*>(.*?)</script>'
data = json.loads(re.search(pattern, html, re.DOTALL).group(1))

item = data["initialSearch"]["result"]["resultsV2"]["items"][0]
print("features:", item.get("features"))

# Also check realEstates for title/description
res = data["initialSearch"]["result"]["realEstates"][0]
print("\nrealEstates[0] keys:", list(res.keys()))
print("title:", res.get("title"))
print("description:", res.get("description", "")[:100])
print("price:", res.get("price"))
print("address:", res.get("address"))
print("surface:", res.get("surface"))
print("rooms:", res.get("rooms"))
print("bathrooms:", res.get("bathrooms"))
print("floor:", res.get("floor"))
print("detailUrl:", res.get("detailUrl"))
