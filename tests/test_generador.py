"""Pruebas del generador de ciudades sintéticas."""
import math

import pytest

from datos.generador_sintetico import (ciudad_como_dict, generar_ciudad,
                                       guardar_ciudad, pares_aleatorios)
from datos.cargador import cargar_mapa


def _conexo(g) -> bool:
    inicio = next(iter(g.nodos))
    vistos, pila = {inicio}, [inicio]
    while pila:
        for v in g.vecinos(pila.pop()):
            if v.nodo not in vistos:
                vistos.add(v.nodo)
                pila.append(v.nodo)
    return len(vistos) == g.num_nodos


@pytest.mark.parametrize("n,lado", [(100, 10), (500, 22), (1000, 32)])
def test_tamano_es_una_cuadricula(n, lado):
    assert generar_ciudad(n).num_nodos == lado * lado


@pytest.mark.parametrize("n", [16, 100, 500])
def test_es_conexa(n):
    assert _conexo(generar_ciudad(n, semilla=3))


def test_misma_semilla_misma_ciudad():
    assert ciudad_como_dict(200, semilla=7) == ciudad_como_dict(200, semilla=7)


def test_distinta_semilla_distinta_ciudad():
    assert ciudad_como_dict(200, semilla=1) != ciudad_como_dict(200, semilla=2)


def test_hay_ciclos_y_costos_variables():
    g = generar_ciudad(100)
    distancias = {t.distancia_m for t in g.tramos}
    assert len(distancias) > 1
    lado = 10
    assert len(g.tramos) == 2 * lado * (lado - 1)        


def test_toda_calle_cumple_distancia_mayor_o_igual_a_la_recta():
    g = generar_ciudad(300, semilla=5)
    for t in g.tramos:
        assert t.distancia_m >= g.distancia_recta(t.de, t.a) - 1e-9


def test_hay_transbordo_posible():
    for semilla in range(5):
        g = generar_ciudad(100, semilla=semilla)
        assert any(len(g.rutas_en(n)) > 1 for n in g.nodos)


def test_numero_de_rutas_por_defecto_y_explicito():
    assert len(generar_ciudad(100).rutas) == 2
    assert len(generar_ciudad(2500).rutas) == 10
    assert len(generar_ciudad(2500, n_rutas=4).rutas) == 4


def test_cantidad_de_estados_sigue_la_formula():
    g = generar_ciudad(400, semilla=2)
    assert g.num_estados == g.num_nodos + sum(len(r.paradas) for r in g.rutas.values())


def test_hay_escaleras_con_probabilidad_alta():
    g = generar_ciudad(400, prob_escalera=0.5, prob_dificil=0.0)
    assert any(t.tipo == "escalera" and t.penalizacion > 0 for t in g.tramos)


def test_sin_escaleras_si_la_probabilidad_es_cero():
    g = generar_ciudad(400, prob_escalera=0.0, prob_dificil=0.0)
    assert all(t.penalizacion == 0 for t in g.tramos)


def test_las_rutas_no_repiten_paradas():
    g = generar_ciudad(900, semilla=4)
    for r in g.rutas.values():
        assert len(set(r.paradas)) == len(r.paradas) >= 2
        assert len(r.tiempos_min) == len(r.paradas) - 1


@pytest.mark.parametrize("kwargs", [
    {"n_nodos": 4},
    {"n_nodos": 100, "salto_paradas": 0},
    {"n_nodos": 100, "espaciado_m": 0},
    {"n_nodos": 100, "prob_escalera": 0.8, "prob_dificil": 0.5},
])
def test_parametros_invalidos(kwargs):
    with pytest.raises(ValueError):
        ciudad_como_dict(**kwargs)


def test_guardar_y_recargar(tmp_path):
    guardar_ciudad(100, tmp_path / "ciudad.json", semilla=1)
    g = cargar_mapa(tmp_path / "ciudad.json")
    assert g.num_nodos == 100 and len(g.rutas) == 2


def test_pares_aleatorios():
    g = generar_ciudad(100)
    pares = pares_aleatorios(g, 20, semilla=1)
    assert len(pares) == 20
    assert all(o != d and o in g.nodos and d in g.nodos for o, d in pares)
    assert pares == pares_aleatorios(g, 20, semilla=1)


def test_ciudad_grande_se_construye():
    assert generar_ciudad(10_000).num_nodos == 10_000