"""Contrato entre el núcleo (Dev A) y la interfaz/análisis (Dev B).

Aquí viven los tipos que ambos comparten. Cambiarlos requiere avisar al otro.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple

CAMINANDO = "CAMINANDO"  


class Estado(NamedTuple):
    """Un estado de búsqueda: dónde estoy y en qué ruta de transporte voy."""

    nodo: str
    ruta: str = CAMINANDO


@dataclass(frozen=True)
class Pesos:
    """Importancia que el usuario da a cada criterio. Todos deben ser >= 0.

    costo = tiempo·minutos + dinero·pesos + abordaje·abordajes + accesibilidad·penalización
    """

    tiempo: float = 1.0
    dinero: float = 0.0
    abordaje: float = 0.0
    accesibilidad: float = 0.0

    def __post_init__(self) -> None:
        valores = (self.tiempo, self.dinero, self.abordaje, self.accesibilidad)
        if any(not math.isfinite(v) or v < 0 for v in valores):
            raise ValueError(f"Los pesos deben ser números finitos >= 0: {valores}")
        if all(v == 0 for v in valores):
            raise ValueError("Al menos un peso debe ser mayor que 0")


class TipoAccion(str, Enum):
    CAMINAR = "caminar"
    ABORDAR = "abordar"
    CONTINUAR = "continuar"
    TRANSBORDAR = "transbordar"


@dataclass(frozen=True)
class Accion:
    """Una transición `origen |-- tipo --> destino` con sus componentes de costo.

    Se guardan los componentes sin ponderar (tiempo, dinero, abordaje,
    penalización); el costo final depende de los Pesos del usuario.
    """

    tipo: TipoAccion
    origen: Estado
    destino: Estado
    tiempo_min: float = 0.0
    dinero: float = 0.0
    abordaje: float = 0.0
    penalizacion: float = 0.0

    def __post_init__(self) -> None:
        componentes = (self.tiempo_min, self.dinero, self.abordaje, self.penalizacion)
        if any(not math.isfinite(c) or c < 0 for c in componentes):
            raise ValueError(f"Los componentes de costo deben ser >= 0: {componentes}")
        self._validar_forma()

    def _validar_forma(self) -> None:
        o, d = self.origen, self.destino
        if self.tipo is TipoAccion.CAMINAR:
            ok = d.ruta == CAMINANDO and o.nodo != d.nodo
        elif self.tipo is TipoAccion.ABORDAR:
            ok = o.ruta == CAMINANDO and d.ruta != CAMINANDO and o.nodo == d.nodo
        elif self.tipo is TipoAccion.CONTINUAR:
            ok = o.ruta != CAMINANDO and o.ruta == d.ruta and o.nodo != d.nodo
        else:  # TRANSBORDAR
            ok = (o.ruta != CAMINANDO and d.ruta != CAMINANDO
                  and o.ruta != d.ruta and o.nodo == d.nodo)
        if not ok:
            raise ValueError(f"Acción {self.tipo.value} inconsistente: {o} -> {d}")

    def costo(self, pesos: Pesos) -> float:
        """Costo ponderado de esta acción."""
        return (pesos.tiempo * self.tiempo_min
                + pesos.dinero * self.dinero
                + pesos.abordaje * self.abordaje
                + pesos.accesibilidad * self.penalizacion)

    def __str__(self) -> str:
        if self.tipo is TipoAccion.CAMINAR:
            return f"caminar: {self.origen.nodo} -> {self.destino.nodo}"
        if self.tipo is TipoAccion.ABORDAR:
            return f"abordar {self.destino.ruta} en {self.origen.nodo}"
        if self.tipo is TipoAccion.CONTINUAR:
            return f"continuar en {self.origen.ruta}: {self.origen.nodo} -> {self.destino.nodo}"
        return (f"transbordar de {self.origen.ruta} a {self.destino.ruta} "
                f"en {self.origen.nodo}")



CLAVES_DESGLOSE = ("tiempo", "dinero", "abordajes", "penalizacion")


@dataclass(frozen=True)
class ResultadoBusqueda:
    """Lo que devuelve cualquier algoritmo de búsqueda al encontrar una ruta."""

    algoritmo: str                    
    ruta: list[Estado]                
    acciones: list[Accion]            
    costo_total: float                
    desglose: dict[str, float]        
    nodos_expandidos: int
    nodos_generados: int
    frontera_max: int
    tiempo_ms: float

    @property
    def origen(self) -> str:
        return self.ruta[0].nodo

    @property
    def destino(self) -> str:
        return self.ruta[-1].nodo

    @property
    def longitud(self) -> int:
        """Número de acciones de la ruta (la profundidad d)."""
        return len(self.acciones)

    @property
    def abordajes(self) -> int:
        return sum(1 for a in self.acciones
                   if a.tipo in (TipoAccion.ABORDAR, TipoAccion.TRANSBORDAR))

    @property
    def transbordos(self) -> int:
        return max(0, self.abordajes - 1)