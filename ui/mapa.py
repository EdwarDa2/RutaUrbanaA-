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
        datos["nodos"] = [{"id": n.id, "x": n.x, "y": n.y} for n in mapa.nodos.values()] if isinstance(mapa.nodos, dict) else mapa.nodos
    if hasattr(mapa, "tramos"):
        datos["tramos"] = mapa.tramos
    if hasattr(mapa, "rutas"):
        datos["rutas"] = mapa.rutas
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

    # 4. Dibujar la ruta solución resaltada
    caminando_etiquetado = False
    transporte_etiquetado = False
    for tramo in elementos.aristas_solucion:
        p1 = tramo["p1"]
        p2 = tramo["p2"]
        if tramo["tipo"] == "CAMINANDO":
            lbl = "Ruta: Caminando" if not caminando_etiquetado else ""
            caminando_etiquetado = True
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color="#2e7d32", linewidth=tramo["grosor"], zorder=5, label=lbl)
        else:
            lbl = "Ruta: En transporte" if not transporte_etiquetado else ""
            transporte_etiquetado = True
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color="#1565c0", linewidth=tramo["grosor"], zorder=5, label=lbl)

    # 5. Dibujar todos los nodos (paradas / esquinas)
    for nid, (x, y) in elementos.posiciones.items():
        es_origen = (nid == elementos.origen_id)
        es_destino = (nid == elementos.destino_id)
        es_transbordo = (nid in elementos.nodos_transbordo)

        if es_origen:
            ax.scatter(x, y, s=260, color="#00c853", edgecolors="black", linewidths=2, zorder=7, label="Origen")
            ax.text(x, y + 12, f"Origen: {nid}", fontsize=10, fontweight="bold", ha="center", zorder=8)
        elif es_destino:
            ax.scatter(x, y, s=260, color="#d50000", edgecolors="black", linewidths=2, zorder=7, label="Destino")
            ax.text(x, y + 12, f"Destino: {nid}", fontsize=10, fontweight="bold", ha="center", zorder=8)
        elif es_transbordo:
            ax.scatter(x, y, s=160, color="#ffd600", marker="D", edgecolors="black", linewidths=1.5, zorder=6, label="Transbordo/Abordaje" if nid == elementos.nodos_transbordo[0] else "")
            ax.text(x, y + 8, nid, fontsize=8.5, ha="center", zorder=8)
        else:
            ax.scatter(x, y, s=80, color="#78909c", edgecolors="white", linewidths=1, zorder=4)
            ax.text(x, y + 6, nid, fontsize=8, color="#37474f", ha="center", zorder=4)

    # Ajustes estéticos y leyendas
    titulo_mapa = titulo or "Plano de Ruta Urbana Multimodal (RutaUrbana A*)"
    ax.set_title(titulo_mapa, fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Coordenada X (metros)", fontsize=10)
    ax.set_ylabel("Coordenada Y (metros)", fontsize=10)
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.set_aspect("equal", adjustable="datalim")

    # Manejar leyendas únicas
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    if by_label:
        ax.legend(by_label.values(), by_label.keys(), loc="upper right", framealpha=0.9)

    fig.tight_layout()
    fig.savefig(ruta_png, dpi=300, bbox_inches="tight")
    plt.close(fig)
