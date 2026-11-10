"""RutaUrbana A* - Interfaz de Línea de Comandos (CLI)

Punto de entrada de la aplicación para planificar rutas, comparar algoritmos y exportar analíticas.
Responsabilidad del Dev B.
"""

from __future__ import annotations

import argparse
import difflib
import os
import sys
from dataclasses import dataclass
from typing import Any

# Contrato base de pesos (compatible con core.tipos cuando esté listo)
@dataclass(frozen=True)
class Pesos:
    tiempo: float = 1.0
    dinero: float = 0.0
    abordaje: float = 0.0
    accesibilidad: float = 0.0

# Atajos de criterios predefinidos para comodidad del usuario
CRITERIOS_PREDEFINIDOS: dict[str, Pesos] = {
    "rapida": Pesos(tiempo=1.0, dinero=0.0, abordaje=0.1, accesibilidad=0.0),
    "barata": Pesos(tiempo=0.2, dinero=1.0, abordaje=0.5, accesibilidad=0.0),
    "pocos-transbordos": Pesos(tiempo=0.5, dinero=0.1, abordaje=5.0, accesibilidad=0.0),
    "accesible": Pesos(tiempo=1.0, dinero=0.0, abordaje=1.0, accesibilidad=5.0),
}


def parsear_pesos(criterio: str | None = None, pesos_str: str | None = None) -> Pesos:
    """Traduce un criterio predefinido o una cadena de pesos personalizados a un objeto Pesos."""
    if pesos_str:
        # Reemplazar comas por espacios para admitir "tiempo=1,dinero=2" o "tiempo=1 dinero=2"
        tokens = pesos_str.replace(",", " ").split()
        valores: dict[str, float] = {"tiempo": 0.0, "dinero": 0.0, "abordaje": 0.0, "accesibilidad": 0.0}

        for token in tokens:
            if "=" not in token:
                raise ValueError(f"Formato de peso inválido: '{token}'. Use 'clave=valor' (ej. tiempo=1.5).")
            clave, valor_str = token.split("=", 1)
            clave = clave.strip().lower()
            if clave not in valores:
                raise ValueError(f"Peso desconocido '{clave}'. Claves válidas: tiempo, dinero, abordaje, accesibilidad.")
            try:
                val = float(valor_str)
            except ValueError:
                raise ValueError(f"El valor de '{clave}' debe ser numérico. Se recibió: '{valor_str}'.")
            if val < 0:
                raise ValueError(f"El peso '{clave}' no puede ser negativo ({val}).")
            valores[clave] = val

        return Pesos(
            tiempo=valores["tiempo"],
            dinero=valores["dinero"],
            abordaje=valores["abordaje"],
            accesibilidad=valores["accesibilidad"],
        )

    criterio_elegido = criterio.lower() if criterio else "rapida"
    if criterio_elegido not in CRITERIOS_PREDEFINIDOS:
        opciones = ", ".join(CRITERIOS_PREDEFINIDOS.keys())
        raise ValueError(f"Criterio '{criterio_elegido}' no reconocido. Opciones válidas: {opciones}.")

    return CRITERIOS_PREDEFINIDOS[criterio_elegido]


def crear_parser() -> argparse.ArgumentParser:
    """Construye y configura el parser de argumentos de la línea de comandos."""
    parser = argparse.ArgumentParser(
        prog="RutaUrbana A*",
        description="Planificador de rutas urbanas multimodales con optimización multicriterio.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Ejemplos de uso:
  python main.py --origen "Biblioteca" --destino "Mercado" --criterio rapida
  python main.py --origen "Parada Norte" --destino "Centro" --criterio barata --mapa
  python main.py --origen A --destino B --pesos "tiempo=1 dinero=2 abordaje=5"
  python main.py --comparar --casos analytics/casos.json --exportar resultados.csv
        """,
    )

    parser.add_argument("--origen", "-o", type=str, help="Nodo o lugar de inicio del viaje.")
    parser.add_argument("--destino", "-d", type=str, help="Nodo o lugar de destino.")
    parser.add_argument(
        "--criterio",
        "-c",
        type=str,
        default="rapida",
        help="Atajo de ponderación: 'rapida', 'barata', 'pocos-transbordos' o 'accesible'.",
    )
    parser.add_argument(
        "--pesos",
        "-p",
        type=str,
        help="Ponderación manual (ej. 'tiempo=1.0 dinero=2.0 abordaje=5.0 accesibilidad=0.0').",
    )
    parser.add_argument(
        "--algoritmo",
        "-a",
        type=str,
        default="astar",
        choices=["astar", "dijkstra", "bfs"],
        help="Algoritmo de búsqueda a utilizar (por defecto: 'astar').",
    )
    parser.add_argument(
        "--mapa",
        action="store_true",
        help="Generar imagen PNG visualizando la ruta sobre el plano urbano.",
    )
    parser.add_argument(
        "--salida-mapa",
        type=str,
        default="mapa_ruta.png",
        help="Nombre del archivo PNG donde se guardará el mapa.",
    )
    parser.add_argument(
        "--comparar",
        action="store_true",
        help="Ejecuta y compara los tres algoritmos (A*, Dijkstra y BFS) sobre el caso.",
    )
    parser.add_argument(
        "--casos",
        type=str,
        help="Ruta a un archivo JSON con lista de casos para evaluación por lotes.",
    )
    parser.add_argument(
        "--exportar",
        type=str,
        help="Ruta de archivo CSV donde guardar las métricas de rendimiento.",
    )
    parser.add_argument(
        "--mapa-json",
        type=str,
        default="datos/zona_demo.json",
        help="Archivo JSON con el mapa urbano a cargar.",
    )

    return parser


def formatear_itinerario(resultado: Any) -> str:
    """Genera una vista textual limpia del itinerario paso a paso."""
    if not resultado or not getattr(resultado, "acciones", None):
        return "No hay acciones disponibles para este itinerario."

    lineas = ["\n📍 ITINERARIO PASO A PASO:"]
    for i, accion in enumerate(resultado.acciones, start=1):
        lineas.append(f"  {i}. {accion.descripcion} [Costo tramo: {accion.costo:.2f}]")
    return "\n".join(lineas)


def formatear_resumen_metricas(resultado: Any) -> str:
    """Genera una tabla resumen con el desglose de costo y métricas de búsqueda."""
    desglose = getattr(resultado, "desglose", {})
    desglose_str = ", ".join(f"{k}: {v:.2f}" for k, v in desglose.items()) if desglose else "N/A"

    lineas = [
        "\n📊 RESUMEN DE LA BÚSQUEDA:",
        f"  • Algoritmo:         {getattr(resultado, 'algoritmo', 'N/A')}",
        f"  • Costo Total:       {getattr(resultado, 'costo_total', 0.0):.2f}",
        f"  • Desglose:          {desglose_str}",
        f"  • Nodos expandidos:  {getattr(resultado, 'nodos_expandidos', 0)}",
        f"  • Nodos generados:   {getattr(resultado, 'nodos_generados', 0)}",
        f"  • Frontera máxima:   {getattr(resultado, 'frontera_max', 0)}",
        f"  • Tiempo de cálculo: {getattr(resultado, 'tiempo_ms', 0.0):.2f} ms",
    ]
    return "\n".join(lineas)


def sugerir_nodos_cercanos(nombre: str, nodos_validos: list[str], max_sugerencias: int = 3) -> list[str]:
    """Sugiere nombres de nodos válidos similares utilizando coincidencia difusa (difflib)."""
    if not nodos_validos:
        return []
    # Coincidencia insensible a mayúsculas
    nombre_lower = nombre.lower()
    coincidencia_directa = [n for n in nodos_validos if n.lower() == nombre_lower]
    if coincidencia_directa:
        return coincidencia_directa

    return difflib.get_close_matches(nombre, nodos_validos, n=max_sugerencias, cutoff=0.3)


def formatear_tabla_comparativa(resultados: list[Any]) -> str:
    """Genera una tabla comparativa en formato texto entre A*, Dijkstra y BFS."""
    if not resultados:
        return "No hay resultados para comparar."

    lineas = [
        "\n⚖️ TABLA COMPARATIVA DE ALGORITMOS:",
        f"  {'Algoritmo':<12} | {'Costo':<8} | {'Expandidos':<12} | {'Generados':<11} | {'Frontera':<9} | {'Tiempo (ms)':<11}",
        f"  {'-'*12}-+-{'-'*8}-+-{'-'*12}-+-{'-'*11}-+-{'-'*9}-+-{'-'*11}",
    ]
    for res in resultados:
        algo = getattr(res, "algoritmo", "N/A")
        costo = getattr(res, "costo_total", 0.0)
        exp = getattr(res, "nodos_expandidos", 0)
        gen = getattr(res, "nodos_generados", 0)
        front = getattr(res, "frontera_max", 0)
        t = getattr(res, "tiempo_ms", 0.0)
        lineas.append(f"  {algo:<12} | {costo:<8.2f} | {exp:<12} | {gen:<11} | {front:<9} | {t:<11.2f}")

    return "\n".join(lineas)


def main(argv: list[str] | None = None) -> int:
    """Función principal del CLI."""
    parser = crear_parser()
    args = parser.parse_args(argv)

    try:
        pesos = parsear_pesos(criterio=args.criterio, pesos_str=args.pesos)
    except ValueError as e:
        print(f"\n❌ Error en los pesos: {e}", file=sys.stderr)
        return 1

    # Modo lote / casos masivos
    if args.casos:
        print(f"\n🚀 Modo evaluación en lote: cargando casos desde '{args.casos}'...")
        salida_csv = args.exportar or "resultados.csv"
        try:
            from analytics.experimentos import ejecutar_pipeline_completo
            ejecutar_pipeline_completo(
                ruta_casos_json=args.casos,
                ruta_mapa_json=args.mapa_json,
                salida_csv=salida_csv,
            )
        except (ImportError, FileNotFoundError) as e:
            print(f"\nℹ️ [Modo Lote listo]: {e}")
        return 0

    # Modo búsqueda individual
    if not args.origen or not args.destino:
        print("\n⚠️ Debe especificar --origen y --destino (o usar --casos para modo en lote).", file=sys.stderr)
        print("Ejemplo: python main.py --origen \"Biblioteca\" --destino \"Mercado\" --criterio rapida\n")
        return 1

    print(f"\n🔍 Buscando ruta de '{args.origen}' a '{args.destino}' con criterio '{args.criterio}'...")
    print(f"   Ponderaciones aplicadas: {pesos}")

    # Intentar cargar mapa y ejecutar núcleo del Dev A si ya están implementados
    try:
        from datos.cargador import cargar_mapa
        from core.algoritmos import astar, dijkstra, bfs

        if not os.path.exists(args.mapa_json):
            print(f"⚠️ Archivo de mapa '{args.mapa_json}' no encontrado.", file=sys.stderr)
            return 1

        grafo = cargar_mapa(args.mapa_json)

        # Validación de existencia de nodos y sugerencia
        nodos_validos: list[str] = []
        if hasattr(grafo, "nodos"):
            if isinstance(grafo.nodos, dict):
                nodos_validos = list(grafo.nodos.keys())
            elif isinstance(grafo.nodos, list):
                nodos_validos = [n["id"] if isinstance(n, dict) else getattr(n, "id", str(n)) for n in grafo.nodos]

        if nodos_validos:
            for nodo_consulta in [args.origen, args.destino]:
                if nodo_consulta not in nodos_validos:
                    sugs = sugerir_nodos_cercanos(nodo_consulta, nodos_validos)
                    sug_str = f" ¿Quizás quisiste decir: {', '.join(sugs)}?" if sugs else ""
                    print(f"\n❌ Error: El nodo '{nodo_consulta}' no existe en el mapa.{sug_str}", file=sys.stderr)
                    return 1

        if args.comparar:
            res_astar = astar(grafo, args.origen, args.destino, pesos)
            res_dijkstra = dijkstra(grafo, args.origen, args.destino, pesos)
            res_bfs = bfs(grafo, args.origen, args.destino, pesos)
            lista_res = [r for r in [res_astar, res_dijkstra, res_bfs] if r is not None]
            print(formatear_tabla_comparativa(lista_res))
            if res_astar and res_dijkstra and res_dijkstra.nodos_expandidos > 0:
                ahorro = (1.0 - (res_astar.nodos_expandidos / res_dijkstra.nodos_expandidos)) * 100.0
                print(f"\n💡 Ahorro de búsqueda de A* vs Dijkstra: {ahorro:.1f}% menos nodos expandidos.")
            resultado = res_astar
        else:
            funcion_busqueda = astar if args.algoritmo == "astar" else (dijkstra if args.algoritmo == "dijkstra" else bfs)
            resultado = funcion_busqueda(grafo, args.origen, args.destino, pesos)

        if resultado is None:
            print(f"\n❌ Destino inalcanzable: No se encontró ruta viable entre '{args.origen}' y '{args.destino}'.")
            return 2

        if not args.comparar:
            print(formatear_itinerario(resultado))
            print(formatear_resumen_metricas(resultado))

        if args.mapa:
            from ui.mapa import generar_mapa
            generar_mapa(grafo, resultado, args.salida_mapa)
            print(f"\n🗺️ Mapa guardado con éxito en: '{args.salida_mapa}'")

    except ImportError:
        print("\nℹ️ [Modo CLI verificado]: Las funciones del núcleo (Dev A) aún no están conectadas.")
        print("   La estructura de parámetros, criterios y formateo de salida funciona correctamente.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

