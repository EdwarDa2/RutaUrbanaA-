"""Módulo de renderizado moderno e interactivo con Plotly para Web (Streamlit).

Responsabilidad del Dev B: Genera figuras interactivas de alta fidelidad para el plano
urbano y el árbol jerárquico de IA con separación espacial optimizada y diseño profesional sin emojis.
"""

from __future__ import annotations

import math
from typing import Any
import plotly.graph_objects as go

from core.tipos import ResultadoBusqueda
from ui.arbol import NodoArbol, PasoExploracion, calcular_posiciones_arbol
from ui.mapa import ElementosMapa, formatear_nombre_nodo


# Paleta moderna ejecutiva: Deep Obsidian Navy con acentos de alto contraste
COLOR_FONDO = "#0b0f19"          # Fondo principal oscuro profundo
COLOR_PANEL = "#151d30"          # Tarjetas y paneles
COLOR_GRID = "#1a2438"           # Rejilla sutil
COLOR_CALLE = "#2a374f"          # Red peatonal base
COLOR_CAMINANDO = "#10b981"      # Verde esmeralda (tramo a pie)
COLOR_TRANSPORTE = "#3b82f6"     # Azul zafiro (tramo en transporte)
COLOR_FRONTERA = "#f59e0b"       # Ámbar (nodos en frontera)
COLOR_CERRADO = "#64748b"        # Gris acero (nodos explorados)
COLOR_ACTUAL = "#facc15"         # Oro luminoso (nodo activo / viajero)
COLOR_META = "#10b981"           # Verde esmeralda (meta alcanzada)
COLOR_ORIGEN = "#10b981"         # Verde (origen)
COLOR_DESTINO = "#f43f5e"        # Carmesí elegante (destino)

# Colores armónicos para líneas de transporte público
COLORES_RUTAS = [
    "#38bdf8",  # Azul Cielo
    "#818cf8",  # Índigo
    "#a78bfa",  # Amatista
    "#fb923c",  # Naranja Cálido
    "#2dd4bf",  # Turquesa Menta
    "#f472b6",  # Rosa
]


def transformar_coordenadas(
    posiciones: dict[str, tuple[float, float]],
    factor_y: float = 2.4,
    distancia_minima: float = 165.0,
) -> dict[str, tuple[float, float]]:
    """Aplica escala vertical y relajación elástica para separar ubicaciones cercanas en el mapa.
    
    Garantiza que ningún par de ubicaciones quede visualmente amontonado, separando
    los puntos a una distancia mínima de al menos `distancia_minima` metros sin alterar
    la orientación geográfica ni la topología de la red.
    """
    # 1. Escalar eje Y para compensar la geometría este-oeste de Tuxtla (4400m x 700m)
    pos_vis: dict[str, list[float]] = {
        nid: [float(p[0]), float(p[1]) * factor_y] for nid, p in posiciones.items()
    }

    # 2. Iteraciones de relajación por repulsión para separar puntos contiguos
    for _ in range(25):
        hubo_ajuste = False
        nodos_keys = list(pos_vis.keys())
        for i in range(len(nodos_keys)):
            n1 = nodos_keys[i]
            p1 = pos_vis[n1]
            for j in range(i + 1, len(nodos_keys)):
                n2 = nodos_keys[j]
                p2 = pos_vis[n2]
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                dist = math.hypot(dx, dy)
                if dist < distancia_minima:
                    hubo_ajuste = True
                    if dist < 0.001:
                        dx, dy = 1.0, 1.0
                        dist = 1.414
                    solapamiento = (distancia_minima - dist) * 0.45
                    ux = dx / dist
                    uy = dy / dist
                    p1[0] -= ux * solapamiento
                    p1[1] -= uy * solapamiento
                    p2[0] += ux * solapamiento
                    p2[1] += uy * solapamiento
        if not hubo_ajuste:
            break

    return {nid: (round(p[0], 2), round(p[1], 2)) for nid, p in pos_vis.items()}


def crear_figura_mapa_plotly(
    elementos: ElementosMapa,
    modo: str = "viajero",
    paso_idx: int | None = None,
    paso_exploracion: PasoExploracion | None = None,
    factor_separacion_y: float = 2.4,
) -> go.Figure:
    """Construye un mapa interactivo con Plotly, zoom fluido y separación espacial sin emojis."""
    pos_vis = transformar_coordenadas(elementos.posiciones, factor_y=factor_separacion_y, distancia_minima=165.0)
    fig = go.Figure()

    # Mapeo de coordenadas originales a coordenadas visuales transformadas
    coord_map = {elem_pos: pos_vis[nid] for nid, elem_pos in elementos.posiciones.items() if nid in pos_vis}

    # 1. Capa de Calles Peatonales (Red base de la ciudad)
    calles_x: list[float | None] = []
    calles_y: list[float | None] = []
    for p1, p2 in elementos.aristas_caminando:
        p1_v = coord_map.get(p1, (p1[0], p1[1] * factor_separacion_y))
        p2_v = coord_map.get(p2, (p2[0], p2[1] * factor_separacion_y))
        calles_x.extend([p1_v[0], p2_v[0], None])
        calles_y.extend([p1_v[1], p2_v[1], None])

    fig.add_trace(
        go.Scatter(
            x=calles_x,
            y=calles_y,
            mode="lines",
            line=dict(color=COLOR_CALLE, width=1.5, dash="dot"),
            hoverinfo="none",
            name="Red Peatonal",
            showlegend=True,
        )
    )

    # 2. Capa de Rutas de Transporte Público
    for idx, (rid, segmentos) in enumerate(elementos.aristas_transporte.items()):
        rx: list[float | None] = []
        ry: list[float | None] = []
        col = COLORES_RUTAS[idx % len(COLORES_RUTAS)]
        for p1, p2 in segmentos:
            p1_v = coord_map.get(p1, (p1[0], p1[1] * factor_separacion_y))
            p2_v = coord_map.get(p2, (p2[0], p2[1] * factor_separacion_y))
            rx.extend([p1_v[0], p2_v[0], None])
            ry.extend([p2_v[1], p2_v[1], None])
        fig.add_trace(
            go.Scatter(
                x=rx,
                y=ry,
                mode="lines",
                line=dict(color=col, width=2.8),
                opacity=0.35,
                hoverinfo="text",
                hovertext=f"Ruta de Transporte: {rid}",
                name=f"Ruta {rid}",
                showlegend=True,
            )
        )

    # 3. MODO VIAJERO: Tramos de la solución recorrida
    if modo == "viajero" and elementos.aristas_solucion:
        limite = len(elementos.aristas_solucion) if paso_idx is None else max(0, min(paso_idx, len(elementos.aristas_solucion)))
        tramos_activos = elementos.aristas_solucion[:limite]

        cam_x, cam_y = [], []
        tra_x, tra_y = [], []
        for tr in tramos_activos:
            p1 = tr["p1"]
            p2 = tr["p2"]
            p1_v = coord_map.get(p1, (p1[0], p1[1] * factor_separacion_y))
            p2_v = coord_map.get(p2, (p2[0], p2[1] * factor_separacion_y))
            if tr["tipo"] == "CAMINANDO":
                cam_x.extend([p1_v[0], p2_v[0], None])
                cam_y.extend([p1_v[1], p2_v[1], None])
            else:
                tra_x.extend([p1_v[0], p2_v[0], None])
                tra_y.extend([p1_v[1], p2_v[1], None])

        if cam_x:
            fig.add_trace(
                go.Scatter(
                    x=cam_x,
                    y=cam_y,
                    mode="lines",
                    line=dict(color=COLOR_CAMINANDO, width=5.5),
                    name="Tramo a Pie",
                    hoverinfo="text",
                    hovertext="Caminando",
                )
            )
        if tra_x:
            fig.add_trace(
                go.Scatter(
                    x=tra_x,
                    y=tra_y,
                    mode="lines",
                    line=dict(color=COLOR_TRANSPORTE, width=5.5),
                    name="Tramo en Transporte",
                    hoverinfo="text",
                    hovertext="Transporte Público",
                )
            )

    # 4. MODO BÚSQUEDA IA: Ramas exploradas por el algoritmo
    if modo == "exploracion" and paso_exploracion:
        exp_x, exp_y = [], []
        for de_id, a_id in paso_exploracion.aristas_exploradas:
            if de_id in pos_vis and a_id in pos_vis:
                p1 = pos_vis[de_id]
                p2 = pos_vis[a_id]
                exp_x.extend([p1[0], p2[0], None])
                exp_y.extend([p1[1], p2[1], None])

        if exp_x:
            fig.add_trace(
                go.Scatter(
                    x=exp_x,
                    y=exp_y,
                    mode="lines",
                    line=dict(color="#06b6d4", width=2.2),
                    opacity=0.70,
                    name="Ramas Exploradas",
                    hoverinfo="none",
                )
            )

        # Si llegó a la meta, resaltar la ruta óptima
        if paso_exploracion.es_meta and elementos.aristas_solucion:
            sol_x, sol_y = [], []
            for tr in elementos.aristas_solucion:
                p1 = tr["p1"]
                p2 = tr["p2"]
                p1_v = coord_map.get(p1, (p1[0], p1[1] * factor_separacion_y))
                p2_v = coord_map.get(p2, (p2[0], p2[1] * factor_separacion_y))
                sol_x.extend([p1_v[0], p2_v[0], None])
                sol_y.extend([p1_v[1], p2_v[1], None])
            fig.add_trace(
                go.Scatter(
                    x=sol_x,
                    y=sol_y,
                    mode="lines",
                    line=dict(color=COLOR_META, width=5.0),
                    name="Ruta Óptima",
                )
            )

    # 5. Capa de Nodos Urbanos (Puntos con información rica)
    hitos_destacados = {
        "parque_marimba", "catedral_san_marcos", "plaza_crystal", "hospital_regional",
        "parque_tuchtlan", "plaza_las_americas", "parque_cana_hueca", "unach_campus1"
    }

    nodo_viajero = elementos.origen_id
    if modo == "viajero" and paso_idx is not None and paso_idx > 0 and elementos.aristas_solucion:
        idx_lim = min(paso_idx - 1, len(elementos.aristas_solucion) - 1)
        nodo_viajero = elementos.aristas_solucion[idx_lim]["destino"]

    base_x, base_y, base_hover, base_names = [], [], [], []
    cerr_x, cerr_y, cerr_hover = [], [], []
    front_x, front_y, front_hover = [], [], []

    for nid, (x, y) in pos_vis.items():
        nombre = formatear_nombre_nodo(nid)
        real_x, real_y = elementos.posiciones[nid]
        hover_info = f"<b>{nombre}</b><br>ID: {nid}<br>Coordenadas: ({real_x:.0f}m, {real_y:.0f}m)"

        if modo == "exploracion" and paso_exploracion:
            if nid in paso_exploracion.nodos_frontera:
                front_x.append(x)
                front_y.append(y)
                front_hover.append(hover_info + "<br><span style='color:#f59e0b;'><b>Estado: En Frontera</b></span>")
                continue
            elif nid in paso_exploracion.nodos_cerrados:
                cerr_x.append(x)
                cerr_y.append(y)
                cerr_hover.append(hover_info + "<br><span style='color:#64748b;'><b>Estado: Explorado</b></span>")
                continue

        base_x.append(x)
        base_y.append(y)
        base_hover.append(hover_info)
        base_names.append(nombre if nid in hitos_destacados else "")

    # Nodos base
    fig.add_trace(
        go.Scatter(
            x=base_x,
            y=base_y,
            mode="markers+text",
            text=base_names,
            textposition="top center",
            textfont=dict(color="#cbd5e1", size=10, family="Segoe UI"),
            marker=dict(color="#334155", size=9, line=dict(color="#64748b", width=1.2)),
            hoverinfo="text",
            hovertext=base_hover,
            name="Ubicaciones",
        )
    )

    # Nodos cerrados (si aplica en exploración)
    if cerr_x:
        fig.add_trace(
            go.Scatter(
                x=cerr_x,
                y=cerr_y,
                mode="markers",
                marker=dict(color=COLOR_CERRADO, size=11, line=dict(color="#94a3b8", width=1.5)),
                hoverinfo="text",
                hovertext=cerr_hover,
                name="Explorados (Cerrados)",
            )
        )

    # Nodos frontera (si aplica en exploración)
    if front_x:
        fig.add_trace(
            go.Scatter(
                x=front_x,
                y=front_y,
                mode="markers",
                marker=dict(color=COLOR_FRONTERA, size=13, symbol="diamond", line=dict(color="#fde68a", width=1.8)),
                hoverinfo="text",
                hovertext=front_hover,
                name="En Frontera (Abiertos)",
            )
        )

    # 6. Destacar ORIGEN y DESTINO sin emojis
    if elementos.origen_id and elementos.origen_id in pos_vis:
        ox, oy = pos_vis[elementos.origen_id]
        nom_o = formatear_nombre_nodo(elementos.origen_id)
        fig.add_trace(
            go.Scatter(
                x=[ox],
                y=[oy],
                mode="markers+text",
                marker=dict(color=COLOR_ORIGEN, size=20, symbol="circle", line=dict(color="white", width=2.5)),
                text=[f"ORIGEN: {nom_o}"],
                textposition="bottom center",
                textfont=dict(color="#34d399", size=11, family="Segoe UI", weight="bold"),
                name="Origen",
                hoverinfo="text",
                hovertext=f"<b>Punto de Partida:</b> {nom_o}",
            )
        )

    if elementos.destino_id and elementos.destino_id in pos_vis:
        dx, dy = pos_vis[elementos.destino_id]
        nom_d = formatear_nombre_nodo(elementos.destino_id)
        col_d = COLOR_META if (paso_exploracion and paso_exploracion.es_meta) else COLOR_DESTINO
        txt_meta = f"META ALCANZADA: {nom_d}" if (paso_exploracion and paso_exploracion.es_meta) else f"DESTINO: {nom_d}"
        c_font = "#34d399" if (paso_exploracion and paso_exploracion.es_meta) else "#fb7185"
        fig.add_trace(
            go.Scatter(
                x=[dx],
                y=[dy],
                mode="markers+text",
                marker=dict(color=col_d, size=22, symbol="star", line=dict(color="white", width=2.5)),
                text=[txt_meta],
                textposition="top center",
                textfont=dict(color=c_font, size=11, family="Segoe UI", weight="bold"),
                name="Destino",
                hoverinfo="text",
                hovertext=f"<b>Punto de Llegada:</b> {nom_d}",
            )
        )

    # 7. Marcador interactivo del paso actual sin emojis
    if modo == "viajero" and nodo_viajero and nodo_viajero in pos_vis:
        vx, vy = pos_vis[nodo_viajero]
        nom_v = formatear_nombre_nodo(nodo_viajero)
        fig.add_trace(
            go.Scatter(
                x=[vx],
                y=[vy],
                mode="markers+text",
                marker=dict(color=COLOR_ACTUAL, size=24, symbol="circle", line=dict(color="#b91c1c", width=3)),
                text=[f"VIAJERO: {nom_v}"],
                textposition="top center",
                textfont=dict(color="#fde047", size=12, family="Segoe UI", weight="bold"),
                name="Posición del Viajero",
                hoverinfo="text",
                hovertext=f"<b>Viajero situado en:</b> {nom_v}",
            )
        )
    elif modo == "exploracion" and paso_exploracion and paso_exploracion.nodo_actual in pos_vis:
        ex, ey = pos_vis[paso_exploracion.nodo_actual]
        nom_e = formatear_nombre_nodo(paso_exploracion.nodo_actual)
        txt_banner = f"EXPANDIENDO:<br>{nom_e}<br>f={paso_exploracion.f:.1f} (g={paso_exploracion.g:.1f} + h={paso_exploracion.h:.1f})"
        fig.add_trace(
            go.Scatter(
                x=[ex],
                y=[ey],
                mode="markers+text",
                marker=dict(color=COLOR_ACTUAL, size=26, symbol="hexagram", line=dict(color="#e11d48", width=3)),
                text=[f"EXPANDIENDO: {nom_e}"],
                textposition="bottom center",
                textfont=dict(color="#facc15", size=11, family="Segoe UI", weight="bold"),
                name="Nodo en Expansión",
                hoverinfo="text",
                hovertext=txt_banner,
            )
        )

    # Estilo y configuración de la visualización Plotly
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=COLOR_FONDO,
        plot_bgcolor=COLOR_FONDO,
        margin=dict(l=20, r=20, t=35, b=20),
        xaxis=dict(
            title="Coordenada X (metros)",
            showgrid=True,
            gridcolor=COLOR_GRID,
            zeroline=False,
            color="#94a3b8",
        ),
        yaxis=dict(
            title="Coordenada Y Espaciada (metros)",
            showgrid=True,
            gridcolor=COLOR_GRID,
            zeroline=False,
            scaleanchor="x",
            scaleratio=1,
            color="#94a3b8",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(color="#cbd5e1", size=10),
            bgcolor="rgba(11, 15, 25, 0.85)",
            bordercolor="#2b3a55",
            borderwidth=1,
        ),
        hoverlabel=dict(
            bgcolor="#151d30",
            font_size=12,
            font_family="Segoe UI",
            font_color="#f8fafc",
            bordercolor="#3b82f6",
        ),
        height=640,
    )

    return fig


def crear_figura_arbol_plotly(
    nodos_arbol: dict[str, NodoArbol],
    raiz_id: str | None,
    algoritmo: str = "A*",
) -> go.Figure:
    """Construye un árbol jerárquico interactivo con Plotly donde se pueden explorar ramas."""
    fig = go.Figure()
    if not nodos_arbol or not raiz_id or raiz_id not in nodos_arbol:
        fig.add_annotation(
            text="Selecciona origen y destino y pulsa 'Calcular Ruta' para generar el árbol de decisiones de la IA.",
            showarrow=False,
            font=dict(size=14, color="#94a3b8"),
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor=COLOR_FONDO,
            plot_bgcolor=COLOR_FONDO,
            height=580,
        )
        return fig

    calcular_posiciones_arbol(nodos_arbol, raiz_id)

    # 1. Dibujar ramas (aristas padre -> hijo)
    sol_edge_x, sol_edge_y = [], []
    alt_edge_x, alt_edge_y = [], []

    for nid, nodo in nodos_arbol.items():
        if nodo.padre_id and nodo.padre_id in nodos_arbol:
            padre = nodos_arbol[nodo.padre_id]
            if nodo.es_solucion and padre.es_solucion:
                sol_edge_x.extend([padre.x, nodo.x, None])
                sol_edge_y.extend([padre.y, nodo.y, None])
            else:
                alt_edge_x.extend([padre.x, nodo.x, None])
                alt_edge_y.extend([padre.y, nodo.y, None])

    # Ramas alternas
    if alt_edge_x:
        fig.add_trace(
            go.Scatter(
                x=alt_edge_x,
                y=alt_edge_y,
                mode="lines",
                line=dict(color="#334155", width=1.5),
                hoverinfo="none",
                name="Ramas Evaluadas",
            )
        )

    # Ramas de solución ganadora
    if sol_edge_x:
        fig.add_trace(
            go.Scatter(
                x=sol_edge_x,
                y=sol_edge_y,
                mode="lines",
                line=dict(color="#10b981", width=3.8),
                hoverinfo="none",
                name="Rama Solución Óptima",
            )
        )

    # 2. Dibujar nodos del árbol
    sol_x, sol_y, sol_text, sol_hover = [], [], [], []
    cerr_x, cerr_y, cerr_text, cerr_hover = [], [], [], []
    front_x, front_y, front_text, front_hover = [], [], [], []

    for nid, nodo in nodos_arbol.items():
        nombre = formatear_nombre_nodo(nodo.estado.nodo)
        info_costo = f"f={nodo.f:.1f}<br>(g={nodo.g:.1f} + h={nodo.h:.1f})"
        hover_txt = (
            f"<b>{nombre}</b> ({nodo.estado.ruta or 'A pie'})<br>"
            f"<b>f(n):</b> {nodo.f:.2f}<br>"
            f"<b>g(n):</b> {nodo.g:.2f} (costo acumulado)<br>"
            f"<b>h(n):</b> {nodo.h:.2f} (estimación admisible)<br>"
            f"<b>Profundidad:</b> Nivel {nodo.profundidad}<br>"
            f"<b>Estado:</b> {'Rama Solución Óptima' if nodo.es_solucion else 'Rama evaluada'}"
        )

        if nodo.es_solucion:
            sol_x.append(nodo.x)
            sol_y.append(nodo.y)
            sol_text.append(f"<b>{nombre}</b><br>{info_costo}")
            sol_hover.append(hover_txt)
        elif nodo.cerrado:
            cerr_x.append(nodo.x)
            cerr_y.append(nodo.y)
            cerr_text.append(f"{nombre}<br>{info_costo}")
            cerr_hover.append(hover_txt)
        else:
            front_x.append(nodo.x)
            front_y.append(nodo.y)
            front_text.append(f"{nombre}<br>{info_costo}")
            front_hover.append(hover_txt)

    if cerr_x:
        fig.add_trace(
            go.Scatter(
                x=cerr_x,
                y=cerr_y,
                mode="markers+text",
                marker=dict(color="#3b82f6", size=30, symbol="circle", line=dict(color="#93c5fd", width=1.5)),
                text=cerr_text,
                textposition="bottom center",
                textfont=dict(color="#94a3b8", size=9, family="Segoe UI"),
                hoverinfo="text",
                hovertext=cerr_hover,
                name="Nodos Explorados",
            )
        )

    if front_x:
        fig.add_trace(
            go.Scatter(
                x=front_x,
                y=front_y,
                mode="markers+text",
                marker=dict(color="#f59e0b", size=30, symbol="circle", line=dict(color="#fde68a", width=1.5)),
                text=front_text,
                textposition="bottom center",
                textfont=dict(color="#fde68a", size=9, family="Segoe UI"),
                hoverinfo="text",
                hovertext=front_hover,
                name="En Frontera",
            )
        )

    if sol_x:
        fig.add_trace(
            go.Scatter(
                x=sol_x,
                y=sol_y,
                mode="markers+text",
                marker=dict(color="#10b981", size=38, symbol="circle", line=dict(color="#ecfdf5", width=2.5)),
                text=sol_text,
                textposition="bottom center",
                textfont=dict(color="#34d399", size=10, family="Segoe UI", weight="bold"),
                hoverinfo="text",
                hovertext=sol_hover,
                name="Rama Solución Óptima",
            )
        )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=COLOR_FONDO,
        plot_bgcolor=COLOR_FONDO,
        margin=dict(l=20, r=20, t=30, b=50),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(color="#cbd5e1", size=10),
            bgcolor="rgba(11, 15, 25, 0.85)",
            bordercolor="#2b3a55",
            borderwidth=1,
        ),
        hoverlabel=dict(
            bgcolor="#151d30",
            font_size=12,
            font_family="Segoe UI",
            font_color="#f8fafc",
            bordercolor="#10b981",
        ),
        height=620,
    )

    return fig


def crear_grafica_comparativa_plotly(resultados: list[ResultadoBusqueda]) -> go.Figure:
    """Genera gráficas de barras comparativas entre A*, Dijkstra y BFS."""
    algoritmos = [r.algoritmo for r in resultados]
    expandidos = [r.nodos_expandidos for r in resultados]

    colores = ["#10b981", "#3b82f6", "#f59e0b"]  # A*, Dijkstra, BFS

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Nodos Expandidos (Menor es mejor)",
            x=algoritmos,
            y=expandidos,
            marker_color=colores[:len(algoritmos)],
            text=[f"{v} nodos" for v in expandidos],
            textposition="auto",
        )
    )

    fig.update_layout(
        template="plotly_dark",
        title="Eficiencia de Exploración: Nodos Expandidos por Algoritmo",
        paper_bgcolor=COLOR_FONDO,
        plot_bgcolor=COLOR_FONDO,
        font=dict(family="Segoe UI", color="#cbd5e1"),
        height=380,
        margin=dict(l=20, r=20, t=50, b=30),
    )
    return fig
