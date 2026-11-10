"""Módulo de exportación de resultados y generación de gráficas estadísticas.

Responsabilidad del Dev B: guarda CSV, JSON y genera visualizaciones con matplotlib.
"""

from __future__ import annotations

import csv
import json
import os
from dataclasses import asdict, is_dataclass
from typing import Any

import matplotlib
matplotlib.use("Agg")  # Backend no interactivo para entornos de consola y servidores
import matplotlib.pyplot as plt

COLUMNAS_CSV = [
    "caso",
    "origen",
    "destino",
    "algoritmo",
    "pesos",
    "costo_total",
    "longitud",
    "nodos_expandidos",
    "nodos_generados",
    "frontera_max",
    "tiempo_ms",
]


def guardar_resultado_csv(resultados: list[dict[str, Any]], ruta_archivo: str) -> None:
    """Guarda una lista de resultados de búsqueda en un archivo CSV con las 11 columnas requeridas."""
    os.makedirs(os.path.dirname(os.path.abspath(ruta_archivo)), exist_ok=True)
    with open(ruta_archivo, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNAS_CSV, extrasaction="ignore")
        writer.writeheader()
        for fila in resultados:
            writer.writerow(fila)


def _convertir_a_dict(obj: Any) -> Any:
    """Serializa recursivamente objetos dataclass, namedtuples o dicts a estructuras nativas de Python."""
    if is_dataclass(obj):
        return asdict(obj)
    if hasattr(obj, "_asdict"):  # NamedTuple
        return obj._asdict()
    if isinstance(obj, (list, tuple)):
        return [_convertir_a_dict(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _convertir_a_dict(v) for k, v in obj.items()}
    return obj


def guardar_resultado_json(resultado: Any, ruta_archivo: str) -> None:
    """Guarda los detalles de un ResultadoBusqueda o diccionario en un archivo JSON formateado."""
    os.makedirs(os.path.dirname(os.path.abspath(ruta_archivo)), exist_ok=True)
    datos = _convertir_a_dict(resultado)
    with open(ruta_archivo, mode="w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)


def grafica_comparativa(datos: list[dict[str, Any]], ruta_png: str) -> None:
    """Genera una gráfica de barras comparando nodos expandidos por algoritmo y caso."""
    os.makedirs(os.path.dirname(os.path.abspath(ruta_png)), exist_ok=True)

    casos_unicos = sorted(list({str(d["caso"]) for d in datos}))
    algoritmos = ["A*", "Dijkstra", "BFS"]
    colores = {"A*": "#2e7d32", "Dijkstra": "#1565c0", "BFS": "#e65100"}

    # Organizar datos: {algoritmo: [expandidos por caso]}
    mapa_datos: dict[str, list[float]] = {algo: [] for algo in algoritmos}
    for c in casos_unicos:
        for algo in algoritmos:
            fila = next((d for d in datos if str(d["caso"]) == c and d["algoritmo"] == algo), None)
            valor = float(fila["nodos_expandidos"]) if fila else 0.0
            mapa_datos[algo].append(valor)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    x = list(range(len(casos_unicos)))
    ancho = 0.25

    for i, algo in enumerate(algoritmos):
        offset = (i - 1) * ancho
        posiciones = [pos + offset for pos in x]
        valores = mapa_datos[algo]
        color = colores.get(algo, "#757575")
        ax.bar(posiciones, valores, ancho, label=algo, color=color, alpha=0.9, edgecolor="black")

    ax.set_xlabel("Caso de Prueba", fontsize=11, fontweight="bold")
    ax.set_ylabel("Nodos Expandidos", fontsize=11, fontweight="bold")
    ax.set_title("Comparación de Eficiencia en Búsqueda (A* vs Dijkstra vs BFS)", fontsize=13, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(casos_unicos, rotation=15, ha="right")
    ax.legend(title="Algoritmo")
    ax.grid(axis="y", linestyle="--", alpha=0.6)

    fig.tight_layout()
    fig.savefig(ruta_png, dpi=300)
    plt.close(fig)


def grafica_escalabilidad(datos: list[dict[str, Any]], ruta_png: str) -> None:
    """Genera una gráfica de líneas mostrando nodos expandidos y tiempo (ms) vs tamaño del grafo."""
    os.makedirs(os.path.dirname(os.path.abspath(ruta_png)), exist_ok=True)

    tamanos = [int(d["tamano"]) for d in datos]
    expandidos = [float(d["nodos_expandidos"]) for d in datos]
    tiempos = [float(d["tiempo_ms"]) for d in datos]

    fig, ax1 = plt.subplots(figsize=(9, 5))

    color_expandidos = "#1565c0"
    ax1.set_xlabel("Tamaño del Grafo (Número de Nodos)", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Nodos Expandidos", color=color_expandidos, fontsize=11, fontweight="bold")
    line1 = ax1.plot(tamanos, expandidos, color=color_expandidos, marker="o", linewidth=2, label="Nodos Expandidos")
    ax1.tick_params(axis="y", labelcolor=color_expandidos)
    ax1.grid(True, linestyle="--", alpha=0.5)

    ax2 = ax1.twinx()
    color_tiempo = "#c62828"
    ax2.set_ylabel("Tiempo de Cómputo (ms)", color=color_tiempo, fontsize=11, fontweight="bold")
    line2 = ax2.plot(tamanos, tiempos, color=color_tiempo, marker="s", linestyle="--", linewidth=2, label="Tiempo (ms)")
    ax2.tick_params(axis="y", labelcolor=color_tiempo)

    # Combinar leyendas
    lineas = line1 + line2
    etiquetas = [l.get_label() for l in lineas]
    ax1.legend(lineas, etiquetas, loc="upper left")

    plt.title("Escalabilidad del Algoritmo A* ante Redes Crecientes", fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(ruta_png, dpi=300)
    plt.close(fig)
