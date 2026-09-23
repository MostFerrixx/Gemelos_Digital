# PLAN DE QA — Configuración web → simulador → visor

> **Documento vivo.** Se actualiza a medida que se ejecutan las pruebas: se
> agregan casos que falten, se quitan los que sobren y se registra cada
> resultado en la sección 9. Última actualización: 2026-09-23.

## 0. Estado actual (se actualiza en cada interacción)

**Objetivo inmediato:** Bloque 8 — Inbound (despues 6 rehecho con el mapa
nuevo, 10, 9, 11, 12 y las combinadas).
**Ultimo cerrado:** Bloque 7 — Outbound Staging (23/09): 5 casos pasan (7.1,
7.2, 7.3, 7.4, 7.7 nuevo); 7.5 y 7.6 pasan al bloque 6 (las zonas ahora son
carriles y se editan en el Excel). **2 errores criticos corregidos: H-29**
(en modo aleatorio un pedido salia partido entre muelles) y **H-30** (abrazo
mortal en la estacion de descarga, destapado por H-29); **H-31** corregido
(fila de destino invalida descartada en silencio). Abiertos: H-32 (7 zonas
fijas) y H-33 (la ruta no viaja en el replay). H-34 cerrado con BK-29.
**Ultimo cerrado:** Bloque 3 — Motor avanzado (19/09): 5 de 6 pasan; QA-3.1
falla por H-15 (tambien con la flota canonica). Corregido **H-26** (quedaban
pallets sin despachar al terminar). Consulta de diseno de H-15 hecha:
`docs/PROPUESTA_DISENO_CIRCULACION_Y_LAYOUT.md` (causa nueva confirmada: H-27).
**Último cerrado:** Bloque 5 — Flota (19/09): 11 de 11 casos pasan; 160/160
posiciones visor = JSON (desde 5.6 también carga y capacidad). **3 errores
corregidos: H-17** (el panel mostraba siempre 0 de 100/200), **H-18** ("Generar
Flota por Defecto" ignoraba el mapa de equipo) y **H-19** (con outbound activo
los ociosos quedaban trabados intentando llegar a una celda bloqueada).
**Pendiente de decisión del Director: H-15 / BK-25** (atasco circular en la
zona de descarga con flota grande).
**Último cerrado:** Bloque 4 — Tiempos (19/09): 16 de 17 casos pasan en los 3
niveles (4.13 no aplicable con los datos actuales); 200/200 posiciones visor
= JSON. **1 error crítico encontrado y corregido: H-14** (el tiempo por celda
se ignoraba con la capa anti-colisión activa).
Después: Bloque 2 — Despacho y tours.
**Último cerrado:** Bloque 1 completo (18/09): 11 corridas, todas pasan tras
corregir H-07; 220/220 posiciones visor = JSON.
**Hallazgos abiertos:** H-02, H-03, H-05 (confirmado), H-06 (decisión), H-08 a H-12.

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
8. **Las carpetas de corridas se borran solo por nombre exacto**, nunca con
   patrones (lección del bloque 4: una limpieza por patrón borró evidencia).
9. **Parámetros con firmas independientes pueden probarse en una misma
   corrida** (p. ej. tiempo por celda → pasos a pie; factor → pasos de
   montacargas; horquilla → picks de montacargas). Si uno fallara, lo delata
   su propia firma. Parámetros que se enmascaran entre sí (p. ej. el mínimo de
   pick tapa a los demás términos) van por separado.

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
| Zonas de picking por pasillo (activar, ayudar en otras, asignación) | `zonas_picking` | `dispatcher` | Cada operario toma trabajo solo de sus pasillos hasta que su zona se agota |
| Cupo por pasillo (activar, operarios por pasillo) | `pasillos` | `operators`, `aisles` | Nunca hay más operarios en un pasillo que el cupo |

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
| QA-1.5 | Distribución 20/20/20/20/20 | N2: cada clase 20% ±8 pp **por pedido** (la mezcla se sortea por pedido; por tarea cambia porque los productos grandes se dividen en más tareas) |
| QA-1.6 | Distribución que suma 90% | La UI bloquea Run y Aplicar con un mensaje claro |
| QA-1.7 | Determinista con archivo válido | N2: `order_id` y SKU = los del archivo; cantidad de pedidos = archivo |
| QA-1.8 | Determinista + Envío Parcial, archivo con 1 SKU inexistente | N2: el pedido sale sin ese ítem; vista previa lo informa |
| QA-1.9 | Determinista + Todo o Nada, mismo archivo: (a) política elegida antes de subir; (b) cambiada después de subir | N2: ese pedido no aparece en ninguna de las dos variantes |
| QA-1.10 | Volver a Estocástico tras cargar archivo | N1: `order_generation_mode = stochastic`; el archivo no se usa |

### Bloque 2 — Despacho y tours

| ID | Caso | Esperado |
|---|---|---|
| QA-2.1 | Ejecución de Plan (canónico) | N2: la 1.ª WO de cada tour es la de menor `pick_sequence` pendiente en el área prioritaria del agente |
| QA-2.2 | Optimización Global | N2: la 1.ª WO es la de menor costo desde la posición; distancia media al 1.er pick < Plan |
| QA-2.3 | Cercanía, radio 100 | N2: 1.ª WO dentro del radio (o expansión justificada) |
| QA-2.4 | Cercanía, radio 5, máx. expansiones 0 | N2: si al pedir trabajo había alguna tarea compatible a ≤ 5 celdas (línea recta, como el motor), el recorrido la usa; si no, cae al almacén completo sin escalones intermedios |
| QA-2.5 | Cercanía, radio 5, paso 5, 2 expansiones | N2: se usa el primer escalón (5, 10, 15) con tareas; 0 recorridos que ignoren una tarea de su escalón |
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
| QA-7.5 | ~~Mover coordenadas de la zona 1 (Guardar ubicaciones)~~ | **Pasa al bloque 6**: desde BK-25 las zonas son carriles de 20 celdas; la pestaña las muestra resumidas y remite al Excel maestro (el botón se oculta) |
| QA-7.6 | ~~Coordenada sobre un rack~~ | **Pasa al bloque 6** (validación del Excel maestro) |
| QA-7.7 | Rutas a Piquear: 10 rutas, reparto 40/30/30 (aleatorio) | N1: `rutas_estocasticas {enabled, cantidad:10}`. N2: cada pedido sale entero por un solo carril; solo carriles 1-3 |

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
| QA-2.1 | 19/09 | `Ejecucion de Plan` \| idéntico | **100%** de los 56 recorridos contiene la tarea pendiente de menor secuencia del área (firma de Plan); 64% contiene la más cercana | 20/20 | **PASA** | — |
| QA-2.2 | 19/09 | `Optimizacion Global` \| idéntico | **97,7%** contiene la tarea más cercana por camino real (la excepción: el arranque, 1 celda de diferencia); solo 13,6% la de menor secuencia; caminata al 1.er pick 13,8 vs 18,4 celdas de Plan | 20/20 | **PASA** | — |
| QA-2.3 | 19/09 | `Cercania` 100/50/5 \| idéntico | Radio 100 no filtra nada en este mapa (distancia máxima ~42): tarea más lejana asignada a 33 celdas; 58% contiene la más cercana | 20/20 | **PASA** | H-13 |
| QA-2.4 | 19/09 | 5/50/**0** \| idéntico (antes de H-07 el 0 llegaba como 5) | 0 violaciones del radio; 3 recorridos a ≤5, 61 al almacén completo | 20/20 | **PASA** | H-13 |
| QA-2.5 | 19/09 | 5/5/2 \| idéntico | Escalones usados: 3 a 5, 6 a 10, 12 a 15, 39 al almacén; **0 violaciones** | 20/20 | **PASA** | — |
| QA-2.6 | 19/09 | Tour Simple + 50/50 zonas 1-2 \| idéntico | **0 de 62** recorridos mezclan zonas; 315/303 tareas (51/49); descargas físicas en (3,29) y (7,29) | 20/20 | **PASA** | — |
| QA-2.7 | 19/09 | Tour Mixto + 50/50 \| idéntico | **53 de 66** recorridos mezclan zonas, y esas 53 rondas de descarga pasan físicamente por las dos zonas | 20/20 | **PASA** | — |
| QA-4.1 | 19/09 | Real → Demo en la web vuelve a 0,1 / 0,8 / 2 | = valores canónicos: pasos 0,1 / 0,08 s, horquilla 2 s, picks exactos (todas las corridas de control) | — | **PASA** | — |
| QA-4.2 (1.er intento) | 19/09 | Real: 1 / 0,5 / 8 \| idéntico | Horquilla 8 s aplicada (623/623 picks exactos) pero **pasos de 0,1 s en vez de 1,0 s**: el tiempo por celda se ignoraba | — | **FALLA** | H-14 |
| QA-4.2 (reprueba) | 19/09 | idéntico | Pasos **1,0 s** a pie y **0,5 s** montacargas; 586/586 picks exactos; 0 co-ocupaciones en operación | 20/20 | **PASA** | H-14 cerrado |
| QA-4.3/4.4/4.5 | 19/09 | 0,5 / 0,25 / 20 \| idéntico; la web muestra "Personalizado" | Pasos 0,5 s a pie y **0,125 s** montacargas; picks de montacargas = fórmula + **40 s** (2 × 20); 624/624 exactos | 20/20 | **PASA** | — |
| QA-4.6/4.7/4.8/4.10 | 19/09 | base 30, unidad 10, kg 0, volumen 0,5 \| idéntico | **605/605** picks = fórmula exacta con los 4 términos | 20/20 | **PASA** | — |
| QA-4.9 | 19/09 | mínimo 60 \| idéntico | Mínimo exacto 60,000 s a pie y 64,000 s montacargas (60 + 2×2); 613/613 exactos | 20/20 | **PASA** | — |
| QA-4.11/4.12 | 19/09 | Pequeño ×3 +20 s; Mediano pack 25 \| idéntico | 634/634 picks exactos (Pequeño con ×3 +20); **todas** las descargas de Mediano = 30 s (5 + 25), las demás 5 s | 20/20 | **PASA** | — |
| QA-4.13 | 19/09 | — | **No aplicable**: los 50 SKUs tienen clase; ninguno usa la fila GENERAL. Se retoma en el bloque 6 con un Excel de prueba | — | N/A | — |
| QA-4.14 | 19/09 | velocidad por carga ON \| idéntico | A pie: vacío 0,1 s/paso, cargado 0,114–0,2 s (tope 50%); montacargas 0,08 s cargado o vacío | 20/20 | **PASA** | — |
| QA-4.15 | 19/09 | + aplicar a montacargas \| idéntico | Montacargas cargado **0,16 s** (0,08 / 0,5), vacío 0,08 s | 20/20 | **PASA** | — |
| QA-4.16 | 19/09 | variabilidad CV 0,25 \| idéntico | σ log medida 0,251 vs 0,246 (+0,7 errores estándar), media real/esperado 0,995 | 20/20 | **PASA** | — |
| QA-4.17 | 19/09 | CV 0,5 \| idéntico | σ log 0,455 vs 0,472 (−1,3 errores estándar); el generador probado aparte con 200.000 muestras da CV 0,501 | 20/20 | **PASA** | — |
| QA-5.1 | 19/09 | 1 terrestre + 1 montacargas \| idéntico | 2 agentes; fin **14.541 s** (≈2× el control de ~7.300 s con 2+2) | 10/10 | **PASA** | — |
| QA-5.2 | 19/09 | 4 + 4 \| idéntico | 8 agentes, todos trabajan; fin 6.756 s (semilla libre) y 7.178 s (semilla fija): **casi no mejora** contra 2+2. Atasco circular en la descarga 1: 28 rendiciones del planificador, 32 co-ocupaciones (hasta 6 agentes en (3,29)) | 40/40 | **PASA** la configuración; **revela H-15** | H-15 |
| QA-5.3/5.4/5.5 | 19/09 | terrestre cap. 50 + descarga 60 s; montacargas cap. 3000 \| idéntico | Carga máx. terrestre **50**; recorridos: montacargas 19,1 tareas vs terrestres 4,2; descarga terrestre **60,0 s**, montacargas 5 s; 626/626 picks exactos. 21 co-ocupaciones en la descarga (H-15). Montacargas cortado en 20 tareas pese a capacidad 3000 (H-16) | 20/20 posiciones; **capacidad y carga del panel: FALLA** (siempre 0 de 100) | **PASA** tras corregir H-17 | H-15, H-16, H-17 |
| H-17 reprueba | 19/09 | — | — | Panel del visor en t=11.983: barras 100% (50/50), 20% (10/50), 3,2% (95/3000), 15,0% (451/3000) = JSON | **PASA** | H-17 cerrado |
| QA-5.6 | 19/09 | Montacargas Special 1, High 2 \| idéntico | Última asignación Special 2.073 s, High 7.457 s (el control canónico al revés: High 5.045, Special 7.549); 18/18 recorridos respetan la prioridad | 20/20 (con carga y capacidad) | **PASA** | — |
| QA-5.7 | 19/09 | Area_High → a pie; a pie Ground 1, High 2 \| idéntico | Las 260 tareas de Area_High las hacen los de a pie, 0 los montacargas (aunque éstos siguen listando Area_High con prioridad 1: el mapa manda). A pie: primero Ground, después High. Carga máx. 150 | 20/20 | **PASA** | H-21 |
| QA-5.8 | 19/09 | Sin grupo de montacargas | Cobertura en rojo "2 sin agente — no se podrá guardar/correr"; Run, Aplicar y Guardar con nombre bloqueados con mensaje claro (qué área y dónde corregir); `config.json` y `output/` intactos | — | **PASA** | — |
| QA-5.9 | 19/09 | Flota vacía | "Flota vacía… Genera o agrega una flota"; Run y Aplicar bloqueados: "La flota está vacía (0 agentes)…" | — | **PASA** | — |
| QA-5.10 (1.er intento) | 19/09 | Con el mapa canónico genera 2+2 150/1000; **con Area_High → a pie genera una flota que la misma pantalla rechaza** ("1 con tipo incorrecto") mientras avisa "cubre todas las áreas" | — | — | **FALLA** | H-18 |
| QA-5.10 (reprueba) | 19/09 | Mapa canónico → idéntica al canónico (High 1, Special 2); Area_High → a pie → válida; `fleet_defaults` importado (a pie 90, montacargas 1200 / 8 s) → aplicado \| idéntico | Carga máx. 90 y 1.200; descargas de montacargas 8 s; 609/609 picks exactos | 20/20 | **PASA** | H-18 cerrado |
| QA-5.11 | 19/09 | 2 grupos a pie: 1×150 y 1×60 \| idéntico | GroundOp-01 carga máx. 150, GroundOp-02 **60**; 155 vs 113 tareas | 20/20; el panel muestra 150 y 60 | **PASA** | — |
| H-19 (detección) | 19/09 | Corrida web con outbound activo (salió de un Importar mal armado, ver §11) | 64.817 avisos "Goal position (1,29)/(5,29) is not walkable"; el navegador se congeló y la corrida murió sin resultados | — | **FALLA** | H-19, H-20 |
| H-19 reprueba | 19/09 | Canónico + outbound activo desde la pestaña Outbound \| idéntico | Termina en ~1 min sin avisos. Semilla 42 sin la corrección: 64.817 avisos y 24.836 s; con la corrección: 60 avisos (otro origen, H-23) y 19.436 s | — | **PASA** | H-19 cerrado |
| QA-3.1 | 19/09 | Canonico (anti-colision encendido) \| identico | 4 corridas web 2+2 con semilla libre: **1 / 7 / 3 / 0** episodios de co-ocupacion, todos en la descarga (3,29)/(4,29), hasta 3 agentes juntos; siguen 1 a 1 a las rendiciones del planificador (1/8/2/0). Con semilla 42 da 0 por casualidad | — | **FALLA** | H-15, H-27 |
| QA-3.2 | 19/09 | Anti-colision apagado \| `congestion.enabled=false, mode=off` | **103** episodios de co-ocupacion (vs 0-7 encendido); los ociosos quedan parados sobre la descarga (3,29) | 28/28; el visor dibuja las superposiciones (3 agentes en (3,29) a t=4.711) | **PASA** | H-24 |
| QA-3.3 | 19/09 | Outbound encendido \| identico | 165 camiones, 618 pallets, cada ~96 s (90 + 2 s por pallet), max 7 por camion. Duracion **16.091 s** (x2,1): 50% del tiempo en descarga, un pallet por tarea, un operario por carril | contadores del visor = JSON | **PASA** | H-25 |
| QA-3.4 | 19/09 | Intervalo 30 s \| identico | Camion cada 32 s (30-44); espera en zona 29 s (vs 89 s); duracion 11.033 s | — | **PASA** | — |
| QA-3.5 | 19/09 | Intervalo 600 s \| identico | Camion cada 604-614 s; espera 593 s; duracion **63.016 s**: los operarios esperan lugar en el carril | — | **PASA** | H-25 |
| QA-3.6 (1.er intento) | 19/09 | Capacidad 2 \| identico | Max 2 por camion; pero **quedaron 3 pallets sin despachar** (1-3 en las 4 corridas con outbound) | — | **PASA** con hallazgo | H-26 |
| QA-3.6 (reprueba) | 19/09 | identico | 622 tareas, **622 despachadas**, 0 pendientes | Camiones con carga y pallets del visor = JSON en t=15.000 (157/314) y al final (318/622) | **PASA** | H-26 cerrado |
| Zonas y cupo por pasillo (controles nuevos, 23/09) | 23/09 | Terrestres → 1-4, montacargas → 5-9, cupo 2 \| idéntico; el canónico sin tocar NO agrega los bloques | Asignación aplicada; `[WARN]` por el pasillo 9 inexistente; el terrestre sale de su zona recién cuando su zona se agotó (t=1.841 vs última propia t=1.828; montacargas 3.808 vs 3.661); texto "uno al tres" bloquea la corrida con mensaje | — | **PASA** | — |
| QA-7.1 | 23/09 | 100% zona 3 \| idéntico | 300 pedidos, 594 tareas completadas, **todas con staging 3**; las 667 descargas en (11,30) y (12,30), los dos puestos del carril 3 | 20/20 | **PASA** | H-34 |
| QA-7.2 | 23/09 | 15/15/14/14/14/14/14 \| idéntico | Tareas por carril 13,6 / 15,4 / 11,8 / 15,9 / 14,7 / 15,4 / 13,3 % (máx. 2,2 pp de desvío) | — | **PASA** con hallazgo | H-29 |
| QA-7.3 | 23/09 | — | Suma 110: la insignia marca el error en vivo y Run se bloquea ("must sum to 100% (current: 110%)", en inglés: H-08); no se lanzó corrida | — | **PASA** | — |
| QA-7.4 | 23/09 | Determinista, 71 pedidos con `destino`; 6 tiendas mapeadas a los carriles 7..2, reparto 100% al 1 \| mapa idéntico | Cada tienda sale entera por su carril (10/10 pedidos cada una); el pedido con `staging_id` 3 explícito le gana a su destino. La fila "TIENDA_7 → 9" **desapareció sin aviso** y sus pedidos cayeron al carril 1 | — | **PASA** con hallazgo | H-31 |
| QA-7.4 (reprueba H-31) | 23/09 | Fila "TIENDA_X → 9" | Run bloqueado: "destino_staging_map['TIENDA_X'] = '9' debe ser un staging_id entero entre 1 y 7." | — | **PASA** | H-31 cerrado |
| QA-7.7 (1.er intento) | 23/09 | `rutas_estocasticas {enabled, cantidad:10}`, 40/30/30 \| idéntico | **150 de 300 pedidos partidos entre carriles** (sin rutas: 184 de 300) | — | **FALLA** | H-29 |
| QA-7.7 (reprueba) | 23/09 | idéntico | 300 pedidos, **0 partidos**, 584/584 completadas; pedidos por carril 38 / 32 / 30 % | — | **PASA** | H-29 y H-30 cerrados |
| H-01 reprueba 1 | 18/09 | Corrida canónica: copia temporal **idéntica** a `config.json` (antes faltaba `cercania_tour_mode`) y = metadata | — | — | **PASA** | H-01 cerrado |
| QA-1.1 | 18/09 | `total_ordenes` 50 \| 50 | 50 pedidos, 107 tareas, todas completadas; fin 1.415 s | 20/20 | **PASA** | — |
| QA-1.2 | 18/09 | 600 \| 600 | 600 pedidos, 1.195 tareas completadas; fin 15.178 s = **2,08×** el control (esperado ~2×) | 20/20 | **PASA** | H-05 (evidencia) |
| QA-1.3 (1.er intento) | 18/09 | **FALLA**: 0% se envió como el % por defecto (30/16/12/6); el formulario decía "Suma 100%" y el servidor rechazó "164%" | — | — | **FALLA** | H-07 |
| QA-1.3 (reprueba) | 18/09 | 100/0/0/0/0 \| idéntico | 568 tareas, **100% `pequeno`**; pick medio 15,4 s (control ~30 s); fin 4.272 s | 20/20 | **PASA** | H-07 cerrado |
| QA-1.4 | 18/09 | 0/0/0/0/100 \| idéntico | 664 tareas **100% `extra_grande`**; pick medio 115 s; mínimo 61,167 s = fórmula exacta para SKU003 (59,9 kg, 1 u): (10+2+0,15·59,9)·2,2+15 | 20/20 | **PASA** | H-05 (373 co-ocupaciones) |
| QA-1.5 | 18/09 | 20×5 \| idéntico | Por pedido: 17,7 / 20,7 / 19,0 / 20,3 / 22,3 % (±3 pp) | 20/20 | **PASA** | — |
| QA-1.6 | 18/09 | — | Suma 90%: Run y Aplicar **bloqueados**; aviso en pantalla "ERROR: Suma 90%"; `config.json` intacto | — | **PASA** | H-08 |
| QA-1.7 | 18/09 | determinista + archivo \| idéntico | 30 pedidos = los del archivo, SKUs y cantidades iguales; cumplimiento 100%; vista previa 30/34/32/0 correcta | 20/20 | **PASA** | H-09, H-10 |
| QA-1.8 | 18/09 | `ship_partial` | ORD-003 sale con SKU015 y SKU039, sin SKU999; vista previa informa el faltante | 20/20 | **PASA** | H-11 |
| QA-1.9a/b | 18/09 | `fill_or_kill` (antes y después de subir) | ORD-003 descartado entero en ambas: la política se aplica al correr | 20/20 | **PASA** | H-12 |
| QA-1.10 | 18/09 | `stochastic`; la ruta del archivo queda pero no se usa | 300 pedidos `ORD-xxxx`, ninguno del archivo | 20/20 | **PASA** | — |
| H-01 reprueba 2 | 18/09 | Importar un `.json` con `personas` + `equipos` (clave sin control web) → Run: la metadata trae las personas | Agentes = **Ana, Beto, Carla, Dario**; pickers solo en Area_Ground, grueros en High/Special; 613 tareas completadas; `config.json` intacto | — | **PASA** | H-01 cerrado |

## 10. Hallazgos

Los hallazgos abiertos están además en `docs/BACKLOG.md` (18/09):
H-02→BK-13, H-03→BK-14, H-05→BK-15, H-06→BK-16, H-08→BK-17, H-09→BK-18,
H-10→BK-19, H-11→BK-20, H-12→BK-21, H-13→BK-24, H-15→BK-25, H-16→BK-22, H-20→BK-26, H-21→BK-27, H-22→BK-28, H-23→BK-29, H-25→BK-30, H-27→BK-25; la sección 4.1 → BK-22.

| # | Severidad | Caso | Descripción | Causa raíz | Propuesta | Estado |
|---|---|---|---|---|---|---|
| H-01 | **CRÍTICO** | QA-0.1 | **Run Simulation descarta las claves que la web no muestra.** Corre solo con lo que arma el formulario, sin fusionarlo con `config.json` (Aplicar sí fusiona). En la corrida de control faltó `cercania_tour_mode`; por el mismo mecanismo se pierden `waves`, `priority_dispatch_enabled`, `fleet_defaults` y todo INIT-11 (`personas`, `equipos`, `perfiles`, `estacionamientos`, `cambio_de_perfil`). El mismo `config.json` da una simulación distinta desde consola que desde Run | `runners.stage_simulation_config` escribe `request.config` tal cual; `config_manager.save_config` fusiona con el existente | **Corregido** en el navegador (`app.js`): (1) el formulario recuerda de qué configuración se cargó — servidor, `.json` importado o preset (antes solo la del servidor, así que al importar también los parámetros internos de congestión/outbound/tiempos salían del `config.json`); (2) al armar la configuración conserva las claves de esa fuente que la web no edita. No se fusiona en el servidor porque una corrida con un archivo importado tomaría las claves del `config.json` y no las del archivo | **Cerrado** (reprobado) |
| H-02 | MENOR | QA-0.1 (N3) | El KPI **"Tareas"** del visor es tareas completadas × 3: un número fijo heredado de la versión de escritorio, no mide nada | `routers/replay.py`: `tareas_completadas = wo_completed * 3` | Reemplazarlo por una métrica real (picks o paradas) o quitarlo | Abierto |
| H-03 | OBS | QA-0.2 | Una corrida cancelada deja una carpeta `output/simulation_*` a medias (solo el Excel) | La cancelación no limpia | Marcarla como incompleta o borrarla al cancelar | Abierto |
| H-04 | OBS (método) | QA-0.2 | La variación natural entre corridas web es ±8% en duración; el criterio inicial de ±10% no discriminaba | Semilla libre | Regla 4 recalibrada | Cerrado |
| H-05 | **MAYOR** (realismo) — confirmado | QA-0.1, 1.2, 1.4, 1.5 | **Dos montacargas ocupan la misma celda al mismo tiempo, incluso pickeando juntos la misma ubicación.** Ej. QA-1.4: ambos en (17, 13) con SKU001, terminando con 0,1 s de diferencia; QA-1.2: uno "en movimiento" encima del otro que pickea en (13, 6). El motor reporta 16-23 co-ocupaciones por corrida con la mezcla normal y **373** con 100% extra grande (pocas ubicaciones → choques frecuentes). El visor lo muestra fielmente: el error está en el motor | Por investigar en la capa anti-colisión (reserva de la permanencia de pick / asignación de dos WOs de la misma ubicación a la vez) **Corregido** en `fix/bk15-anticolision` (`119064f`, `258d9f7`): C1-C3, reservas omitidas en silencio, tolerancia numérica, zonas de espera (decisión del Director) y verificación al ejecutar. **0 co-ocupaciones en operación** (canónica y extrema, semilla 42); reprueba desde la web: 0 y 20/20 visor = JSON | **Cerrado** (integrado, baseline `5c7f4c32`) |

| H-06 | MENOR (decisión) | QA-1.1 | El servidor que usa el cliente (`start_server.bat` → `server.py`) corre con **recarga automática** vigilando todo el proyecto: cualquier cambio en un `.py` (actualizar el programa con git, por ejemplo) reinicia el servidor y **cancela la simulación en curso**. Canceló dos corridas de QA | `uvicorn.run(reload=True, reload_dirs=[PROJECT_ROOT])`; el botón **Restart** depende de esa recarga (toca `server.py`) — ligado a BK-10 | Recarga solo en modo desarrollo y un Restart que no dependa de ella. **Se consulta al Director** (toca BK-10). Mientras tanto QA usa un servidor sin recarga (`web-qa` en `.claude/launch.json`) | Abierto |
| H-07 | **CRÍTICO** | QA-1.3 | **Un 0 en la web se reemplazaba por el valor por defecto.** Imposible excluir una clase de la mezcla (0% → 30/16/12/6), "0 expansiones" de Cercanía pasaba a 5 (el manual promete lo contrario), y en Optimización/A/B un costo o penalización 0 volvía al default y la semilla 0 a 1000. Además la flota truncaba decimales (descarga 2,5 s → 2) | `parseInt(valor) \|\| defecto`: en JavaScript el 0 cuenta como falso. En la flota, `parseInt` | Función única `WebConfigurator.numero(id, defecto)`: el default solo si el campo está vacío o no es número. Flota con `parseFloat` | **Cerrado** (reprobado QA-1.3; 2.4 y 5.5 lo vuelven a cubrir) |

| H-08 | OBS | QA-1.6 | Los mensajes de validación del servidor están en **inglés** ("Distribution percentages must sum to 100%") dentro de una interfaz en español | `config_manager.validate_config` | Traducirlos (y revisar que digan dónde corregir) | Abierto |
| H-09 | OBS | QA-1.7 | La ruta del archivo de órdenes se guarda **absoluta** (`D:\...\uploads\...`): un preset o `config.json` con archivo no funciona en otra carpeta o máquina | `/api/upload-orders` devuelve la ruta absoluta | Guardarla relativa al proyecto | Abierto |
| H-10 | OBS (realismo) | QA-1.7, 1.8 | Con pocas tareas (10-34), **un operario de cada tipo se lleva todo el trabajo** en un solo recorrido y el otro queda ocioso toda la corrida | Ejecución de Plan + tope de tareas por tour: el primero que pide arma el tour más grande posible | Evaluar reparto más equilibrado (tope por tour configurable, o repartir cuando hay ociosos). Decisión de diseño | Abierto |
| H-11 | OBS (realismo) | QA-1.8 | El cumplimiento (fill rate) queda en 100% aunque una línea se rechazó por SKU inexistente: la línea rechazada no cuenta como pedida | `service_level` se calcula sobre lo aceptado | Contar lo rechazado como no servido (el cliente lo pidió) | Abierto |
| H-14 | **CRÍTICO** | QA-4.2 | **El tiempo por celda configurado se ignoraba.** Con la capa anti-colisión activa (canónico) todo el movimiento sale del plan, y el planificador se creaba con `time_per_cell=0.1` fijo: el perfil "Real" (1,0 s/celda) o cualquier valor de la web no cambiaba la velocidad de nadie (el factor de montacargas y la horquilla sí se aplicaban) | `warehouse.py`: `SpaceTimePlanner(time_per_cell=0.1)` | **Corregido** (`c06742d`): se lee de `tiempos.time_per_cell`. +3 tests. Gate PASS (el canónico usa 0,1) | **Cerrado** (reprobado) |
| H-13 | OBS (diseño) | QA-2.3, 2.4 | **Cercanía casi no se distingue de "cualquier tarea".** (1) El radio por defecto (100) no filtra nada en este mapa (distancia máxima ~42). (2) Más de fondo: todo recorrido termina en la zona de descarga, así que la cercanía se mide siempre desde ahí; con radio 5, 61 de 64 recorridos no tenían nada cerca y cayeron al almacén completo. Además, por código, Cercanía filtra por equipo compatible pero **no** por prioridad de área (Plan y Global sí): sin verificar su efecto | Diseño de la estrategia | → BK-24 | Abierto |
| H-12 | MENOR | QA-1.9 | Con "Todo o Nada", la vista previa dice "10 Órdenes" y no avisa que el pedido con el ítem inválido se descarta entero | La vista previa no mira la política | Mostrar "órdenes que se descartarán" según la política | Abierto |
| H-15 | **MAYOR** (realismo) | QA-5.2, 5.5 | **Atasco circular en la zona de descarga.** La descarga admite un solo operario; los que esperan turno se paran en las celdas vecinas (2,29), (4,29), (3,28), que son la única salida del que descarga. Nadie cede; tras 10 min de reintentos el motor se rinde, avanza por la ruta fija y vuelven las co-ocupaciones (hasta 6 agentes en (3,29)). Duplicar la flota casi no acorta la corrida | Capacidad 1 de la descarga + espera en la boca de salida | → BK-25. **Decisión de diseño del Director** | Abierto |
| H-16 | MENOR (configurabilidad) | QA-5.4 | El tope de tareas por recorrido (`max_wos_por_tour`, 20) no tiene control en la web: un montacargas de capacidad 3000 sigue cortando sus recorridos en 20 tareas y el cliente no sabe por qué | Clave del motor sin control | → BK-22 | Abierto |
| H-17 | MENOR (visor) | QA-5.3 (N3) | **El panel del visor mostraba siempre carga 0 de capacidad 100 (terrestre) o 200 (montacargas)**, sin importar la configuración ni lo que llevaba el operario | `app_state._apply_event_to_state` descartaba `cargo_volume` y `capacidad` del evento; `routers/replay.py` completaba con 100/200 fijos | **Corregido** (`63c9c39`): se copian del evento. +1 test | **Cerrado** (reprobado) |
| H-18 | **MAYOR** (usabilidad) | QA-5.10 | **"Generar Flota por Defecto" ignoraba el mapa de equipo por área** que está en la misma tarjeta: repartía las áreas por el nombre. Con Area_High → a pie armaba una flota que la pantalla rechazaba, mientras avisaba "cubre todas las áreas". Además dejaba todas las prioridades en 1 (empate) y usaba 150/1000/5 s fijos aunque la config trajera `fleet_defaults` | `fleet-manager._executeDefaultFleet`: reparto por nombre | **Corregido** (`f011034`): reparte por el mapa; prioridades 1, 2, 3 en orden del layout (reproduce la flota canónica); capacidad y descarga desde `fleet_defaults` si existe. Manual actualizado | **Cerrado** (reprobado) |
| H-19 | **CRÍTICO** (con outbound) | Corrida web 5.10 (1.er intento) | **Con el muelle de salida activo, los operarios sin trabajo quedaban trabados.** Las celdas de espera de BK-15 se elegían antes de que el outbound convirtiera cada descarga en un carril de 8 celdas bloqueadas: (1,29), (5,29)… quedaban adentro de un carril y el ocioso intentaba llegar para siempre. Semilla 42: 64.817 avisos, duración +28%. En la web, el aluvión de avisos congeló el navegador y la corrida terminó sin resultados. El gate no lo veía (el canónico tiene el outbound apagado) | Orden de construcción en `warehouse.py` (lo introdujo BK-15) | **Corregido** (`61697d8`): las zonas de espera se arman después del outbound y todo el carril cuenta como descarga. +2 tests. Gate PASS | **Cerrado** (reprobado) |
| H-20 | MENOR (usabilidad) | H-19 | La consola del "Simulation Runner" agrega cada línea del log sin límite: con decenas de miles de líneas el navegador se congela | Sin tope de líneas | → BK-26 | Abierto |
| H-21 | OBS (usabilidad) | QA-5.7 | Si el mapa le da un área a otro tipo de equipo, las prioridades de esa área en los grupos del tipo anterior quedan en el formulario sin aviso: no hacen nada y confunden | Sin aviso | → BK-27 | Abierto |
| H-22 | MENOR (decisión) | QA-5.10 (1.er intento) | Una configuración **sin** bloque `outbound` (o `congestion`) corre desde la web con el outbound **encendido** y desde consola **apagado**: el mismo archivo da dos simulaciones distintas | Decisión explícita en `app.js` ("ausencia de bloque = ON") | → BK-28. **Decisión del Director** | Abierto |
| H-23 | OBS (realismo) | H-19 reprueba | Con outbound activo algunos operarios arrancan dentro de celdas que el carril después bloquea (60 avisos "Start position … is not walkable") | Posición inicial anterior al bloqueo de carriles | → BK-29 | **Arranque corregido** (BK-29). Los 58 avisos que quedan son del outbound al salir del fondo del carril → BK-30 |
| H-24 | OBS | QA-3.2 | Con la anti-colision apagada, los operarios sin trabajo se quedan parados sobre la zona de descarga el resto de la corrida (las zonas de espera dependen de esa capa). Es el modo "sin fisica" de comparacion | Zonas de espera solo con planificador | Documentar en el manual | Abierto |
| H-25 | **MAYOR** (realismo, decision) | QA-3.3, 3.5 | **El muelle de salida (outbound) no es realista en WH1.** Cada tarea es un pallet; se depositan de a uno y un operario por carril: la corrida dura x2,1 (x8,6 con camion cada 600 s). Las 7 zonas se expanden a manchas de 8 celdas que tapan las filas 28-29 enteras (el pasillo frontal queda en 1 fila); 52 saltos de 2-3 celdas al entrar o salir del carril; los camiones nunca cargaron mas de 7 de 8 | Modelo de carriles de INIT-3 sobre un mapa sin anden | → BK-30. Decisiones D3 y D10 de la propuesta de diseno | Abierto |
| H-26 | MENOR | QA-3.6 | **Con outbound, la corrida terminaba con 1-3 pallets sin despachar**: cortaba al llegar la ultima tarea a la zona, sin esperar el ultimo camion | `simulacion_ha_terminado` solo miraba las tareas | **Corregido** (`dcf71b3`): con camiones activos termina cuando se despacho todo. +1 test. Gate PASS | **Cerrado** (reprobado) |
| H-27 | **MAYOR** (causa de H-15) | Consulta de diseno | **El que espera ocupa dos celdas.** Si el plan de un operario incluye una espera, el planificador le reserva tambien la celda de la que salio durante toda la espera, aunque ya no esta ahi. Esa reserva de mas choca con otras y se rechazan planes validos: 92-95% de los planes rechazados en corridas 2+2. Lo introdujo BK-15 (C2) | `spacetime_planner._plan_reserve_core` usa el tiempo de SALIDA de la celda siguiente como fin de la reserva del origen | Hallado por el consultor (Fable 5.1) y **confirmado**: reproduccion de 25 lineas + lectura del ejecutor (se mueve y espera en la celda nueva). → BK-25 F0 | Abierto |
| H-28 | **MAYOR** (visor) | Prueba del layout grande | **El visor dibujaba el mapa de `config.json`, no el de la corrida cargada.** Correr desde la web no toca `config.json`: con `layouts/WH1 v2.tmx` la simulacion usaba 30x42 y el visor dibujaba 30x30 (el almacen equivocado). Es lo que el Director recordaba como "el layout nuevo no cargaba" | `routers/replay.get_layout` resolvia solo desde el config | **Corregido** (`b7ba14a`): el mapa sale de la metadata del replay. +2 tests | **Cerrado** (verificado en el visor) |
| H-29 | **CRÍTICO** (realismo) | QA-7.7, 7.2 | **En modo aleatorio un pedido salía partido entre muelles.** El carril (y la ruta, con Rutas a Piquear) se sorteaba por LÍNEA, no por pedido: 184 de 300 pedidos quedaban repartidos en 2-3 carriles; con rutas, un mismo pedido pertenecía a varias rutas. Un pedido es de una tienda: sale entero por un muelle | `order_strategies.StochasticOrderStrategy`: el sorteo estaba dentro del bucle de líneas | **Corregido**: se sortea una vez por pedido. +1 test (falla con el código viejo). Cambia la secuencia aleatoria → baseline nuevo | **Cerrado** (reprobado QA-7.7) |
| H-30 | **CRÍTICO** | Gate tras H-29 | **Abrazo mortal en la estación de descarga.** Con otra secuencia de pedidos (H-29), la corrida canónica (semilla 42) se trababa en t≈2.350 s y la cortaba el vigilante: 392 de 624 tareas sin hacer. Carril 1: los operarios con puesto asignado estaban DETRÁS de las entradas, y en las entradas (la única puerta de cada puesto) esperaban otros dos a que se liberara un puesto que ya tenía dueño | `Estacion.tomar` daba el puesto al primero que lo pedía, aunque otro esperara en la fila; y al dárselo soltaba la entrada, donde podía pararse otro | **Corregido**: (1) la fila se respeta (el puesto es de quien espera en la entrada de esa columna); (2) quien recibe el puesto aparta la entrada hasta llegar. +3 tests. Canónica: 624/624 | **Cerrado** |
| H-31 | MENOR (usabilidad) | QA-7.4 | Una fila de Destino → Zona con zona fuera de 1-7 **se descartaba en silencio** y sus pedidos caían al reparto sin aviso | `app.js _serializeDestinoStagingRows` filtraba la fila | **Corregido**: la fila viaja y la validación del servidor bloquea la corrida diciendo cuál es | **Cerrado** (reprobado) |
| H-32 | MENOR (configurabilidad) | QA-7.2 | La pestaña Outbound tiene **7 casillas fijas** (y el editor de destinos y la validación del servidor aceptan solo 1-7): un mapa con 5 o 10 carriles no se puede configurar bien | Número de zonas fijo en `index.html`, `app.js` y `config_manager.py` | Armar las casillas desde las zonas de `warehouse.db` → BK nuevo | Abierto |
| H-33 | OBS (usabilidad) | QA-7.7 | La **ruta** de cada pedido no viaja en el replay: ni el visor ni el QA pueden ver qué ruta es cada pedido | La WO la tiene (`wo.ruta`) pero los 8 puntos que emiten `work_order_update` no la incluyen | Emitirla solo si hay rutas (no cambia el canónico) | Abierto |
| H-34 | OBS (realismo) | QA-7.1 | Todos los operarios **nacen dentro del carril 1**: el punto de partida es la primera celda de la zona 1 (3,30), que ahora es un puesto de descarga. Es el origen probable de la co-ocupación del arranque | Depot = primera celda del staging 1 | **Corregido** (BK-29): cada operario nace en una celda propia (zonas de inicio > estacionamiento > celdas de espera). Semilla 42: 0 co-ocupaciones, tambien en el arranque | **Cerrado** |


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
- 2026-09-18 — Nivel 3 endurecido: con corridas grandes el visor tarda en
  responder y leer su estado a tiempo fijo daba lecturas viejas. Ahora cada
  lectura espera el evento `snapshotReady` del visor (`qaLeerVisor`). QA corre
  con el servidor `web-qa` (sin recarga automática) por H-06.
- 2026-09-18 — H-05: investigación con corridas instrumentadas (semilla 42) y
  trazas por celda; corrección en rama propia. Aprendizaje de método: al
  envolver funciones del motor para medir, el envoltorio debe aceptar
  parámetros nuevos (`**kw`); un envoltorio desactualizado invalidó una
  medición (las co-ocupaciones "subieron" por el instrumento, no por el motor).
- 2026-09-18 — Bloque 1 cerrado. QA-1.5 mide la mezcla por pedido. QA-1.9 se
  desdobla en (a) política antes de subir y (b) después. Método del nivel 3:
  esperar a que el visor termine el `autoload` (recarga la página) antes de
  leer. Archivos de órdenes con `DragEvent('drop')` sobre `#orders-dropzone`.
- 2026-09-19 — Bloque 2 cerrado. Herramientas nuevas:
  `scripts/qa/analizar_tours.py` (firma de cada estrategia por recorrido,
  con el mismo buscador de rutas del motor) y `scripts/qa/verificar_radio.py`
  (regla de radio y escalones de Cercanía). **Lección de método:** la
  posición para juzgar un despacho es la del momento en que el operario PIDIÓ
  trabajo, no la del mismo instante después de su primer paso
  (`analizar_replay.posicion_al_pedir`); sin eso aparecieron 18 "violaciones"
  falsas del radio. QA-2.4/2.5 reescritos con el criterio correcto.
- 2026-09-19 — Bloque 4 cerrado. Herramienta nueva:
  `scripts/qa/verificar_tiempos.py` (cada pick contra la fórmula con la
  config de la corrida y los datos maestros; duración de pasos y descargas).
  **Lecciones de método:** (1) el Excel de resultados se escribe ANTES de que
  termine el `.jsonl`: `esperar_corrida.py` ahora exige que el `.jsonl` cierre
  con `SIMULATION_END` (se analizó un archivo a medio escribir y parecieron
  40 tareas colgadas que no existían; descartado además con 6 semillas);
  (2) al medir la variabilidad, restar los componentes fijos (horquilla) y
  usar la muestra completa, con el error estándar como criterio; (3) reglas 8
  y 9 agregadas.
- 2026-09-19 — Bloque 5 (en curso). El nivel 3 suma la **carga y capacidad**
  de cada operario en el panel (no solo celda y estado): así apareció H-17.
  Lección: comparar cada dato que el visor dibuja, no solo la posición.
- 2026-09-19 — Bloque 5 cerrado. **Lecciones de método:** (1) un archivo
  para Importar se arma desde `/api/configurator/config` y se verifica que
  traiga la config completa: se usó una ruta inexistente (`/api/config`,
  404) y se importó un archivo casi vacío; la corrida salió con los valores
  por defecto del formulario (así aparecieron H-22 y, por el outbound
  encendido, H-19). (2) Un proceso de una investigación anterior (traza de
  H-05) quedó corriendo 10 horas en segundo plano: al cerrar una
  investigación, verificar que no queden procesos vivos. (3) El gate solo
  prueba el canónico (outbound apagado): H-19 se escapó por eso.
- 2026-09-19 — Bloque 3 cerrado. Herramientas de sesion: conteo propio de
  co-ocupaciones desde el replay (independiente del reporte del motor) y
  analisis de camiones/pallets. **Leccion:** un invariante probado con la
  semilla 42 no esta probado; QA-3.1 lo mide con varias corridas de semilla
  libre. Primera consulta a un consultor externo (Fable 5.1) con encargo
  escrito; su hallazgo principal (H-27) se verifico antes de aceptarlo.
