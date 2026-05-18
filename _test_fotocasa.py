from scraper.http_client import fetch_html
from scraper.scrapers.fotocasa import FotocasaScraper
s = FotocasaScraper()
url = "https://www.fotocasa.es/es/comprar/viviendas/barcelona-capital/eixample/l"
html = fetch_html(url, use_js=True)
items = list(s.parse_search_page(html, url))
print("Items found:", len(items))
if items:
    k = items[0]
    print("url:", k.get("url", ""))
    print("precio:", k.get("precio_venta", ""))
    print("metros:", k.get("metros_cuadrados", ""))
