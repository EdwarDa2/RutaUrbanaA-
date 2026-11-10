"""RutaUrbana A* - Interfaz Web Moderna (Dashboard Interactivo Streamlit).

Dashboard analítico y visual para la planificación de rutas con búsqueda informada A*.
Ofrece control interactivo paso a paso, visualización con Plotly y métricas en tiempo real.
"""

from __future__ import annotations

import os
import streamlit as st

from core.algoritmos import astar
from core.tipos import Pesos
from datos.cargador import cargar_mapa
from main import CRITERIOS_PREDEFINIDOS
from ui.arbol import extraer_arbol_y_pasos
from ui.mapa import preparar_elementos_mapa, formatear_nombre_nodo
from ui.web_visualizador import (
    crear_figura_mapa_plotly,
    crear_figura_arbol_plotly,
    formatear_nombre_ruta,
)


# Configuración global de la página sin emojis
st.set_page_config(
    page_title="RutaUrbana A* | Tuxtla Gutiérrez",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilos CSS modernos: Paleta Deep Obsidian Navy con acentos en azul real y esmeralda
st.markdown(
    """
    <style>
    /* Fondo principal y fuentes */
    .stApp {
        background-color: #0b0f19;
        color: #f1f5f9;
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    }
    /* Tarjetas de métricas */
    .metric-card {
        background-color: #151d30;
        border: 1px solid #263554;
        border-radius: 10px;
        padding: 16px 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }
    .metric-value {
        font-size: 26px;
        font-weight: 700;
        color: #f8fafc;
        margin-top: 4px;
        letter-spacing: -0.02em;
    }
    .metric-label {
        font-size: 12px;
        color: #94a3b8;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    .metric-delta {
        font-size: 13px;
        font-weight: 600;
        color: #10b981;
        margin-top: 2px;
    }
    /* Banner de paso actual */
    .step-banner {
        background: linear-gradient(90deg, #151d30 0%, #0b0f19 100%);
        border-left: 4px solid #3b82f6;
        padding: 12px 18px;
        border-radius: 8px;
        margin-bottom: 12px;
        font-size: 13.5px;
        color: #e2e8f0;
        border-top: 1px solid #1e293b;
        border-right: 1px solid #1e293b;
        border-bottom: 1px solid #1e293b;
    }
    /* Pestañas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        border-bottom: 1px solid #263554;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px 6px 0 0;
        padding: 8px 18px;
        font-size: 14px;
        font-weight: 600;
        color: #94a3b8;
    }
    .stTabs [aria-selected="true"] {
        color: #3b82f6 !important;
        border-bottom: 2px solid #3b82f6 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def obtener_grafo():
    """Carga y cachea la red urbana de Tuxtla Gutiérrez."""
    ruta = os.path.join(os.path.dirname(__file__), "datos", "zona_demo.json")
    return cargar_mapa(ruta)


def main():
    grafo = obtener_grafo()
    nodos_lista = sorted(list(grafo.nodos.keys()))

    # Encabezado principal sobrio y académico
    st.markdown(
        """
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.2rem; border-bottom: 1px solid #1e293b; padding-bottom: 0.8rem;">
            <div>
                <h1 style="margin: 0; font-size: 2.0rem; font-weight: 700; color: #f8fafc; letter-spacing: -0.02em;">RutaUrbana A*</h1>
                <p style="margin: 4px 0 0 0; color: #94a3b8; font-size: 0.95rem;">
                    Planificador Multimodal de Rutas Urbanas con Búsqueda Informada — Tuxtla Gutiérrez, Chiapas
                </p>
            </div>
            <div style="background-color: #151d30; border: 1px solid #263554; padding: 6px 14px; border-radius: 6px;">
                <span style="color: #38bdf8; font-weight: 600; font-size: 0.85rem; letter-spacing: 0.03em;">Red Urbana: 46 Nodos Georreferenciados</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- BARRA LATERAL (SIDEBAR DE CONFIGURACIÓN) ---
    with st.sidebar:
        st.markdown("### Parámetros de Ruta")

        # 1. Origen y Destino
        def_orig_idx = nodos_lista.index("parque_marimba") if "parque_marimba" in nodos_lista else 0
        def_dest_idx = nodos_lista.index("catedral_san_marcos") if "catedral_san_marcos" in nodos_lista else min(1, len(nodos_lista) - 1)

        origen = st.selectbox(
            "Punto de Origen:",
            options=nodos_lista,
            index=def_orig_idx,
            format_func=formatear_nombre_nodo,
            help="Selecciona el nodo de partida",
        )

        destino = st.selectbox(
            "Punto de Destino:",
            options=nodos_lista,
            index=def_dest_idx,
            format_func=formatear_nombre_nodo,
            help="Selecciona el nodo de llegada",
        )

        puntos_iguales = (origen == destino)
        if puntos_iguales:
            st.warning("Regla de negocio: El origen y el destino deben ser diferentes.")

        st.markdown("<div style='margin-top: 0.8rem;'></div>", unsafe_allow_html=True)

        # 2. Criterio de Búsqueda
        st.markdown("### Criterio de Optimización")
        opciones_criterio = {
            "rapida": "Ruta Más Rápida (Minimiza tiempo)",
            "barata": "Ruta Más Económica (Minimiza pasajes)",
            "pocos-transbordos": "Menor Cantidad de Transbordos",
            "accesible": "Ruta Accesible (Sin barreras físicas)",
            "personalizado": "Ponderación Personalizada de Pesos",
        }

        criterio_key = st.selectbox(
            "Función de Costo:",
            options=list(opciones_criterio.keys()),
            format_func=lambda k: opciones_criterio[k],
        )

        if criterio_key == "personalizado":
            st.markdown("##### Ajuste de Pesos:")
            w_tiempo = st.slider("Peso Tiempo (w1)", 0.0, 5.0, 1.0, 0.1)
            w_dinero = st.slider("Peso Dinero (w2)", 0.0, 5.0, 0.5, 0.1)
            w_transbordos = st.slider("Peso Transbordos (w3)", 0.0, 5.0, 2.0, 0.1)
            w_accesible = st.slider("Peso Accesibilidad (w4)", 0.0, 5.0, 0.5, 0.1)
            pesos = Pesos(tiempo=w_tiempo, dinero=w_dinero, abordaje=w_transbordos, accesibilidad=w_accesible)
        else:
            pesos = CRITERIOS_PREDEFINIDOS.get(criterio_key, Pesos())

        st.markdown("<div style='margin-top: 0.8rem;'></div>", unsafe_allow_html=True)

        # 3. Algoritmo (fijo en A*)
        st.markdown("### Algoritmo")
        st.markdown(
            "<p style='color:#94a3b8; font-size:0.85rem; margin:0;'>"
            "Algoritmo: <b style='color:#38bdf8;'>A* (heurística admisible)</b></p>",
            unsafe_allow_html=True,
        )

        st.markdown("<div style='margin-top: 1.0rem;'></div>", unsafe_allow_html=True)
        btn_calcular = st.button("Calcular Ruta Óptima", type="primary", width="stretch", disabled=puntos_iguales)

    # Validar regla de negocio en el área principal
    if puntos_iguales:
        st.info(
            "Regla de negocio activa: No se puede seleccionar una ubicación inicial como meta al mismo tiempo. "
            "Por favor, selecciona un punto de destino diferente al origen en el panel lateral."
        )
        return

    # Si se cambiaron los puntos respecto a un cálculo anterior, invalidar resultado previo
    if "resultado_guardado" in st.session_state and not btn_calcular:
        guardado = st.session_state["resultado_guardado"]
        if guardado.get("origen") != origen or guardado.get("destino") != destino:
            del st.session_state["resultado_guardado"]

    # Estado de sesión para persistir resultados al presionar el botón o mover el slider interactivo
    if btn_calcular:
        res_sol = astar(grafo, origen, destino, pesos)
        nodos_arbol, raiz_id, pasos_exp = extraer_arbol_y_pasos(grafo, origen, destino, pesos, "A*")

        st.session_state["resultado_guardado"] = {
            "res_sol": res_sol,
            "nodos_arbol": nodos_arbol,
            "raiz_id": raiz_id,
            "pasos_exp": pasos_exp,
            "origen": origen,
            "destino": destino,
            "pesos": pesos,
        }

    # Si aún no se ha presionado el botón para calcular ruta
    if "resultado_guardado" not in st.session_state:
        st.info(
            "Configura el origen, destino y criterios en el panel lateral y presiona "
            "**Calcular Ruta Óptima** para ejecutar los algoritmos y visualizar el recorrido paso a paso."
        )
        elementos_base = preparar_elementos_mapa(grafo)
        elementos_base.origen_id = origen
        elementos_base.destino_id = destino
        fig_base = crear_figura_mapa_plotly(
            elementos_base,
            modo="viajero",
            paso_idx=0,
        )
        st.plotly_chart(fig_base, width="stretch")
        return

    datos_sesion = st.session_state["resultado_guardado"]
    res_sol = datos_sesion["res_sol"]
    nodos_arbol = datos_sesion["nodos_arbol"]
    raiz_id = datos_sesion["raiz_id"]
    pasos_exp = datos_sesion["pasos_exp"]

    if res_sol is None:
        st.error(f"No existe una ruta viable entre {formatear_nombre_nodo(origen)} y {formatear_nombre_nodo(destino)} con los criterios seleccionados.")
        return

    # Elementos geométricos
    elementos = preparar_elementos_mapa(grafo, resultado=res_sol)

    # --- 1. SECCIÓN DE MÉTRICAS (KPI CARDS) ---
    # Acceso directo a las claves del contrato: si un nombre cambia, debe fallar a la vista.
    tiempo_total = res_sol.desglose["tiempo"]
    dinero_total = res_sol.desglose["dinero"]
    penalizacion_total = res_sol.desglose["penalizacion"]

    sub_tiempo = "Caminata + Espera + Traslado"
    if penalizacion_total > 0:
        sub_tiempo = f"Penalización de accesibilidad: {penalizacion_total:.2f}"

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Tiempo Estimado</div>
                <div class="metric-value">{tiempo_total:.1f} min</div>
                <div style="font-size: 11.5px; color: #64748b; margin-top: 2px;">{sub_tiempo}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Tarifa Total</div>
                <div class="metric-value">${dinero_total:.2f} MXN</div>
                <div style="font-size: 11.5px; color: #64748b; margin-top: 2px;">Gasto acumulado en pasajes</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Transbordos</div>
                <div class="metric-value">{res_sol.transbordos}</div>
                <div style="font-size: 11.5px; color: #64748b; margin-top: 2px;">Cambios de modalidad</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Abordajes</div>
                <div class="metric-value">{res_sol.abordajes}</div>
                <div style="font-size: 11.5px; color: #64748b; margin-top: 2px;">Pagos de abordaje cobrados</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col5:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Nodos Expandidos (A*)</div>
                <div class="metric-value">{res_sol.nodos_expandidos}</div>
                <div class="metric-delta">{res_sol.nodos_generados} generados</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-top: 1.2rem;'></div>", unsafe_allow_html=True)

    # --- PESTAÑAS PRINCIPALES SIN EMOJIS ---
    tab_mapa, tab_arbol, tab_itinerario = st.tabs([
        "Plano Urbano Interactivo",
        "Árbol de Búsqueda (IA)",
        "Itinerario Detallado",
    ])

    # --- PESTAÑA 1: MAPA URBANO INTERACTIVO ---
    with tab_mapa:
        ctrl_col1, ctrl_col2 = st.columns([1.5, 3])
        with ctrl_col1:
            modo_visual = st.radio(
                "Modo de Visualización:",
                ["Avance del Viajero", "Exploración del Algoritmo (IA)"],
                horizontal=False,
            )

        es_modo_exploracion = "Exploración" in modo_visual

        if es_modo_exploracion:
            total_pasos = max(0, len(pasos_exp) - 1)
        else:
            total_pasos = len(elementos.aristas_solucion)

        with ctrl_col2:
            paso_slider = st.slider(
                "Línea de Tiempo del Recorrido (Paso actual):",
                min_value=0,
                max_value=total_pasos,
                value=total_pasos,
                help="Avanza o retrocede los pasos de la búsqueda o del viaje",
            )

        # Banner descriptivo del paso actual
        if es_modo_exploracion and pasos_exp:
            p_actual = pasos_exp[paso_slider]
            nom_p = formatear_nombre_nodo(p_actual.nodo_actual)
            if p_actual.num_paso == 0:
                msg_step = f"<b>Búsqueda Inicial (Paso 0/{total_pasos}):</b> Origen en frontera: <b>{nom_p}</b> (f={p_actual.f:.1f})"
            elif p_actual.es_meta:
                msg_step = f"<b>Meta Alcanzada (Paso {paso_slider}/{total_pasos}):</b> Destino alcanzado en <b>{nom_p}</b> con costo óptimo total={p_actual.f:.2f}."
            else:
                msg_step = (
                    f"<b>Paso {paso_slider} de {total_pasos}:</b> Expandiendo <b>{nom_p}</b> | "
                    f"<b>f(n) = {p_actual.f:.1f}</b> (g={p_actual.g:.1f} + h={p_actual.h:.1f}) | "
                    f"<b>{len(p_actual.nodos_frontera)}</b> en frontera | "
                    f"<b>{len(p_actual.nodos_cerrados)}</b> explorados."
                )
            st.markdown(f"<div class='step-banner'>{msg_step}</div>", unsafe_allow_html=True)
            fig_mapa = crear_figura_mapa_plotly(
                elementos,
                modo="exploracion",
                paso_exploracion=p_actual,
            )
        else:
            if paso_slider == 0:
                nodo_actual_nombre = formatear_nombre_nodo(elementos.origen_id or "")
                msg_step = f"<b>Paso 0 de {total_pasos}:</b> Viajero situado en el punto de partida: <b>{nodo_actual_nombre}</b>."
            elif paso_slider == total_pasos:
                nodo_actual_nombre = formatear_nombre_nodo(elementos.destino_id or "")
                msg_step = f"<b>Paso {paso_slider} de {total_pasos}:</b> Llegada al destino: <b>{nodo_actual_nombre}</b>."
            else:
                tr_act = elementos.aristas_solucion[paso_slider - 1]
                nom_dest_tramo = formatear_nombre_nodo(tr_act["destino"])
                id_ruta = tr_act.get("ruta")
                medio_str = "a pie" if tr_act.get("tipo") == "CAMINANDO" else (f"en {formatear_nombre_ruta(id_ruta)}" if id_ruta else "en transporte público")
                msg_step = f"<b>Paso {paso_slider} de {total_pasos}:</b> Avanzando hacia <b>{nom_dest_tramo}</b> ({medio_str})."
            st.markdown(f"<div class='step-banner'>{msg_step}</div>", unsafe_allow_html=True)
            fig_mapa = crear_figura_mapa_plotly(
                elementos,
                modo="viajero",
                paso_idx=paso_slider,
            )

        st.plotly_chart(fig_mapa, width="stretch")

    # --- PESTAÑA 2: ÁRBOL DE BÚSQUEDA JERÁRQUICO ---
    with tab_arbol:
        st.markdown(
            """
            <div class="step-banner">
                <b>Jerarquía de Exploración (IA):</b>
                Las ramas y nodos en <span style="color:#10b981;"><b>Verde Esmeralda</b></span> corresponden a la <b>rama de solución óptima ganadora</b>.
                Los nodos en <span style="color:#3b82f6;"><b>Azul</b></span> fueron explorados en ramas alternas y en <span style="color:#f59e0b;"><b>Ámbar</b></span> quedaron en la frontera abierta.
                Pasa el cursor sobre cualquier nodo para ver sus costos <code>f(n) = g(n) + h(n)</code>.
            </div>
            """,
            unsafe_allow_html=True,
        )
        fig_arbol = crear_figura_arbol_plotly(nodos_arbol, raiz_id, algoritmo="A*")
        st.plotly_chart(fig_arbol, width="stretch")

    # --- PESTAÑA 3: ITINERARIO DETALLADO ---
    with tab_itinerario:
        st.markdown(f"### Itinerario Detallado: {formatear_nombre_nodo(origen)} hacia {formatear_nombre_nodo(destino)}")

        if not res_sol.acciones:
            st.info("El origen y el destino son el mismo punto: no hay tramos que recorrer.")
        else:
            for i, accion in enumerate(res_sol.acciones, start=1):
                st.markdown(
                    f"""
                    <div class="metric-card" style="margin-bottom: 8px;">
                        <div style="font-size: 13.5px; font-weight: 600; color: #e2e8f0;">
                            Paso {i}. {str(accion)}
                        </div>
                        <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">
                            Tiempo: <b>{accion.tiempo_min:.2f} min</b> &nbsp;|&nbsp;
                            Dinero: <b>${accion.dinero:.2f} MXN</b> &nbsp;|&nbsp;
                            Penalización: <b>{accion.penalizacion:.2f}</b>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            total_tiempo_it = sum(a.tiempo_min for a in res_sol.acciones)
            total_dinero_it = sum(a.dinero for a in res_sol.acciones)
            total_penalizacion_it = sum(a.penalizacion for a in res_sol.acciones)
            st.markdown(
                f"""
                <div class="metric-card" style="border-color: #3b82f6;">
                    <div class="metric-label">Totales del Itinerario</div>
                    <div class="metric-value">{total_tiempo_it:.1f} min &nbsp;·&nbsp; ${total_dinero_it:.2f} MXN</div>
                    <div style="font-size: 11.5px; color: #64748b; margin-top: 2px;">
                        Penalización de accesibilidad acumulada: {total_penalizacion_it:.2f}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


if __name__ == "__main__":
    main()
