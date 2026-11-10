"""Renderizador del mapa visual para la red urbana multimodal.

Responsabilidad del Dev B: genera visualizaciones gráficas de la ciudad,
la ruta óptima y los nodos explorados por cada algoritmo con matplotlib.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Paleta de colores para diferentes rutas de transporte público
def formatear_nombre_nodo(nid: str) -> str:
    """Convierte un identificador como 'parque_tuchtlan' en 'Parque Tuchtlan' para vista legible."""
    if not nid:
        return ""
    # Reemplazar abreviaciones comunes y dar formato título
    nombre = nid.replace("interseccion_", "").replace("_", " ").title()
    # Casos especiales comunes en el mapa
    reemplazos = {
        "Unach": "UNACH",
        "Fca": "FCA",
        "Blvd": "Blvd.",
        "Cana": "Caña",
        "Joyyo": "Joyyo",
    }
    for k, v in reemplazos.items():
        nombre = nombre.replace(k, v)
    return nombre

COLORES_RUTAS = ["#1e88e5", "#43a047", "#8e24aa", "#fb8c00", "#00acc1", "#d81b60"]


@dataclass
class ElementosMapa:
    """Contenedor de elementos geométricos y estilos calculados para el dibujo."""
    posiciones: dict[str, tuple[float, float]] = field(default_factory=dict)
    aristas_caminando: list[tuple[tuple[float, float], tuple[float, float]]] = field(default_factory=list)
    aristas_transporte: dict[str, list[tuple[tuple[float, float], tuple[float, float]]]] = field(default_factory=dict)
    aristas_solucion: list[dict[str, Any]] = field(default_factory=list)
    nodos_transbordo: list[str] = field(default_factory=list)
    coords_explorados: list[tuple[float, float]] = field(default_factory=list)
    origen_id: str | None = None
    destino_id: str | None = None


def _obtener_datos_dict(mapa: Any) -> dict[str, Any]:
    """Extrae la estructura de diccionario de un mapa JSON o de un objeto Grafo."""
    if isinstance(mapa, dict):
        return mapa
    if hasattr(mapa, "to_dict"):
        return mapa.to_dict()
    # Compatibilidad con objetos Grafo que tengan atributos nodos, tramos, rutas
    datos: dict[str, Any] = {"nodos": [], "tramos": [], "rutas": []}
    if hasattr(mapa, "nodos"):
        if isinstance(mapa.nodos, dict):
            datos["nodos"] = [{"id": n.id, "x": n.x, "y": n.y} for n in mapa.nodos.values()]
        else:
            datos["nodos"] = mapa.nodos
    if hasattr(mapa, "tramos"):
        tramos_lista = []
        for t in mapa.tramos:
            if isinstance(t, dict):
                tramos_lista.append(t)
            else:
                tramos_lista.append({"de": t.de, "a": t.a, "distancia_m": getattr(t, "distancia_m", 0)})
        datos["tramos"] = tramos_lista
    if hasattr(mapa, "rutas"):
        rutas_lista = []
        coleccion_rutas = mapa.rutas.values() if isinstance(mapa.rutas, dict) else mapa.rutas
        for r in coleccion_rutas:
            if isinstance(r, dict):
                rutas_lista.append(r)
            else:
                rutas_lista.append({"id": r.id, "paradas": list(r.paradas)})
        datos["rutas"] = rutas_lista
    return datos


def preparar_elementos_mapa(
    mapa: Any,
    resultado: Any = None,
    nodos_explorados: list[str] | None = None,
) -> ElementosMapa:
    """Calcula las geometrías, distinciones de transporte y ruta sin acoplarse al renderizado."""
    datos = _obtener_datos_dict(mapa)
    elementos = ElementosMapa()

    # 1. Extraer posiciones cartesianas de los nodos
    for nodo in datos.get("nodos", []):
        nid = nodo.get("id") or str(nodo.get("nombre"))
        x = float(nodo.get("x", 0.0))
        y = float(nodo.get("y", 0.0))
        elementos.posiciones[nid] = (x, y)

    # 2. Tramos peatonales base
    for tramo in datos.get("tramos", []):
        origen = tramo.get("de")
        destino = tramo.get("a")
        if origen in elementos.posiciones and destino in elementos.posiciones:
            p1 = elementos.posiciones[origen]
            p2 = elementos.posiciones[destino]
            elementos.aristas_caminando.append((p1, p2))

    # 3. Rutas de transporte base
    for ruta in datos.get("rutas", []):
        rid = ruta.get("id", "Ruta")
        paradas = ruta.get("paradas", [])
        segmentos = []
        for i in range(len(paradas) - 1):
            p_orig = paradas[i]
            p_dest = paradas[i + 1]
            if p_orig in elementos.posiciones and p_dest in elementos.posiciones:
                segmentos.append((elementos.posiciones[p_orig], elementos.posiciones[p_dest]))
        elementos.aristas_transporte[rid] = segmentos

    # 4. Procesar la ruta solución (si se proporcionó un ResultadoBusqueda)
    if resultado and getattr(resultado, "ruta", None):
        secuencia_estados = resultado.ruta
        if len(secuencia_estados) > 0:
            elementos.origen_id = secuencia_estados[0].nodo
            elementos.destino_id = secuencia_estados[-1].nodo

        for i in range(len(secuencia_estados) - 1):
            e_actual = secuencia_estados[i]
            e_siguiente = secuencia_estados[i + 1]

            n_orig = e_actual.nodo
            n_dest = e_siguiente.nodo

            if n_orig in elementos.posiciones and n_dest in elementos.posiciones:
                p1 = elementos.posiciones[n_orig]
                p2 = elementos.posiciones[n_dest]

                es_caminando = (e_actual.ruta == "CAMINANDO" and e_siguiente.ruta == "CAMINANDO")
                tipo_tramo = "CAMINANDO" if es_caminando else "TRANSPORTE"
                color = "#43a047" if es_caminando else "#1e88e5"

                elementos.aristas_solucion.append({
                    "origen": n_orig,
                    "destino": n_dest,
                    "p1": p1,
                    "p2": p2,
                    "tipo": tipo_tramo,
                    "color": color,
                    "grosor": 4.5,
                })

            # Detectar transbordo o abordaje/bajada
            if e_actual.ruta != e_siguiente.ruta:
                if n_orig not in elementos.nodos_transbordo:
                    elementos.nodos_transbordo.append(n_orig)
                if n_dest not in elementos.nodos_transbordo:
                    elementos.nodos_transbordo.append(n_dest)

    # 5. Mapear nodos explorados a coordenadas
    if nodos_explorados:
        for nid in nodos_explorados:
            if nid in elementos.posiciones:
                elementos.coords_explorados.append(elementos.posiciones[nid])

    return elementos


def generar_mapa(
    mapa: Any,
    resultado: Any = None,
    ruta_png: str = "mapa_ruta.png",
    nodos_explorados: list[str] | None = None,
    titulo: str | None = None,
) -> None:
    """Dibuja el mapa urbano, la ruta resaltada y los nodos explorados en formato PNG."""
    os.makedirs(os.path.dirname(os.path.abspath(ruta_png)), exist_ok=True)
    elementos = preparar_elementos_mapa(mapa, resultado, nodos_explorados)

    fig, ax = plt.subplots(figsize=(11, 7.5))

    # 1. Dibujar tramos peatonales base
    for i, (p1, p2) in enumerate(elementos.aristas_caminando):
        etiqueta = "Red peatonal (calles)" if i == 0 else ""
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color="#cfd8dc", linestyle="--", linewidth=1.5, zorder=1, label=etiqueta)

    # 2. Dibujar rutas de transporte base
    for idx, (rid, segmentos) in enumerate(elementos.aristas_transporte.items()):
        color = COLORES_RUTAS[idx % len(COLORES_RUTAS)]
        for s_idx, (p1, p2) in enumerate(segmentos):
            etiqueta = f"Ruta {rid}" if s_idx == 0 else ""
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=color, alpha=0.35, linewidth=2.5, zorder=2, label=etiqueta)

    # 3. Dibujar nodos explorados por el algoritmo (si los hay)
    if elementos.coords_explorados:
        exp_x = [c[0] for c in elementos.coords_explorados]
        exp_y = [c[1] for c in elementos.coords_explorados]
        ax.scatter(exp_x, exp_y, s=180, color="#ffe082", alpha=0.65, edgecolors="#ffa000", zorder=3, label="Nodos explorados")

    # 4. Dibujar la ruta solución resaltada con flechas de dirección
    caminando_etiquetado = False
    transporte_etiquetado = False
    for tramo in elementos.aristas_solucion:
        p1 = tramo["p1"]
        p2 = tramo["p2"]
        color = tramo["color"]
        if tramo["tipo"] == "CAMINANDO":
            lbl = "Ruta: Caminando" if not caminando_etiquetado else ""
            caminando_etiquetado = True
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color="#2e7d32", linewidth=tramo["grosor"], zorder=5, label=lbl)
        else:
            lbl = "Ruta: En transporte" if not transporte_etiquetado else ""
            transporte_etiquetado = True
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color="#1565c0", linewidth=tramo["grosor"], zorder=5, label=lbl)

        # Flecha indicadora de sentido de avance
        mx = (p1[0] + p2[0]) / 2.0
        my = (p1[1] + p2[1]) / 2.0
        dx = (p2[0] - p1[0]) * 0.05
        dy = (p2[1] - p1[1]) * 0.05
        ax.annotate("", xy=(mx + dx, my + dy), xytext=(mx - dx, my - dy),
                    arrowprops=dict(arrowstyle="->", color="black", lw=2, mutation_scale=14), zorder=6)

    # 5. Dibujar nodos con etiquetas legibles y espaciado inteligente anticolisión
    nodos_ruta = set()
    if elementos.origen_id:
        nodos_ruta.add(elementos.origen_id)
    if elementos.destino_id:
        nodos_ruta.add(elementos.destino_id)
    for tramo in elementos.aristas_solucion:
        nodos_ruta.add(tramo["origen"])
        nodos_ruta.add(tramo["destino"])

    # Puntos de referencia icónicos que conviene rotular si no saturan
    hitos_principales = {"parque_marimba", "catedral_san_marcos", "plaza_crystal", "hospital_regional", "parque_tuchtlan", "plaza_las_americas", "parque_cana_hueca"}

    for nid, (x, y) in elementos.posiciones.items():
        es_origen = (nid == elementos.origen_id)
        es_destino = (nid == elementos.destino_id)
        es_transbordo = (nid in elementos.nodos_transbordo)
        es_de_ruta = (nid in nodos_ruta)
        nombre_legible = formatear_nombre_nodo(nid)

        if es_origen:
            ax.scatter(x, y, s=300, color="#00c853", edgecolors="black", linewidths=2.5, zorder=8, label="Origen")
            ax.annotate(
                f"ORIGEN:\n{nombre_legible}",
                xy=(x, y),
                xytext=(x, y + 45),
                fontsize=9.5,
                fontweight="bold",
                ha="center",
                va="bottom",
                zorder=10,
                bbox=dict(boxstyle="round,pad=0.35", facecolor="#e8f5e9", edgecolor="#2e7d32", lw=2, alpha=0.95),
                arrowprops=dict(arrowstyle="->", color="#2e7d32", lw=1.5),
            )
        elif es_destino:
            ax.scatter(x, y, s=300, color="#d50000", edgecolors="black", linewidths=2.5, zorder=8, label="Destino")
            ax.annotate(
                f"DESTINO:\n{nombre_legible}",
                xy=(x, y),
                xytext=(x, y + 45),
                fontsize=9.5,
                fontweight="bold",
                ha="center",
                va="bottom",
                zorder=10,
                bbox=dict(boxstyle="round,pad=0.35", facecolor="#ffebee", edgecolor="#c62828", lw=2, alpha=0.95),
                arrowprops=dict(arrowstyle="->", color="#c62828", lw=1.5),
            )
        elif es_transbordo:
            ax.scatter(x, y, s=180, color="#ffd600", marker="D", edgecolors="black", linewidths=1.8, zorder=7,
                       label="Transbordo/Abordaje" if nid == elementos.nodos_transbordo[0] else "")
            ax.text(x, y - 28, f"Transbordo:\n{nombre_legible}", fontsize=8, fontweight="bold", ha="center", va="top", zorder=8,
                    bbox=dict(boxstyle="round,pad=0.25", facecolor="#fffde7", edgecolor="#fbc02d", lw=1.2, alpha=0.95))
        elif es_de_ruta:
            # Puntos intermedios de la ruta: etiqueta limpia debajo para no tapar el origen/destino
            ax.scatter(x, y, s=120, color="#ff9800", edgecolors="black", linewidths=1.2, zorder=6)
            ax.text(x, y - 24, nombre_legible, fontsize=8, fontweight="bold", color="#e65100", ha="center", va="top", zorder=7,
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="#ff9800", lw=1.0, alpha=0.9))
        elif nid in hitos_principales:
            # Puntos de referencia icónicos en el mapa: discretos
            ax.scatter(x, y, s=70, color="#78909c", edgecolors="white", linewidths=1, zorder=3)
            ax.text(x, y + 16, nombre_legible, fontsize=7.5, color="#37474f", ha="center", va="bottom", zorder=3,
                    bbox=dict(boxstyle="round,pad=0.15", facecolor="white", alpha=0.75, edgecolor="#cfd8dc", lw=0.6))
        else:
            # Esquinas y paradas secundarias: solo punto limpio sin texto invasivo
            ax.scatter(x, y, s=35, color="#b0bec5", edgecolors="white", linewidths=0.5, zorder=2)

    # Ajustes estéticos, leyendas y márgenes holgados
    titulo_mapa = titulo or "Plano de Ruta Urbana Multimodal (RutaUrbana A*)"
    ax.set_title(titulo_mapa, fontsize=12, fontweight="bold", pad=14)
    ax.set_xlabel("Coordenada X (metros)", fontsize=9.5)
    ax.set_ylabel("Coordenada Y (metros)", fontsize=9.5)
    ax.grid(True, linestyle=":", alpha=0.45)
    ax.set_aspect("equal", adjustable="box")

    # Margen extra de respiro (padding del 8% alrededor de los puntos)
    todas_x = [pos[0] for pos in elementos.posiciones.values()]
    todas_y = [pos[1] for pos in elementos.posiciones.values()]
    if todas_x and todas_y:
        margen_x = (max(todas_x) - min(todas_x)) * 0.08
        margen_y = (max(todas_y) - min(todas_y)) * 0.18
        ax.set_xlim(min(todas_x) - margen_x, max(todas_x) + margen_x)
        ax.set_ylim(min(todas_y) - margen_y, max(todas_y) + margen_y)
    ax.set_aspect("equal", adjustable="box")

    # Manejar leyendas únicas
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    if by_label:
        ax.legend(by_label.values(), by_label.keys(), loc="upper right", framealpha=0.9)

    fig.tight_layout()
    fig.savefig(ruta_png, dpi=300, bbox_inches="tight")
    plt.close(fig)


def dibujar_paso_busqueda_en_mapa(
    ax: plt.Axes,
    elementos: ElementosMapa,
    paso: Any,
    total_pasos: int,
    algoritmo: str = "A*",
) -> None:
    """Dibuja el estado de exploración del algoritmo (frontera, cerrados, nodo actual) sobre el plano urbano."""
    ax.clear()

    # 1. Calles peatonales base
    for i, (p1, p2) in enumerate(elementos.aristas_caminando):
        lbl = "Red peatonal (calles)" if i == 0 else ""
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color="#cfd8dc", linestyle="--", linewidth=1.2, zorder=1, label=lbl)

    # 2. Rutas de transporte base
    for idx, (rid, segmentos) in enumerate(elementos.aristas_transporte.items()):
        col = COLORES_RUTAS[idx % len(COLORES_RUTAS)]
        for s_idx, (p1, p2) in enumerate(segmentos):
            lbl = f"Ruta {rid}" if s_idx == 0 else ""
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=col, alpha=0.25, linewidth=2.0, zorder=2, label=lbl)

    # 3. Aristas exploradas por el árbol de búsqueda hasta este paso
    aristas_dibujadas = False
    for de_id, a_id in paso.aristas_exploradas:
        if de_id in elementos.posiciones and a_id in elementos.posiciones:
            p1 = elementos.posiciones[de_id]
            p2 = elementos.posiciones[a_id]
            lbl = "Ramas exploradas" if not aristas_dibujadas else ""
            aristas_dibujadas = True
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color="#00acc1", alpha=0.65, linewidth=2.2, linestyle="-", zorder=4, label=lbl)

    # 4. Si la meta fue alcanzada en este paso, resaltar la ruta óptima completa
    if paso.es_meta and elementos.aristas_solucion:
        sol_etiquetada = False
        for tr in elementos.aristas_solucion:
            p1 = tr["p1"]
            p2 = tr["p2"]
            lbl = "Ruta Óptima Ganadora" if not sol_etiquetada else ""
            sol_etiquetada = True
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color="#00c853", linewidth=4.5, zorder=8, label=lbl)

    hitos_principales = {"parque_marimba", "catedral_san_marcos", "plaza_crystal", "hospital_regional", "parque_tuchtlan", "plaza_las_americas", "parque_cana_hueca"}

    # 5. Dibujar nodos según su estado de búsqueda
    cerrados_etiquetados = False
    frontera_etiquetada = False
    actual_etiquetado = False

    for nid, (x, y) in elementos.posiciones.items():
        nombre = formatear_nombre_nodo(nid)
        es_actual = (nid == paso.nodo_actual)
        es_origen = (nid == elementos.origen_id)
        es_destino = (nid == elementos.destino_id)
        es_frontera = (nid in paso.nodos_frontera)
        es_cerrado = (nid in paso.nodos_cerrados)

        if es_actual:
            lbl = "Nodo en Expansión" if not actual_etiquetado else ""
            actual_etiquetado = True
            ax.scatter(x, y, s=360, color="#ffd600", edgecolors="#c2185b", linewidths=3.0, zorder=12, label=lbl)

            texto_expandiendo = f"EXPANDIENDO ({algoritmo}):\n{nombre}\nf={paso.f:.1f} (g={paso.g:.1f} + h={paso.h:.1f})"
            ax.annotate(
                texto_expandiendo,
                xy=(x, y),
                xytext=(x, y + 48),
                fontsize=9.0,
                fontweight="bold",
                color="#880e4f",
                ha="center",
                va="bottom",
                zorder=13,
                bbox=dict(boxstyle="round,pad=0.35", facecolor="#fff9c4", edgecolor="#c2185b", lw=2.0, alpha=0.98),
                arrowprops=dict(arrowstyle="->", color="#c2185b", lw=2.0),
            )
        elif es_origen:
            ax.scatter(x, y, s=260, color="#00c853", edgecolors="black", linewidths=2.2, zorder=9, label="Origen")
            ax.text(x, y + 25, f"ORIGEN:\n{nombre}", fontsize=8.5, fontweight="bold", ha="center", va="bottom", zorder=10,
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="#e8f5e9", edgecolor="#2e7d32", lw=1.5, alpha=0.9))
        elif es_destino:
            color_dest = "#00e676" if paso.es_meta else "#d50000"
            borde_dest = "#1b5e20" if paso.es_meta else "black"
            lbl_dest = "Meta Encontrada" if paso.es_meta else "Destino"
            ax.scatter(x, y, s=280, color=color_dest, edgecolors=borde_dest, linewidths=2.5, zorder=9, label=lbl_dest)
            texto_dest = f"¡META ALCANZADA!:\n{nombre}" if paso.es_meta else f"DESTINO:\n{nombre}"
            c_fondo = "#e8f5e9" if paso.es_meta else "#ffebee"
            c_borde = "#2e7d32" if paso.es_meta else "#c62828"
            ax.text(x, y + 25, texto_dest, fontsize=8.5, fontweight="bold", ha="center", va="bottom", zorder=10,
                    bbox=dict(boxstyle="round,pad=0.3", facecolor=c_fondo, edgecolor=c_borde, lw=1.8, alpha=0.95))
        elif es_frontera:
            lbl = "En Frontera (Abierto)" if not frontera_etiquetada else ""
            frontera_etiquetada = True
            ax.scatter(x, y, s=110, color="#ffa000", edgecolors="#e65100", linewidths=1.5, zorder=7, label=lbl)
            ax.text(x, y - 22, nombre, fontsize=7.0, color="#bf360c", ha="center", va="top", zorder=7,
                    bbox=dict(boxstyle="round,pad=0.15", facecolor="#fff8e1", edgecolor="#ffa000", lw=0.8, alpha=0.85))
        elif es_cerrado:
            lbl = "Explorado (Cerrado)" if not cerrados_etiquetados else ""
            cerrados_etiquetados = True
            ax.scatter(x, y, s=75, color="#1976d2", edgecolors="white", linewidths=1.0, zorder=6, label=lbl)
            if nid in hitos_principales:
                ax.text(x, y - 20, nombre, fontsize=6.8, color="#0d47a1", ha="center", va="top", zorder=6,
                        bbox=dict(boxstyle="round,pad=0.12", facecolor="#e3f2fd", edgecolor="#90caf9", lw=0.6, alpha=0.8))
        elif nid in hitos_principales:
            ax.scatter(x, y, s=50, color="#90a4ae", edgecolors="white", linewidths=0.8, zorder=3)
            ax.text(x, y + 14, nombre, fontsize=6.8, color="#37474f", ha="center", va="bottom", zorder=3,
                    bbox=dict(boxstyle="round,pad=0.15", facecolor="white", alpha=0.75, edgecolor="#cfd8dc", lw=0.5))
        else:
            ax.scatter(x, y, s=25, color="#cfd8dc", edgecolors="white", linewidths=0.5, zorder=2)

    # Título, márgenes y leyendas
    nom_actual = formatear_nombre_nodo(paso.nodo_actual)
    ax.set_title(
        f"Exploración {algoritmo} - Paso {paso.num_paso}/{total_pasos}: Expandiendo '{nom_actual}'",
        fontsize=11,
        fontweight="bold",
        pad=12,
    )
    ax.set_xlabel("Coordenada X (metros)", fontsize=9)
    ax.set_ylabel("Coordenada Y (metros)", fontsize=9)
    ax.grid(True, linestyle=":", alpha=0.45)
    ax.set_aspect("equal", adjustable="box")

    todas_x = [pos[0] for pos in elementos.posiciones.values()]
    todas_y = [pos[1] for pos in elementos.posiciones.values()]
    if todas_x and todas_y:
        margen_x = (max(todas_x) - min(todas_x)) * 0.08
        margen_y = (max(todas_y) - min(todas_y)) * 0.18
        ax.set_xlim(min(todas_x) - margen_x, max(todas_x) + margen_x)
        ax.set_ylim(min(todas_y) - margen_y, max(todas_y) + margen_y)

    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    if by_label:
        ax.legend(by_label.values(), by_label.keys(), loc="upper right", fontsize=8, framealpha=0.9)
