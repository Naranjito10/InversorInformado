"""Valida que todas las URLs de zones.json devuelvan 200 (no 404/redirect)."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).parent.parent
ZONES_FILE = ROOT / "config" / "zones.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

PORTALS_ORDER = ["idealista", "fotocasa", "pisos", "habitaclia"]

OK = "[OK]  "
FAIL = "[FAIL]"
SKIP = "[--]  "


def check_url(client: httpx.Client, url: str) -> tuple[int, str]:
    try:
        r = client.get(url, timeout=15)
        return r.status_code, str(r.url)
    except Exception as e:
        return 0, str(e)[:60]


def main() -> None:
    zones = json.loads(ZONES_FILE.read_text(encoding="utf-8"))["zones"]

    failures: list[dict] = []
    total = ok_count = skip_count = 0

    with httpx.Client(headers=HEADERS, follow_redirects=True) as client:
        for zone_key, zone in zones.items():
            label = zone["label"]
            print(f"\n{label}")
            for portal in PORTALS_ORDER:
                url = zone["portals"].get(portal)
                if url is None:
                    print(f"  {SKIP} {portal:<12} (no aplica)")
                    skip_count += 1
                    continue

                total += 1
                status, final_url = check_url(client, url)
                time.sleep(0.3)  # throttle suave

                # Un redirect que cambia el slug es un 404 disfrazado
                slug_changed = final_url.rstrip("/") != url.rstrip("/") and status == 200

                if status == 200 and not slug_changed:
                    print(f"  {OK} {portal:<12} {status}")
                    ok_count += 1
                else:
                    icon = FAIL
                    note = f"-> redirige a {final_url}" if slug_changed else f"HTTP {status}"
                    print(f"  {icon} {portal:<12} {note}")
                    failures.append({
                        "zone": zone_key,
                        "label": label,
                        "portal": portal,
                        "url": url,
                        "status": status,
                        "final_url": final_url,
                    })

    print(f"\n{'='*60}")
    print(f"Resultado: {ok_count}/{total} URLs OK  |  {skip_count} no aplican")

    if failures:
        print(f"\n{len(failures)} URLs con problemas:\n")
        for f in failures:
            print(f"  [{f['zone']}] {f['portal']}: {f['url']}")
            print(f"    → {f['final_url']} (HTTP {f['status']})")

        report_path = ROOT / "config" / "zones_validation_failures.json"
        report_path.write_text(
            json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\nFallos guardados en: {report_path}")
        sys.exit(1)
    else:
        print("Todas las URLs son válidas.")


if __name__ == "__main__":
    main()
