"""Clase base para todos los enriquecedores."""
from __future__ import annotations
from abc import ABC, abstractmethod


class BaseEnricher(ABC):
    name: str  # identificador único, e.g. "catastro"

    def needs_enrichment(self, listing_row: dict) -> bool:
        """
        Devuelve False para saltarse este listing (ya enriquecido,
        campos requeridos ausentes, etc.). Override en cada enriquecedor.
        """
        return True

    @abstractmethod
    def enrich(self, listing_row: dict) -> dict:
        """
        Recibe la fila completa del listing desde BD.
        Devuelve {campo: valor} con los campos a persistir.
        Devuelve {} si no hay nada que escribir.
        """
        ...
