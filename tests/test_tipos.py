import dataclasses
import inspect
import math

import pytest

from core import algoritmos
from core.tipos import (
    CAMINANDO, CLAVES_DESGLOSE, Accion, Estado, Pesos, ResultadoBusqueda, TipoAccion,
)



def test_estado_es_hashable_y_comparable():
    a, b = Estado("biblioteca", "R1"), Estado("biblioteca", "R1")
    assert a == b and hash(a) == hash(b)
    assert {a: 1}[b] == 1


def test_estado_por_defecto_va_caminando():
    assert Estado("biblioteca").ruta == CAMINANDO



def test_pesos_por_defecto_solo_miden_tiempo():
    assert Pesos() == Pesos(tiempo=1.0, dinero=0.0, abordaje=0.0, accesibilidad=0.0)


@pytest.mark.parametrize("malo", [
    dict(tiempo=-1), dict(dinero=-0.1), dict(abordaje=-5), dict(accesibilidad=-2),
    dict(tiempo=math.nan), dict(tiempo=math.inf),
])
def test_pesos_invalidos_lanzan_error(malo):
    with pytest.raises(ValueError):
        Pesos(**malo)


def test_pesos_todos_cero_lanza_error():
    with pytest.raises(ValueError):
        Pesos(tiempo=0, dinero=0, abordaje=0, accesibilidad=0)


def test_pesos_son_inmutables():
    with pytest.raises(dataclasses.FrozenInstanceError):
        Pesos().tiempo = 5



def abordar():
    return Accion(TipoAccion.ABORDAR, Estado("norte"), Estado("norte", "R1"),
                  tiempo_min=4, dinero=10, abordaje=1, penalizacion=0)


def test_costo_pondera_cada_componente():
    assert abordar().costo(Pesos(tiempo=1, dinero=2, abordaje=5, accesibilidad=0)) == 4 + 20 + 5


def test_peso_cero_ignora_ese_componente():
    assert abordar().costo(Pesos(tiempo=1)) == 4


def test_la_penalizacion_solo_cuenta_si_su_peso_es_positivo():
    a = Accion(TipoAccion.CAMINAR, Estado("a"), Estado("b"), tiempo_min=2, penalizacion=8)
    assert a.costo(Pesos(tiempo=1)) == 2
    assert a.costo(Pesos(tiempo=1, accesibilidad=3)) == 2 + 24


@pytest.mark.parametrize("campo", ["tiempo_min", "dinero", "abordaje", "penalizacion"])
def test_accion_rechaza_componentes_negativos(campo):

    with pytest.raises(ValueError):
        Accion(TipoAccion.CAMINAR, Estado("a"), Estado("b"), **{campo: -1})



def test_formas_validas_de_las_cuatro_acciones():
    Accion(TipoAccion.CAMINAR, Estado("a"), Estado("b"))
    Accion(TipoAccion.CAMINAR, Estado("a", "R1"), Estado("b"))      
    Accion(TipoAccion.ABORDAR, Estado("a"), Estado("a", "R1"))
    Accion(TipoAccion.CONTINUAR, Estado("a", "R1"), Estado("b", "R1"))
    Accion(TipoAccion.TRANSBORDAR, Estado("a", "R1"), Estado("a", "R2"))


@pytest.mark.parametrize("tipo, origen, destino", [
    (TipoAccion.CAMINAR, Estado("a"), Estado("b", "R1")),           
    (TipoAccion.CAMINAR, Estado("a"), Estado("a")),                 
    (TipoAccion.ABORDAR, Estado("a", "R1"), Estado("a", "R2")),     
    (TipoAccion.ABORDAR, Estado("a"), Estado("b", "R1")),           
    (TipoAccion.CONTINUAR, Estado("a", "R1"), Estado("b", "R2")),   
    (TipoAccion.CONTINUAR, Estado("a"), Estado("b")),               
    (TipoAccion.TRANSBORDAR, Estado("a", "R1"), Estado("a", "R1")), 
    (TipoAccion.TRANSBORDAR, Estado("a"), Estado("a", "R1")),       
])
def test_formas_invalidas_lanzan_error(tipo, origen, destino):
    with pytest.raises(ValueError):
        Accion(tipo, origen, destino)


def test_accion_se_muestra_legible():
    assert str(abordar()) == "abordar R1 en norte"
    assert str(Accion(TipoAccion.CAMINAR, Estado("a"), Estado("b"))) == "caminar: a -> b"
    assert str(Accion(TipoAccion.CONTINUAR, Estado("a", "R1"), Estado("b", "R1"))) \
        == "continuar en R1: a -> b"
    assert str(Accion(TipoAccion.TRANSBORDAR, Estado("c", "R1"), Estado("c", "R2"))) \
        == "transbordar de R1 a R2 en c"



def resultado_ejemplo():
    e0, e1, e2, e3 = (Estado("A"), Estado("N"), Estado("N", "R1"), Estado("M", "R1"))
    e4 = Estado("M", "R2")
    acciones = [
        Accion(TipoAccion.CAMINAR, e0, e1, tiempo_min=3),
        Accion(TipoAccion.ABORDAR, e1, e2, dinero=10, abordaje=1),
        Accion(TipoAccion.CONTINUAR, e2, e3, tiempo_min=5),
        Accion(TipoAccion.TRANSBORDAR, e3, e4, dinero=10, abordaje=1),
    ]
    return ResultadoBusqueda(
        algoritmo="astar", ruta=[e0, e1, e2, e3, e4], acciones=acciones,
        costo_total=8.0, desglose=dict.fromkeys(CLAVES_DESGLOSE, 0.0),
        nodos_expandidos=5, nodos_generados=9, frontera_max=3, tiempo_ms=0.4)


def test_resultado_expone_origen_destino_y_longitud():
    r = resultado_ejemplo()
    assert (r.origen, r.destino, r.longitud) == ("A", "M", 4)


def test_transbordos_son_abordajes_menos_uno():
    r = resultado_ejemplo()
    assert r.abordajes == 2
    assert r.transbordos == 1


def test_sin_transporte_no_hay_transbordos():
    e0, e1 = Estado("A"), Estado("B")
    r = dataclasses.replace(
        resultado_ejemplo(), ruta=[e0, e1],
        acciones=[Accion(TipoAccion.CAMINAR, e0, e1, tiempo_min=2)])
    assert (r.abordajes, r.transbordos) == (0, 0)


def test_resultado_es_inmutable():
    with pytest.raises(dataclasses.FrozenInstanceError):
        resultado_ejemplo().costo_total = 0


FUNCIONES = [algoritmos.bfs, algoritmos.dijkstra, algoritmos.astar]


def test_las_tres_funciones_tienen_la_misma_firma():
    firmas = [list(inspect.signature(f).parameters) for f in FUNCIONES]
    assert firmas[0] == firmas[1] == firmas[2] == ["grafo", "origen", "destino", "pesos"]


