import httpx, re

r = httpx.get("https://www.casaradar.es/", follow_redirects=True, timeout=10,
              headers={"User-Agent": "Mozilla/5.0"})
# Find href patterns with comprar/venta/piso
urls = re.findall(r'href="(/[^"]+)"', r.text)
relevant = [u for u in urls if any(k in u for k in ("comprar", "venta", "piso", "buscar", "search"))]
print("Relevant URLs:", relevant[:15])

# Also check city search patterns
city_urls = re.findall(r'href="(/[^"]+barcelona[^"]*)"', r.text, re.IGNORECASE)
print("Barcelona URLs:", city_urls[:10])
