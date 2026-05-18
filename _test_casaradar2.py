import httpx, re

r = httpx.get("https://www.casaradar.es/", follow_redirects=True, timeout=10,
              headers={"User-Agent": "Mozilla/5.0"})
print("Status:", r.status_code)
print("HTML snippet (first 2000):")
print(r.text[:2000])
