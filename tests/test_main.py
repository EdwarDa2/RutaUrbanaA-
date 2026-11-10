"""Pruebas unitarias para la interfaz de línea de comandos (main.py)."""

import pytest
from dataclasses import dataclass
from typing import NamedTuple

from main import (
    CRITERIOS_PREDEFINIDOS,
    crear_parser,
    parsear_pesos,
    formatear_itinerario,
    formatear_resumen_metricas,
    sugerir_nodos_cercanos,
    formatear_tabla_comparativa,
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
def parser():
    return crear_parser()


@pytest.fixture
def resultado_mock():
    return ResultadoBusquedaMock(
        algoritmo="A*",
        ruta=[
            EstadoMock("biblioteca", "CAMINANDO"),
            EstadoMock("parada_norte", "R1"),
            EstadoMock("mercado", "R1"),
        ],
        acciones=[
            AccionMock("CAMINAR", "biblioteca", "parada_norte", 4.0, "Caminar 180 metros"),
            AccionMock("ABORDAR", "parada_norte", "mercado", 10.5, "Tomar ruta R1 hasta mercado"),
        ],
        costo_total=14.5,
        desglose={"tiempo": 10.5, "dinero": 4.0, "abordajes": 1.0, "accesibilidad": 0.0},
        nodos_expandidos=15,
        nodos_generados=32,
        frontera_max=8,
        tiempo_ms=1.75,
    )


def test_parser_argumentos_basicos(parser):
    """Verifica que el parser reconozca origen, destino y banderas."""
    args = parser.parse_args(["--origen", "Biblioteca", "--destino", "Mercado", "--criterio", "rapida", "--mapa"])
    assert args.origen == "Biblioteca"
    assert args.destino == "Mercado"
    assert args.criterio == "rapida"
    assert args.mapa is True


def test_parsear_pesos_criterios_predefinidos():
    """Verifica la traducción de atajos predefinidos a ponderaciones numéricas."""
    for criterio in ["rapida", "barata", "pocos-transbordos", "accesible"]:
        pesos = parsear_pesos(criterio=criterio, pesos_str=None)
        assert pesos.tiempo >= 0
        assert pesos.dinero >= 0
        assert pesos.abordaje >= 0
        assert pesos.accesibilidad >= 0

    # Criterio rapida debe priorizar tiempo
    p_rapida = parsear_pesos(criterio="rapida", pesos_str=None)
    assert p_rapida.tiempo > p_rapida.dinero

    # Criterio barata debe priorizar dinero
    p_barata = parsear_pesos(criterio="barata", pesos_str=None)
    assert p_barata.dinero > p_barata.tiempo


def test_parsear_pesos_manuales():
    """Verifica el parseo de pesos personalizados ingresados por el usuario."""
    # Formato espacio o coma
    pesos1 = parsear_pesos(criterio=None, pesos_str="tiempo=1.5 dinero=2.0 abordaje=5.0 accesibilidad=0.5")
    assert pesos1.tiempo == 1.5
    assert pesos1.dinero == 2.0
    assert pesos1.abordaje == 5.0
    assert pesos1.accesibilidad == 0.5

    pesos2 = parsear_pesos(criterio=None, pesos_str="tiempo=2,dinero=3")
    assert pesos2.tiempo == 2.0
    assert pesos2.dinero == 3.0
    assert pesos2.abordaje == 0.0


def test_parsear_pesos_invalido():
    """Verifica que arroje ValueError si se ingresan valores negativos o texto incorrecto."""
    with pytest.raises(ValueError):
        parsear_pesos(criterio=None, pesos_str="tiempo=-1")

    with pytest.raises(ValueError):
        parsear_pesos(criterio="criterio_inexistente", pesos_str=None)


def test_formatear_itinerario(resultado_mock):
    """Verifica que el itinerario muestre cada paso de forma amigable."""
    texto = formatear_itinerario(resultado_mock)
    assert "1. Caminar 180 metros" in texto
    assert "2. Tomar ruta R1 hasta mercado" in texto


def test_formatear_resumen_metricas(resultado_mock):
    """Verifica que el resumen incluya costo total, desglose y métricas de búsqueda."""
    texto = formatear_resumen_metricas(resultado_mock)
    assert "Costo Total:" in texto
    assert "14.50" in texto
    assert "Nodos expandidos:  15" in texto
    assert "Nodos generados:   32" in texto
    assert "Tiempo de cálculo: 1.75 ms" in texto


def test_sugerir_nodos_cercanos():
    """Verifica que el CLI sugiera nombres válidos cuando el usuario comete un error tipográfico."""
    nodos = ["biblioteca", "mercado", "parada_norte", "parque_central"]

    # Caso difuso: "biblioteka" -> debe sugerir "biblioteca"
    sugerencias = sugerir_nodos_cercanos("biblioteka", nodos)
    assert "biblioteca" in sugerencias

    # Caso insensible a mayúsculas: "MERCADO" -> "mercado"
    assert "mercado" in sugerir_nodos_cercanos("MERCADO", nodos)

    # Caso sin coincidencia razonable
    assert sugerir_nodos_cercanos("xyz123", nodos) == []


def test_formatear_tabla_comparativa(resultado_mock):
    """Verifica que la tabla comparativa de algoritmos se imprima con encabezados y métricas."""
    resultado_dijkstra = ResultadoBusquedaMock(
        algoritmo="Dijkstra",
        ruta=resultado_mock.ruta,
        acciones=resultado_mock.acciones,
        costo_total=14.5,
        desglose=resultado_mock.desglose,
        nodos_expandidos=45,
        nodos_generados=90,
        frontera_max=22,
        tiempo_ms=3.2,
    )
    tabla = formatear_tabla_comparativa([resultado_mock, resultado_dijkstra])
    assert "TABLA COMPARATIVA DE ALGORITMOS" in tabla
    assert "A*" in tabla
    assert "Dijkstra" in tabla
    assert "14.50" in tabla
    assert "15" in tabla
    assert "45" in tabla


def test_regla_negocio_origen_igual_destino(monkeypatch, capsys):
    """Verifica que main() aplique la regla de negocio rechazando origen idéntico al destino."""
    from main import main
    monkeypatch.setattr("sys.argv", ["main.py", "--origen", "parque_marimba", "--destino", "parque_marimba"])
    codigo = main()
    assert codigo == 1
    captured = capsys.readouterr()
    assert "origen y de destino no pueden ser iguales" in captured.err
