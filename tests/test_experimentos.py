"""Pruebas unitarias para el módulo de experimentos y benchmarking (analytics/experimentos.py)."""

import pytest
from dataclasses import dataclass
from typing import NamedTuple

from analytics.experimentos import (
    calcular_ahorro_nodos,
    ejecutar_experimento_completo,
    ejecutar_experimento_escalabilidad,
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
def casos_prueba_mock():
    return [
        {"id": "caso_01", "origen": "A", "destino": "B"},
        {"id": "caso_02", "origen": "B", "destino": "C"},
    ]


@pytest.fixture
def algoritmos_mock():
    """Genera funciones de búsqueda simuladas para A*, Dijkstra y BFS."""
    def mock_astar(grafo, origen, destino, pesos):
        return ResultadoBusquedaMock(
            algoritmo="A*",
            ruta=[EstadoMock(origen, "CAMINANDO"), EstadoMock(destino, "CAMINANDO")],
            acciones=[AccionMock("CAMINAR", origen, destino, 10.0, "Caminar directo")],
            costo_total=10.0,
            desglose={"tiempo": 10.0},
            nodos_expandidos=15,
            nodos_generados=30,
            frontera_max=6,
            tiempo_ms=1.2,
        )

    def mock_dijkstra(grafo, origen, destino, pesos):
        return ResultadoBusquedaMock(
            algoritmo="Dijkstra",
            ruta=[EstadoMock(origen, "CAMINANDO"), EstadoMock(destino, "CAMINANDO")],
            acciones=[AccionMock("CAMINAR", origen, destino, 10.0, "Caminar directo")],
            costo_total=10.0,
            desglose={"tiempo": 10.0},
            nodos_expandidos=45,
            nodos_generados=80,
            frontera_max=20,
            tiempo_ms=2.8,
        )

    def mock_bfs(grafo, origen, destino, pesos):
        return ResultadoBusquedaMock(
            algoritmo="BFS",
            ruta=[EstadoMock(origen, "CAMINANDO"), EstadoMock(destino, "CAMINANDO")],
            acciones=[AccionMock("CAMINAR", origen, destino, 12.0, "Caminar")],
            costo_total=12.0,
            desglose={"tiempo": 12.0},
            nodos_expandidos=60,
            nodos_generados=110,
            frontera_max=35,
            tiempo_ms=3.5,
        )

    return {"A*": mock_astar, "Dijkstra": mock_dijkstra, "BFS": mock_bfs}


def test_calcular_ahorro_nodos():
    """Verifica la fórmula: 1 - (expandidos_A* / expandidos_Dijkstra)."""
    # Si A* expande 20 y Dijkstra 100, el ahorro es 80% (0.8)
    ahorro = calcular_ahorro_nodos(expandidos_astar=20, expandidos_dijkstra=100)
    assert pytest.approx(ahorro, 0.001) == 0.8

    # Si expanden lo mismo, el ahorro es 0.0
    assert calcular_ahorro_nodos(50, 50) == 0.0

    # Evitar división por cero
    assert calcular_ahorro_nodos(10, 0) == 0.0


def test_ejecutar_experimento_completo(casos_prueba_mock, algoritmos_mock):
    """Verifica la ejecución por lotes, verificación de optimalidad y filas para CSV."""
    reporte = ejecutar_experimento_completo(
        casos=casos_prueba_mock,
        grafo={},
        algoritmos=algoritmos_mock,
        repeticiones=3,
    )

    assert "filas_csv" in reporte
    assert len(reporte["filas_csv"]) == 6  # 2 casos x 3 algoritmos
    assert reporte["diferencias_costo_astar_dijkstra"] == 0  # Costo idéntico
    assert reporte["ahorro_promedio"] > 0.5  # A* expandió 15 vs 45 -> 66.6% ahorro

    # Verificar estructura de fila CSV
    primera_fila = reporte["filas_csv"][0]
    assert "caso" in primera_fila
    assert "algoritmo" in primera_fila
    assert "costo_total" in primera_fila
    assert "nodos_expandidos" in primera_fila


def test_ejecutar_experimento_escalabilidad():
    """Verifica la medición sobre grafos de tamaño creciente."""
    def generador_mock(tamano):
        return {"n": tamano}

    def busqueda_mock(grafo, origen, destino, pesos):
        n = grafo["n"]
        return ResultadoBusquedaMock(
            algoritmo="A*",
            ruta=[],
            acciones=[],
            costo_total=50.0,
            desglose={},
            nodos_expandidos=int(n * 0.1),
            nodos_generados=int(n * 0.25),
            frontera_max=10,
            tiempo_ms=0.01 * n,
        )

    tamanos = [100, 500, 1000]
    resultados = ejecutar_experimento_escalabilidad(
        generador_func=generador_mock,
        tamanos=tamanos,
        algoritmo_func=busqueda_mock,
        repeticiones=2,
    )

    assert len(resultados) == 3
    assert resultados[0]["tamano"] == 100
    assert resultados[2]["tamano"] == 1000
    assert resultados[0]["nodos_expandidos"] == 10
    assert resultados[2]["nodos_expandidos"] == 100

