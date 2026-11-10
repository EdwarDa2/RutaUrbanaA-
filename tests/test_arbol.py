"""Pruebas unitarias para el módulo del árbol de búsqueda (ui/arbol.py)."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

from core.tipos import Pesos
from datos.cargador import cargar_mapa
from ui.arbol import extraer_arbol_busqueda, extraer_arbol_y_pasos, calcular_posiciones_arbol, dibujar_arbol_en_axes


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


def test_extraer_arbol_busqueda(mapa_prueba):
    """Verifica que se extraigan los nodos, costos g, h, f y la rama de solución."""
    from datos.cargador import grafo_desde_dict
    grafo = grafo_desde_dict(mapa_prueba)
    pesos = Pesos(tiempo=1.0)

    nodos, raiz_id = extraer_arbol_busqueda(grafo, "A", "C", pesos, algoritmo="A*")

    assert raiz_id is not None
    assert raiz_id in nodos
    assert nodos[raiz_id].g == 0.0

    # Rama solución debe contener origen y destino
    nodos_solucion = [n for n in nodos.values() if n.es_solucion]
    assert len(nodos_solucion) >= 2


def test_dibujar_arbol_en_axes(mapa_prueba):
    """Verifica que el renderizado sobre un Axes de matplotlib funcione sin excepciones."""
    from datos.cargador import grafo_desde_dict
    grafo = grafo_desde_dict(mapa_prueba)
    pesos = Pesos(tiempo=1.0)

    nodos, raiz_id = extraer_arbol_busqueda(grafo, "A", "C", pesos, algoritmo="A*")

    fig, ax = plt.subplots(figsize=(8, 6))
    dibujar_arbol_en_axes(ax, nodos, raiz_id, algoritmo="A*")
    plt.close(fig)


def test_dibujar_arbol_vacio():
    """Verifica el comportamiento cuando no hay nodos para dibujar."""
    fig, ax = plt.subplots(figsize=(8, 6))
    dibujar_arbol_en_axes(ax, {}, None)
    plt.close(fig)


def test_extraer_arbol_dijkstra_y_bfs(mapa_prueba):
    """Verifica que la extracción de árbol funcione para Dijkstra y BFS."""
    from datos.cargador import grafo_desde_dict
    grafo = grafo_desde_dict(mapa_prueba)
    pesos = Pesos(tiempo=1.0)

    nodos_dijk, raiz_d = extraer_arbol_busqueda(grafo, "A", "C", pesos, algoritmo="Dijkstra")
    assert raiz_d in nodos_dijk

    nodos_bfs, raiz_b = extraer_arbol_busqueda(grafo, "A", "C", pesos, algoritmo="BFS")
    assert raiz_b in nodos_bfs


def test_extraer_arbol_y_pasos(mapa_prueba):
    """Verifica que se capturen los pasos de exploración secuenciales."""
    from datos.cargador import grafo_desde_dict
    grafo = grafo_desde_dict(mapa_prueba)
    pesos = Pesos(tiempo=1.0)

    nodos, raiz_id, pasos = extraer_arbol_y_pasos(grafo, "A", "C", pesos, algoritmo="A*")
    assert len(pasos) >= 2
    # El primer paso (paso 0) es el estado inicial
    assert pasos[0].num_paso == 0
    assert pasos[0].nodo_actual == "A"
    # El último paso debe haber alcanzado la meta
    assert any(p.es_meta for p in pasos)
