from collections import Counter
from scraper.db import get_client

client = get_client()
r = client.table("listings").select("fuente, barrio, municipio, precio_venta, metros_cuadrados, score, score_label", count="exact").execute()
rows = r.data

print(f"Total en Supabase: {r.count} anuncios\n")

by_source = Counter(row["fuente"] for row in rows)
print("Por fuente:")
for src, cnt in sorted(by_source.items(), key=lambda x: -x[1]):
    print(f"  {src}: {cnt}")

by_barrio = Counter(row["barrio"] for row in rows if row["barrio"])
print("\nTop barrios:")
for barrio, cnt in by_barrio.most_common(8):
    print(f"  {barrio}: {cnt}")

by_label = Counter(row["score_label"] for row in rows)
print("\nScore labels:")
for label, cnt in sorted(by_label.items(), key=lambda x: -x[1]):
    print(f"  {label}: {cnt}")

precios = [row["precio_venta"] for row in rows if row["precio_venta"]]
if precios:
    print(f"\nPrecios: min={min(precios):,} € | max={max(precios):,} € | media={int(sum(precios)/len(precios)):,} €")
