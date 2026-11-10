"""Pruebas de BFS, Dijkstra y A*: optimalidad, métricas y casos límite."""
import itertools
from pathlib import Path

import pytest

from core.algoritmos import astar, bfs, dijkstra
from core.grafo import Grafo, Nodo, Tramo
from core.tipos import CAMINANDO, CLAVES_DESGLOSE, Estado, Pesos, TipoAccion
from datos.cargador import cargar_mapa
from datos.generador_sintetico import generar_ciudad, pares_aleatorios

RAIZ = Path(__file__).resolve().parent.parent
_EJEMPLO = [RAIZ / "tests" / "datos" / "mapa_ejemplo.json",
            RAIZ / "datos" / "mapa_ejemplo.json"]
EJEMPLO = next(p for p in _EJEMPLO if p.exists())
ZONA = RAIZ / "datos" / "zona_demo.json"

PESOS = [
    Pesos(),
    Pesos(tiempo=1, dinero=2, abordaje=5),
    Pesos(tiempo=0.1, dinero=1),
    Pesos(tiempo=1, accesibilidad=3),
    Pesos(tiempo=0, dinero=1),
]
APROX = dict(rel=1e-9, abs=1e-9)
ALGS = [bfs, dijkstra, astar]


@pytest.fixture(scope="module")
def ejemplo():
    return cargar_mapa(EJEMPLO)


@pytest.fixture(scope="module")
def zona():
    return cargar_mapa(ZONA)


def _ruta_valida(res, origen, destino):
    assert res.ruta[0] == Estado(origen, CAMINANDO)
    assert res.ruta[-1].nodo == destino
    assert len(res.ruta) == len(res.acciones) + 1
    for i, a in enumerate(res.acciones):
        assert a.origen == res.ruta[i] and a.destino == res.ruta[i + 1]


 
def test_astar_ejemplo_toma_el_transporte(ejemplo):
    r = astar(ejemplo, "parada_norte", "mercado", Pesos())
    assert r.costo_total == pytest.approx(4.0)        
    assert [a.tipo for a in r.acciones] == [TipoAccion.ABORDAR, TipoAccion.CONTINUAR,
                                            TipoAccion.CONTINUAR]
    assert r.transbordos == 0
    _ruta_valida(r, "parada_norte", "mercado")


def test_con_peso_de_dinero_conviene_caminar(ejemplo):
    r = astar(ejemplo, "parada_norte", "mercado", Pesos(tiempo=1, dinero=5))
    assert r.desglose["dinero"] == 0
    assert all(a.tipo is TipoAccion.CAMINAR for a in r.acciones)


def test_la_accesibilidad_cambia_la_ruta(ejemplo):
    rapida = astar(ejemplo, "entrada", "biblioteca", Pesos())
    accesible = astar(ejemplo, "entrada", "biblioteca", Pesos(tiempo=1, accesibilidad=3))
    assert rapida.desglose["penalizacion"] > 0            
    assert accesible.desglose["penalizacion"] == 0        
    assert accesible.longitud > rapida.longitud


def test_el_peso_de_abordaje_evita_transbordos(ejemplo):
    barato = dijkstra(ejemplo, "parada_norte", "clinica", Pesos())
    sin_bordos = dijkstra(ejemplo, "parada_norte", "clinica", Pesos(tiempo=1, abordaje=100))
    assert sin_bordos.abordajes <= barato.abordajes
    assert sin_bordos.transbordos == 0


 
@pytest.mark.parametrize("pesos", PESOS)
def test_astar_igual_a_dijkstra_en_todos_los_pares_del_ejemplo(ejemplo, pesos):
    for o, d in itertools.permutations(ejemplo.nodos, 2):
        a, dj = astar(ejemplo, o, d, pesos), dijkstra(ejemplo, o, d, pesos)
        assert (a is None) == (dj is None)
        if a is not None:
            assert a.costo_total == pytest.approx(dj.costo_total, **APROX), (o, d)


@pytest.mark.parametrize("pesos", PESOS)
def test_astar_igual_a_dijkstra_en_la_zona_real(zona, pesos):
    for o, d in pares_aleatorios(zona, 60, semilla=11):
        a, dj = astar(zona, o, d, pesos), dijkstra(zona, o, d, pesos)
        assert a is not None and dj is not None, (o, d)
        assert a.costo_total == pytest.approx(dj.costo_total, **APROX), (o, d)
        _ruta_valida(a, o, d)


@pytest.mark.parametrize("pesos", PESOS[:4])
def test_astar_igual_a_dijkstra_en_ciudades_sinteticas(pesos):
    g = generar_ciudad(400, semilla=2)
    for o, d in pares_aleatorios(g, 15, semilla=5):
        a, dj = astar(g, o, d, pesos), dijkstra(g, o, d, pesos)
        assert a.costo_total == pytest.approx(dj.costo_total, **APROX), (o, d)


def test_astar_expande_menos_que_dijkstra_en_conjunto():
    g = generar_ciudad(900, semilla=1)
    pares = pares_aleatorios(g, 15, semilla=3)
    ea = sum(astar(g, o, d, Pesos()).nodos_expandidos for o, d in pares)
    ed = sum(dijkstra(g, o, d, Pesos()).nodos_expandidos for o, d in pares)
    assert ea < ed


 
def test_bfs_minimiza_acciones_y_nunca_gana_en_costo(zona):
    for o, d in pares_aleatorios(zona, 30, semilla=4):
        b, dj = bfs(zona, o, d, Pesos()), dijkstra(zona, o, d, Pesos())
        assert b.longitud <= dj.longitud
        assert b.costo_total >= dj.costo_total - 1e-9
        _ruta_valida(b, o, d)

 
@pytest.mark.parametrize("alg", ALGS)
def test_origen_igual_a_destino(ejemplo, alg):
    r = alg(ejemplo, "plaza", "plaza", Pesos())
    assert r.costo_total == 0 and r.longitud == 0
    assert r.ruta == [Estado("plaza", CAMINANDO)]


@pytest.mark.parametrize("alg", ALGS)
def test_destino_inalcanzable_devuelve_none(alg):
    g = Grafo([Nodo("a", 0, 0), Nodo("b", 100, 0), Nodo("c", 900, 0)],
              [Tramo("a", "b", 100)], [])
    assert alg(g, "a", "c", Pesos()) is None


@pytest.mark.parametrize("alg", ALGS)
@pytest.mark.parametrize("o,d", [("nada", "mercado"), ("entrada", "nada")])
def test_nodo_inexistente_lanza_error(ejemplo, alg, o, d):
    with pytest.raises(ValueError):
        alg(ejemplo, o, d, Pesos())


def test_tramo_de_un_solo_sentido_se_respeta():
    g = Grafo([Nodo("a", 0, 0), Nodo("b", 100, 0)],
              [Tramo("a", "b", 100, bidireccional=False)], [])
    assert astar(g, "a", "b", Pesos()) is not None
    assert astar(g, "b", "a", Pesos()) is None


 
@pytest.mark.parametrize("alg", ALGS)
def test_metricas_completas_y_coherentes(zona, alg):
    o, d = pares_aleatorios(zona, 1, semilla=9)[0]
    pesos = Pesos(tiempo=1, dinero=0.5, abordaje=2, accesibilidad=1)
    r = alg(zona, o, d, pesos)
    assert r.nodos_expandidos >= 1
    assert r.nodos_generados >= r.nodos_expandidos
    assert r.frontera_max >= 1
    assert r.tiempo_ms >= 0
    assert set(r.desglose) == set(CLAVES_DESGLOSE)
    assert r.costo_total == pytest.approx(sum(a.costo(pesos) for a in r.acciones))
    ponderado = (pesos.tiempo * r.desglose["tiempo"] + pesos.dinero * r.desglose["dinero"]
                 + pesos.abordaje * r.desglose["abordajes"]
                 + pesos.accesibilidad * r.desglose["penalizacion"])
    assert r.costo_total == pytest.approx(ponderado)
    assert r.algoritmo in ("BFS", "Dijkstra", "A*")


def test_el_resultado_se_puede_repetir(zona):
    o, d = pares_aleatorios(zona, 1, semilla=2)[0]
    r1, r2 = astar(zona, o, d, Pesos()), astar(zona, o, d, Pesos())
    assert r1.ruta == r2.ruta and r1.nodos_expandidos == r2.nodos_expandidos