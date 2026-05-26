from __future__ import annotations
from scraper.infrastructure.db import get_client


def get_fuentes(solo_activos: bool = False) -> list[dict]:
    client = get_client()
    if client is None:
        return []
    q = client.table("fuentes").select("*").order("nombre")
    if solo_activos:
        q = q.eq("activo", True)
    return q.execute().data or []


def create_fuente(id: str, nombre: str, test_url: str | None = None) -> dict:
    client = get_client()
    payload: dict = {"id": id, "nombre": nombre}
    if test_url:
        payload["test_url"] = test_url
    resp = client.table("fuentes").insert(payload).execute()
    return resp.data[0] if resp.data else {}


def toggle_fuente(id: str, activo: bool) -> dict:
    client = get_client()
    resp = client.table("fuentes").update({"activo": activo}).eq("id", id).execute()
    return resp.data[0] if resp.data else {}


def update_fuente(id: str, nombre: str, test_url: str | None) -> dict:
    client = get_client()
    payload: dict = {"nombre": nombre}
    payload["test_url"] = test_url  # permite borrarla enviando None
    resp = client.table("fuentes").update(payload).eq("id", id).execute()
    return resp.data[0] if resp.data else {}


def delete_fuente(id: str) -> bool:
    client = get_client()
    client.table("fuentes").delete().eq("id", id).execute()
    return True
