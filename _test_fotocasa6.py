import json, re

with open("_fotocasa_live.html", encoding="utf-8") as f:
    html = f.read()

pattern = r'<script[^>]*id="__initial_props__"[^>]*>(.*?)</script>'
data = json.loads(re.search(pattern, html, re.DOTALL).group(1))

items = data["initialSearch"]["result"]["resultsV2"]["items"]
print("Total items:", len(items))
item = items[0]
print("\nTop keys:", list(item.keys()))

# Price
print("\nPrice:", item.get("price"))

# Location
print("Location:", item.get("location"))

# Detail URL
print("detailUrl:", item.get("detailUrl"))

# Dynamic features
print("dynamicFeatures:", item.get("dynamicFeatures", [])[:5])

# contracts
print("contracts:", item.get("contracts", []))
