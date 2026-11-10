"""Problema de búsqueda de rutas: estado inicial, meta, sucesores y costos.

Implementa la tabla de transiciones de la ficha del proyecto:

    caminar      (n, r)    -> (m, CAMINANDO)   calle entre n y m
    abordar      (n, CAM.) -> (n, k)           n es parada de la ruta k
    continuar    (n, k)    -> (m, k)           m es la siguiente parada de k
    transbordar  (n, k)    -> (n, k')          n es parada de k y de k'

Optimización: no se genera "abordar" ni "transbordar" hacia una ruta cuya
parada actual es la última (no se podría continuar). Esos estados no pueden
mejorar ninguna ruta, así que podarlos no afecta la optimalidad.
"""
from __future__ import annotations

from core.grafo import Grafo
from core.tipos import (
    CAMINANDO, CLAVES_DESGLOSE, Accion, Estado, Pesos, TipoAccion,
)


class Problema:
    def __init__(self, grafo: Grafo, origen: str, destino: str, pesos: Pesos):
        for nombre, nodo in (("origen", origen), ("destino", destino)):
            if nodo not in grafo.nodos:
                raise ValueError(f"El {nombre} '{nodo}' no existe en el mapa")
        self.grafo = grafo
        self.origen = origen
        self.destino = destino
        self.pesos = pesos

    @property
    def estado_inicial(self) -> Estado:
        return Estado(self.origen, CAMINANDO)

    def es_meta(self, estado: Estado) -> bool:
        """Se llega a la meta en el nodo destino, caminando o en cualquier ruta."""
        return estado.nodo == self.destino

    def costo(self, accion: Accion) -> float:
        return accion.costo(self.pesos)

    def sucesores(self, estado: Estado) -> list[Accion]:
        """Todas las acciones válidas desde `estado`, con su estado destino."""
        g, nodo = self.grafo, estado.nodo
        acciones: list[Accion] = []

         
        for v in g.vecinos(nodo):
            acciones.append(Accion(
                TipoAccion.CAMINAR, estado, Estado(v.nodo, CAMINANDO),
                tiempo_min=Grafo.tiempo_caminata(v.distancia_m),
                penalizacion=v.penalizacion))

         
        tipo = TipoAccion.ABORDAR if estado.ruta == CAMINANDO else TipoAccion.TRANSBORDAR
        for ruta in g.rutas_en(nodo):
            if ruta.id == estado.ruta:
                continue
            if g.siguiente_parada(ruta.id, nodo) is None:
                continue                      
            acciones.append(Accion(
                tipo, estado, Estado(nodo, ruta.id),
                tiempo_min=ruta.espera_min, dinero=ruta.tarifa, abordaje=1))

    
        if estado.ruta != CAMINANDO:
            siguiente = g.siguiente_parada(estado.ruta, nodo)
            if siguiente is not None:
                parada, tiempo = siguiente
                acciones.append(Accion(
                    TipoAccion.CONTINUAR, estado, Estado(parada, estado.ruta),
                    tiempo_min=tiempo))

        return acciones


def desglose_de(acciones: list[Accion]) -> dict[str, float]:
    """Suma sin ponderar cada componente del costo (claves en CLAVES_DESGLOSE)."""
    totales = dict.fromkeys(CLAVES_DESGLOSE, 0.0)
    for a in acciones:
        totales["tiempo"] += a.tiempo_min
        totales["dinero"] += a.dinero
        totales["abordajes"] += a.abordaje
        totales["penalizacion"] += a.penalizacion
    return totales


def costo_de(acciones: list[Accion], pesos: Pesos) -> float:
    """Costo total ponderado de una secuencia de acciones."""
    return sum(a.costo(pesos) for a in acciones)