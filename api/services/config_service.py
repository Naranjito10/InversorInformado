from __future__ import annotations
from datetime import datetime, timezone
from scraper.infrastructure.db import get_client


def get_all_config() -> list[dict]:
    client = get_client()
    if client is None:
        return []
    return client.table("config").select("*").order("key").execute().data or []


def get_config(key: str) -> str | None:
    client = get_client()
    if client is None:
        return None
    res = client.table("config").select("value").eq("key", key).limit(1).execute()
    return res.data[0]["value"] if res.data else None


def set_config(key: str, value: str) -> dict:
    client = get_client()
    resp = (
        client.table("config")
        .update({"value": value, "updated_at": datetime.now(timezone.utc).isoformat()})
        .eq("key", key)
        .execute()
    )
    return resp.data[0] if resp.data else {}
