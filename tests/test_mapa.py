"""Pruebas unitarias para el renderizador del mapa visual (ui/mapa.py).

Verifica la separación entre el cálculo de elementos visuales y el dibujo en matplotlib.
"""

import os
from dataclasses import dataclass
from typing import NamedTuple
import pytest

from ui.mapa import preparar_elementos_mapa, generar_mapa, dibujar_paso_busqueda_en_mapa


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
def mapa_demo_dict():
    """Grafo de ejemplo con 5 nodos, tramos peatonales y una ruta de transporte."""
    return {
        "nodos": [
            {"id": "biblioteca", "x": 0.0, "y": 0.0},
            {"id": "parada_norte", "x": 100.0, "y": 0.0},
            {"id": "parada_centro", "x": 200.0, "y": 100.0},
            {"id": "mercado", "x": 300.0, "y": 100.0},
            {"id": "parque", "x": 100.0, "y": -100.0},
        ],
        "tramos": [
            {"de": "biblioteca", "a": "parada_norte", "distancia_m": 100, "tipo": "calle"},
            {"de": "parada_norte", "a": "parque", "distancia_m": 100, "tipo": "calle"},
            {"de": "parada_centro", "a": "mercado", "distancia_m": 100, "tipo": "calle"},
        ],
        "rutas": [
            {
                "id": "R1",
                "tarifa": 10.0,
                "espera_min": 5,
                "paradas": ["parada_norte", "parada_centro"],
                "tiempos_min": [6],
            }
        ],
    }


@pytest.fixture
def resultado_demo():
    """Ruta que va de biblioteca (a pie) a parada_norte, toma R1 a parada_centro y camina a mercado."""
    return ResultadoBusquedaMock(
        algoritmo="A*",
        ruta=[
            EstadoMock("biblioteca", "CAMINANDO"),
            EstadoMock("parada_norte", "R1"),
            EstadoMock("parada_centro", "CAMINANDO"),
            EstadoMock("mercado", "CAMINANDO"),
        ],
        acciones=[
            AccionMock("CAMINAR", "biblioteca", "parada_norte", 2.0, "Caminar 100m"),
            AccionMock("ABORDAR", "parada_norte", "parada_centro", 10.0, "Tomar ruta R1"),
            AccionMock("CAMINAR", "parada_centro", "mercado", 2.0, "Caminar a mercado"),
        ],
        costo_total=14.0,
        desglose={"tiempo": 10.0, "dinero": 10.0},
        nodos_expandidos=4,
        nodos_generados=8,
        frontera_max=3,
        tiempo_ms=0.8,
    )


def test_preparar_elementos_mapa_posiciones(mapa_demo_dict):
    """Verifica que se extraigan las coordenadas exactas de cada nodo."""
    elementos = preparar_elementos_mapa(mapa_demo_dict)
    assert len(elementos.posiciones) == 5
    assert elementos.posiciones["biblioteca"] == (0.0, 0.0)
    assert elementos.posiciones["mercado"] == (300.0, 100.0)


def test_preparar_elementos_mapa_distincion_tramos(mapa_demo_dict, resultado_demo):
    """Verifica que se clasifiquen correctamente tramos caminando, de transporte y transbordos."""
    elementos = preparar_elementos_mapa(mapa_demo_dict, resultado=resultado_demo)

    # Tramos base
    assert len(elementos.aristas_caminando) >= 2
    assert "R1" in elementos.aristas_transporte

    # Ruta solución: debe tener 3 tramos (caminar, transporte, caminar)
    assert len(elementos.aristas_solucion) == 3
    tipos_solucion = [tramo["tipo"] for tramo in elementos.aristas_solucion]
    assert "CAMINANDO" in tipos_solucion
    assert "TRANSPORTE" in tipos_solucion
    assert any(tramo.get("ruta") == "R1" for tramo in elementos.aristas_solucion)

    # Puntos de cambio de modalidad / transbordo detectados
    assert "parada_norte" in elementos.nodos_transbordo
    assert "parada_centro" in elementos.nodos_transbordo


def test_preparar_elementos_nodos_explorados(mapa_demo_dict, resultado_demo):
    """Verifica que los nodos explorados se mapeen a coordenadas cartesianas."""
    explorados = ["biblioteca", "parada_norte", "parque"]
    elementos = preparar_elementos_mapa(mapa_demo_dict, resultado=resultado_demo, nodos_explorados=explorados)

    assert len(elementos.coords_explorados) == 3
    assert (100.0, -100.0) in elementos.coords_explorados


def test_generar_mapa_png(tmp_path, mapa_demo_dict, resultado_demo):
    """Verifica que generar_mapa produzca un archivo PNG válido no vacío."""
    salida_png = tmp_path / "mapa_prueba.png"
    nodos_explorados = ["biblioteca", "parada_norte", "parque"]

    generar_mapa(
        mapa=mapa_demo_dict,
        resultado=resultado_demo,
        ruta_png=str(salida_png),
        nodos_explorados=nodos_explorados,
        titulo="Prueba Visual Mapa RutaUrbana",
    )

    assert salida_png.exists()
    assert salida_png.stat().st_size > 1000  # PNG real con contenido gráfico


def test_dibujar_paso_busqueda_en_mapa(mapa_demo_dict):
    """Verifica que dibujar_paso_busqueda_en_mapa renderice sobre un Axes sin lanzar excepciones."""
    import matplotlib.pyplot as plt
    from dataclasses import dataclass

    @dataclass
    class PasoMock:
        num_paso: int = 1
        nodo_actual: str = "biblioteca"
        f: float = 12.0
        g: float = 5.0
        h: float = 7.0
        nodos_cerrados: set = None
        nodos_frontera: set = None
        aristas_exploradas: list = None
        es_meta: bool = False

    elementos = preparar_elementos_mapa(mapa_demo_dict)
    paso = PasoMock(nodos_cerrados={"biblioteca"}, nodos_frontera={"parada_norte"}, aristas_exploradas=[("biblioteca", "parada_norte")])

    fig, ax = plt.subplots(figsize=(6, 5))
    dibujar_paso_busqueda_en_mapa(ax, elementos, paso, total_pasos=5, algoritmo="A*")
    plt.close(fig)

