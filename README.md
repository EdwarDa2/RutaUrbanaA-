# RutaUrbana A* 🚇🚶🗺️

Planificador de rutas urbanas multimodales con optimización multicriterio y búsqueda informada mediante el algoritmo **A\***, comparado frente a **Dijkstra** (costo uniforme) y **BFS** (búsqueda en anchura).

---

## 📖 Descripción del Proyecto

**RutaUrbana A\*** resuelve el problema de encontrar la mejor ruta entre dos puntos en una red urbana multimodal (caminata peatonal y transporte público como camión o metro). A diferencia de los planificadores tradicionales basados únicamente en distancia o tiempo, este sistema evalúa una función de **costo multicriterio**:

$$\text{Costo} = w_1 \cdot \text{tiempo} + w_2 \cdot \text{dinero} + w_3 \cdot \text{transbordos} + w_4 \cdot \text{accesibilidad}$$

Donde los pesos $w_i \ge 0$ se ajustan según las preferencias del usuario (ruta más rápida, más económica, con menor cantidad de transbordos o accesible).

---

## 📁 Estructura del Repositorio

```text
RutaUrbanaA-/
├── core/                         # [Dev A] Núcleo algorítmico y matemático
│   ├── tipos.py                  # Tipos de datos compartidos (Estado, Pesos, ResultadoBusqueda)
│   ├── grafo.py                  # Representación de la red urbana multimodal
│   ├── heuristicas.py            # Heurística admisible (Distancia Euclidiana / Vmax)
│   ├── problema.py               # Definición formal del espacio de estados
│   └── algoritmos.py             # Implementación de A*, Dijkstra y BFS
├── datos/                        # [Dev A] Datos geográficos y rutas
│   ├── cargador.py               # Cargador y validador de archivos JSON
│   ├── zona_demo.json            # Mapa urbano de la zona demostrativa
│   ├── rutas_transporte.json     # Catálogo de líneas de transporte y frecuencias
│   └── generador_sintetico.py    # Generador de ciudades sintéticas de N nodos
├── ui/                           # [Dev B] Interfaz y visualización
│   └── mapa.py                   # Renderizado del mapa y rutas en PNG con matplotlib
├── analytics/                    # [Dev B] Análisis estadístico y experimentos
│   ├── exportador.py             # Generador de CSV, JSON y gráficas estadísticas
│   ├── experimentos.py           # Automatización de benchmarks entre algoritmos
│   └── casos.json                # Banco de 15 a 20 casos de prueba reales
├── tests/                        # Pruebas unitarias automatizadas con pytest
│   ├── test_exportador.py        # Pruebas de exportación a CSV, JSON y gráficas
│   ├── test_main.py              # Pruebas del CLI y validación de parámetros
│   └── test_mapa.py              # Pruebas de dibujo y cálculo espacial
├── main.py                       # [Dev B] Interfaz de línea de comandos (CLI)
├── requirements.txt              # Dependencias del proyecto (matplotlib, pytest)
└── README.md                     # Documentación general del proyecto
```

---

## ⚙️ Requisitos e Instalación

### Requisitos Previos
- **Python 3.10 o superior**.

### Instalación
1. Clonar el repositorio y situarse en la carpeta del proyecto:
   ```bash
   cd RutaUrbanaA-
   ```
2. Instalar las dependencias requeridas:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🖥️ Formas Sencillas de Ejecutar la Aplicación

El proyecto ofrece múltiples opciones pensadas para que cualquier evaluador, docente o usuario pueda ejecutarlo de inmediato sin complicaciones técnicas:

### ⚡ Opción 1: Un solo clic (Recomendada para Evaluación)
Haz doble clic sobre el archivo ejecutable por lotes:
```text
ejecutar_interfaz.bat
```
> **¿Qué hace automáticamente?**
> * Detecta tu instalación de Python (`python` o `py`).
> * Comprueba e instala automáticamente las librerías necesarias (`matplotlib`, `pytest`) si hicieran falta.
> * Inicia la interfaz gráfica de inmediato.

---

### 🪟 Opción 2: Modo silencioso sin ventana de consola
Si prefieres que la aplicación se abra directamente como un software de escritorio nativo (sin la ventana negra de CMD de fondo):
```text
ejecutar_sin_consola.vbs
```
*(Haz doble clic sobre este archivo en el Explorador de Windows).*

---

### 📦 Opción 3: Generar un Ejecutable Autónomo Windows (.EXE)
Si deseas generar un archivo `.exe` totalmente independiente para compartirlo o ejecutarlo en cualquier computadora sin necesidad de tener Python instalado:
1. Haz doble clic sobre:
   ```text
   crear_ejecutable.bat
   ```
2. El script compilará automáticamente el proyecto y creará el ejecutable en:
   ```text
   dist\RutaUrbanaAstar\RutaUrbanaAstar.exe
   ```

---

### 💻 Opción 4: Desde la Terminal o PowerShell
Si prefieres iniciar la interfaz visual por consola de comandos:
```bash
# Situarse en la carpeta del proyecto
cd RutaUrbanaA-

# Iniciar la interfaz gráfica
python app.py
```

---

## 🎮 Guía de Uso de la Interfaz Visual

La interfaz está dividida en dos paneles principales:

### 1. Panel Izquierdo: Configuración y Controles
* **1. Parámetros de Ruta:**
  * **Origen y Destino:** Elige entre los 46 puntos reales georreferenciados de Tuxtla Gutiérrez (ej. *Parque de la Marimba*, *Catedral de San Marcos*, *Plaza Crystal*, *UNACH*).
  * **Criterio de Optimización:**
    * `rapida`: Minimiza tiempo de viaje total.
    * `barata`: Minimiza costos y pasajes de transporte.
    * `pocos-transbordos`: Penaliza cambios de línea o abordajes repetidos.
    * `accesible`: Evita tramos con barreras físicas o pendientes.
  * **Algoritmo:** Selecciona $A^*$, Dijkstra, BFS o **Comparar Todos** para ver un análisis comparativo en tabla.
  * **Botón "Calcular Ruta":** Ejecuta los algoritmos instantáneamente.

* **2. Reproducción y Análisis IA (Paso a Paso):**
  * **Selector de Modo:**
    * `🔍 Búsqueda IA`: Muestra cómo el algoritmo razona y explora la ciudad, marcando en **ámbar** los nodos en la frontera (cola de prioridad), en **azul** los nodos explorados (cerrados) y en **amarillo/carmesí** el nodo actual con su costo $f(n) = g(n) + h(n)$.
    * `🚶 Viajero`: Muestra el viaje físico por la ruta resultante (tramos a pie en verde y transporte público en azul).
  * **Botonera de Control:**
    * `⏮` / `⏭`: Avanzar o retroceder paso a paso.
    * `▶ Animar` / `⏸ Pausar`: Reproducción automática continua.
    * `⚡ Completo`: Salta directamente al estado final completado.
    * `↺`: Reinicia la animación al inicio.
    * **Velocidad:** Configurable entre Rápida (300 ms), Normal (700 ms) y Lenta (1200 ms).

* **3. Itinerario y Métricas:**
  * Muestra el desglose detallado de cada acción del viaje, tiempos, costos, transbordos y el ahorro porcentual de nodos expandidos de $A^*$ frente a Dijkstra.

### 2. Panel Derecho: Pestañas Interactivas
* **🗺️ Plano Urbano Multimodal:** Mapa interactivo con nombres legibles anticolisión, tramos coloreados y barra de zoom/desplazamiento.
* **🌳 Árbol de Búsqueda (IA):** Diagrama jerárquico de exploración donde se aprecia el árbol completo de búsqueda con la **rama de solución óptima ganadora en verde esmeralda** y las ramas descartadas en azul/amarillo, acompañadas de sus valores $f = g + h$.

---

## 🚀 Guía de Uso del CLI por Terminal (`main.py`)

El punto de entrada principal es `main.py`, que ofrece múltiples opciones de consulta:

### 1. Búsqueda con criterios predefinidos
```bash
# Ruta más rápida (prioriza tiempo)
python main.py --origen "Biblioteca" --destino "Mercado" --criterio rapida

# Ruta más económica (prioriza minimizar tarifas de transporte)
python main.py --origen "Biblioteca" --destino "Mercado" --criterio barata

# Ruta con pocos transbordos (penaliza cambios de línea)
python main.py --origen "Parada Norte" --destino "Campus Sur" --criterio pocos-transbordos

# Ruta accesible (evita tramos con escaleras o pendientes)
python main.py --origen "Estación Central" --destino "Hospital" --criterio accesible
```

### 2. Búsqueda con ponderación manual de pesos
```bash
python main.py --origen "Biblioteca" --destino "Mercado" --pesos "tiempo=1.5 dinero=2.0 abordaje=5.0 accesibilidad=0.5"
```

### 3. Generación del mapa visual en imagen PNG
```bash
python main.py --origen "Biblioteca" --destino "Mercado" --criterio rapida --mapa --salida-mapa "mi_ruta.png"
```

### 4. Comparativa de algoritmos (A* vs. Dijkstra vs. BFS)
```bash
python main.py --origen "Biblioteca" --destino "Mercado" --comparar
```

### 5. Evaluación por lotes y exportación de analíticas
```bash
python main.py --casos analytics/casos.json --exportar resultados.csv
```

---

## 🧪 Ejecución de Pruebas Unitarias

Para correr la suite completa de pruebas automatizadas:

```bash
python -m pytest
```

Para ver la salida detallada con el nombre de cada prueba ejecutada:

```bash
python -m pytest -v
```

