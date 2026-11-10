"""Representación del mapa: nodos, tramos de calle y rutas de transporte.

El Grafo valida todo al construirse, de modo que cualquier dato incorrecto
falla aquí con un mensaje claro y nunca llega a los algoritmos.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import NamedTuple

from core.tipos import CAMINANDO

VELOCIDAD_CAMINATA_M_MIN = 80.0       
LIMITE_VELOCIDAD_TRANSPORTE_M_MIN = 1000.0   
TOLERANCIA = 1e-9


class ErrorMapa(ValueError):
    """El mapa tiene datos inválidos o inconsistentes."""


@dataclass(frozen=True)
class Nodo:
    id: str
    x: float          
    y: float          


@dataclass(frozen=True)
class Tramo:
    """Tramo de calle entre dos nodos."""

    de: str
    a: str
    distancia_m: float
    penalizacion: float = 0.0     
    tipo: str = "calle"           
    bidireccional: bool = True


@dataclass(frozen=True)
class RutaTransporte:
    """Ruta de transporte de UN solo sentido, en el orden en que se listan las paradas.

    Para el regreso se define otra ruta. `tiempos_min[i]` es el tiempo entre
    `paradas[i]` y `paradas[i + 1]`.
    """

    id: str
    tarifa: float
    espera_min: float
    paradas: tuple[str, ...]
    tiempos_min: tuple[float, ...]


class Vecino(NamedTuple):
    """Un nodo alcanzable caminando desde otro."""

    nodo: str
    distancia_m: float
    penalizacion: float
    tipo: str


class Grafo:
    def __init__(self, nodos: list[Nodo], tramos: list[Tramo], rutas: list[RutaTransporte]):
        self.nodos: dict[str, Nodo] = {}
        for n in nodos:
            if n.id in self.nodos:
                raise ErrorMapa(f"Nodo duplicado: '{n.id}'")
            if not (math.isfinite(n.x) and math.isfinite(n.y)):
                raise ErrorMapa(f"Coordenadas inválidas en el nodo '{n.id}'")
            self.nodos[n.id] = n

        self.tramos: tuple[Tramo, ...] = tuple(tramos)
        self._ady: dict[str, list[Vecino]] = {nid: [] for nid in self.nodos}
        for t in self.tramos:
            self._validar_tramo(t)
            self._ady[t.de].append(Vecino(t.a, t.distancia_m, t.penalizacion, t.tipo))
            if t.bidireccional:
                self._ady[t.a].append(Vecino(t.de, t.distancia_m, t.penalizacion, t.tipo))

        self.rutas: dict[str, RutaTransporte] = {}
        self._rutas_en: dict[str, list[str]] = {nid: [] for nid in self.nodos}
        self._siguiente: dict[tuple[str, str], tuple[str, float]] = {}
        self.velocidad_max_m_min = VELOCIDAD_CAMINATA_M_MIN
        for r in rutas:
            self._registrar_ruta(r)

    
    def _validar_tramo(self, t: Tramo) -> None:
        for extremo in (t.de, t.a):
            if extremo not in self.nodos:
                raise ErrorMapa(f"El tramo {t.de}->{t.a} menciona el nodo inexistente '{extremo}'")
        if t.de == t.a:
            raise ErrorMapa(f"El tramo {t.de}->{t.a} une un nodo consigo mismo")
        if not math.isfinite(t.distancia_m) or t.distancia_m <= 0:
            raise ErrorMapa(f"El tramo {t.de}->{t.a} tiene una distancia inválida: {t.distancia_m}")
        if not math.isfinite(t.penalizacion) or t.penalizacion < 0:
            raise ErrorMapa(f"El tramo {t.de}->{t.a} tiene una penalización negativa: {t.penalizacion}")
        recta = self.distancia_recta(t.de, t.a)
        if t.distancia_m < recta - TOLERANCIA:
            raise ErrorMapa(
                f"El tramo {t.de}->{t.a} mide {t.distancia_m} m pero la distancia en línea recta "
                f"es {recta:.1f} m. Un tramo no puede ser más corto que la línea recta: "
                f"rompería la admisibilidad de la heurística de A*.")

    def _registrar_ruta(self, r: RutaTransporte) -> None:
        if r.id == CAMINANDO:
            raise ErrorMapa(f"'{CAMINANDO}' es un nombre reservado y no puede ser una ruta")
        if r.id in self.rutas:
            raise ErrorMapa(f"Ruta duplicada: '{r.id}'")
        if len(r.paradas) < 2:
            raise ErrorMapa(f"La ruta '{r.id}' necesita al menos 2 paradas")
        if len(set(r.paradas)) != len(r.paradas):
            raise ErrorMapa(f"La ruta '{r.id}' repite paradas; cada parada debe aparecer una sola vez")
        for p in r.paradas:
            if p not in self.nodos:
                raise ErrorMapa(f"La ruta '{r.id}' menciona la parada inexistente '{p}'")
        if len(r.tiempos_min) != len(r.paradas) - 1:
            raise ErrorMapa(
                f"La ruta '{r.id}' tiene {len(r.paradas)} paradas pero {len(r.tiempos_min)} tiempos; "
                f"debe haber exactamente {len(r.paradas) - 1}")
        if not math.isfinite(r.tarifa) or r.tarifa < 0:
            raise ErrorMapa(f"La ruta '{r.id}' tiene una tarifa inválida: {r.tarifa}")
        if not math.isfinite(r.espera_min) or r.espera_min < 0:
            raise ErrorMapa(f"La ruta '{r.id}' tiene una espera inválida: {r.espera_min}")

        for i, tiempo in enumerate(r.tiempos_min):
            a, b = r.paradas[i], r.paradas[i + 1]
            if not math.isfinite(tiempo) or tiempo <= 0:
                raise ErrorMapa(f"La ruta '{r.id}' tiene un tiempo no positivo entre {a} y {b}: {tiempo}")
            velocidad = self.distancia_recta(a, b) / tiempo
            if velocidad > LIMITE_VELOCIDAD_TRANSPORTE_M_MIN:
                raise ErrorMapa(
                    f"La ruta '{r.id}' recorre {a}->{b} a {velocidad:.0f} m/min "
                    f"(más de {LIMITE_VELOCIDAD_TRANSPORTE_M_MIN:.0f}): el tiempo es poco realista.")
            self.velocidad_max_m_min = max(self.velocidad_max_m_min, velocidad)
            self._siguiente[(r.id, a)] = (b, tiempo)

        self.rutas[r.id] = r
        for p in r.paradas:
            self._rutas_en[p].append(r.id)

    
    def distancia_recta(self, a: str, b: str) -> float:
        na, nb = self.nodos[a], self.nodos[b]
        return math.hypot(na.x - nb.x, na.y - nb.y)

    @staticmethod
    def tiempo_caminata(distancia_m: float) -> float:
        return distancia_m / VELOCIDAD_CAMINATA_M_MIN

    def vecinos(self, nodo: str) -> list[Vecino]:
        """Nodos alcanzables caminando desde `nodo`."""
        return self._ady[nodo]

    def rutas_en(self, nodo: str) -> list[RutaTransporte]:
        """Rutas de transporte que tienen parada en `nodo`."""
        return [self.rutas[rid] for rid in self._rutas_en[nodo]]

    def siguiente_parada(self, ruta_id: str, nodo: str) -> tuple[str, float] | None:
        """(siguiente parada, tiempo en minutos) o None si `nodo` es la última parada."""
        return self._siguiente.get((ruta_id, nodo))

    @property
    def num_nodos(self) -> int:
        return len(self.nodos)

    @property
    def num_estados(self) -> int:
        """|S| = N + suma de las paradas de cada ruta (ver ficha del proyecto)."""
        return self.num_nodos + sum(len(r.paradas) for r in self.rutas.values())