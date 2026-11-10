"""Módulo de experimentación, benchmarking y evaluación de rendimiento.

Responsabilidad del Dev B: ejecuta comparaciones empíricas entre A*, Dijkstra y BFS,
mide tiempos promediados, valida optimalidad y calcula tasas de ahorro de búsqueda.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Callable

from analytics.exportador import guardar_resultado_csv, grafica_comparativa, grafica_escalabilidad
from main import Pesos


def calcular_ahorro_nodos(expandidos_astar: int, expandidos_dijkstra: int) -> float:
    """Calcula la tasa de ahorro de exploración de A* respecto a Dijkstra:
    Ahorro = 1 - (expandidos_A* / expandidos_Dijkstra).
    """
    if expandidos_dijkstra <= 0:
        return 0.0
    return 1.0 - (expandidos_astar / float(expandidos_dijkstra))


def ejecutar_caso_con_algoritmo(
    grafo: Any,
    origen: str,
    destino: str,
    pesos: Any,
    algoritmo_func: Callable,
    repeticiones: int = 10,
) -> Any:
    """Ejecuta un algoritmo sobre un caso promediando el tiempo de ejecución en varias corridas."""
    resultado = None
    tiempos_ms: list[float] = []

    for _ in range(max(1, repeticiones)):
        t_inicio = time.perf_counter()
        res = algoritmo_func(grafo, origen, destino, pesos)
        t_fin = time.perf_counter()
        tiempos_ms.append((t_fin - t_inicio) * 1000.0)
        resultado = res

    if resultado is None:
        return None

    # Asignar tiempo promedio de ejecución
    tiempo_promedio = sum(tiempos_ms) / len(tiempos_ms)
    # Si el objeto es inmutable (dataclass frozen), podemos usar getattr o recrear un dict
    return resultado, tiempo_promedio


def ejecutar_experimento_completo(
    casos: list[dict[str, Any]],
    grafo: Any,
    algoritmos: dict[str, Callable] | None = None,
    pesos: Any = None,
    repeticiones: int = 10,
) -> dict[str, Any]:
    """Ejecuta los tres algoritmos sobre todos los casos especificados y recopila métricas."""
    if pesos is None:
        pesos = Pesos(tiempo=1.0, dinero=0.0, abordaje=0.1, accesibilidad=0.0)

    # Si no se proporcionan funciones simuladas, intentar importar las del Dev A
    if algoritmos is None:
        from core.algoritmos import astar, dijkstra, bfs
        algoritmos = {"A*": astar, "Dijkstra": dijkstra, "BFS": bfs}

    filas_csv: list[dict[str, Any]] = []
    diferencias_costo = 0
    ahorros_lista: list[float] = []
    resultados_por_caso: dict[str, dict[str, Any]] = {}

    for c in casos:
        cid = c.get("id") or f"{c.get('origen')}_{c.get('destino')}"
        origen = c["origen"]
        destino = c["destino"]
        resultados_por_caso[cid] = {}

        costo_astar = None
        costo_dijkstra = None
        exp_astar = 0
        exp_dijkstra = 0

        for nombre_algo in ["A*", "Dijkstra", "BFS"]:
            func = algoritmos.get(nombre_algo)
            if not func:
                continue

            ejecucion = ejecutar_caso_con_algoritmo(grafo, origen, destino, pesos, func, repeticiones)
            if ejecucion is None:
                continue

            res, tiempo_promedio_ms = ejecucion
            costo_total = float(getattr(res, "costo_total", 0.0))
            nodos_exp = int(getattr(res, "nodos_expandidos", 0))
            nodos_gen = int(getattr(res, "nodos_generados", 0))
            frontera = int(getattr(res, "frontera_max", 0))
            longitud = len(getattr(res, "ruta", []))

            if nombre_algo == "A*":
                costo_astar = costo_total
                exp_astar = nodos_exp
            elif nombre_algo == "Dijkstra":
                costo_dijkstra = costo_total
                exp_dijkstra = nodos_exp

            filas_csv.append({
                "caso": cid,
                "origen": origen,
                "destino": destino,
                "algoritmo": nombre_algo,
                "pesos": f"t={pesos.tiempo},d={pesos.dinero},a={pesos.abordaje}",
                "costo_total": costo_total,
                "longitud": longitud,
                "nodos_expandidos": nodos_exp,
                "nodos_generados": nodos_gen,
                "frontera_max": frontera,
                "tiempo_ms": tiempo_promedio_ms,
            })

            resultados_por_caso[cid][nombre_algo] = res

        # Validar consistencia y optimalidad entre A* y Dijkstra
        if costo_astar is not None and costo_dijkstra is not None:
            if abs(costo_astar - costo_dijkstra) > 1e-4:
                diferencias_costo += 1

            ahorro = calcular_ahorro_nodos(exp_astar, exp_dijkstra)
            ahorros_lista.append(ahorro)

    ahorro_promedio = (sum(ahorros_lista) / len(ahorros_lista)) if ahorros_lista else 0.0

    return {
        "filas_csv": filas_csv,
        "diferencias_costo_astar_dijkstra": diferencias_costo,
        "ahorro_promedio": ahorro_promedio,
        "resultados_por_caso": resultados_por_caso,
    }


def ejecutar_experimento_escalabilidad(
    generador_func: Callable[[int], Any],
    tamanos: list[int],
    algoritmo_func: Callable,
    pesos: Any = None,
    repeticiones: int = 5,
) -> list[dict[str, Any]]:
    """Evalúa la escalabilidad generando grafos sintéticos de tamaño creciente."""
    if pesos is None:
        pesos = Pesos(tiempo=1.0, dinero=0.0, abordaje=0.0, accesibilidad=0.0)

    mediciones: list[dict[str, Any]] = []

    for n in tamanos:
        grafo_n = generador_func(n)
        tiempos: list[float] = []
        nodos_exp = 0

        for _ in range(max(1, repeticiones)):
            t0 = time.perf_counter()
            # En ciudades sintéticas se busca entre extremos o nodos 0 y n-1
            res = algoritmo_func(grafo_n, "nodo_0", f"nodo_{n-1}", pesos)
            t1 = time.perf_counter()
            tiempos.append((t1 - t0) * 1000.0)
            if res:
                nodos_exp = int(getattr(res, "nodos_expandidos", 0))

        tiempo_prom = sum(tiempos) / len(tiempos) if tiempos else 0.0
        mediciones.append({
            "tamano": n,
            "tiempo_ms": tiempo_prom,
            "nodos_expandidos": nodos_exp,
        })

    return mediciones


def ejecutar_pipeline_completo(
    ruta_casos_json: str = "analytics/casos.json",
    ruta_mapa_json: str = "datos/zona_demo.json",
    salida_csv: str = "resultados.csv",
    salida_png_grafica: str = "grafica_comparativa.png",
) -> None:
    """Pipeline integral que lee casos, ejecuta algoritmos y exporta tablas y gráficas."""
    if not os.path.exists(ruta_casos_json):
        raise FileNotFoundError(f"Archivo de casos no encontrado: '{ruta_casos_json}'")

    with open(ruta_casos_json, mode="r", encoding="utf-8") as f:
        casos = json.load(f)

    from datos.cargador import cargar_mapa
    from core.algoritmos import astar, dijkstra, bfs

    grafo = cargar_mapa(ruta_mapa_json)
    algos = {"A*": astar, "Dijkstra": dijkstra, "BFS": bfs}

    print(f"🔬 Ejecutando {len(casos)} casos sobre BFS, Dijkstra y A*...")
    reporte = ejecutar_experimento_completo(casos, grafo, algos)

    guardar_resultado_csv(reporte["filas_csv"], salida_csv)
    print(f"📄 Resultados guardados en CSV: '{salida_csv}'")

    grafica_comparativa(reporte["filas_csv"], salida_png_grafica)
    print(f"📊 Gráfica comparativa guardada en: '{salida_png_grafica}'")
    print(f"✨ Diferencias de costo A* vs Dijkstra: {reporte['diferencias_costo_astar_dijkstra']} (0 esperado)")
    print(f"✨ Ahorro de exploración promedio de A*: {reporte['ahorro_promedio']*100:.1f}%")

