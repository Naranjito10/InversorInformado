import json, re
from scraper.http_client import fetch_html

url = "https://www.fotocasa.es/es/comprar/viviendas/barcelona-capital/eixample/l"
html = fetch_html(url, use_js=True)

m = re.search(r'<script id="__initial_props__"[^>]*>(.*?)</script>', html, re.DOTALL)
if m:
    data = json.loads(m.group(1))
    print("__initial_props__ top keys:", list(data.keys()))
    # dig into realEstates / listings
    def find_listings(obj, path="", depth=0):
        if depth > 5: return
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ("realEstates", "listings", "items", "properties", "results"):
                    print(f"  Found '{k}' at {path}: {type(v)}, len={len(v) if isinstance(v, list) else 'N/A'}")
                    if isinstance(v, list) and v:
                        print("  First element keys:", list(v[0].keys()) if isinstance(v[0], dict) else v[0])
                find_listings(v, f"{path}.{k}", depth+1)
        elif isinstance(obj, list):
            for i, item in enumerate(obj[:2]):
                find_listings(item, f"{path}[{i}]", depth+1)
    find_listings(data)
else:
    print("No __initial_props__ found")
    m2 = re.search(r'<script id="__initial_context__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if m2:
        data2 = json.loads(m2.group(1))
        print("__initial_context__ top keys:", list(data2.keys()))
