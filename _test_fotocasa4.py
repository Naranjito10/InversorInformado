import json, re
from scraper.http_client import fetch_html

url = "https://www.fotocasa.es/es/comprar/viviendas/barcelona-capital/eixample/l"
html = fetch_html(url, use_js=True)

# Save to file for inspection
with open("_fotocasa_live.html", "w", encoding="utf-8") as f:
    f.write(html)
print("Saved HTML, total chars:", len(html))

# Permissive regex - id can be after other attributes
for script_id in ["__initial_props__", "__initial_context__", "__NEXT_DATA__"]:
    pattern = rf'<script[^>]*id="{re.escape(script_id)}"[^>]*>(.*?)</script>'
    m = re.search(pattern, html, re.DOTALL)
    if m:
        content = m.group(1).strip()
        print(f"{script_id} found, length:", len(content))
        try:
            data = json.loads(content)
            print(f"  Top keys: {list(data.keys())[:8]}")
        except Exception as e:
            print(f"  JSON parse error: {e}, first 200: {content[:200]}")
    else:
        print(f"{script_id}: NOT FOUND")
