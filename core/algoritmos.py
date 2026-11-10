"""Algoritmos de búsqueda: BFS, Dijkstra y A*. Las tres funciones comparten la MISMA firma.

Devuelven None si el destino es inalcanzable. Estado = (nodo, ruta_actual).
La meta es cualquier estado cuyo nodo sea el destino.
Los sucesores y los costos vienen de `core.problema.Problema`.
"""
from __future__ import annotations

import heapq
import math
import time
from collections import deque
from itertools import count
from typing import TYPE_CHECKING, Callable

from core.heuristicas import crear_heuristica, heuristica_cero
from core.problema import Problema, costo_de, desglose_de
from core.tipos import Accion, Estado, Pesos, ResultadoBusqueda

if TYPE_CHECKING:
    from core.grafo import Grafo

Heuristica = Callable[[Estado], float]


def _resultado(nombre: str, final: Estado, padres: dict, pesos: Pesos,
               expandidos: int, generados: int, frontera_max: int,
               t0: float) -> ResultadoBusqueda:
    """Reconstruye la ruta desde `final` siguiendo los padres y arma el resultado."""
    acciones: list[Accion] = []
    estado = final
    while padres[estado][0] is not None:
        padre, accion = padres[estado]
        acciones.append(accion)
        estado = padre
    acciones.reverse()
    ruta = [estado] + [a.destino for a in acciones]       
    return ResultadoBusqueda(
        algoritmo=nombre,
        ruta=ruta,
        acciones=acciones,
        costo_total=costo_de(acciones, pesos),
        desglose=desglose_de(acciones),
        nodos_expandidos=expandidos,
        nodos_generados=generados,
        frontera_max=frontera_max,
        tiempo_ms=(time.perf_counter() - t0) * 1000.0,
    )


def _mejor_primero(nombre: str, p: Problema, h: Heuristica) -> ResultadoBusqueda | None:
    """Núcleo común de Dijkstra (h = 0) y A* (h admisible y consistente).

    La meta se prueba al SACAR el estado de la cola (no al generarlo), que es
    lo que garantiza la optimalidad. Con h consistente un estado cerrado nunca
    se reabre.
    """
    t0 = time.perf_counter()
    inicial = p.estado_inicial
    g = {inicial: 0.0}
    padres: dict[Estado, tuple[Estado | None, Accion | None]] = {inicial: (None, None)}
    desempate = count()
    frontera = [(h(inicial), next(desempate), inicial)]
    cerrados: set[Estado] = set()
    expandidos, generados, frontera_max = 0, 1, 1

    while frontera:
        _, _, e = heapq.heappop(frontera)
        if e in cerrados:                       
            continue
        if p.es_meta(e):
            return _resultado(nombre, e, padres, p.pesos, expandidos, generados,
                              frontera_max, t0)
        cerrados.add(e)
        expandidos += 1
        for accion in p.sucesores(e):
            s = accion.destino
            nuevo = g[e] + p.costo(accion)
            if nuevo < g.get(s, math.inf):
                g[s] = nuevo
                padres[s] = (e, accion)
                heapq.heappush(frontera, (nuevo + h(s), next(desempate), s))
                generados += 1
                frontera_max = max(frontera_max, len(frontera))
    return None


def bfs(grafo: Grafo, origen: str, destino: str, pesos: Pesos) -> ResultadoBusqueda | None:
    """Búsqueda en anchura: minimiza el número de acciones e ignora los costos.

    Los pesos solo se usan para reportar el costo de la ruta que encuentra.
    """
    p = Problema(grafo, origen, destino, pesos)
    t0 = time.perf_counter()
    inicial = p.estado_inicial
    padres: dict[Estado, tuple[Estado | None, Accion | None]] = {inicial: (None, None)}
    if p.es_meta(inicial):
        return _resultado("BFS", inicial, padres, pesos, 0, 1, 1, t0)

    cola = deque([inicial])
    visitados = {inicial}
    expandidos, generados, frontera_max = 0, 1, 1
    while cola:
        e = cola.popleft()
        expandidos += 1
        for accion in p.sucesores(e):
            s = accion.destino
            if s in visitados:
                continue
            visitados.add(s)
            padres[s] = (e, accion)
            generados += 1
            if p.es_meta(s):
                return _resultado("BFS", s, padres, pesos, expandidos, generados,
                                  frontera_max, t0)
            cola.append(s)
            frontera_max = max(frontera_max, len(cola))
    return None


def dijkstra(grafo: Grafo, origen: str, destino: str, pesos: Pesos) -> ResultadoBusqueda | None:
    """Costo uniforme: óptimo, sin heurística."""
    p = Problema(grafo, origen, destino, pesos)
    return _mejor_primero("Dijkstra", p, heuristica_cero(grafo, destino, pesos))


def astar(grafo: Grafo, origen: str, destino: str, pesos: Pesos) -> ResultadoBusqueda | None:
    """A*: óptimo con heurística admisible y consistente."""
    p = Problema(grafo, origen, destino, pesos)
    return _mejor_primero("A*", p, crear_heuristica(grafo, destino, pesos))