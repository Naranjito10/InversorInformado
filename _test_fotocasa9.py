import json, re

with open("_fotocasa_live.html", encoding="utf-8") as f:
    html = f.read()

pattern = r'<script[^>]*id="__initial_props__"[^>]*>(.*?)</script>'
data = json.loads(re.search(pattern, html, re.DOTALL).group(1))
res = data["initialSearch"]["result"]["realEstates"][0]
print("rawPrice:", res.get("rawPrice"))
print("detail:", res.get("detail"))
print("address.neighborhood:", res.get("address", {}).get("neighborhood"))
print("address.district:", res.get("address", {}).get("district"))
print("address.municipality:", res.get("address", {}).get("municipality"))
print("address.province:", res.get("address", {}).get("province"))
print("coordinates:", res.get("coordinates"))
