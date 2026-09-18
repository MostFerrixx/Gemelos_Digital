# PLAN DE QA — Configuración web → simulador → visor

> **Documento vivo.** Se actualiza a medida que se ejecutan las pruebas: se
> agregan casos que falten, se quitan los que sobren y se registra cada
> resultado en la sección 9. Última actualización: 2026-09-18.

## 0. Estado actual (se actualiza en cada interacción)

**Objetivo inmediato:** Bloque 1 — Carga de Trabajo.
**Último cerrado:** H-01 corregido y reprobado (18/09).
**Hallazgos abiertos:** H-02, H-03, H-05.

### Modo de trabajo (pedido del Director, 18/09)

Cada interacción tiene **un objetivo inmediato** y este documento marca la
ruta. Ciclo por hallazgo:

1. Se detecta y se registra (sección 10) con evidencia y causa raíz.
2. Si es un error, **se corrige cuanto antes** (no se acumula para el final).
3. **Se reprueba** el caso que lo detectó y se deja la evidencia.
4. Recién entonces se sigue con lo próximo del plan.

Cada cosa que se descubre alimenta este documento, que es a la vez la ruta y
el registro de todo lo hecho.

## 1. Objetivo

Responder con evidencia a la sospecha del Director:

> *"Muchas de las configuraciones de la web no están funcionando y el simulador
> toma valores por defecto en vez del comportamiento configurado."*

Para cada control de la web se verifica la cadena completa:

```
UI web  ──(1)──►  config de la corrida  ──(2)──►  comportamiento del motor  ──(3)──►  lo que muestra el visor
```

Una configuración **funciona** solo si pasa los tres eslabones. Si falla
cualquiera, es un hallazgo.

## 2. Reglas del juego

1. **Toda configuración se hace desde la UI web**, con el navegador, como la
   haría un usuario. Prohibido editar `config.json` o archivos a mano para
   preparar un caso. (Leer archivos para *verificar* sí está permitido.)
2. La corrida se lanza con **Run Simulation** (usa una copia temporal y no toca
   `config.json`), salvo en los casos que prueban justamente **Aplicar
   Configuración**.
3. **Una variable por caso**, contra una corrida de **control** (canónico sin
   cambios). Las pruebas combinadas (sección 7) cambian varias a propósito.
4. Las corridas desde la web **no fijan semilla**: dos corridas iguales dan
   números distintos. Por eso los resultados esperados son **estructurales**
   (algo aparece o no aparece, un tope se respeta, una fórmula se cumple
   exacta) o con **margen explícito**. Cuando haga falta rigor estadístico se
   usa la pestaña Experimentos A/B, que sí usa semillas pareadas.
   **Calibrado en el bloque 0:** entre corridas idénticas la duración total
   varió de 6.772 a 7.833 s (±8% alrededor de la media) y la cantidad de
   tareas de 603 a 625. Regla: **nunca se juzga un efecto por la duración de
   una sola corrida** si la diferencia esperada es menor al 30%; en ese caso
   se usa A/B.
5. Todo lo que modifica datos reales (Aplicar Excel, coordenadas de zonas y
   muelles, Aplicar Configuración) se hace con **backup previo y restauración
   posterior**, verificada con el gate de regresión.
6. **Los errores se corrigen apenas se confirman** (ver "Modo de trabajo") y
   se reprueba el caso antes de seguir. Si la corrección no es obvia o cambia
   el diseño, se le consulta al Director antes.
7. **No se crean ni editan archivos `.py` del proyecto mientras corre una
   simulación**: el servidor de desarrollo se reinicia solo y cancela la
   corrida (lección del bloque 0).

## 3. Método de verificación

### Nivel 1 — Transmisión (UI → corrida)

La primera línea del `.jsonl` (`SIMULATION_START`) guarda la configuración con
la que corrió el motor (`config`). Se compara el valor elegido en la UI contra:

- el archivo temporal de la corrida (`temp_web/run_config_*.json`), y
- `config` de la metadata del `.jsonl`.

**Pasa** si el valor llega idéntico (o con la conversión documentada, p. ej.
`10.0 → 10`). **Falla** si llega el default, llega otro valor o no llega.

### Nivel 2 — Efecto (corrida → comportamiento)

Se mide en el `.jsonl` (y el Excel de resultados cuando aplique) una
**firma observable** de la configuración: algo que solo puede ocurrir si el
motor la usó. Ejemplos: la duración exacta de un pick según la fórmula; que
ningún tour mezcle zonas; que todas las entregas vayan a la zona 3.

Herramienta: `scripts/qa/analizar_replay.py` (se construye en el bloque 0).
Resume una corrida (config efectiva, duración, WOs, tours, picks por área y por
agente, entregas por zona, camiones, putaway, colisiones, duraciones de pick) y
permite comparar dos corridas.

### Nivel 3 — Visor (comportamiento → pantalla)

1. Se carga la corrida en el visor.
2. Se eligen **5 instantes al azar con operarios en movimiento o trabajando**
   (no ociosos) — la herramienta los propone a partir del `.jsonl`.
3. En cada instante se compara, **para cada operario**, la celda según el
   `.jsonl` con la celda que dibuja el visor (estado interno del visor +
   `/api/snapshot`), y se toma una captura.
4. Además, cuando el caso lo pida, se verifica un elemento visual propio de la
   configuración (camiones, pallets en staging, panel de inbound, etc.).

**Pasa** si las posiciones coinciden en los 5 instantes (tolerancia: 0 celdas
en reposo, 1 celda en movimiento por interpolación) y el estado (idle,
picking, moving) coincide.

### Severidad de los hallazgos

| Nivel | Significado |
|---|---|
| **CRÍTICO** | La configuración se ignora: el motor usa un default o un valor distinto al elegido |
| **MAYOR** | Llega y se usa, pero el efecto es parcial o incorrecto |
| **MENOR** | Problema de la UI o del visor que no altera la simulación |
| **OBS** | Observación de diseño (configurable que falta, texto confuso, etc.) |

## 4. Inventario de configuraciones de la web

Columna *Lector*: dónde el motor lee la clave (verificado en el código).
Columna *Firma observable*: qué se mide en el nivel 2.

### Pestaña 1 — Carga de Trabajo

| Control | Clave | Lector | Firma observable |
|---|---|---|---|
| Modo de generación | `order_generation_mode` | `order_strategies` | Estocástico: pedidos `ORD-xxxx` inventados. Determinista: los `order_id` del archivo |
| Archivo de órdenes | `order_file_path` | `order_strategies` | `order_id` y SKU de las WOs = los del archivo |
| Política de cumplimiento | `fulfillment_policy` | `order_strategies` | Con un ítem inválido: parcial lo descarta solo a él; todo-o-nada descarta el pedido |
| Total de órdenes | `total_ordenes` | `warehouse` | Cantidad de `order_id` distintos = N |
| Distribución por clase (5 %) | `distribucion_tipos` | `order_strategies` | Proporción de WOs por clase de SKU ≈ % (margen ±8 pp con 300 órdenes) |

### Pestaña 2 — Estrategias

| Control | Clave | Lector | Firma observable |
|---|---|---|---|
| Estrategia de asignación | `dispatch_strategy` | `dispatcher` | Plan: la 1.ª WO de cada tour es la de menor secuencia pendiente del área. Global: la más barata desde la posición. Cercanía: dentro del radio |
| Radio / paso / máx. expansiones | `radio_*` | `dispatcher._estrategia_cercania` | Distancia de la 1.ª WO al operario ≤ radio + expansiones × paso |
| Tipo de tour | `tour_type` | `dispatcher` | Simple: ningún tour mezcla `staging_id`. Mixto: puede mezclar |
| Ruteo anti-colisión | `congestion.enabled/mode` | `warehouse`, `operators` | Encendido: nunca dos operarios en la misma celda al mismo tiempo. Apagado: aparecen superposiciones |
| Subsistema outbound | `outbound.enabled` | `outbound` | Encendido: eventos de camión y pallets en staging. Apagado: no existen |
| Intervalo de camión | `outbound.truck_interval` | `outbound` | Separación entre salidas de camión ≈ intervalo |
| Capacidad de camión | `outbound.truck_capacity` | `outbound` | Pallets por camión ≤ capacidad |
| Perfil de velocidad | `tiempos.*` (preset) | `operators` | Los 3 campos toman los valores del perfil |
| Tiempo por celda | `tiempos.time_per_cell` | `operators` | Tiempo de cada paso de un operario a pie = valor |
| Factor montacargas | `tiempos.speed_factor_forklift` | `operators` | Tiempo por paso de montacargas = celda × factor |
| Horquilla | `tiempos.tiempo_horquilla` | `operators` | Pick de montacargas = pick + 2 × horquilla |
| Fórmula de pick (base, unidad, volumen, kg, mínimo) | `tiempos.pick_time_model` | `operators._compute_pick_time` | Duración de cada pick = fórmula **exacta** (sin variabilidad) |
| Clases de manejo (mult, recargo, pack × 6) | `tiempos.clases_manejo` | `operators` | Pick = fórmula × mult + recargo; descarga + pack |
| Velocidad según carga (3 campos) | `tiempos.velocidad_por_carga` | `operators` | Operario cargado tarda más por paso; montacargas no (salvo casilla) |
| Variabilidad humana (CV) | `tiempos.variabilidad` | `operators` | Picks idénticos dejan de durar lo mismo; CV medido ≈ CV configurado |

### Pestaña 3 — Flota de Agentes

| Control | Clave | Lector | Firma observable |
|---|---|---|---|
| Equipo por área | `work_area_equipment` | `core.work_areas` | Las WOs de un área solo las toma ese tipo de equipo |
| Generar Flota por Defecto | `agent_types` | `core.fleet` | Aparece la flota estándar |
| Cantidad por grupo | `agent_types[].` (n entradas) | `core.fleet` | Cantidad de `agent_id` distintos por tipo |
| Capacidad | `agent_types[].capacity` | `operators`, `warehouse` | `cargo_volume` nunca supera la capacidad; tamaño de tareas del área |
| Tiempo de descarga | `agent_types[].discharge_time` | `operators` | Duración de la descarga en staging |
| Prioridades de área | `agent_types[].work_area_priorities` | `dispatcher` | El agente agota su área de prioridad 1 antes de la 2 |
| Cobertura de áreas | (validación) | UI | Área sin agente capaz: no deja correr |

### Pestaña 4 — Layout y Datos

| Control | Efecto | Firma observable |
|---|---|---|
| Archivo Layout / Examinar | `layout_file` | El visor dibuja el mapa elegido; el motor rutea sobre él |
| Archivo de Secuencia / Examinar | `sequence_file` + validación | Resumen del Excel subido |
| Aplicar Excel | reconstruye `warehouse.db` | Cambios del Excel aparecen en la simulación; backup y restauración |
| Datos maestros en uso / tablas | lectura | Coinciden con `warehouse.db` |
| Cargar Work Areas | desplegables de Flota | Aparecen las áreas del Excel |

### Pestaña 5 — Outbound Staging

| Control | Clave | Firma observable |
|---|---|---|
| Reparto por zona (7 %) | `outbound_staging_distribution` | Proporción de WOs/entregas por `staging_id` ≈ % |
| Destino → Zona | `destino_staging_map` | (Determinista con `destino`) todos los pedidos de un destino van a su zona |
| Coordenadas de zonas (Guardar ubicaciones) | `warehouse.db` | Los operarios descargan en la celda nueva |

### Pestaña 6 — Inbound

| Control | Clave | Firma observable |
|---|---|---|
| Activar inbound | `inbound.enabled` | Aparecen camiones de entrada, pallets y tareas de putaway |
| Modo de llegadas | `inbound.arrival_mode` | Determinista: camiones y horas del ASN. Estocástico: sintéticos |
| Archivo ASN | `inbound.asn_file_path` | `truck_id` y horas = las del archivo |
| Intervalo / cantidad / pallets / unidades | `inbound.*` | Llegadas cada intervalo; N camiones × P pallets × U unidades |
| Descarga por pallet | `inbound.unload_time_per_pallet` | Separación entre pallets del mismo camión |
| Carga del pallet por el operario | `inbound.putaway_load_time` | Duración de la carga en el muelle |
| Prioridad de la flota | `inbound.putaway_priority` | Recepción primero: la espera pallet→agente baja mucho |
| Cross-docking | `inbound.cross_dock_enabled` | (Determinista) aparecen WOs `WO-XD-*`; fill-rate efectivo > apertura |
| Estrategia de slotting | `inbound.slotting_strategy` | Destinos de putaway distintos por estrategia (cercana: menor distancia) |
| Coordenadas de muelles | `warehouse.db` | Los camiones descargan en la celda nueva |

### Pestaña 7 — Optimización y Pestaña 8 — Experimentos A/B

| Control | Firma observable |
|---|---|
| Trials, jobs | Se corren N trials, con hasta J en paralelo |
| Costos y penalizaciones | Cambian el score; con el montacargas carísimo, el mejor trial usa menos montacargas |
| Config A / B, réplicas, semilla | A = B → "sin diferencia significativa"; A ≠ B con efecto grande → "significativa"; misma semilla → mismos números |

### Barra superior

| Botón | Firma observable |
|---|---|
| Run Simulation | Corre lo que está en pantalla y **no** modifica `config.json` |
| Aplicar Configuración | Escribe `config.json` (con backup); guardar sin cambios no altera el archivo |
| Default | Vuelve todo a los valores por defecto (sin aplicar) |
| Importar | Carga un `.json` al formulario (incluye bloques que la UI no edita) |
| Guardar / Cargar / Gestionar | Un preset guardado vuelve idéntico al cargarlo |
| Restart | Reinicia el servidor (BK-10: problema conocido) |
| Abrir Visor | Abre el visor con la última corrida |

### 4.1 Configuración que existe en el motor pero NO tiene control en la web

Por el principio rector #2, todo lo que el cliente no puede ajustar desde la
web es un hallazgo de configurabilidad (**OBS**). Se valida en el bloque 10
que estas claves al menos **se conserven** al guardar desde la web.

| Clave | Estado |
|---|---|
| `personas`, `equipos`, `perfiles`, `cambio_de_perfil`, `estacionamientos` | Plan INIT-11 F10 (solo por Importar) |
| `congestion.spawn_offset`, `staggered_start`, `timewindow.*` | Parámetros técnicos de la capa anti-colisión |
| `outbound.loading_time`, `zone_capacity_default`, `slot_wait_alert`, `slot_poll_dt`, `dwell_scaffold`, `dispatch_policy` | Parámetros del muelle de salida |
| `tiempos.cell_size_m`, `tiempos.speed_factor_ground` | La UI los preserva pero no los muestra |
| `cercania_tour_mode` | Descartado (BK-03); evaluar si se elimina |
| `priority_dispatch_enabled`, `waves` | Prioridad de pedidos y olas (INIT-4): sin control en la web |
| `fleet_defaults` | Defaults de flota (BK-06) |

## 5. Casos de prueba por bloque

Formato: **ID — qué se cambia en la UI → resultado esperado** (N1 / N2 / N3).
Salvo indicación, todo lo demás queda en el canónico.

### Bloque 0 — Método y línea base

| ID | Caso | Esperado |
|---|---|---|
| QA-0.1 | **Control**: Run Simulation sin tocar nada | N1: `config` de la metadata = `config.json`. N2: termina, 300 órdenes, todas las WOs completadas. N3: 5 instantes, posiciones del visor = JSON |
| QA-0.2 | Control repetido (3 corridas) | N2: mismas firmas estructurales que QA-0.1; se mide la variación natural de la duración para calibrar márgenes |
| QA-0.3 | Herramienta de análisis sobre el replay del gate (semilla 42) | Resultado idéntico en dos pasadas (la herramienta es determinista) |

### Bloque 1 — Carga de Trabajo

| ID | Caso | Esperado |
|---|---|---|
| QA-1.1 | Total de órdenes 50 | N1: 50. N2: 50 `order_id` distintos. N3: visor muestra el total de WOs coherente |
| QA-1.2 | Total de órdenes 600 | N2: 600 pedidos; duración ≈ 2× el control (±25%) |
| QA-1.3 | Distribución 100% Pequeño | N2: 100% de las WOs con SKU de clase `pequeno` |
| QA-1.4 | Distribución 100% Extra grande | N2: 100% `extra_grande`; picks más largos que en QA-1.3 (mult 2.2 + 15 s) |
| QA-1.5 | Distribución 20/20/20/20/20 | N2: cada clase 20% ±8 pp |
| QA-1.6 | Distribución que suma 90% | La UI bloquea Run y Aplicar con un mensaje claro |
| QA-1.7 | Determinista con archivo válido | N2: `order_id` y SKU = los del archivo; cantidad de pedidos = archivo |
| QA-1.8 | Determinista + Envío Parcial, archivo con 1 SKU inexistente | N2: el pedido sale sin ese ítem; vista previa lo informa |
| QA-1.9 | Determinista + Todo o Nada, mismo archivo | N2: ese pedido no aparece |
| QA-1.10 | Volver a Estocástico tras cargar archivo | N1: `order_generation_mode = stochastic`; el archivo no se usa |

### Bloque 2 — Despacho y tours

| ID | Caso | Esperado |
|---|---|---|
| QA-2.1 | Ejecución de Plan (canónico) | N2: la 1.ª WO de cada tour es la de menor `pick_sequence` pendiente en el área prioritaria del agente |
| QA-2.2 | Optimización Global | N2: la 1.ª WO es la de menor costo desde la posición; distancia media al 1.er pick < Plan |
| QA-2.3 | Cercanía, radio 100 | N2: 1.ª WO dentro del radio (o expansión justificada) |
| QA-2.4 | Cercanía, radio 5, máx. expansiones 0 | N2: ningún primer pick fuera de 5 celdas… salvo el respaldo a todo el almacén; documentar el comportamiento real |
| QA-2.5 | Cercanía, radio 5, paso 5, 2 expansiones | N2: distancias ≤ 15 o respaldo |
| QA-2.6 | Tour Simple + reparto 50/50 entre zonas 1 y 2 | N2: **ningún** tour mezcla zonas |
| QA-2.7 | Tour Mixto + mismo reparto | N2: existen tours con más de una zona |

### Bloque 3 — Motor avanzado

| ID | Caso | Esperado |
|---|---|---|
| QA-3.1 | Anti-colisión encendido (canónico) | N2: 0 instantes con dos operarios en la misma celda (salvo spawn/staging documentado) |
| QA-3.2 | Anti-colisión apagado | N1: `congestion.enabled=false`. N2: aparecen superposiciones; N3: se ven operarios superpuestos |
| QA-3.3 | Outbound encendido | N2: eventos de camión, pallets en staging. N3: el visor muestra pallets/camiones |
| QA-3.4 | Outbound encendido, intervalo 30 s | N2: salidas cada ~30 s |
| QA-3.5 | Outbound encendido, intervalo 600 s | N2: salidas cada ~600 s; más espera de slot |
| QA-3.6 | Outbound encendido, capacidad 2 | N2: ningún camión con más de 2 pallets |

### Bloque 4 — Tiempos

| ID | Caso | Esperado |
|---|---|---|
| QA-4.1 | Perfil Demo | N1: 0.1 / 0.8 / 2 |
| QA-4.2 | Perfil Real | N1: 1.0 / 0.5 / 8. N2: duración total mucho mayor que Demo |
| QA-4.3 | Tiempo por celda 0.5 (personalizado) | N1: 0.5. N2: tiempo por paso a pie = 0.5 s |
| QA-4.4 | Factor montacargas 0.25 | N2: paso de montacargas = celda × 0.25 |
| QA-4.5 | Horquilla 20 s | N2: pick de montacargas = pick de fórmula + 40 s |
| QA-4.6 | Base 30, resto igual | N2: **cada** pick = fórmula exacta con base 30 |
| QA-4.7 | Por unidad 10 | N2: fórmula exacta; picks de cantidad alta crecen |
| QA-4.8 | Por kg 0 | N2: el peso deja de influir |
| QA-4.9 | Mínimo 60 | N2: ningún pick < 60 s |
| QA-4.10 | Por volumen 0.5 | N2: fórmula exacta con término de volumen |
| QA-4.11 | Clases: Pequeño mult 3, recargo 20 | N2: picks de `pequeno` = fórmula × 3 + 20; el resto igual |
| QA-4.12 | Clases: Pack de Mediano 25 | N2: descargas de `mediano` +25 s |
| QA-4.13 | Clase GENERAL modificada | N2: afecta solo SKUs sin clase (documentar si no existen en el catálogo) |
| QA-4.14 | Velocidad según carga ON | N2: operario a pie cargado tarda más por paso; montacargas igual |
| QA-4.15 | Velocidad según carga ON + aplicar a montacargas | N2: el montacargas cargado también se enlentece |
| QA-4.16 | Variabilidad ON, CV 0.25 | N2: picks equivalentes varían; CV medido 0.25 ±0.05 |
| QA-4.17 | Variabilidad ON, CV 0.5 | N2: CV medido 0.5 ±0.1 |

### Bloque 5 — Flota

| ID | Caso | Esperado |
|---|---|---|
| QA-5.1 | 1 terrestre + 1 montacargas | N2: 2 `agent_id`; duración mayor que el control |
| QA-5.2 | 4 terrestres + 4 montacargas | N2: 8 agentes; duración menor |
| QA-5.3 | Capacidad terrestre 50 | N2: `cargo_volume` de terrestres ≤ 50; más tours |
| QA-5.4 | Capacidad montacargas 3000 | N2: tours de montacargas más largos |
| QA-5.5 | Descarga 60 s | N2: cada descarga dura 60 s (+ pack) |
| QA-5.6 | Montacargas: prioridad Special 1, High 2 | N2: agotan Special antes que High |
| QA-5.7 | Equipo por área: Area_High → GroundOperator (con prioridad) | N2: los terrestres toman WOs de Area_High; montacargas ya no |
| QA-5.8 | Área sin agente capaz | La UI bloquea con mensaje |
| QA-5.9 | Flota vacía | La UI bloquea |
| QA-5.10 | Generar Flota por Defecto | N1: flota estándar en el formulario |
| QA-5.11 | Grupos con capacidades distintas del mismo tipo | N2: cada agente respeta su propia capacidad; visor muestra la capacidad correcta |

### Bloque 6 — Layout y Datos (modifica datos: backup obligatorio)

| ID | Caso | Esperado |
|---|---|---|
| QA-6.1 | Datos maestros en uso | Cantidades = `warehouse.db` |
| QA-6.2 | Tablas de consulta (ubicaciones, SKUs) | Datos = `warehouse.db`; búsqueda y paginado funcionan |
| QA-6.3 | Subir Excel modificado (sin aplicar) | Muestra resumen; la simulación **no** cambia |
| QA-6.4 | Aplicar Excel modificado (p. ej. una clase de SKU distinta) | La simulación refleja el cambio; backup creado; restaurar al final |
| QA-6.5 | Cargar Work Areas | Desplegables de Flota con las áreas del Excel |
| QA-6.6 | Subir TMX inválido | Rechazo con mensaje claro |

### Bloque 7 — Outbound Staging

| ID | Caso | Esperado |
|---|---|---|
| QA-7.1 | 100% zona 3 | N2: todas las WOs con `staging_id` 3; descargas en la celda de la zona 3. N3: el visor muestra descargas ahí |
| QA-7.2 | Reparto 15/15/14/14/14/14/14 | N2: proporciones ±6 pp |
| QA-7.3 | Reparto que suma 110 | La UI bloquea |
| QA-7.4 | Destino → zona (determinista con `destino`) | N2: todos los pedidos de cada destino en su zona, aunque el reparto diga otra |
| QA-7.5 | Mover coordenadas de la zona 1 (Guardar ubicaciones) | N2: descargas en la celda nueva; restaurar |
| QA-7.6 | Coordenada sobre un rack | Rechazo con mensaje |

### Bloque 8 — Inbound

| ID | Caso | Esperado |
|---|---|---|
| QA-8.1 | Inbound ON, determinista, ASN de ejemplo | N2: camiones y horas = ASN; todos los pallets guardados. N3: panel de inbound en el visor |
| QA-8.2 | Inbound ON, estocástico: 3 camiones × 4 pallets, intervalo 300 | N2: 3 llegadas separadas 300 s; 12 putaways |
| QA-8.3 | Unidades por pallet 50 | N2: stock agregado = 50 por pallet |
| QA-8.4 | Descarga por pallet 60 s | N2: pallets del mismo camión separados 60 s |
| QA-8.5 | Carga del pallet 45 s | N2: carga en muelle = 45 s |
| QA-8.6 | Picking primero vs Recepción primero | N2: espera pallet→agente mucho menor en "recepción primero" |
| QA-8.7 | Slotting fija / cercana / ABC | N2: destinos distintos; "cercana" con menor distancia media de putaway |
| QA-8.8 | Cross-docking ON (determinista con backorders) | N2: WOs `WO-XD-*`; fill-rate efectivo > apertura |
| QA-8.9 | Cross-docking ON en modo estocástico | La UI avisa; el motor no genera `WO-XD` |
| QA-8.10 | Mover coordenadas de un muelle | N2: descarga en la celda nueva; restaurar |

### Bloque 9 — Personas, equipos y perfiles (INIT-11, solo por Importar)

| ID | Caso | Esperado |
|---|---|---|
| QA-9.1 | Importar un `.json` con `personas` + `equipos` | La pestaña Flota muestra el aviso; N1: los bloques llegan a la corrida; N2: `agent_id` = nombres |
| QA-9.2 | Idem con `perfiles` + `estacionamientos` | N2: eventos `cambio_de_equipo` cuando corresponde |
| QA-9.3 | Guardar tras importar | Los bloques se conservan en `config.json` |

### Bloque 10 — Barra superior y ciclo de configuración

| ID | Caso | Esperado |
|---|---|---|
| QA-10.1 | Run Simulation con cambios | `config.json` sin modificar (hash igual) |
| QA-10.2 | Aplicar Configuración con cambios | `config.json` cambia; backup creado |
| QA-10.3 | Aplicar sin cambios | `config.json` idéntico |
| QA-10.4 | Default | Formulario con defaults; `config.json` intacto hasta Aplicar |
| QA-10.5 | Guardar preset → cambiar todo → Cargar preset | Formulario idéntico al guardado |
| QA-10.6 | Importar `.json` | Formulario refleja el archivo |
| QA-10.7 | Claves sin UI (4.1) tras Aplicar | Se conservan |
| QA-10.8 | Abrir Visor tras una corrida | Abre la última corrida |

### Bloque 11 — Optimización

| ID | Caso | Esperado |
|---|---|---|
| QA-11.1 | 4 trials, 2 jobs | Termina; 4 trials; parámetros dentro de rangos |
| QA-11.2 | Costo de montacargas × 20 | El mejor trial usa menos montacargas que en QA-11.1 |

### Bloque 12 — Experimentos A/B

| ID | Caso | Esperado |
|---|---|---|
| QA-12.1 | A = B (Actual vs mismo preset), 5 réplicas | "Sin diferencia significativa"; diferencias exactamente 0 (semillas pareadas) |
| QA-12.2 | A = canónico, B = 1+1 agentes | "Significativa"; B peor |
| QA-12.3 | Repetir QA-12.2 con la misma semilla | Mismos números |

### Bloque 13 — Visor (se aplica en todos los bloques)

| ID | Caso | Esperado |
|---|---|---|
| QA-13.1 | Sincronía de posiciones (5 instantes por corrida) | Coinciden |
| QA-13.2 | KPIs del panel vs `.jsonl` | Tiempo, WOs completadas y tareas coinciden |
| QA-13.3 | Saltar tiempos muertos | Salta solo tramos sin movimiento; el % mostrado coincide con el cálculo del `.jsonl` |
| QA-13.4 | Capacidad y estado por operario | Coinciden con el `.jsonl` |

## 6. Orden de ejecución

Se ejecuta **de a un bloque**, con reporte al Director al cerrar cada uno:

1. **Bloque 0** (método y herramienta) — si el método falla, nada de lo demás vale.
2. **Bloques 1, 2, 4, 5** — lo que más usa el cliente.
3. **Bloques 3, 7** — motor avanzado y salida.
4. **Bloques 8, 6** — inbound y datos maestros (con backup).
5. **Bloques 10, 9** — ciclo de configuración e INIT-11.
6. **Bloques 11, 12** — herramientas de análisis.
7. **Sección 7** — combinadas.

## 7. Pruebas combinadas (interacciones)

| ID | Combinación | Por qué | Esperado |
|---|---|---|---|
| QA-X.1 | Tour Simple + reparto en 3 zonas + outbound ON | Tour simple y camiones dependen de la zona | Ningún tour mezcla zonas y ningún camión mezcla zonas |
| QA-X.2 | Cercanía radio chico + montacargas con 2 áreas | El radio vs la prioridad de área | Documentar qué manda |
| QA-X.3 | Fórmula de pick + clases + variabilidad OFF | Validar la fórmula completa | Cada pick = `(base + u·q + kg·peso + vol·v) × mult + recargo`, acotado por mínimo |
| QA-X.4 | Variabilidad ON + A/B con misma semilla | Reproducibilidad | Mismos números en las dos corridas |
| QA-X.5 | Velocidad por carga ON + capacidad terrestre 300 | Más carga, más lento | Pasos más lentos que con capacidad 150 |
| QA-X.6 | Determinista + destino→zona + Tour Simple | Rutas reales | Cada tour = un destino/zona |
| QA-X.7 | Inbound Recepción primero + slotting cercana + flota 1+1 | Contención extrema | El picking se demora; putaway rápido |
| QA-X.8 | Anti-colisión OFF + 8 agentes | Estrés de superposición | Muchas superposiciones; el visor las muestra |
| QA-X.9 | Perfil Real + outbound ON | Escala real con camiones | Intervalos de camión en segundos reales coherentes |
| QA-X.10 | Equipo por área cambiado + capacidades distintas | Dimensionado de tareas por área | Tamaño de WO del área = capacidad mínima del equipo que la atiende |

## 8. Entregables por bloque

- Resultado de cada caso (sección 9) con evidencia: valores N1, métricas N2,
  capturas N3 (en `output/qa/<bloque>/`).
- Lista de hallazgos con severidad, causa raíz y propuesta.
- Actualización de este documento (casos agregados o quitados y por qué).

## 9. Registro de resultados

| ID | Fecha | N1 | N2 | N3 | Resultado | Hallazgo |
|---|---|---|---|---|---|---|
| QA-0.3 | 18/09 | — | Herramienta determinista (dos pasadas idénticas sobre el replay de semilla 42) | — | **PASA** | — |
| QA-0.1 | 18/09 | Copia temporal = metadata del `.jsonl`; vs `config.json` falta solo `cercania_tour_mode` | 300 órdenes, 603 tareas, todas completadas, todo a zona 1, capacidades 150/1000 respetadas, cada equipo solo en sus áreas | 5 instantes × 4 operarios: **20/20** coinciden en celda y estado; captura OK | **PASA** con hallazgo | H-01, H-02 |
| QA-0.2 | 18/09 | Igual que QA-0.1 | 3 corridas: estructura idéntica; duración 6.772 / 7.256 / 7.833 s; tareas 603 / 625 / 606 | — | **PASA** (criterio recalibrado) | H-04 |
| H-01 reprueba 1 | 18/09 | Corrida canónica: copia temporal **idéntica** a `config.json` (antes faltaba `cercania_tour_mode`) y = metadata | — | — | **PASA** | H-01 cerrado |
| H-01 reprueba 2 | 18/09 | Importar un `.json` con `personas` + `equipos` (clave sin control web) → Run: la metadata trae las personas | Agentes = **Ana, Beto, Carla, Dario**; pickers solo en Area_Ground, grueros en High/Special; 613 tareas completadas; `config.json` intacto | — | **PASA** | H-01 cerrado |

## 10. Hallazgos

| # | Severidad | Caso | Descripción | Causa raíz | Propuesta | Estado |
|---|---|---|---|---|---|---|
| H-01 | **CRÍTICO** | QA-0.1 | **Run Simulation descarta las claves que la web no muestra.** Corre solo con lo que arma el formulario, sin fusionarlo con `config.json` (Aplicar sí fusiona). En la corrida de control faltó `cercania_tour_mode`; por el mismo mecanismo se pierden `waves`, `priority_dispatch_enabled`, `fleet_defaults` y todo INIT-11 (`personas`, `equipos`, `perfiles`, `estacionamientos`, `cambio_de_perfil`). El mismo `config.json` da una simulación distinta desde consola que desde Run | `runners.stage_simulation_config` escribe `request.config` tal cual; `config_manager.save_config` fusiona con el existente | **Corregido** en el navegador (`app.js`): (1) el formulario recuerda de qué configuración se cargó — servidor, `.json` importado o preset (antes solo la del servidor, así que al importar también los parámetros internos de congestión/outbound/tiempos salían del `config.json`); (2) al armar la configuración conserva las claves de esa fuente que la web no edita. No se fusiona en el servidor porque una corrida con un archivo importado tomaría las claves del `config.json` y no las del archivo | **Cerrado** (reprobado) |
| H-02 | MENOR | QA-0.1 (N3) | El KPI **"Tareas"** del visor es tareas completadas × 3: un número fijo heredado de la versión de escritorio, no mide nada | `routers/replay.py`: `tareas_completadas = wo_completed * 3` | Reemplazarlo por una métrica real (picks o paradas) o quitarlo | Abierto |
| H-03 | OBS | QA-0.2 | Una corrida cancelada deja una carpeta `output/simulation_*` a medias (solo el Excel) | La cancelación no limpia | Marcarla como incompleta o borrarla al cancelar | Abierto |
| H-04 | OBS (método) | QA-0.2 | La variación natural entre corridas web es ±8% en duración; el criterio inicial de ±10% no discriminaba | Semilla libre | Regla 4 recalibrada | Cerrado |
| H-05 | A investigar (QA-3.1) | QA-0.1 | Con el anti-colisión activo hay co-ocupaciones: el propio motor reporta 16-23 eventos en 8-9 celdas por corrida (sobre todo la zona de descarga (3, 28)/(3, 29) y cruces) | — | Verificar en QA-3.1 si son las excepciones documentadas (spawn/staging) o fallas | Abierto |

## 11. Registro de cambios de este plan

- 2026-09-18 — Versión inicial: 13 bloques, ~110 casos + 10 combinadas.
- 2026-09-18 — Bloque 0 ejecutado. Se agregan las reglas 4 (calibración) y 7
  (no tocar `.py` durante corridas). QA-0.2 pasa a medir la variación en vez
  de exigir ±10%. QA-9.1 y QA-10.7 quedan marcados como afectados por H-01.
  Herramientas: `scripts/qa/analizar_replay.py` y `scripts/qa/esperar_corrida.py`.
  Método del nivel 3 validado: el visor se carga con `?autoload=<ruta>`, el
  reloj se mueve con el control de tiempo (`#time-slider`, redondea a 0,1 s)
  y se lee lo dibujado en `AppState.agents`.
- 2026-09-18 — Modo de trabajo del Director: corregir cada error apenas se
  confirma, reprobar y recién seguir; sección 0 con el objetivo inmediato.
  H-01 corregido. Método para Importar sin diálogo del sistema: se asigna un
  `File` al `#file-import-input` y se dispara `change` (mismo código que usa
  el selector).
