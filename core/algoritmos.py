"""Algoritmos de búsqueda. Las tres funciones comparten la MISMA firma.

Devuelven None si el destino es inalcanzable. Esqueleto de la Fase 0: la
implementación llega en la Fase 2.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from core.tipos import Pesos, ResultadoBusqueda

if TYPE_CHECKING:  
    from core.grafo import Grafo


def bfs(grafo: Grafo, origen: str, destino: str, pesos: Pesos) -> ResultadoBusqueda | None:
    """Búsqueda en anchura: minimiza el número de acciones e ignora los costos."""
    raise NotImplementedError("Fase 2")


def dijkstra(grafo: Grafo, origen: str, destino: str, pesos: Pesos) -> ResultadoBusqueda | None:
    """Costo uniforme: óptimo, sin heurística."""
    raise NotImplementedError("Fase 2")


def astar(grafo: Grafo, origen: str, destino: str, pesos: Pesos) -> ResultadoBusqueda | None:
    """A*: óptimo con heurística admisible."""
    raise NotImplementedError("Fase 2")