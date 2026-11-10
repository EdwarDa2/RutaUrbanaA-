"""Carga un mapa desde un archivo JSON y construye el Grafo."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.grafo import ErrorMapa, Grafo, Nodo, RutaTransporte, Tramo


def _exigir(dic: Any, campo: str, donde: str) -> Any:
    if not isinstance(dic, dict):
        raise ErrorMapa(f"{donde} debe ser un objeto JSON")
    if campo not in dic:
        raise ErrorMapa(f"Falta el campo '{campo}' en {donde}")
    return dic[campo]


def _numero(valor: Any, campo: str, donde: str) -> float:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ErrorMapa(f"El campo '{campo}' de {donde} debe ser un número, no {valor!r}")
    return float(valor)


def _lista(valor: Any, campo: str, donde: str) -> list:
    if not isinstance(valor, list):
        raise ErrorMapa(f"El campo '{campo}' de {donde} debe ser una lista")
    return valor


def grafo_desde_dict(datos: dict) -> Grafo:
    """Construye un Grafo a partir de un diccionario con 'nodos', 'tramos' y 'rutas'."""
    nodos, tramos, rutas = [], [], []

    for i, n in enumerate(_lista(_exigir(datos, "nodos", "el mapa"), "nodos", "el mapa")):
        d = f"nodos[{i}]"
        nodos.append(Nodo(str(_exigir(n, "id", d)),
                          _numero(_exigir(n, "x", d), "x", d),
                          _numero(_exigir(n, "y", d), "y", d)))

    for i, t in enumerate(_lista(_exigir(datos, "tramos", "el mapa"), "tramos", "el mapa")):
        d = f"tramos[{i}]"
        tramos.append(Tramo(
            de=str(_exigir(t, "de", d)),
            a=str(_exigir(t, "a", d)),
            distancia_m=_numero(_exigir(t, "distancia_m", d), "distancia_m", d),
            penalizacion=_numero(t.get("penalizacion", 0), "penalizacion", d),
            tipo=str(t.get("tipo", "calle")),
            bidireccional=bool(t.get("bidireccional", True)),
        ))

    for i, r in enumerate(_lista(datos.get("rutas", []), "rutas", "el mapa")):
        d = f"rutas[{i}]"
        paradas = _lista(_exigir(r, "paradas", d), "paradas", d)
        tiempos = _lista(_exigir(r, "tiempos_min", d), "tiempos_min", d)
        rutas.append(RutaTransporte(
            id=str(_exigir(r, "id", d)),
            tarifa=_numero(_exigir(r, "tarifa", d), "tarifa", d),
            espera_min=_numero(_exigir(r, "espera_min", d), "espera_min", d),
            paradas=tuple(str(p) for p in paradas),
            tiempos_min=tuple(_numero(t, "tiempos_min", d) for t in tiempos),
        ))

    return Grafo(nodos, tramos, rutas)


def cargar_mapa(ruta_json: str | Path) -> Grafo:
    """Lee un archivo JSON y devuelve el Grafo validado."""
    with open(ruta_json, encoding="utf-8") as f:
        try:
            datos = json.load(f)
        except json.JSONDecodeError as e:
            raise ErrorMapa(f"El archivo {ruta_json} no es un JSON válido: {e}") from e
    return grafo_desde_dict(datos)