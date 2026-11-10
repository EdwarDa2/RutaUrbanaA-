import pytest

from core.grafo import Grafo, Nodo, RutaTransporte, Tramo
from core.problema import Problema, costo_de, desglose_de
from core.tipos import CAMINANDO, CLAVES_DESGLOSE, Estado, Pesos, TipoAccion
from datos.cargador import cargar_mapa


@pytest.fixture(scope="module")
def mapa():
    return cargar_mapa("datos/mapa_ejemplo.json")


@pytest.fixture
def prob(mapa):
    return Problema(mapa, "entrada", "mercado", Pesos())


def por_tipo(acciones, tipo):
    return [a for a in acciones if a.tipo is tipo]


def destinos(acciones):
    return {a.destino for a in acciones}


 
def test_estado_inicial_es_el_origen_caminando(prob):
    assert prob.estado_inicial == Estado("entrada", CAMINANDO)


def test_meta_es_el_nodo_destino_en_cualquier_ruta(prob):
    assert prob.es_meta(Estado("mercado"))
    assert prob.es_meta(Estado("mercado", "R1"))
    assert not prob.es_meta(Estado("plaza"))


@pytest.mark.parametrize("origen, destino", [("nada", "mercado"), ("entrada", "nada")])
def test_nodos_inexistentes_lanzan_error(mapa, origen, destino):
    with pytest.raises(ValueError, match="no existe"):
        Problema(mapa, origen, destino, Pesos())


 
def test_desde_un_nodo_sin_parada_solo_se_camina(prob):
    acciones = prob.sucesores(Estado("entrada"))
    assert {a.tipo for a in acciones} == {TipoAccion.CAMINAR}
    assert destinos(acciones) == {Estado("biblioteca"), Estado("rampa")}


def test_caminar_calcula_tiempo_y_penalizacion(prob):
    escalera = [a for a in prob.sucesores(Estado("entrada"))
                if a.destino.nodo == "biblioteca"][0]
    assert escalera.tiempo_min == 200 / 80
    assert escalera.penalizacion == 6
    assert escalera.dinero == 0 and escalera.abordaje == 0


def test_se_puede_bajar_y_caminar_desde_una_ruta(prob):
    acciones = prob.sucesores(Estado("parada_centro", "R1"))
    caminar = por_tipo(acciones, TipoAccion.CAMINAR)
    assert {a.destino for a in caminar} == {
        Estado("parada_norte"), Estado("cafeteria"), Estado("mercado")}


def test_los_tramos_de_un_solo_sentido_se_respetan():
    nodos = [Nodo("A", 0, 0), Nodo("B", 100, 0)]
    g = Grafo(nodos, [Tramo("A", "B", 100, bidireccional=False)], [])
    p = Problema(g, "A", "B", Pesos())
    assert destinos(p.sucesores(Estado("A"))) == {Estado("B")}
    assert p.sucesores(Estado("B")) == []


 
def test_abordar_cobra_espera_tarifa_y_abordaje(prob):
    abordar = por_tipo(prob.sucesores(Estado("parada_norte")), TipoAccion.ABORDAR)
    assert len(abordar) == 1
    a = abordar[0]
    assert a.destino == Estado("parada_norte", "R1")
    assert (a.tiempo_min, a.dinero, a.abordaje) == (2.0, 10.0, 1)


def test_en_un_nodo_con_dos_rutas_se_puede_abordar_cualquiera(prob):
    abordar = por_tipo(prob.sucesores(Estado("parada_centro")), TipoAccion.ABORDAR)
    assert destinos(abordar) == {Estado("parada_centro", "R1"), Estado("parada_centro", "R2")}


def test_no_se_aborda_en_la_ultima_parada(prob):
     
    assert por_tipo(prob.sucesores(Estado("mercado")), TipoAccion.ABORDAR) == []
    assert por_tipo(prob.sucesores(Estado("clinica")), TipoAccion.ABORDAR) == []


def test_ir_caminando_no_permite_continuar_ni_transbordar(prob):
    acciones = prob.sucesores(Estado("parada_centro"))
    assert por_tipo(acciones, TipoAccion.CONTINUAR) == []
    assert por_tipo(acciones, TipoAccion.TRANSBORDAR) == []

 
def test_continuar_va_a_la_siguiente_parada(prob):
    cont = por_tipo(prob.sucesores(Estado("parada_norte", "R1")), TipoAccion.CONTINUAR)
    assert len(cont) == 1
    assert cont[0].destino == Estado("parada_centro", "R1")
    assert cont[0].tiempo_min == 1.0
    assert (cont[0].dinero, cont[0].abordaje) == (0, 0)


def test_en_la_ultima_parada_no_se_puede_continuar(prob):
    assert por_tipo(prob.sucesores(Estado("mercado", "R1")), TipoAccion.CONTINUAR) == []

 
def test_transbordar_cobra_de_nuevo_espera_tarifa_y_abordaje(prob):
    trans = por_tipo(prob.sucesores(Estado("parada_centro", "R1")), TipoAccion.TRANSBORDAR)
    assert len(trans) == 1
    t = trans[0]
    assert t.destino == Estado("parada_centro", "R2")
    assert (t.tiempo_min, t.dinero, t.abordaje) == (3.0, 10.0, 1)


def test_no_hay_transbordo_donde_solo_pasa_una_ruta(prob):
    assert por_tipo(prob.sucesores(Estado("parada_norte", "R1")), TipoAccion.TRANSBORDAR) == []


def test_no_se_transborda_a_una_ruta_en_su_ultima_parada():
    nodos = [Nodo("A", 0, 0), Nodo("B", 200, 0), Nodo("C", 400, 0)]
    r1 = RutaTransporte("R1", 5, 1, ("A", "B"), (1.0,))
    r2 = RutaTransporte("R2", 5, 1, ("C", "B"), (1.0,))       
    p = Problema(Grafo(nodos, [], [r1, r2]), "A", "B", Pesos())
    assert por_tipo(p.sucesores(Estado("B", "R1")), TipoAccion.TRANSBORDAR) == []


 
def alcanzables(problema):
    vistos, pendientes = {problema.estado_inicial}, [problema.estado_inicial]
    while pendientes:
        for a in problema.sucesores(pendientes.pop()):
            if a.destino not in vistos:
                vistos.add(a.destino)
                pendientes.append(a.destino)
    return vistos


def test_los_estados_alcanzables_coinciden_con_la_formula_de_la_ficha(mapa, prob):
    assert len(alcanzables(prob)) == mapa.num_estados == 16


def test_toda_accion_parte_del_estado_consultado_y_tiene_costo_no_negativo(mapa, prob):
    for estado in alcanzables(prob):
        for a in prob.sucesores(estado):
            assert a.origen == estado
            assert prob.costo(a) >= 0


def test_cada_accion_cuesta_al_menos_la_distancia_recta_entre_v_max(mapa, prob):
    """Admisibilidad de h, verificada sobre TODAS las acciones del espacio de estados."""
    for estado in alcanzables(prob):
        for a in prob.sucesores(estado):
            recta = mapa.distancia_recta(a.origen.nodo, a.destino.nodo)
            assert a.tiempo_min >= recta / mapa.velocidad_max_m_min - 1e-9


 
def trayecto(prob):
    """entrada -> rampa -> biblioteca -> parada_norte, abordar R1, ir a parada_centro."""
    est = [Estado("entrada"), Estado("rampa"), Estado("biblioteca"), Estado("parada_norte"),
           Estado("parada_norte", "R1"), Estado("parada_centro", "R1")]
    acciones = []
    for origen, destino in zip(est, est[1:]):
        acciones.append(next(a for a in prob.sucesores(origen) if a.destino == destino))
    return acciones


def test_desglose_suma_cada_componente(prob):
    d = desglose_de(trayecto(prob))
    assert set(d) == set(CLAVES_DESGLOSE)
    assert d["tiempo"] == pytest.approx(140 / 80 + 140 / 80 + 160 / 80 + 2.0 + 1.0)
    assert d["dinero"] == 10.0
    assert d["abordajes"] == 1
    assert d["penalizacion"] == 0


def test_costo_total_pondera_el_desglose(prob):
    pesos = Pesos(tiempo=1, dinero=2, abordaje=5)
    d = desglose_de(trayecto(prob))
    esperado = d["tiempo"] + 2 * d["dinero"] + 5 * d["abordajes"]
    assert costo_de(trayecto(prob), pesos) == pytest.approx(esperado)