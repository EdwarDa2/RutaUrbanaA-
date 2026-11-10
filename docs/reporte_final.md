# Reporte Final: RutaUrbana A*
## Planificador de Rutas Urbanas Multicriterio mediante Búsqueda Heurística

**Materia:** Inteligencia Artificial  
**Proyecto:** RutaUrbana A*  
**Equipo de Desarrollo:**  
- **Dev A:** Núcleo Algorítmico, Heurísticas y Estructura de Datos (Grafo)  
- **Dev B:** Interfaz CLI, Visualización Espacial, Análisis Experimental y Reporte  

---

## 1. Lógica General del Problema y Espacio de Estados

### 1.1 Definición del Problema
El sistema resuelve el problema de navegación y planificación de trayectos dentro de una **red urbana multimodal**, compuesta por tramos peatonales (caminata por calles) y líneas de transporte público (camión, metro o metrobús).

A diferencia de los problemas clásicos de camino más corto que minimizan exclusivamente la distancia geográfica, en el entorno urbano real los usuarios toman decisiones basadas en múltiples factores simultáneos. Por ello, se formula una función de **costo multicriterio**:

$$\text{Costo}(e) = w_1 \cdot \text{tiempo}(e) + w_2 \cdot \text{dinero}(e) + w_3 \cdot \text{transbordo}(e) + w_4 \cdot \text{penalización}(e)$$

Donde cada ponderador $w_i \ge 0$ refleja la preferencia del usuario:
* **Rápida:** $w_1 = 1.0, w_2 = 0.0, w_3 = 0.1, w_4 = 0.0$ (minimiza tiempo total).
* **Barata:** $w_1 = 0.2, w_2 = 1.0, w_3 = 0.5, w_4 = 0.0$ (minimiza el costo de pasajes y transbordos de pago).
* **Pocos transbordos:** $w_1 = 0.5, w_2 = 0.1, w_3 = 5.0, w_4 = 0.0$ (prioriza confort y continuidad en una sola línea).
* **Accesible:** $w_1 = 1.0, w_2 = 0.0, w_3 = 1.0, w_4 = 5.0$ (penaliza escaleras, puentes peatonales o pendientes pronunciadas).

### 1.2 Formulación del Espacio de Estados
Un nodo geográfico por sí solo no describe por completo el estado del viajero, ya que abordar o cambiar de transporte implica costos no locales (esperas y tarifas). Por ello, el espacio de estados se modela como:

$$s = \langle \text{nodo}, \text{modo\_actual} \rangle$$

Donde:
* $\text{nodo} \in V$: Identificador de la esquina, parada o estación.
* $\text{modo\_actual} \in \{\text{"CAMINANDO"}\} \cup \{\text{id\_ruta}_1, \text{id\_ruta}_2, \dots\}$: Modo o línea en la que se encuentra actualmente el agente.

#### Acciones del Agente:
1. **CAMINAR$(u, v)$:** Traslado a pie entre esquinas adyacentes conectadas por calles.
2. **ABORDAR$(u, \text{ruta}_k)$:** Subir a una unidad de transporte en una parada autorizada, pagando la tarifa correspondiente e incurriendo en el tiempo de espera inicial.
3. **BAJAR$(u, \text{ruta}_k)$:** Descender de la unidad para continuar a pie.
4. **TRANSBORDAR$(u, \text{ruta}_j, \text{ruta}_k)$:** Cambiar de una línea de transporte a otra en un nodo compartido.

---

## 2. Justificación de los Algoritmos de Búsqueda Evaluados

Para resolver este problema se evaluaron tres algoritmos representativos de la Inteligencia Artificial:

| Algoritmo | Categoría | Función de Evaluación | Garantía de Optimalidad | Comportamiento Espacial |
|---|---|---|---|---|
| **BFS** (Anchura) | No Informado | $f(n) = \text{profundidad}(n)$ | Solo si costos uniformes | Expande por niveles de aristas; no considera tiempos ni dinero. |
| **Dijkstra** (Costo Uniforme) | No Informado | $f(n) = g(n)$ | Sí, si $c(e) \ge 0$ | Expande concéntricamente en todas direcciones (onda circular). |
| **A\*** | Heurístico / Informado | $f(n) = g(n) + h(n)$ | Sí, si $h(n)$ es admisible | Enfoca la búsqueda hacia el destino guiado por la heurística. |

### ¿Por qué A\* es el algoritmo superior para este problema?
1. **Heterogeneidad de Costos:** Dado que el costo entre dos paradas de metro no equivale a caminar una cuadra, BFS queda descartado porque solo minimiza número de pasos, ignorando si un paso tarda 2 minutos o 20 minutos.
2. **Eficiencia Direccional:** Dijkstra encuentra la solución óptima garantizada, pero expande nodos en 360 grados sin importar dónde se localiza la meta. En cambio, A* incorpora la distancia estimada hacia el destino ($h(n)$), podando ramas que se alejan del objetivo.

---

## 3. Demostración Matemática de la Heurística Admisible

### 3.1 Definición de la Heurística
Para que A* garantice encontrar la ruta de costo mínimo sobre un grafo con múltiples modos de transporte a distintas velocidades, la función heurística $h(n)$ debe ser una **cota inferior optimista** del costo real restante $h^*(n)$:

$$h(n) = w_1 \cdot \left( \frac{\text{distancia\_euclidiana}(n, \text{destino})}{V_{\max}} \right)$$

Donde:
* $\text{distancia\_euclidiana}(n, \text{destino}) = \sqrt{(x_n - x_d)^2 + (y_n - y_d)^2}$ es la distancia en línea recta en metros.
* $V_{\max}$ es la velocidad máxima posible de cualquier vehículo en la red (ej. la velocidad de crucero del metro o metrobús en m/min).
* Se asume dinero $= 0$, transbordos $= 0$ y penalización $= 0$ como la mejor situación posible restante.

### 3.2 Demostración de Admisibilidad ($h(n) \le h^*(n)$)
1. **Propiedad de la Geometría Euclidiana:** La distancia en línea recta entre dos puntos en el plano representa la distancia mínima posible en cualquier espacio métrico:
   $$\text{distancia\_euclidiana}(n, \text{destino}) \le \text{distancia\_real\_grafo}(n, \text{destino})$$
2. **Propiedad de la Cota Superior de Velocidad:** Si la velocidad máxima de cualquier modo de transporte es $V_{\max}$, entonces para cualquier velocidad real $v \le V_{\max}$:
   $$\frac{\text{distancia\_real}}{v} \ge \frac{\text{distancia\_euclidiana}}{V_{\max}}$$
3. **Ponderación Multicriterio:** Dado que $w_i \ge 0$ y los costos de dinero, transbordo y penalización son no negativos ($c \ge 0$):
   $$h^*(n) \ge w_1 \cdot \text{tiempo\_real}^*(n) \ge w_1 \cdot \left( \frac{\text{distancia\_euclidiana}(n, \text{destino})}{V_{\max}} \right) = h(n)$$

Por tanto, queda demostrado que $h(n) \le h^*(n)$ para todo nodo $n$, lo que satisface la condición de **admisibilidad**.

### 3.3 Consistencia (Monotonía)
Para cualquier nodo $n$ y su sucesor $n'$ alcanzable con costo $c(n, a, n')$:
$$h(n) \le c(n, a, n') + h(n')$$
Por la desigualdad triangular en el plano euclidiano:
$$\text{dist}(n, d) \le \text{dist}(n, n') + \text{dist}(n', d)$$
Dividiendo entre $V_{\max}$ y multiplicando por $w_1$, la desigualdad se preserva. Al ser consistente, se garantiza que **ningún nodo es reabierto**, permitiendo una complejidad óptima de exploración.

---

## 4. Factor de Ramificación ($b$) y Profundidad ($d$)

### 4.1 Factor de Ramificación Medio ($b$)
Se mide como el grado de salida promedio del grafo extendido de estados:

$$b = \frac{1}{|V_S|} \sum_{s \in V_S} |\text{Sucesores}(s)|$$

* **En la red peatonal:** Cada esquina conecta típicamente con 2 a 4 calles adyacentes ($b_{\text{peatonal}} \approx 2.8$ a $3.5$).
* **En nodos multimodales (paradas/estaciones):** Desde una parada el agente tiene las opciones de caminar más las opciones de abordar cada línea disponible, incrementando el factor de ramificación local a $b \approx 4.5$ a $6.0$.
* **Factor medio global:** $b_{\text{promedio}} \approx 3.2$ a $3.8$.

### 4.2 Profundidad de la Solución ($d$)
La profundidad representa el número de transiciones de estado (tramos) que componen la ruta óptima:
* **Trayectos cortos:** $d = 3$ a $5$ tramos.
* **Trayectos medianos con transbordo:** $d = 8$ a $14$ tramos.
* **Trayectos largos de periferia a periferia:** $d = 18$ a $25$ tramos.

---

## 5. Análisis Experimental y Ahorro de Exploración

### 5.1 Metodología de Medición
Se ejecutaron los 16 casos de prueba del archivo `casos.json` sobre exactamente el mismo grafo, ejecutando 10 repeticiones por consulta para registrar tiempos promedio libres de fluctuaciones de CPU.

### 5.2 Métrica de Ahorro de Búsqueda
Se calculó la tasa de reducción de nodos expandidos lograda por A* frente a Dijkstra:

$$\text{Ahorro} = 1 - \frac{\text{Nodos Expandidos}_{A^*}}{\text{Nodos Expandidos}_{\text{Dijkstra}}}$$

### 5.3 Resultados Obtenidos
1. **Optimalidad:** En el 100% de los casos analizados, el costo encontrado por A* fue idéntico al de Dijkstra (diferencia $= 0.0$), corroborando empíricamente la admisibilidad de la heurística.
2. **Ahorro Promedio:** A* redujo la cantidad de nodos expandidos entre un **45% y un 75%** en comparación con Dijkstra en trayectos de media y larga distancia.
3. **Casos Límite:**
   - En trayectos peatonales muy cortos ($d \le 3$), la ventaja de A* es menor ($\approx 20\%$) debido a que el espacio de búsqueda es reducido.
   - Cuando el usuario asigna un peso de tiempo nulo ($w_1 = 0$) y prioriza únicamente dinero, $h(n)$ se reduce a 0. En este escenario, la heurística deja de aportar información y A* se comporta exactamente como Dijkstra, expandiendo la misma cantidad de nodos sin perder la optimalidad.

---

## 6. Persistencia y Almacenamiento del Sistema

El sistema genera 4 tipos de evidencia estructurada para su análisis:

1. **Tabla de Métricas en CSV (`resultados.csv`):**  
   Almacena 11 columnas por cada ejecución: `caso`, `origen`, `destino`, `algoritmo`, `pesos`, `costo_total`, `longitud`, `nodos_expandidos`, `nodos_generados`, `frontera_max`, `tiempo_ms`.
2. **Detalle de la Ruta en JSON (`detalle_ruta.json`):**  
   Itinerario paso a paso con las coordenadas de cada tramo, modo de transporte utilizado, transbordos y desglose de costo acumulado.
3. **Gráficas Estadísticas en PNG:**
   - `grafica_comparativa.png`: Gráfica de barras comparando el desempeño de los 3 algoritmos.
   - `grafica_escalabilidad.png`: Gráfica de curvas mostrando el crecimiento de tiempo y nodos ante grafos sintéticos de 100 a 10,000 nodos.
4. **Visualización Urbana en PNG (`mapa_ruta.png`):**
   - Tramos peatonales en líneas punteadas.
   - Rutas de transporte en colores normalizados por línea.
   - Ruta óptima resaltada con trazo continuo (verde para tramos peatonales, azul para transporte).
   - Nodos de transbordo señalizados con rombos amarillos y nodos explorados con halos semitransparentes.

---

## 7. Conclusión
El planificador multimodal **RutaUrbana A\*** demuestra cómo la formulación formal del espacio de estados y el diseño riguroso de una heurística admisible y consistente permiten resolver problemas logísticos urbanos complejos con eficiencia computacional muy superior a los métodos no informados, garantizando rutas óptimas personalizadas a las necesidades de tiempo, costo y accesibilidad del ciudadano.

