"""Registro de enriquecedores. Cada enriquecedor se registra con register()."""
from __future__ import annotations
from .base import BaseEnricher

_registry: list[BaseEnricher] = []


def register(enricher: BaseEnricher) -> None:
    _registry.append(enricher)


def get_all() -> list[BaseEnricher]:
    return list(_registry)


# Auto-registro — orden importa: Catastro primero (geocodifica), Photos después
from .catastro import CatastroEnricher  # noqa: E402
from .photo import PhotoEnricher        # noqa: E402
register(CatastroEnricher())
register(PhotoEnricher())
