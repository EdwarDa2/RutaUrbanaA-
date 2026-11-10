"""Generador de ciudades sintéticas (cuadrículas) para los experimentos de escalabilidad.

Todo sale de una semilla, así que la misma semilla da la misma ciudad.
Las distancias de calle son >= la línea recta (el Grafo lo exige), por lo que
la heurística de A* sigue siendo admisible.
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

from core.grafo import Grafo
from datos.cargador import grafo_desde_dict

TARIFAS = (8.0, 10.0, 12.0)
ESPERAS_MIN = (2.0, 3.0, 4.0, 5.0, 6.0)
VELOCIDAD_TRANSPORTE_M_MIN = 350.0
PENALIZACION_ESCALERA = 6.0
PENALIZACION_DIFICIL = 3.0


def _id(i: int, j: int) -> str:
    return f"n{i}_{j}"


def ciudad_como_dict(
    n_nodos: int,
    semilla: int = 0,
    espaciado_m: float = 100.0,
    n_rutas: int | None = None,
    salto_paradas: int = 3,
    prob_escalera: float = 0.05,
    prob_dificil: float = 0.05,
) -> dict:
    """Construye el mapa como diccionario (mismo formato que los JSON del proyecto)."""
    if salto_paradas < 1:
        raise ValueError("salto_paradas debe ser >= 1")
    if espaciado_m <= 0:
        raise ValueError("espaciado_m debe ser > 0")
    if not (0 <= prob_escalera and 0 <= prob_dificil and prob_escalera + prob_dificil <= 1):
        raise ValueError("Las probabilidades deben estar en [0, 1] y sumar <= 1")
    lado = round(math.sqrt(n_nodos))
    if lado < salto_paradas + 1:
        raise ValueError(
            f"n_nodos={n_nodos} es muy pequeño: se necesita una cuadrícula de al menos "
            f"{salto_paradas + 1}x{salto_paradas + 1} para tener rutas de 2 paradas")

    rng = random.Random(semilla)

    nodos = [{"id": _id(i, j), "x": j * espaciado_m, "y": i * espaciado_m}
             for i in range(lado) for j in range(lado)]

    def tramo(a: str, b: str) -> dict:
        distancia = math.ceil(espaciado_m * rng.uniform(1.0, 1.4))
        r = rng.random()
        if r < prob_escalera:
            pen, tipo = PENALIZACION_ESCALERA, "escalera"
        elif r < prob_escalera + prob_dificil:
            pen, tipo = PENALIZACION_DIFICIL, "dificil"
        else:
            pen, tipo = 0.0, "calle"
        return {"de": a, "a": b, "distancia_m": distancia, "penalizacion": pen, "tipo": tipo}

    tramos = []
    for i in range(lado):
        for j in range(lado):
            if j + 1 < lado:
                tramos.append(tramo(_id(i, j), _id(i, j + 1)))
            if i + 1 < lado:
                tramos.append(tramo(_id(i, j), _id(i + 1, j)))

     
    posiciones = list(range(0, lado, salto_paradas))
    disponibles = 2 * len(posiciones)
    if n_rutas is None:
        n_rutas = max(2, lado // 5)
    n_rutas = max(2, min(n_rutas, disponibles))
    filas, columnas = posiciones[:], posiciones[:]
    rng.shuffle(filas)
    rng.shuffle(columnas)

    tiempo_tramo = max(1.0, round(espaciado_m * salto_paradas / VELOCIDAD_TRANSPORTE_M_MIN * 2) / 2)
    rutas = []
    for k in range(n_rutas):
        horizontal = (k % 2 == 0 and filas) or not columnas
        linea = filas.pop() if horizontal else columnas.pop()
        if horizontal:
            paradas = [_id(linea, c) for c in posiciones]
        else:
            paradas = [_id(f, linea) for f in posiciones]
        if rng.random() < 0.5:
            paradas.reverse()
        rutas.append({
            "id": f"R{k + 1}",
            "tarifa": rng.choice(TARIFAS),
            "espera_min": rng.choice(ESPERAS_MIN),
            "paradas": paradas,
            "tiempos_min": [tiempo_tramo] * (len(paradas) - 1),
        })

    return {"nodos": nodos, "tramos": tramos, "rutas": rutas}


def generar_ciudad(n_nodos: int, semilla: int = 0, **opciones) -> Grafo:
    """Genera una ciudad sintética de ~n_nodos nodos y devuelve el Grafo ya validado."""
    return grafo_desde_dict(ciudad_como_dict(n_nodos, semilla, **opciones))


def guardar_ciudad(n_nodos: int, ruta_json: str | Path, semilla: int = 0, **opciones) -> None:
    """Guarda la ciudad como JSON (útil para inspeccionarla o reutilizarla)."""
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(ciudad_como_dict(n_nodos, semilla, **opciones), f, ensure_ascii=False)


def pares_aleatorios(grafo: Grafo, cantidad: int, semilla: int = 0) -> list[tuple[str, str]]:
    """Pares (origen, destino) distintos y reproducibles, para los experimentos."""
    ids = list(grafo.nodos)
    if len(ids) < 2:
        raise ValueError("Se necesitan al menos 2 nodos")
    rng = random.Random(semilla)
    pares = []
    while len(pares) < cantidad:
        o, d = rng.sample(ids, 2)
        pares.append((o, d))
    return pares