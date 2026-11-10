"""Pruebas unitarias para el módulo de exportación de analíticas (exportador.py)."""

import csv
import json
import os
from dataclasses import asdict, dataclass
from typing import NamedTuple
import pytest

from analytics.exportador import (
    COLUMNAS_CSV,
    guardar_resultado_csv,
    guardar_resultado_json,
    grafica_comparativa,
    grafica_escalabilidad,
)


class EstadoMock(NamedTuple):
    nodo: str
    ruta: str


@dataclass(frozen=True)
class AccionMock:
    tipo: str
    origen: str
    destino: str
    costo: float
    descripcion: str


@dataclass(frozen=True)
class ResultadoBusquedaMock:
    algoritmo: str
    ruta: list[EstadoMock]
    acciones: list[AccionMock]
    costo_total: float
    desglose: dict[str, float]
    nodos_expandidos: int
    nodos_generados: int
    frontera_max: int
    tiempo_ms: float


@pytest.fixture
def resultados_ejemplo_csv():
    """Genera filas de ejemplo con las 11 columnas requeridas para CSV."""
    return [
        {
            "caso": "caso_1",
            "origen": "biblioteca",
            "destino": "mercado",
            "algoritmo": "A*",
            "pesos": "tiempo=1.0,dinero=0.0",
            "costo_total": 14.5,
            "longitud": 3,
            "nodos_expandidos": 12,
            "nodos_generados": 28,
            "frontera_max": 9,
            "tiempo_ms": 1.45,
        },
        {
            "caso": "caso_1",
            "origen": "biblioteca",
            "destino": "mercado",
            "algoritmo": "Dijkstra",
            "pesos": "tiempo=1.0,dinero=0.0",
            "costo_total": 14.5,
            "longitud": 3,
            "nodos_expandidos": 35,
            "nodos_generados": 60,
            "frontera_max": 20,
            "tiempo_ms": 3.12,
        },
        {
            "caso": "caso_1",
            "origen": "biblioteca",
            "destino": "mercado",
            "algoritmo": "BFS",
            "pesos": "tiempo=1.0,dinero=0.0",
            "costo_total": 18.0,
            "longitud": 3,
            "nodos_expandidos": 42,
            "nodos_generados": 75,
            "frontera_max": 25,
            "tiempo_ms": 3.80,
        },
    ]


@pytest.fixture
def resultado_mock_completo():
    """Genera un ResultadoBusqueda simulado para exportar a JSON."""
    return ResultadoBusquedaMock(
        algoritmo="A*",
        ruta=[
            EstadoMock("biblioteca", "CAMINANDO"),
            EstadoMock("parada_norte", "R1"),
            EstadoMock("mercado", "R1"),
        ],
        acciones=[
            AccionMock("CAMINAR", "biblioteca", "parada_norte", 4.0, "Caminar 180m"),
            AccionMock("ABORDAR", "parada_norte", "mercado", 10.5, "Tomar ruta R1"),
        ],
        costo_total=14.5,
        desglose={"tiempo": 10.5, "dinero": 4.0, "abordajes": 1.0, "penalizacion": 0.0},
        nodos_expandidos=12,
        nodos_generados=28,
        frontera_max=9,
        tiempo_ms=1.45,
    )


def test_guardar_resultado_csv(tmp_path, resultados_ejemplo_csv):
    """Verifica que el CSV se cree con las 11 columnas exactas y el número correcto de filas."""
    archivo_csv = tmp_path / "resultados_test.csv"
    guardar_resultado_csv(resultados_ejemplo_csv, str(archivo_csv))

    assert archivo_csv.exists()
    assert archivo_csv.stat().st_size > 0

    with open(archivo_csv, mode="r", encoding="utf-8") as f:
        reader = csv.reader(f)
        encabezados = next(reader)
        assert encabezados == COLUMNAS_CSV

        filas = list(reader)
        assert len(filas) == 3
        # Validar primera fila (A*)
        assert filas[0][0] == "caso_1"
        assert filas[0][3] == "A*"
        assert float(filas[0][5]) == 14.5
        assert int(filas[0][7]) == 12


def test_guardar_resultado_json(tmp_path, resultado_mock_completo):
    """Verifica que el JSON se cree, sea válido y preserve los datos de la ruta."""
    archivo_json = tmp_path / "detalle_test.json"
    guardar_resultado_json(resultado_mock_completo, str(archivo_json))

    assert archivo_json.exists()
    with open(archivo_json, mode="r", encoding="utf-8") as f:
        contenido = json.load(f)

    assert contenido["algoritmo"] == "A*"
    assert contenido["costo_total"] == 14.5
    assert len(contenido["ruta"]) == 3
    assert len(contenido["acciones"]) == 2
    assert contenido["nodos_expandidos"] == 12


def test_grafica_comparativa(tmp_path, resultados_ejemplo_csv):
    """Verifica que se genere la gráfica de barras en formato PNG."""
    archivo_png = tmp_path / "grafica_comparativa_test.png"
    grafica_comparativa(resultados_ejemplo_csv, str(archivo_png))

    assert archivo_png.exists()
    assert archivo_png.stat().st_size > 500  # Archivo PNG válido no vacío


def test_grafica_escalabilidad(tmp_path):
    """Verifica que se genere la gráfica de escalabilidad en formato PNG."""
    datos_escalabilidad = [
        {"tamano": 100, "tiempo_ms": 1.2, "nodos_expandidos": 20},
        {"tamano": 500, "tiempo_ms": 4.5, "nodos_expandidos": 65},
        {"tamano": 1000, "tiempo_ms": 9.8, "nodos_expandidos": 130},
        {"tamano": 5000, "tiempo_ms": 48.0, "nodos_expandidos": 580},
    ]
    archivo_png = tmp_path / "grafica_escalabilidad_test.png"
    grafica_escalabilidad(datos_escalabilidad, str(archivo_png))

    assert archivo_png.exists()
    assert archivo_png.stat().st_size > 500

