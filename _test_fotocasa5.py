import json, re

with open("_fotocasa_live.html", encoding="utf-8") as f:
    html = f.read()

pattern = r'<script[^>]*id="__initial_props__"[^>]*>(.*?)</script>'
m = re.search(pattern, html, re.DOTALL)
data = json.loads(m.group(1))

print("All top keys:", list(data.keys()))

# Look for realEstates or listings
def find_key(obj, targets, path="", depth=0):
    if depth > 4: return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if any(t in k.lower() for t in targets):
                cnt = len(v) if isinstance(v, list) else ("dict" if isinstance(v, dict) else type(v).__name__)
                print(f"  [{path}.{k}] = {cnt}")
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    print("    First keys:", list(v[0].keys())[:10])
            find_key(v, targets, f"{path}.{k}", depth+1)
    elif isinstance(obj, list):
        for i, item in enumerate(obj[:1]):
            find_key(item, targets, f"{path}[{i}]", depth+1)

find_key(data, ["realestate", "listing", "propert", "result", "item", "anunci"])
