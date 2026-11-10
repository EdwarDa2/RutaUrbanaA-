"""Pruebas de la heurística: valores, admisibilidad y consistencia."""
import heapq
import math
from collections import defaultdict
from pathlib import Path

import pytest

from core.grafo import Grafo, Nodo, RutaTransporte, Tramo, VELOCIDAD_CAMINATA_M_MIN
from core.heuristicas import calcular_v_max, crear_heuristica, heuristica_cero
from core.tipos import CAMINANDO, Accion, Estado, Pesos, TipoAccion
from datos.cargador import cargar_mapa

DATOS = Path(__file__).resolve().parent.parent / "datos"
EPS = 1e-9

PESOS_VARIOS = [
    Pesos(),
    Pesos(tiempo=1, dinero=2, abordaje=5),
    Pesos(tiempo=0.1, dinero=1),
    Pesos(tiempo=1, accesibilidad=3),
    Pesos(tiempo=3, dinero=0.5, abordaje=1, accesibilidad=2),
    Pesos(tiempo=0, dinero=1),          # h = 0
]

 
def _mapa_ejemplo() -> Grafo:
    n = lambda i, x, y: Nodo(i, x, y)
    nodos = [n("entrada", 0, 0), n("rampa", 100, -80), n("biblioteca", 200, 0),
             n("parada_norte", 200, 150), n("cafeteria", 400, 0),
             n("parada_centro", 400, 150), n("plaza", 600, 0), n("mercado", 600, 150),
             n("parada_sur", 400, -150), n("clinica", 600, -150)]
    tramos = [
        Tramo("entrada", "biblioteca", 200, 6, "escalera"),
        Tramo("entrada", "rampa", 140, 0, "rampa"),
        Tramo("rampa", "biblioteca", 140, 0, "rampa"),
        Tramo("biblioteca", "parada_norte", 160),
        Tramo("biblioteca", "cafeteria", 210),
        Tramo("parada_norte", "parada_centro", 210),
        Tramo("cafeteria", "parada_centro", 160),
        Tramo("cafeteria", "plaza", 210),
        Tramo("cafeteria", "parada_sur", 160),
        Tramo("plaza", "mercado", 160),
        Tramo("parada_centro", "mercado", 210),
        Tramo("parada_sur", "clinica", 210),
        Tramo("plaza", "clinica", 160),
    ]
    rutas = [
        RutaTransporte("R1", 10.0, 2.0, ("parada_norte", "parada_centro", "mercado"), (1.0, 1.0)),
        RutaTransporte("R2", 10.0, 3.0, ("parada_centro", "parada_sur", "clinica"), (1.5, 1.0)),
    ]
    return Grafo(nodos, tramos, rutas)


 
def _estados(grafo: Grafo) -> list[Estado]:
    est = [Estado(nid, CAMINANDO) for nid in grafo.nodos]
    for r in grafo.rutas.values():
        est += [Estado(p, r.id) for p in r.paradas]
    return est


def _acciones_desde(grafo: Grafo, e: Estado) -> list[Accion]:
    acc = []
    for v in grafo.vecinos(e.nodo):
        acc.append(Accion(TipoAccion.CAMINAR, e, Estado(v.nodo, CAMINANDO),
                          tiempo_min=Grafo.tiempo_caminata(v.distancia_m),
                          penalizacion=v.penalizacion))
    if e.ruta == CAMINANDO:
        for r in grafo.rutas_en(e.nodo):
            acc.append(Accion(TipoAccion.ABORDAR, e, Estado(e.nodo, r.id),
                              tiempo_min=r.espera_min, dinero=r.tarifa, abordaje=1.0))
    else:
        sig = grafo.siguiente_parada(e.ruta, e.nodo)
        if sig is not None:
            acc.append(Accion(TipoAccion.CONTINUAR, e, Estado(sig[0], e.ruta), tiempo_min=sig[1]))
        for r in grafo.rutas_en(e.nodo):
            if r.id != e.ruta:
                acc.append(Accion(TipoAccion.TRANSBORDAR, e, Estado(e.nodo, r.id),
                                  tiempo_min=r.espera_min, dinero=r.tarifa, abordaje=1.0))
    return acc


def _aristas(grafo: Grafo, pesos: Pesos) -> list[tuple[Estado, Estado, float]]:
    return [(a.origen, a.destino, a.costo(pesos))
            for e in _estados(grafo) for a in _acciones_desde(grafo, e)]


def _costo_restante(grafo, aristas, destino) -> dict[Estado, float]:
    """Costo óptimo real de cada estado hasta cualquier estado con nodo == destino."""
    inversa = defaultdict(list)
    for o, d, c in aristas:
        inversa[d].append((o, c))
    dist = {e: math.inf for e in _estados(grafo)}
    cola = []
    for e in dist:
        if e.nodo == destino:
            dist[e] = 0.0
            heapq.heappush(cola, (0.0, e))
    while cola:
        d, e = heapq.heappop(cola)
        if d > dist[e]:
            continue
        for o, c in inversa[e]:
            if d + c < dist[o]:
                dist[o] = d + c
                heapq.heappush(cola, (dist[o], o))
    return dist


 
def test_v_max_ejemplo_es_200():
    assert calcular_v_max(_mapa_ejemplo()) == pytest.approx(200.0)


def test_v_max_sin_rutas_es_la_caminata():
    g = Grafo([Nodo("a", 0, 0), Nodo("b", 100, 0)], [Tramo("a", "b", 100)], [])
    assert calcular_v_max(g) == VELOCIDAD_CAMINATA_M_MIN


def test_h_en_el_destino_es_cero():
    g = _mapa_ejemplo()
    h = crear_heuristica(g, "mercado", Pesos())
    assert h(Estado("mercado", CAMINANDO)) == 0.0
    assert h(Estado("mercado", "R1")) == 0.0


def test_h_valor_conocido():
    g = _mapa_ejemplo()
    h = crear_heuristica(g, "mercado", Pesos())
    assert h(Estado("entrada", CAMINANDO)) == pytest.approx(math.hypot(600, 150) / 200)


def test_h_depende_solo_del_nodo():
    g = _mapa_ejemplo()
    h = crear_heuristica(g, "mercado", Pesos())
    assert h(Estado("parada_centro", CAMINANDO)) == h(Estado("parada_centro", "R1")) \
        == h(Estado("parada_centro", "R2"))


def test_h_escala_con_el_peso_de_tiempo():
    g = _mapa_ejemplo()
    h1 = crear_heuristica(g, "clinica", Pesos(tiempo=1))
    h2 = crear_heuristica(g, "clinica", Pesos(tiempo=2))
    e = Estado("entrada", CAMINANDO)
    assert h2(e) == pytest.approx(2 * h1(e))


def test_w1_cero_da_h_cero():
    g = _mapa_ejemplo()
    h = crear_heuristica(g, "mercado", Pesos(tiempo=0, dinero=1))
    assert all(h(e) == 0.0 for e in _estados(g))


def test_destino_inexistente_falla():
    g = _mapa_ejemplo()
    with pytest.raises(ValueError):
        crear_heuristica(g, "no_existe", Pesos())
    with pytest.raises(ValueError):
        heuristica_cero(g, "no_existe", Pesos())


def test_heuristica_cero_siempre_cero():
    g = _mapa_ejemplo()
    h = heuristica_cero(g, "mercado", Pesos())
    assert all(h(e) == 0.0 for e in _estados(g))


 
def test_oraculo_costo_conocido():
    g = _mapa_ejemplo()
    aristas = _aristas(g, Pesos())          # solo tiempo
    dist = _costo_restante(g, aristas, "mercado")
     
    assert dist[Estado("parada_norte", CAMINANDO)] == pytest.approx(4.0)
    assert dist[Estado("parada_norte", "R1")] == pytest.approx(2.0)


 
def _verificar(grafo: Grafo, pesos: Pesos) -> None:
    aristas = _aristas(grafo, pesos)
    for destino in grafo.nodos:
        h = crear_heuristica(grafo, destino, pesos)
        real = _costo_restante(grafo, aristas, destino)
        for e, costo in real.items():
            if math.isfinite(costo):                       
                assert h(e) <= costo + EPS, f"sobreestima en {e} hacia {destino}"
        for o, d, c in aristas:                             
            assert h(o) <= c + h(d) + EPS, f"inconsistente en {o}->{d} hacia {destino}"


@pytest.mark.parametrize("pesos", PESOS_VARIOS)
def test_admisible_y_consistente_mapa_ejemplo(pesos):
    _verificar(_mapa_ejemplo(), pesos)


@pytest.mark.parametrize("archivo", ["mapa_ejemplo.json", "zona_demo.json"])
@pytest.mark.parametrize("pesos", PESOS_VARIOS[:3])
def test_admisible_y_consistente_mapas_reales(archivo, pesos):
    _verificar(cargar_mapa(DATOS / archivo), pesos)