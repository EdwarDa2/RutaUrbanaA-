"""Heurística de A*: tiempo mínimo posible hasta el destino.

h(estado) = w1 · distancia_recta(nodo, destino) / v_max

Es admisible porque ningún tramo se recorre a más de v_max, y dinero,
abordajes y penalización son >= 0 (omitirlos solo subestima). Es consistente
por la desigualdad triangular. Solo depende del nodo, así que vale lo mismo
para (n, CAMINANDO) y (n, k).
"""
from __future__ import annotations

from typing import Callable

from core.grafo import Grafo
from core.tipos import Estado, Pesos

Heuristica = Callable[[Estado], float]


def calcular_v_max(grafo: Grafo) -> float:
    """Mayor velocidad (m/min) de cualquier modo del grafo: caminata o transporte."""
    v_max = grafo.velocidad_max_m_min
    if not v_max > 0:
        raise ValueError(f"v_max debe ser positiva: {v_max}")
    return v_max


def crear_heuristica(grafo: Grafo, destino: str, pesos: Pesos) -> Heuristica:
    """Devuelve h(estado) para un destino y unos pesos dados."""
    if destino not in grafo.nodos:
        raise ValueError(f"El destino '{destino}' no existe en el mapa")
    factor = pesos.tiempo / calcular_v_max(grafo)
    cache: dict[str, float] = {}

    def h(estado: Estado) -> float:
        nodo = estado.nodo
        valor = cache.get(nodo)
        if valor is None:
            valor = factor * grafo.distancia_recta(nodo, destino)
            cache[nodo] = valor
        return valor

    return h


def heuristica_cero(grafo: Grafo, destino: str, pesos: Pesos) -> Heuristica:
    """h = 0: con ella A* se comporta como Dijkstra (línea base)."""
    if destino not in grafo.nodos:
        raise ValueError(f"El destino '{destino}' no existe en el mapa")
    return lambda estado: 0.0