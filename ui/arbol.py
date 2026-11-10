"""Módulo de extracción y renderizado jerárquico del Árbol de Búsqueda.

Responsabilidad del Dev B: extrae las relaciones padre-hijo durante la ejecución
de A*, Dijkstra o BFS y genera el diagrama visual de árbol con f(n) = g(n) + h(n).
"""

from __future__ import annotations

import heapq
import math
from collections import deque
from dataclasses import dataclass, field
from itertools import count
from typing import Any, Callable

import matplotlib.pyplot as plt

from core.heuristicas import crear_heuristica, heuristica_cero
from core.problema import Problema
from core.tipos import Estado, Pesos
from ui.mapa import formatear_nombre_nodo


@dataclass
class NodoArbol:
    """Representa un nodo dentro del árbol de exploración de búsqueda."""
    id: str
    estado: Estado
    padre_id: str | None = None
    g: float = 0.0
    h: float = 0.0
    f: float = 0.0
    profundidad: int = 0
    es_solucion: bool = False
    cerrado: bool = False
    x: float = 0.0
    y: float = 0.0


@dataclass
class PasoExploracion:
    """Captura el estado completo de la búsqueda en una iteración específica del algoritmo."""
    num_paso: int
    nodo_actual: str
    estado_actual: Estado
    g: float
    h: float
    f: float
    nodos_cerrados: set[str] = field(default_factory=set)
    nodos_frontera: set[str] = field(default_factory=set)
    aristas_exploradas: list[tuple[str, str]] = field(default_factory=list)
    sucesores_generados: list[str] = field(default_factory=list)
    es_meta: bool = False


def extraer_arbol_y_pasos(
    grafo: Any,
    origen: str,
    destino: str,
    pesos: Pesos,
    algoritmo: str = "A*",
    max_nodos: int = 50,
) -> tuple[dict[str, NodoArbol], str | None, list[PasoExploracion]]:
    """Ejecuta la búsqueda registrando la jerarquía de árbol y los pasos de exploración."""
    p = Problema(grafo, origen, destino, pesos)
    es_astar = "A*" in algoritmo
    es_dijkstra = "Dijkstra" in algoritmo
    es_bfs = "BFS" in algoritmo

    if es_astar:
        h_func = crear_heuristica(grafo, destino, pesos)
    else:
        h_func = heuristica_cero(grafo, destino, pesos)

    inicial = p.estado_inicial
    raiz_id = f"{inicial.nodo}_{inicial.ruta}"
    h_ini = h_func(inicial) if (es_astar or es_dijkstra) else 0.0

    nodos_dict: dict[str, NodoArbol] = {
        raiz_id: NodoArbol(
            id=raiz_id,
            estado=inicial,
            padre_id=None,
            g=0.0,
            h=h_ini,
            f=h_ini,
            profundidad=0,
        )
    }

    pasos: list[PasoExploracion] = []
    # Paso 0: Nodo inicial listo en la frontera
    pasos.append(
        PasoExploracion(
            num_paso=0,
            nodo_actual=inicial.nodo,
            estado_actual=inicial,
            g=0.0,
            h=h_ini,
            f=h_ini,
            nodos_cerrados=set(),
            nodos_frontera={inicial.nodo},
            aristas_exploradas=[],
            sucesores_generados=[],
            es_meta=p.es_meta(inicial),
        )
    )

    aristas_arbol: list[tuple[str, str]] = []
    meta_id: str | None = None

    if es_bfs:
        cola = deque([(inicial, raiz_id, 0.0)])
        visitados_bfs = {inicial}
        cerrados_bfs: set[Estado] = set()

        while cola and len(nodos_dict) < max_nodos:
            e, eid, g_val = cola.popleft()
            cerrados_bfs.add(e)
            if eid in nodos_dict:
                nodos_dict[eid].cerrado = True

            es_meta = p.es_meta(e)
            nodos_en_frontera = {item[0].nodo for item in cola}
            nodos_cerrados = {item.nodo for item in cerrados_bfs}

            if es_meta:
                meta_id = eid
                pasos.append(
                    PasoExploracion(
                        num_paso=len(pasos),
                        nodo_actual=e.nodo,
                        estado_actual=e,
                        g=g_val,
                        h=0.0,
                        f=g_val,
                        nodos_cerrados=set(nodos_cerrados),
                        nodos_frontera=set(nodos_en_frontera),
                        aristas_exploradas=list(aristas_arbol),
                        sucesores_generados=[],
                        es_meta=True,
                    )
                )
                break

            padre_nodo = nodos_dict[eid]
            sucesores_nombres = []

            for accion in p.sucesores(e):
                s = accion.destino
                if s not in visitados_bfs:
                    visitados_bfs.add(s)
                    s_id = f"{s.nodo}_{s.ruta}"
                    costo_s = g_val + 1.0
                    nodos_dict[s_id] = NodoArbol(
                        id=s_id,
                        estado=s,
                        padre_id=eid,
                        g=costo_s,
                        h=0.0,
                        f=costo_s,
                        profundidad=padre_nodo.profundidad + 1,
                    )
                    cola.append((s, s_id, costo_s))
                    aristas_arbol.append((e.nodo, s.nodo))
                    sucesores_nombres.append(s.nodo)

            pasos.append(
                PasoExploracion(
                    num_paso=len(pasos),
                    nodo_actual=e.nodo,
                    estado_actual=e,
                    g=g_val,
                    h=0.0,
                    f=g_val,
                    nodos_cerrados=set(nodos_cerrados),
                    nodos_frontera={item[0].nodo for item in cola},
                    aristas_exploradas=list(aristas_arbol),
                    sucesores_generados=sucesores_nombres,
                    es_meta=False,
                )
            )
    else:
        desempate = count()
        frontera = [(h_ini, next(desempate), inicial, raiz_id)]
        cerrados: set[Estado] = set()
        g_map: dict[Estado, float] = {inicial: 0.0}

        while frontera and len(nodos_dict) < max_nodos:
            f_val, _, e, eid = heapq.heappop(frontera)
            if e in cerrados:
                continue

            es_meta = p.es_meta(e)
            cerrados.add(e)
            if eid in nodos_dict:
                nodos_dict[eid].cerrado = True

            nodos_en_frontera = {item[2].nodo for item in frontera}
            nodos_cerrados = {item.nodo for item in cerrados}

            if es_meta:
                meta_id = eid
                pasos.append(
                    PasoExploracion(
                        num_paso=len(pasos),
                        nodo_actual=e.nodo,
                        estado_actual=e,
                        g=g_map.get(e, 0.0),
                        h=h_func(e),
                        f=f_val,
                        nodos_cerrados=set(nodos_cerrados),
                        nodos_frontera=set(nodos_en_frontera),
                        aristas_exploradas=list(aristas_arbol),
                        sucesores_generados=[],
                        es_meta=True,
                    )
                )
                break

            padre_nodo = nodos_dict[eid]
            sucesores_nombres = []

            for accion in p.sucesores(e):
                s = accion.destino
                costo_s = g_map[e] + p.costo(accion)

                if costo_s < g_map.get(s, math.inf):
                    g_map[s] = costo_s
                    s_id = f"{s.nodo}_{s.ruta}"
                    h_s = h_func(s) if (es_astar or es_dijkstra) else 0.0
                    f_s = costo_s + h_s

                    nodos_dict[s_id] = NodoArbol(
                        id=s_id,
                        estado=s,
                        padre_id=eid,
                        g=costo_s,
                        h=h_s,
                        f=f_s,
                        profundidad=padre_nodo.profundidad + 1,
                    )
                    heapq.heappush(frontera, (f_s, next(desempate), s, s_id))
                    aristas_arbol.append((e.nodo, s.nodo))
                    sucesores_nombres.append(s.nodo)

            pasos.append(
                PasoExploracion(
                    num_paso=len(pasos),
                    nodo_actual=e.nodo,
                    estado_actual=e,
                    g=g_map.get(e, 0.0),
                    h=h_func(e),
                    f=f_val,
                    nodos_cerrados=set(nodos_cerrados),
                    nodos_frontera={item[2].nodo for item in frontera},
                    aristas_exploradas=list(aristas_arbol),
                    sucesores_generados=sucesores_nombres,
                    es_meta=False,
                )
            )

    # Marcar la rama de solución ganadora hacia atrás
    if meta_id:
        actual: str | None = meta_id
        while actual:
            if actual in nodos_dict:
                nodos_dict[actual].es_solucion = True
                actual = nodos_dict[actual].padre_id
            else:
                break

    return nodos_dict, raiz_id, pasos


def extraer_arbol_busqueda(
    grafo: Any,
    origen: str,
    destino: str,
    pesos: Pesos,
    algoritmo: str = "A*",
    max_nodos: int = 40,
) -> tuple[dict[str, NodoArbol], str | None]:
    """Ejecuta la búsqueda registrando la estructura del árbol, costos y rama ganadora."""
    nodos_dict, raiz_id, _ = extraer_arbol_y_pasos(grafo, origen, destino, pesos, algoritmo, max_nodos)
    return nodos_dict, raiz_id


def calcular_posiciones_arbol(nodos: dict[str, NodoArbol], raiz_id: str) -> None:
    """Asigna coordenadas (x, y) en layout jerárquico centrado por niveles."""
    if not nodos or raiz_id not in nodos:
        return

    # Agrupar nodos por nivel de profundidad
    niveles: dict[int, list[str]] = {}
    for nid, nodo in nodos.items():
        prof = nodo.profundidad
        niveles.setdefault(prof, []).append(nid)

    # Ordenar cada nivel: primero los nodos de la solución, luego por id
    for prof, lista_nids in niveles.items():
        lista_nids.sort(key=lambda x: (not nodos[x].es_solucion, nodos[x].f))

    # Asignar coordenadas
    espacio_y = 120.0
    for prof, lista_nids in niveles.items():
        y_val = -prof * espacio_y
        total_en_nivel = len(lista_nids)
        ancho_nivel = (total_en_nivel - 1) * 160.0
        x_inicio = -ancho_nivel / 2.0

        for idx, nid in enumerate(lista_nids):
            nodos[nid].x = x_inicio + idx * 160.0
            nodos[nid].y = y_val


def dibujar_arbol_en_axes(
    ax: plt.Axes,
    nodos: dict[str, NodoArbol],
    raiz_id: str | None,
    algoritmo: str = "A*",
) -> None:
    """Dibuja el árbol jerárquico sobre un eje Matplotlib con estilos, etiquetas y ramas."""
    ax.clear()
    if not nodos or not raiz_id or raiz_id not in nodos:
        ax.text(0.5, 0.5, "Seleccione origen y destino y calcule una ruta\npara generar el árbol de búsqueda.",
                fontsize=11, ha="center", va="center", color="#78909c", transform=ax.transAxes)
        ax.axis("off")
        return

    calcular_posiciones_arbol(nodos, raiz_id)

    # 1. Dibujar aristas entre padres e hijos
    for nid, nodo in nodos.items():
        if nodo.padre_id and nodo.padre_id in nodos:
            padre = nodos[nodo.padre_id]
            es_rama_solucion = nodo.es_solucion and padre.es_solucion

            if es_rama_solucion:
                ax.plot([padre.x, nodo.x], [padre.y, nodo.y], color="#2e7d32", linewidth=3.2, zorder=3)
            else:
                ax.plot([padre.x, nodo.x], [padre.y, nodo.y], color="#cfd8dc", linestyle="--", linewidth=1.2, zorder=1)

    # 2. Dibujar nodos con cajas de información (Estado, g, h, f)
    for nid, nodo in nodos.items():
        nombre = formatear_nombre_nodo(nodo.estado.nodo)
        modo = nodo.estado.ruta if nodo.estado.ruta != "CAMINANDO" else "A pie"

        if nodo.es_solucion:
            color_fondo = "#e8f5e9"
            color_borde = "#2e7d32"
            grosor = 2.0
            zorder = 8
            etiqueta_estado = "[META]" if (nodo.profundidad > 0 and not any(h.padre_id == nid and h.es_solucion for h in nodos.values())) else ("[ORIGEN]" if nodo.profundidad == 0 else "[SOLUCION]")
        elif nodo.cerrado:
            color_fondo = "#e3f2fd"
            color_borde = "#1565c0"
            grosor = 1.0
            zorder = 5
            etiqueta_estado = "[EXPANDIDO]"
        else:
            color_fondo = "#fffde7"
            color_borde = "#fbc02d"
            grosor = 0.8
            zorder = 4
            etiqueta_estado = "[FRONTERA]"

        texto = f"{etiqueta_estado} {nombre}\n[{modo}]\ng={nodo.g:.1f} | h={nodo.h:.1f}\nf={nodo.f:.1f}"

        ax.text(
            nodo.x,
            nodo.y,
            texto,
            fontsize=7.2,
            fontweight="bold" if nodo.es_solucion else "normal",
            ha="center",
            va="center",
            zorder=zorder,
            bbox=dict(
                boxstyle="round,pad=0.3",
                facecolor=color_fondo,
                edgecolor=color_borde,
                linewidth=grosor,
                alpha=0.95,
            ),
        )

    # Ajustes estéticos del árbol
    ax.set_title(f"Árbol de Búsqueda {algoritmo} — Jerarquía de Exploración y Evaluación f(n) = g(n) + h(n)",
                 fontsize=11, fontweight="bold", pad=12)
    ax.axis("off")

    # Ajustar límites con margen
    todas_x = [n.x for n in nodos.values()]
    todas_y = [n.y for n in nodos.values()]
    if todas_x and todas_y:
        margen_x = max(80.0, (max(todas_x) - min(todas_x)) * 0.1)
        margen_y = max(60.0, (max(todas_y) - min(todas_y)) * 0.1)
        ax.set_xlim(min(todas_x) - margen_x, max(todas_x) + margen_x)
        ax.set_ylim(min(todas_y) - margen_y, max(todas_y) + margen_y)
