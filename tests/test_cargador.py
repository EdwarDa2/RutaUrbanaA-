import json

import pytest

from core.grafo import ErrorMapa
from datos.cargador import cargar_mapa, grafo_desde_dict

MINIMO = {
    "nodos": [{"id": "A", "x": 0, "y": 0}, {"id": "B", "x": 300, "y": 400}],
    "tramos": [{"de": "A", "a": "B", "distancia_m": 500}],
}


def guardar(tmp_path, datos, nombre="mapa.json"):
    ruta = tmp_path / nombre
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    return ruta


# ---------- mapa de ejemplo ----------
def test_el_mapa_de_ejemplo_carga_completo():
    g = cargar_mapa("datos/mapa_ejemplo.json")
    assert g.num_nodos == 10
    assert len(g.tramos) == 13
    assert set(g.rutas) == {"R1", "R2"}
    assert g.num_estados == 16
    assert g.velocidad_max_m_min == 200.0


def test_el_mapa_de_ejemplo_tiene_escalera_y_rampa():
    g = cargar_mapa("datos/mapa_ejemplo.json")
    tipos = {t.tipo: t.penalizacion for t in g.tramos}
    assert tipos["escalera"] > 0
    assert tipos["rampa"] == 0


def test_hay_un_transbordo_posible_en_el_mapa_de_ejemplo():
    g = cargar_mapa("datos/mapa_ejemplo.json")
    comunes = {p for p in g.rutas["R1"].paradas} & {p for p in g.rutas["R2"].paradas}
    assert comunes == {"parada_centro"}


# ---------- valores por defecto ----------
def test_valores_por_defecto(tmp_path):
    g = cargar_mapa(guardar(tmp_path, MINIMO))
    t = g.tramos[0]
    assert (t.penalizacion, t.tipo, t.bidireccional) == (0.0, "calle", True)
    assert g.rutas == {}                      # 'rutas' es opcional


# ---------- errores con mensaje claro ----------
def copia():
    return json.loads(json.dumps(MINIMO))


@pytest.mark.parametrize("seccion, indice, campo, mensaje", [
    ("nodos", 0, "id", r"Falta el campo 'id' en nodos\[0\]"),
    ("nodos", 1, "x", r"Falta el campo 'x' en nodos\[1\]"),
    ("tramos", 0, "distancia_m", r"Falta el campo 'distancia_m' en tramos\[0\]"),
])
def test_campos_faltantes(seccion, indice, campo, mensaje):
    datos = copia()
    del datos[seccion][indice][campo]
    with pytest.raises(ErrorMapa, match=mensaje):
        grafo_desde_dict(datos)


def test_seccion_faltante():
    with pytest.raises(ErrorMapa, match="Falta el campo 'tramos'"):
        grafo_desde_dict({"nodos": []})


def test_tipo_incorrecto_de_un_numero():
    datos = copia()
    datos["nodos"][0]["x"] = "cien"
    with pytest.raises(ErrorMapa, match="debe ser un número"):
        grafo_desde_dict(datos)


def test_un_booleano_no_cuenta_como_numero():
    datos = copia()
    datos["nodos"][0]["x"] = True
    with pytest.raises(ErrorMapa, match="debe ser un número"):
        grafo_desde_dict(datos)


def test_seccion_que_no_es_lista():
    datos = copia()
    datos["nodos"] = {"id": "A"}
    with pytest.raises(ErrorMapa, match="debe ser una lista"):
        grafo_desde_dict(datos)


def test_las_reglas_del_grafo_tambien_se_aplican_al_cargar():
    datos = copia()
    datos["tramos"][0]["distancia_m"] = 100        # menor que la recta (500)
    with pytest.raises(ErrorMapa, match="línea recta"):
        grafo_desde_dict(datos)


def test_json_mal_formado(tmp_path):
    ruta = tmp_path / "roto.json"
    ruta.write_text("{ esto no es json", encoding="utf-8")
    with pytest.raises(ErrorMapa, match="no es un JSON válido"):
        cargar_mapa(ruta)


def test_archivo_inexistente(tmp_path):
    with pytest.raises(FileNotFoundError):
        cargar_mapa(tmp_path / "no_existe.json")


def test_mapa_vacio_carga_un_grafo_vacio():
    g = grafo_desde_dict({"nodos": [], "tramos": []})
    assert g.num_nodos == 0