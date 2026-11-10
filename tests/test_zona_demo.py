"""Pruebas de los datos reales: zona_demo.json + rutas_transporte.json."""
from pathlib import Path

import pytest

from datos.cargador import cargar_mapa

DATOS = Path(__file__).resolve().parent.parent / "datos"


@pytest.fixture(scope="module")
def g():
    return cargar_mapa(DATOS / "zona_demo.json")


def test_tamano_del_mapa(g):
    assert 40 <= g.num_nodos <= 100


def test_tiene_de_2_a_4_rutas(g):
    assert 2 <= len(g.rutas) <= 4


def test_hay_transbordo_posible(g):
    assert any(len(g.rutas_en(n)) > 1 for n in g.nodos)


def test_el_mapa_es_conexo_caminando(g):
    inicio = next(iter(g.nodos))
    vistos, pila = {inicio}, [inicio]
    while pila:
        for v in g.vecinos(pila.pop()):
            if v.nodo not in vistos:
                vistos.add(v.nodo)
                pila.append(v.nodo)
    assert vistos == set(g.nodos), f"aislados: {sorted(set(g.nodos) - vistos)}"


def test_hay_escaleras_y_rampas(g):
    tipos = {t.tipo for t in g.tramos}
    assert "escalera" in tipos and "rampa" in tipos


def test_toda_parada_tiene_calle(g):
    for r in g.rutas.values():
        for p in r.paradas:
            assert g.vecinos(p), f"la parada {p} no tiene calles"