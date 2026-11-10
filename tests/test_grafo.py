import pytest

from core.grafo import (
    VELOCIDAD_CAMINATA_M_MIN, ErrorMapa, Grafo, Nodo, RutaTransporte, Tramo,
)
from datos.cargador import cargar_mapa

A, B, C = Nodo("A", 0, 0), Nodo("B", 300, 400), Nodo("C", 600, 0)    


def grafo_base():
    tramos = [Tramo("A", "B", 500), Tramo("B", "C", 500, penalizacion=4, tipo="escalera")]
    rutas = [RutaTransporte("R1", 10.0, 2.0, ("A", "B", "C"), (1.0, 1.0))]
    return Grafo([A, B, C], tramos, rutas)


 
def test_cuenta_nodos_y_estados():
    g = grafo_base()
    assert g.num_nodos == 3
    assert g.num_estados == 3 + 3         


def test_tramo_bidireccional_por_defecto():
    g = grafo_base()
    assert {v.nodo for v in g.vecinos("A")} == {"B"}
    assert {v.nodo for v in g.vecinos("B")} == {"A", "C"}


def test_tramo_de_un_solo_sentido():
    g = Grafo([A, B], [Tramo("A", "B", 500, bidireccional=False)], [])
    assert [v.nodo for v in g.vecinos("A")] == ["B"]
    assert g.vecinos("B") == []


def test_vecino_conserva_penalizacion_y_tipo():
    v = [x for x in grafo_base().vecinos("C") if x.nodo == "B"][0]
    assert (v.distancia_m, v.penalizacion, v.tipo) == (500, 4, "escalera")


def test_rutas_en_y_siguiente_parada():
    g = grafo_base()
    assert [r.id for r in g.rutas_en("B")] == ["R1"]
    assert g.siguiente_parada("R1", "A") == ("B", 1.0)
    assert g.siguiente_parada("R1", "C") is None       
    assert g.siguiente_parada("R1", "Z") is None


def test_la_ruta_es_de_un_solo_sentido():
    g = grafo_base()
    assert g.siguiente_parada("R1", "B") == ("C", 1.0)
    assert g.siguiente_parada("R1", "C") is None      


def test_tiempo_de_caminata():
    assert Grafo.tiempo_caminata(160) == 160 / VELOCIDAD_CAMINATA_M_MIN


def test_distancia_recta():
    assert grafo_base().distancia_recta("A", "B") == 500


 
def test_tramo_mas_corto_que_la_recta_se_rechaza():
    with pytest.raises(ErrorMapa, match="línea recta"):
        Grafo([A, B], [Tramo("A", "B", 499)], [])


def test_tramo_igual_a_la_recta_se_acepta():
    Grafo([A, B], [Tramo("A", "B", 500)], [])


 
def test_nodo_duplicado():
    with pytest.raises(ErrorMapa, match="duplicado"):
        Grafo([A, Nodo("A", 5, 5)], [], [])


@pytest.mark.parametrize("tramo, mensaje", [
    (Tramo("A", "Z", 500), "inexistente"),
    (Tramo("A", "A", 500), "consigo mismo"),
    (Tramo("A", "B", 0), "distancia inválida"),
    (Tramo("A", "B", -5), "distancia inválida"),
    (Tramo("A", "B", 500, penalizacion=-1), "penalización negativa"),
    (Tramo("A", "B", float("nan")), "distancia inválida"),
])
def test_tramos_invalidos(tramo, mensaje):
    with pytest.raises(ErrorMapa, match=mensaje):
        Grafo([A, B], [tramo], [])


 
def ruta(**cambios):
    base = dict(id="R1", tarifa=10.0, espera_min=2.0, paradas=("A", "B"), tiempos_min=(1.0,))
    base.update(cambios)
    return RutaTransporte(**base)


@pytest.mark.parametrize("cambios, mensaje", [
    (dict(id="CAMINANDO"), "reservado"),
    (dict(paradas=("A",), tiempos_min=()), "al menos 2 paradas"),
    (dict(paradas=("A", "B", "A"), tiempos_min=(1.0, 1.0)), "repite paradas"),
    (dict(paradas=("A", "Z"), tiempos_min=(1.0,)), "parada inexistente"),
    (dict(tiempos_min=(1.0, 2.0)), "debe haber exactamente 1"),
    (dict(tiempos_min=(0.0,)), "no positivo"),
    (dict(tiempos_min=(-1.0,)), "no positivo"),
    (dict(tarifa=-1.0), "tarifa inválida"),
    (dict(espera_min=-1.0), "espera inválida"),
    (dict(tiempos_min=(0.1,)), "poco realista"),      
])
def test_rutas_invalidas(cambios, mensaje):
    with pytest.raises(ErrorMapa, match=mensaje):
        Grafo([A, B], [], [ruta(**cambios)])


def test_ruta_duplicada():
    with pytest.raises(ErrorMapa, match="duplicada"):
        Grafo([A, B], [], [ruta(), ruta()])



def test_velocidad_max_es_la_de_caminata_si_el_transporte_es_mas_lento():
    lento = ruta(tiempos_min=(100.0,))                
    assert Grafo([A, B], [], [lento]).velocidad_max_m_min == VELOCIDAD_CAMINATA_M_MIN


def test_velocidad_max_toma_la_del_transporte_mas_rapido():
    g = Grafo([A, B], [], [ruta(tiempos_min=(2.5,))])   
    assert g.velocidad_max_m_min == 200.0


 
    """tiempo real de cada acción >= distancia recta / v_max (admisibilidad de h)."""
    g = cargar_mapa("datos/mapa_ejemplo.json")
    for t in g.tramos:
        recta = g.distancia_recta(t.de, t.a)
        assert Grafo.tiempo_caminata(t.distancia_m) >= recta / g.velocidad_max_m_min - 1e-9
    for r in g.rutas.values():
        for i, tiempo in enumerate(r.tiempos_min):
            recta = g.distancia_recta(r.paradas[i], r.paradas[i + 1])
            assert tiempo >= recta / g.velocidad_max_m_min - 1e-9