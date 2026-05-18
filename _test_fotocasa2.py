import json, re
from scraper.http_client import fetch_html

url = "https://www.fotocasa.es/es/comprar/viviendas/barcelona-capital/eixample/l"
html = fetch_html(url, use_js=True)

# Check __NEXT_DATA__
m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
if m:
    data = json.loads(m.group(1))
    # Navigate into the data to find listings
    props = data.get("props", {}).get("pageProps", {})
    print("pageProps keys:", list(props.keys())[:10])
    # Try to find results
    for key in ["initialSearch", "search", "listingSearch", "items"]:
        if key in props:
            print(f"Found key '{key}':", type(props[key]))
else:
    print("No __NEXT_DATA__ found")
    # Check what scripts are present
    scripts = re.findall(r'<script[^>]*id="([^"]+)"', html)
    print("Script ids:", scripts)
    # Check first 500 chars
    print("HTML start:", html[:500])
