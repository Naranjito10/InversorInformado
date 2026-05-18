from scraper.db import get_client
c = get_client()

# Check table columns first
r = c.table("listings").select("*").limit(1).execute()
if r.data:
    print("Columns:", list(r.data[0].keys()))
else:
    print("Table empty, checking schema via count...")

# Count total rows
r2 = c.table("listings").select("*", count="exact").limit(1).execute()
print(f"Total rows: {r2.count}")
