"""RutaUrbana A* - Interfaz Gráfica de Usuario (GUI)

Aplicación visual interactiva construida con Tkinter y Matplotlib.
Permite al evaluador seleccionar origen, destino, criterios y algoritmos de forma intuitiva,
viendo el mapa urbano y el itinerario en tiempo real con un solo clic.
"""

from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import messagebox, ttk

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from core.algoritmos import astar, dijkstra, bfs
from core.tipos import Pesos
from datos.cargador import cargar_mapa
from main import CRITERIOS_PREDEFINIDOS, formatear_itinerario, formatear_resumen_metricas, formatear_tabla_comparativa
from ui.arbol import extraer_arbol_busqueda, extraer_arbol_y_pasos, dibujar_arbol_en_axes, PasoExploracion
from ui.mapa import COLORES_RUTAS, preparar_elementos_mapa, formatear_nombre_nodo, dibujar_paso_busqueda_en_mapa


class RutaUrbanaApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("RutaUrbana A* - Planificador Multicriterio")
        self.root.geometry("1200x780")
        self.root.minsize(1000, 680)

        # Cargar mapa
        self.ruta_mapa = os.path.join(os.path.dirname(__file__), "datos", "zona_demo.json")
        try:
            self.grafo = cargar_mapa(self.ruta_mapa)
            self.nodos_disponibles = sorted(list(self.grafo.nodos.keys()))
        except Exception as e:
            messagebox.showerror("Error al cargar mapa", f"No se pudo cargar '{self.ruta_mapa}':\n{e}")
            self.nodos_disponibles = []

        # Estado de animación y reproducción paso a paso
        self.resultado_actual = None
        self.elementos_actuales = None
        self.pasos_exploracion: list[PasoExploracion] = []
        self.modo_visual = "exploracion"
        self.algoritmo_actual = "A*"
        self.paso_actual = 0
        self.total_pasos = 0
        self.animando = False
        self.timer_animacion = None
        self.velocidad_ms = 700

        self._configurar_estilos()
        self._construir_interfaz()
        self._dibujar_mapa_inicial()

    def _configurar_estilos(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"), foreground="#1565c0")
        style.configure("Title.TLabel", font=("Segoe UI", 15, "bold"), foreground="#0d47a1")
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), background="#1e88e5", foreground="white")
        style.map("Accent.TButton", background=[("active", "#1565c0")])

    def _construir_interfaz(self):
        # Contenedor principal dividido en 2 columnas: panel izquierdo (controles) y derecho (mapa)
        panel_principal = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        panel_principal.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # --- PANEL IZQUIERDO: CONTROLES Y RESULTADOS ---
        frame_izq = ttk.Frame(panel_principal, padding="10")
        panel_principal.add(frame_izq, weight=1)

        # Título
        ttk.Label(frame_izq, text="RutaUrbana A*", style="Title.TLabel").pack(anchor="w", pady=(0, 2))
        ttk.Label(frame_izq, text="Planificador multimodal en red urbana", font=("Segoe UI", 9, "italic")).pack(anchor="w", pady=(0, 12))

        # Sección Selección
        ttk.Label(frame_izq, text="1. Parámetros del Viaje", style="Header.TLabel").pack(anchor="w", pady=(4, 6))

        # Origen
        ttk.Label(frame_izq, text="Origen:").pack(anchor="w")
        self.combo_origen = ttk.Combobox(frame_izq, values=self.nodos_disponibles, state="normal")
        self.combo_origen.pack(fill=tk.X, pady=(2, 8))
        if "parque_tuchtlan" in self.nodos_disponibles:
            self.combo_origen.set("parque_tuchtlan")
        elif self.nodos_disponibles:
            self.combo_origen.set(self.nodos_disponibles[0])

        # Destino
        ttk.Label(frame_izq, text="Destino:").pack(anchor="w")
        self.combo_destino = ttk.Combobox(frame_izq, values=self.nodos_disponibles, state="normal")
        self.combo_destino.pack(fill=tk.X, pady=(2, 8))
        if "plaza_las_americas" in self.nodos_disponibles:
            self.combo_destino.set("plaza_las_americas")
        elif len(self.nodos_disponibles) > 1:
            self.combo_destino.set(self.nodos_disponibles[1])

        # Criterio de Búsqueda
        ttk.Label(frame_izq, text="Criterio de Ponderación:").pack(anchor="w")
        self.criterios = list(CRITERIOS_PREDEFINIDOS.keys())
        self.combo_criterio = ttk.Combobox(frame_izq, values=self.criterios, state="readonly")
        self.combo_criterio.set("rapida")
        self.combo_criterio.pack(fill=tk.X, pady=(2, 8))

        # Algoritmo
        ttk.Label(frame_izq, text="Algoritmo de Búsqueda:").pack(anchor="w")
        self.algos = ["A* (Recomendado)", "Dijkstra (Costo Uniforme)", "BFS (Anchura)", "Comparar los 3"]
        self.combo_algo = ttk.Combobox(frame_izq, values=self.algos, state="readonly")
        self.combo_algo.set("A* (Recomendado)")
        self.combo_algo.pack(fill=tk.X, pady=(2, 12))

        # Botón Calcular
        btn_calcular = ttk.Button(frame_izq, text="Calcular Ruta", style="Accent.TButton", command=self.calcular_ruta)
        btn_calcular.pack(fill=tk.X, pady=(0, 10))

        # Sección 2: Control de Recorrido Paso a Paso
        ttk.Label(frame_izq, text="2. Reproducción y Análisis IA", style="Header.TLabel").pack(anchor="w", pady=(6, 4))
        
        frame_controles = ttk.LabelFrame(frame_izq, text="Control Paso a Paso", padding="6")
        frame_controles.pack(fill=tk.X, pady=(0, 8))

        # Selector de Modo Visual (Exploración IA vs Recorrido del Viajero)
        frame_modo = ttk.Frame(frame_controles)
        frame_modo.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(frame_modo, text="Modo visual:", font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT)
        self.var_modo_vista = tk.StringVar(value="exploracion")
        self.rb_viajero = ttk.Radiobutton(frame_modo, text="Viajero", value="viajero", variable=self.var_modo_vista, command=self._cambiar_modo_visual)
        self.rb_exploracion = ttk.Radiobutton(frame_modo, text="Búsqueda IA", value="exploracion", variable=self.var_modo_vista, command=self._cambiar_modo_visual)
        self.rb_viajero.pack(side=tk.RIGHT, padx=2)
        self.rb_exploracion.pack(side=tk.RIGHT, padx=2)

        # Etiqueta de estado del paso
        self.lbl_paso_info = ttk.Label(frame_controles, text="Selecciona puntos y pulsa Calcular.", font=("Segoe UI", 8, "italic"), foreground="#0d47a1")
        self.lbl_paso_info.pack(anchor="w", pady=(0, 4))

        # Botonera de control
        frame_botones = ttk.Frame(frame_controles)
        frame_botones.pack(fill=tk.X, pady=(2, 4))

        self.btn_ant = ttk.Button(frame_botones, text="⏮", width=3, command=self.paso_anterior, state="disabled")
        self.btn_ant.pack(side=tk.LEFT, padx=(0, 2))

        self.btn_play = ttk.Button(frame_botones, text="▶ Animar", width=9, command=self.toggle_reproducir, state="disabled")
        self.btn_play.pack(side=tk.LEFT, padx=2)

        self.btn_sig = ttk.Button(frame_botones, text="⏭", width=3, command=self.paso_siguiente, state="disabled")
        self.btn_sig.pack(side=tk.LEFT, padx=2)

        self.btn_instant = ttk.Button(frame_botones, text="⚡ Completo", width=10, command=self.modo_instantaneo, state="disabled")
        self.btn_instant.pack(side=tk.LEFT, padx=2)

        self.btn_reset = ttk.Button(frame_botones, text="↺", width=3, command=self.reiniciar_recorrido, state="disabled")
        self.btn_reset.pack(side=tk.LEFT, padx=(2, 0))

        # Selector de Velocidad
        frame_vel = ttk.Frame(frame_controles)
        frame_vel.pack(fill=tk.X, pady=(2, 2))
        ttk.Label(frame_vel, text="Velocidad:", font=("Segoe UI", 8)).pack(side=tk.LEFT)
        self.combo_vel = ttk.Combobox(frame_vel, values=["Rápida (300 ms)", "Normal (700 ms)", "Lenta (1200 ms)"], state="readonly", width=16)
        self.combo_vel.set("Normal (700 ms)")
        self.combo_vel.pack(side=tk.RIGHT)
        self.combo_vel.bind("<<ComboboxSelected>>", self._cambiar_velocidad)

        # Sección 3: Resultados e Itinerario
        ttk.Label(frame_izq, text="3. Itinerario y Métricas", style="Header.TLabel").pack(anchor="w", pady=(6, 4))
        
        self.txt_resultados = tk.Text(frame_izq, wrap=tk.WORD, height=14, font=("Consolas", 9), bg="#f5f7fa", relief=tk.SOLID, borderwidth=1)
        scrollbar = ttk.Scrollbar(frame_izq, orient=tk.VERTICAL, command=self.txt_resultados.yview)
        self.txt_resultados.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_resultados.pack(fill=tk.BOTH, expand=True)

        # --- PANEL DERECHO: PESTAÑAS (MAPA Y ÁRBOL DE BÚSQUEDA) ---
        self.notebook = ttk.Notebook(panel_principal)
        panel_principal.add(self.notebook, weight=3)

        # PESTAÑA 1: Plano Urbano Multimodal
        tab_mapa = ttk.Frame(self.notebook, padding="2")
        self.notebook.add(tab_mapa, text="Plano Urbano Multimodal")

        self.fig_mapa, self.ax_mapa = plt.subplots(figsize=(7, 6))
        self.fig_mapa.tight_layout()

        self.canvas_mapa = FigureCanvasTkAgg(self.fig_mapa, master=tab_mapa)
        self.canvas_widget_mapa = self.canvas_mapa.get_tk_widget()
        self.canvas_widget_mapa.pack(fill=tk.BOTH, expand=True)

        toolbar_mapa = NavigationToolbar2Tk(self.canvas_mapa, tab_mapa)
        toolbar_mapa.update()
        toolbar_mapa.pack(side=tk.BOTTOM, fill=tk.X)

        # PESTAÑA 2: Árbol de Búsqueda
        tab_arbol = ttk.Frame(self.notebook, padding="2")
        self.notebook.add(tab_arbol, text="Árbol de Búsqueda (IA)")

        frame_header_arbol = ttk.Frame(tab_arbol, padding="6")
        frame_header_arbol.pack(fill=tk.X)
        ttk.Label(
            frame_header_arbol,
            text="Jerarquía de Búsqueda: Verde = Rama Solución Óptima  |  Azul = Nodos Expandidos  |  Amarillo = En Frontera",
            font=("Segoe UI", 8, "bold"),
            foreground="#1565c0",
        ).pack(side=tk.LEFT)

        self.fig_arbol, self.ax_arbol = plt.subplots(figsize=(8, 6))
        self.fig_arbol.tight_layout()

        self.canvas_arbol = FigureCanvasTkAgg(self.fig_arbol, master=tab_arbol)
        self.canvas_widget_arbol = self.canvas_arbol.get_tk_widget()
        self.canvas_widget_arbol.pack(fill=tk.BOTH, expand=True)

        toolbar_arbol = NavigationToolbar2Tk(self.canvas_arbol, tab_arbol)
        toolbar_arbol.update()
        toolbar_arbol.pack(side=tk.BOTTOM, fill=tk.X)

    def _dibujar_mapa_inicial(self):
        """Dibuja el grafo base de la ciudad con nombres de puntos clave."""
        self.ax_mapa.clear()
        elementos = preparar_elementos_mapa(self.grafo)

        # Calles peatonales
        for i, (p1, p2) in enumerate(elementos.aristas_caminando):
            lbl = "Red peatonal (calles)" if i == 0 else ""
            self.ax_mapa.plot([p1[0], p2[0]], [p1[1], p2[1]], color="#cfd8dc", linestyle="--", linewidth=1.2, zorder=1, label=lbl)

        # Rutas de transporte
        for idx, (rid, segmentos) in enumerate(elementos.aristas_transporte.items()):
            col = COLORES_RUTAS[idx % len(COLORES_RUTAS)]
            for s_idx, (p1, p2) in enumerate(segmentos):
                lbl = f"Ruta {rid}" if s_idx == 0 else ""
                self.ax_mapa.plot([p1[0], p2[0]], [p1[1], p2[1]], color=col, alpha=0.35, linewidth=2.5, zorder=2, label=lbl)

        # Nodos y nombres legibles
        for nid, (x, y) in elementos.posiciones.items():
            nombre = formatear_nombre_nodo(nid)
            es_clave = any(c in nid for c in ["parque", "plaza", "catedral", "hospital", "unach", "palacio", "mercado"])
            if es_clave:
                self.ax_mapa.scatter(x, y, s=80, color="#1565c0", edgecolors="white", linewidths=1.2, zorder=4)
                self.ax_mapa.text(x, y + 15, nombre, fontsize=7.5, fontweight="bold", color="#1a237e", ha="center", zorder=5,
                                  bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.9, edgecolor="#90caf9", lw=0.8))
            else:
                self.ax_mapa.scatter(x, y, s=35, color="#90a4ae", edgecolors="white", linewidths=0.5, zorder=3)

        self.ax_mapa.set_title("Plano Urbano de Tuxtla Gutiérrez (Zona Demo)", fontsize=11, fontweight="bold")
        self.ax_mapa.set_xlabel("Coordenada X (metros)", fontsize=9)
        self.ax_mapa.set_ylabel("Coordenada Y (metros)", fontsize=9)
        self.ax_mapa.grid(True, linestyle=":", alpha=0.5)
        self.ax_mapa.set_aspect("equal", adjustable="datalim")
        self.fig_mapa.tight_layout()
        self.canvas_mapa.draw()

        # Árbol inicial
        dibujar_arbol_en_axes(self.ax_arbol, {}, None)
        self.fig_arbol.tight_layout()
        self.canvas_arbol.draw()

    def calcular_ruta(self):
        origen = self.combo_origen.get().strip()
        destino = self.combo_destino.get().strip()
        criterio = self.combo_criterio.get().strip()
        algo_opcion = self.combo_algo.get()

        if not origen or not destino:
            messagebox.showwarning("Campos incompletos", "Por favor seleccione un nodo de origen y uno de destino.")
            return

        if origen not in self.grafo.nodos:
            messagebox.showerror("Origen no válido", f"El nodo '{origen}' no existe en el mapa.")
            return

        if destino not in self.grafo.nodos:
            messagebox.showerror("Destino no válido", f"El nodo '{destino}' no existe en el mapa.")
            return

        if origen == destino:
            messagebox.showwarning(
                "Origen y Destino Idénticos",
                "Regla de negocio: No se puede seleccionar una ubicación inicial como meta al mismo tiempo.\n"
                "Por favor seleccione un punto de destino diferente al origen."
            )
            return

        pesos = CRITERIOS_PREDEFINIDOS.get(criterio, Pesos())

        self.txt_resultados.delete("1.0", tk.END)

        if "Comparar" in algo_opcion:
            # Modo comparativa
            res_astar = astar(self.grafo, origen, destino, pesos)
            res_dijkstra = dijkstra(self.grafo, origen, destino, pesos)
            res_bfs = bfs(self.grafo, origen, destino, pesos)

            resultados = [r for r in [res_astar, res_dijkstra, res_bfs] if r is not None]
            texto_comp = formatear_tabla_comparativa(resultados)

            ahorro_str = ""
            if res_astar and res_dijkstra and res_dijkstra.nodos_expandidos > 0:
                ahorro = (1.0 - (res_astar.nodos_expandidos / res_dijkstra.nodos_expandidos)) * 100.0
                ahorro_str = f"\nAhorro de A* vs Dijkstra: {ahorro:.1f}% menos nodos expandidos.\n"

            self.txt_resultados.insert(tk.END, texto_comp + ahorro_str)
            if res_astar:
                self.txt_resultados.insert(tk.END, formatear_itinerario(res_astar))
                self._preparar_recorrido_resultado(res_astar)
            else:
                messagebox.showinfo("Inalcanzable", "No se encontró ruta viable entre los puntos seleccionados.")
        else:
            # Modo algoritmo individual
            func = astar if "A*" in algo_opcion else (dijkstra if "Dijkstra" in algo_opcion else bfs)
            res = func(self.grafo, origen, destino, pesos)
            if res is None:
                self.txt_resultados.insert(tk.END, f"Destino inalcanzable desde '{origen}' hacia '{destino}'.")
                messagebox.showinfo("Inalcanzable", "No existe camino viable entre los nodos.")
                self._deshabilitar_controles()
                dibujar_arbol_en_axes(self.ax_arbol, {}, None)
                self.fig_arbol.tight_layout()
                self.canvas_arbol.draw()
                return

            self.txt_resultados.insert(tk.END, formatear_itinerario(res))
            self.txt_resultados.insert(tk.END, "\n" + formatear_resumen_metricas(res))
            self._preparar_recorrido_resultado(res)

        # Generar y dibujar Árbol de Búsqueda (IA) y pasos de exploración
        algo_arbol = "A*" if "Comparar" in algo_opcion else algo_opcion
        self.algoritmo_actual = algo_arbol
        nodos_arbol, raiz_id, self.pasos_exploracion = extraer_arbol_y_pasos(
            self.grafo, origen, destino, pesos, algo_arbol
        )
        dibujar_arbol_en_axes(self.ax_arbol, nodos_arbol, raiz_id, algoritmo=algo_arbol)
        self.fig_arbol.tight_layout()
        self.canvas_arbol.draw()

        # Actualizar visualización en el mapa según el modo seleccionado
        self._actualizar_limites_modo()
        self._dibujar_paso_actual()

    def _deshabilitar_controles(self):
        self.btn_ant.config(state="disabled")
        self.btn_play.config(state="disabled")
        self.btn_sig.config(state="disabled")
        self.btn_instant.config(state="disabled")
        self.btn_reset.config(state="disabled")
        self.lbl_paso_info.config(text="Sin ruta activa.")

    def _preparar_recorrido_resultado(self, resultado):
        """Prepara las estructuras y habilita la botonera para reproducir la ruta paso a paso."""
        self._pausar_animacion()
        self.resultado_actual = resultado
        self.elementos_actuales = preparar_elementos_mapa(self.grafo, resultado=resultado)
        self._actualizar_limites_modo()

        self.btn_ant.config(state="normal")
        self.btn_play.config(state="normal", text="▶ Animar")
        self.btn_sig.config(state="normal")
        self.btn_instant.config(state="normal")
        self.btn_reset.config(state="normal")

    def _cambiar_modo_visual(self):
        """Alterna entre ver la exploración del algoritmo y el recorrido del viajero."""
        self._pausar_animacion()
        self.modo_visual = self.var_modo_vista.get()
        self._actualizar_limites_modo()
        self._dibujar_paso_actual()

    def _actualizar_limites_modo(self):
        """Actualiza el número total de pasos según el modo activo."""
        if self.modo_visual == "exploracion" and self.pasos_exploracion:
            self.total_pasos = len(self.pasos_exploracion) - 1
        elif self.elementos_actuales:
            self.total_pasos = len(self.elementos_actuales.aristas_solucion)
        else:
            self.total_pasos = 0
        self.paso_actual = self.total_pasos

    def _dibujar_paso_actual(self):
        """Dibuja en el mapa el paso actual dependiendo del modo activo."""
        if self.modo_visual == "exploracion":
            self._dibujar_exploracion_en_paso(self.paso_actual)
        else:
            self._dibujar_recorrido_en_paso(self.paso_actual)

    def _cambiar_velocidad(self, event=None):
        val = self.combo_vel.get()
        if "300" in val:
            self.velocidad_ms = 300
        elif "1200" in val:
            self.velocidad_ms = 1200
        else:
            self.velocidad_ms = 700

    def toggle_reproducir(self):
        if self.animando:
            self._pausar_animacion()
        else:
            self._iniciar_animacion()

    def _iniciar_animacion(self):
        if not self.resultado_actual and not self.pasos_exploracion:
            return
        if self.paso_actual >= self.total_pasos:
            self.paso_actual = 0
            self._dibujar_paso_actual()
        self.animando = True
        self.btn_play.config(text="⏸ Pausar")
        self._ciclo_animacion()

    def _pausar_animacion(self):
        self.animando = False
        if self.timer_animacion:
            self.root.after_cancel(self.timer_animacion)
            self.timer_animacion = None
        self.btn_play.config(text="▶ Animar")

    def _ciclo_animacion(self):
        if not self.animando:
            return
        if self.paso_actual < self.total_pasos:
            self.paso_actual += 1
            self._dibujar_paso_actual()
            self.timer_animacion = self.root.after(self.velocidad_ms, self._ciclo_animacion)
        else:
            self._pausar_animacion()

    def paso_siguiente(self):
        self._pausar_animacion()
        if self.paso_actual < self.total_pasos:
            self.paso_actual += 1
            self._dibujar_paso_actual()

    def paso_anterior(self):
        self._pausar_animacion()
        if self.paso_actual > 0:
            self.paso_actual -= 1
            self._dibujar_paso_actual()

    def modo_instantaneo(self):
        self._pausar_animacion()
        self.paso_actual = self.total_pasos
        self._dibujar_paso_actual()

    def reiniciar_recorrido(self):
        self._pausar_animacion()
        self.paso_actual = 0
        self._dibujar_paso_actual()

    def _dibujar_exploracion_en_paso(self, paso_idx: int):
        """Dibuja el mapa mostrando el estado de exploración del algoritmo en el paso indicado."""
        if not self.pasos_exploracion or not self.elementos_actuales:
            return
        idx = max(0, min(paso_idx, len(self.pasos_exploracion) - 1))
        paso = self.pasos_exploracion[idx]
        total = len(self.pasos_exploracion) - 1

        dibujar_paso_busqueda_en_mapa(
            self.ax_mapa,
            self.elementos_actuales,
            paso,
            total,
            algoritmo=self.algoritmo_actual,
        )

        nom = formatear_nombre_nodo(paso.nodo_actual)
        if paso.num_paso == 0:
            self.lbl_paso_info.config(text=f"Búsqueda Inicial (0/{total}): Origen en Frontera ({nom})")
        elif paso.es_meta:
            self.lbl_paso_info.config(text=f"¡Paso {idx}/{total}: Meta alcanzada en '{nom}'!")
        else:
            self.lbl_paso_info.config(
                text=f"Paso {idx}/{total}: Expandiendo {nom} | f={paso.f:.1f} (g={paso.g:.1f}+h={paso.h:.1f}) | {len(paso.nodos_frontera)} en frontera"
            )

        self.fig_mapa.tight_layout()
        self.canvas_mapa.draw()

    def _dibujar_recorrido_en_paso(self, paso: int):
        """Dibuja el mapa mostrando el avance exacto del viajero en el paso actual."""
        if not self.grafo or not self.resultado_actual or not self.elementos_actuales:
            return

        self.ax_mapa.clear()
        elementos = self.elementos_actuales
        total = self.total_pasos

        # 1. Calles base
        for i, (p1, p2) in enumerate(elementos.aristas_caminando):
            lbl = "Red peatonal (calles)" if i == 0 else ""
            self.ax_mapa.plot([p1[0], p2[0]], [p1[1], p2[1]], color="#cfd8dc", linestyle="--", linewidth=1.2, zorder=1, label=lbl)

        # 2. Rutas de transporte base
        for idx, (rid, segmentos) in enumerate(elementos.aristas_transporte.items()):
            col = COLORES_RUTAS[idx % len(COLORES_RUTAS)]
            for s_idx, (p1, p2) in enumerate(segmentos):
                lbl = f"Ruta {rid}" if s_idx == 0 else ""
                self.ax_mapa.plot([p1[0], p2[0]], [p1[1], p2[1]], color=col, alpha=0.28, linewidth=2.2, zorder=2, label=lbl)

        # 3. Tramos recorridos hasta este paso
        tramos_activos = elementos.aristas_solucion[:paso]
        caminando_etiquetado = False
        transporte_etiquetado = False
        for tramo in tramos_activos:
            p1 = tramo["p1"]
            p2 = tramo["p2"]
            if tramo["tipo"] == "CAMINANDO":
                lbl = "Tramo recorrido: A pie" if not caminando_etiquetado else ""
                caminando_etiquetado = True
                self.ax_mapa.plot([p1[0], p2[0]], [p1[1], p2[1]], color="#2e7d32", linewidth=5.0, zorder=5, label=lbl)
            else:
                lbl = "Tramo recorrido: En transporte" if not transporte_etiquetado else ""
                transporte_etiquetado = True
                self.ax_mapa.plot([p1[0], p2[0]], [p1[1], p2[1]], color="#1565c0", linewidth=5.0, zorder=5, label=lbl)

            # Flechas indicadoras de avance
            mx = (p1[0] + p2[0]) / 2.0
            my = (p1[1] + p2[1]) / 2.0
            dx = (p2[0] - p1[0]) * 0.05
            dy = (p2[1] - p1[1]) * 0.05
            self.ax_mapa.annotate("", xy=(mx + dx, my + dy), xytext=(mx - dx, my - dy),
                                  arrowprops=dict(arrowstyle="->", color="black", lw=2.0, mutation_scale=13), zorder=6)

        # 4. Determinar nodo actual donde se encuentra el viajero
        nodo_viajero = elementos.origen_id
        if paso > 0 and paso <= len(elementos.aristas_solucion):
            nodo_viajero = elementos.aristas_solucion[paso - 1]["destino"]

        nodos_recorridos_ids = {elementos.origen_id}
        for tr in tramos_activos:
            nodos_recorridos_ids.add(tr["origen"])
            nodos_recorridos_ids.add(tr["destino"])

        hitos_principales = {"parque_marimba", "catedral_san_marcos", "plaza_crystal", "hospital_regional", "parque_tuchtlan", "plaza_las_americas", "parque_cana_hueca"}

        # 5. Dibujar nodos con capas de profundidad
        for nid, (x, y) in elementos.posiciones.items():
            nombre = formatear_nombre_nodo(nid)
            es_viajero = (nid == nodo_viajero)
            es_origen = (nid == elementos.origen_id)
            es_destino = (nid == elementos.destino_id)
            es_transbordo = (nid in elementos.nodos_transbordo and nid in nodos_recorridos_ids)

            if es_viajero:
                # Marcador brillante pulsante del viajero
                self.ax_mapa.scatter(x, y, s=360, color="#ffd600", edgecolors="#b71c1c", linewidths=3.0, zorder=12, label="Posición del Viajero")
                self.ax_mapa.annotate(
                    f"VIAJERO AQUÍ:\n{nombre}",
                    xy=(x, y),
                    xytext=(x, y + 48),
                    fontsize=9.5,
                    fontweight="bold",
                    color="#b71c1c",
                    ha="center",
                    va="bottom",
                    zorder=13,
                    bbox=dict(boxstyle="round,pad=0.35", facecolor="#fff9c4", edgecolor="#f57f17", lw=2.2, alpha=0.98),
                    arrowprops=dict(arrowstyle="->", color="#f57f17", lw=2.0),
                )
            elif es_origen:
                self.ax_mapa.scatter(x, y, s=260, color="#00c853", edgecolors="black", linewidths=2.2, zorder=8, label="Origen")
                self.ax_mapa.text(x, y + 25, f"ORIGEN:\n{nombre}", fontsize=8.5, fontweight="bold", ha="center", va="bottom", zorder=9,
                                  bbox=dict(boxstyle="round,pad=0.3", facecolor="#e8f5e9", edgecolor="#2e7d32", lw=1.5, alpha=0.9))
            elif es_destino:
                self.ax_mapa.scatter(x, y, s=260, color="#d50000", edgecolors="black", linewidths=2.2, zorder=8, label="Destino")
                self.ax_mapa.text(x, y + 25, f"DESTINO:\n{nombre}", fontsize=8.5, fontweight="bold", ha="center", va="bottom", zorder=9,
                                  bbox=dict(boxstyle="round,pad=0.3", facecolor="#ffebee", edgecolor="#c62828", lw=1.5, alpha=0.9))
            elif es_transbordo:
                self.ax_mapa.scatter(x, y, s=150, color="#ffd600", marker="D", edgecolors="black", linewidths=1.5, zorder=7)
                self.ax_mapa.text(x, y - 26, f"Transbordo:\n{nombre}", fontsize=7.5, fontweight="bold", ha="center", va="top", zorder=8,
                                  bbox=dict(boxstyle="round,pad=0.2", facecolor="#fffde7", edgecolor="#fbc02d", lw=1.0, alpha=0.9))
            elif nid in nodos_recorridos_ids:
                self.ax_mapa.scatter(x, y, s=90, color="#ff9800", edgecolors="black", linewidths=1.0, zorder=6)
                self.ax_mapa.text(x, y - 22, nombre, fontsize=7.0, fontweight="bold", color="#e65100", ha="center", va="top", zorder=7,
                                  bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor="#ff9800", lw=0.8, alpha=0.85))
            elif nid in hitos_principales:
                self.ax_mapa.scatter(x, y, s=50, color="#78909c", edgecolors="white", linewidths=0.8, zorder=3)
                self.ax_mapa.text(x, y + 14, nombre, fontsize=6.8, color="#37474f", ha="center", va="bottom", zorder=3,
                                  bbox=dict(boxstyle="round,pad=0.15", facecolor="white", alpha=0.75, edgecolor="#cfd8dc", lw=0.5))
            else:
                self.ax_mapa.scatter(x, y, s=25, color="#cfd8dc", edgecolors="white", linewidths=0.5, zorder=2)

        # 6. Actualizar texto de información del paso
        nom_viajero = formatear_nombre_nodo(nodo_viajero)
        if paso == 0:
            self.lbl_paso_info.config(text=f"Paso 0 de {total}: En Origen ({nom_viajero})")
        elif paso == total:
            self.lbl_paso_info.config(text=f"Paso {paso} de {total}: ¡Llegada al Destino ({nom_viajero})!")
        else:
            self.lbl_paso_info.config(text=f"Paso {paso} de {total}: En {nom_viajero}")

        # Título y márgenes
        nom_orig = formatear_nombre_nodo(elementos.origen_id or "")
        nom_dest = formatear_nombre_nodo(elementos.destino_id or "")
        self.ax_mapa.set_title(f"Recorrido del Viajero: {nom_orig} -> {nom_dest} (Paso {paso}/{total})", fontsize=11, fontweight="bold", pad=12)
        self.ax_mapa.set_xlabel("Coordenada X (metros)", fontsize=9)
        self.ax_mapa.set_ylabel("Coordenada Y (metros)", fontsize=9)
        self.ax_mapa.grid(True, linestyle=":", alpha=0.45)
        self.ax_mapa.set_aspect("equal", adjustable="box")

        todas_x = [pos[0] for pos in elementos.posiciones.values()]
        todas_y = [pos[1] for pos in elementos.posiciones.values()]
        if todas_x and todas_y:
            margen_x = (max(todas_x) - min(todas_x)) * 0.08
            margen_y = (max(todas_y) - min(todas_y)) * 0.18
            self.ax_mapa.set_xlim(min(todas_x) - margen_x, max(todas_x) + margen_x)
            self.ax_mapa.set_ylim(min(todas_y) - margen_y, max(todas_y) + margen_y)

        handles, labels = self.ax_mapa.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        if by_label:
            self.ax_mapa.legend(by_label.values(), by_label.keys(), loc="upper right", fontsize=8, framealpha=0.9)

        self.fig_mapa.tight_layout()
        self.canvas_mapa.draw()


def main():
    root = tk.Tk()
    app = RutaUrbanaApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

