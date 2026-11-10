"""Pruebas unitarias para el visualizador web interactivo con Plotly."""

import pytest
import plotly.graph_objects as go

from core.tipos import Pesos, ResultadoBusqueda
from datos.cargador import grafo_desde_dict
from ui.arbol import extraer_arbol_y_pasos
from ui.mapa import preparar_elementos_mapa
from ui.web_visualizador import (
    transformar_coordenadas,
    crear_figura_mapa_plotly,
    crear_figura_arbol_plotly,
    crear_grafica_comparativa_plotly,
    formatear_nombre_ruta,
)


@pytest.fixture
def mapa_prueba():
    return {
        "nodos": [
            {"id": "A", "x": 0.0, "y": 0.0},
            {"id": "B", "x": 100.0, "y": 0.0},
            {"id": "C", "x": 200.0, "y": 0.0},
        ],
        "tramos": [
            {"de": "A", "a": "B", "distancia_m": 100.0, "tipo": "calle"},
            {"de": "B", "a": "C", "distancia_m": 100.0, "tipo": "calle"},
        ],
        "rutas": [],
    }


def test_transformar_coordenadas():
    pos = {"A": (100.0, 50.0)}
    trans = transformar_coordenadas(pos, factor_y=2.5)
    assert trans["A"][0] == 100.0
    assert trans["A"][1] == 125.0


def test_transformar_coordenadas_repulsion():
    import math
    pos = {"A": (0.0, 0.0), "B": (30.0, 0.0)}
    trans = transformar_coordenadas(pos, factor_y=1.0, distancia_minima=165.0)
    dx = trans["B"][0] - trans["A"][0]
    dy = trans["B"][1] - trans["A"][1]
    assert math.hypot(dx, dy) >= 164.0


def test_crear_figura_mapa_plotly(mapa_prueba):
    grafo = grafo_desde_dict(mapa_prueba)
    elementos = preparar_elementos_mapa(grafo)

    fig = crear_figura_mapa_plotly(elementos, modo="viajero")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0


def test_crear_figura_mapa_exploracion_plotly(mapa_prueba):
    grafo = grafo_desde_dict(mapa_prueba)
    elementos = preparar_elementos_mapa(grafo)
    nodos, raiz_id, pasos = extraer_arbol_y_pasos(grafo, "A", "C", Pesos(), "A*")

    fig = crear_figura_mapa_plotly(elementos, modo="exploracion", paso_exploracion=pasos[-1])
    assert isinstance(fig, go.Figure)


def test_crear_figura_arbol_plotly(mapa_prueba):
    grafo = grafo_desde_dict(mapa_prueba)
    nodos, raiz_id, pasos = extraer_arbol_y_pasos(grafo, "A", "C", Pesos(), "A*")

    fig = crear_figura_arbol_plotly(nodos, raiz_id, algoritmo="A*")
    assert isinstance(fig, go.Figure)


def test_crear_grafica_comparativa_plotly():
    res1 = ResultadoBusqueda(algoritmo="A*", ruta=[], acciones=[], costo_total=10.0, desglose={}, nodos_expandidos=5, nodos_generados=10, frontera_max=4, tiempo_ms=1.2)
    res2 = ResultadoBusqueda(algoritmo="Dijkstra", ruta=[], acciones=[], costo_total=10.0, desglose={}, nodos_expandidos=15, nodos_generados=25, frontera_max=8, tiempo_ms=2.5)

    fig = crear_grafica_comparativa_plotly([res1, res2])
    assert isinstance(fig, go.Figure)


def test_formatear_nombre_ruta():
    assert formatear_nombre_ruta("ruta_1_belisario_ida") == "R1 Belisario (ida)"
    assert formatear_nombre_ruta("linea_2_centro_vuelta") == "R2 Centro (vuelta)"
    assert formatear_nombre_ruta("colectivo_4") == "Colectivo 4"
    assert formatear_nombre_ruta("") == ""
