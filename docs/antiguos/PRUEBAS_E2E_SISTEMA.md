# PRUEBAS END-TO-END — GEMELO DIGITAL DE ALMACÉN
# Versión de referencia: V12.1 (rama feature/allocation-layer-v12.1)
# Última actualización: 2026-06-13

> **NOTA 2026-06-29 (arquitectura):** este catálogo se redactó cuando el visor
> Pygame (`run_replay_viewer.py`) aún era cadena viva. Desde el commit `3cd37e6`
> las 3 GUI de escritorio están archivadas en `_legacy/gui_escritorio/`; el único
> frontend vigente es el **viewer web** (`web_prototype`, :8000). Los casos que
> mencionan el visor Pygame aplican solo a esa GUI ya deprecada. Para las features
> nuevas (INIT-4: prioridad/olas/tiempos de pick) ver `docs/PLAN_INIT4.md`.

---

## TABLA DE CONTENIDOS

1. [Propósito y alcance](#1-propósito-y-alcance)
2. [Convenciones del catálogo](#2-convenciones-del-catálogo)
3. [Criterios de aceptación globales](#3-criterios-de-aceptación-globales)
4. [Configuraciones de referencia](#4-configuraciones-de-referencia)
5. [Suite H — Pipeline Headless](#5-suite-h--pipeline-headless)
6. [Suite SIM — Motor de Simulación](#6-suite-sim--motor-de-simulación)
7. [Suite ALLOC — Allocation Layer](#7-suite-alloc--allocation-layer)
8. [Suite TW — Congestión Opción C (Space-Time Planner)](#8-suite-tw--congestión-opción-c-space-time-planner)
9. [Suite OB — Outbound Fase 2](#9-suite-ob--outbound-fase-2)
10. [Suite CAL — Calibración C1-C5](#10-suite-cal--calibración-c1-c5)
11. [Suite WEB — Interfaz Web](#11-suite-web--interfaz-web)
12. [Suite MIG — Migración SQLite](#12-suite-mig--migración-sqlite)
13. [Suite REG — No-Regresión](#13-suite-reg--no-regresión)
14. [Checklist de aceptación de release](#14-checklist-de-aceptación-de-release)

---

## 1. PROPÓSITO Y ALCANCE

Este documento es la guía de validación empírica del sistema completo. Cubre
todos los subsistemas activos en V12.1 y sirve como referencia antes de
cualquier merge a `main` o entrega de milestone.

**Principio fundamental:** ninguna prueba se da por aprobada hasta que el
Director ve la evidencia concreta (log, captura, archivo generado).  
**No ejecutar** las pruebas durante la redacción de este documento; es
únicamente la guía detallada.

Subsistemas cubiertos:
- Pipeline headless (event_generator → .jsonl → Excel + heatmap)
- Motor SimPy (dispatcher, operarios, rutas, stock)
- Allocation Layer V12.1 (asignación FCFS antes de crear WorkOrders)
- Congestión Opción C (SpaceTimePlanner, ReservationTable)
- Outbound Fase 2 (FIFO truck, poll-wait lane, eventos viewer, staging A*)
- Calibración de tiempos C1-C5 (demo vs. escala real)
- Interfaz web FastAPI (configurador, runner, replay viewer, KPIs)
- Migración SQLite (Excel → warehouse.db)

Fuera de alcance en este documento:
- Optimizador Optuna (`run_optimization.py`) — requiere suite propia.
- Visor Pygame (`run_replay_viewer.py`) — validación visual manual.
- Código muerto / legacy (ver AUDITORIA.md).

---

## 2. CONVENCIONES DEL CATÁLOGO

Cada caso de prueba sigue la estructura:

| Campo              | Descripción                                              |
|--------------------|----------------------------------------------------------|
| **ID**             | Identificador único (Suite-NN, p.ej. H-01)              |
| **Objetivo**       | Qué se está verificando                                  |
| **Tipo**           | Happy Path / Edge Case / No-Regresión                    |
| **Precondiciones** | Estado del sistema y config necesaria antes de ejecutar  |
| **Pasos**          | Comandos exactos y reproducibles                         |
| **Resultado esp.** | Evidencia concreta y verificable (logs, archivos, JSON)  |
| **Estado**         | PENDIENTE / APROBADO / FALLIDO                           |

Directorio raíz del proyecto: `D:\Documentos\Martin\Gemelos Digital\`  
Todos los comandos se ejecutan desde esa raíz.

### Convenciones de placeholder

- `{TS}` = timestamp del run, formato `YYYYMMDD_HHMMSS`.
- `output/simulation_{TS}/` = directorio de salida del run.
- `config.json` = configuración demo activa (perfil rápido).

---

## 3. CRITERIOS DE ACEPTACIÓN GLOBALES

Para que una suite completa se marque APROBADA, **todos** sus casos deben
cumplir:

1. **Sin excepción no controlada:** el proceso termina con código 0 y sin
   traceback en stderr.
2. **Sin UnicodeEncodeError:** la consola no muestra errores de encoding
   (violación de Ley 4 del CLAUDE.md).
3. **Archivos de salida generados:** los archivos listados en "Resultado esp."
   existen en `output/simulation_{TS}/` con tamaño > 0.
4. **Métricas dentro de rango:** los KPIs numéricos no se alejan más de ±10%
   de los valores de referencia documentados aquí (salvo que el test sea
   explícitamente estocástico y se indique otra tolerancia).
5. **No-regresión del baseline:** la suite REG pasa antes de aprobar cualquier
   otra suite que modifique el motor.

---

## 4. CONFIGURACIONES DE REFERENCIA

### 4.1 config.json — Perfil Demo (predeterminado)

```
Agentes    : 4 (2 GroundOperator + 2 Forklift)
Órdenes    : 150 (estocástico; 60% pequeñas, 30% medianas, 10% grandes)
Layout     : layouts/WH1 v2.tmx
Congestión : timewindow, dt_wait=0.1, clearance=0, max_expansions=20000
Outbound   : enabled=true, policy=interval, truck_interval=20,
             truck_capacity=8, loading_time=2
time_per_cell: 0.1 s
Escala     : RÁPIDA (demo, no 1:1 con real)
```

### 4.2 config_calibrado_v1.json — Perfil Escala Real

```
Agentes    : 4 (2 GroundOperator + 2 Forklift)
Órdenes    : 150 (mismo mix)
time_per_cell: 1.0 s (1 celda = 1 m, Ground 1.0 m/s)
speed_factor_forklift: 0.5 (Forklift 2.0 m/s → 0.5 × time)
picking_time: 15.0 s/línea, horquilla: 8.0 s
Outbound   : truck_interval=3600, truck_capacity=26, loading_time=90 s/pallet
Congestión : dt_wait=1.0, wait_timeout=5.0, wait_hard_cap=300
```

### 4.3 config_stress_tw_v2.json — Stress 20 agentes (outbound ON)

```
Agentes    : 20 (mix GroundOperator + Forklift)
Outbound   : enabled=true, policy=interval, truck_interval=20
Congestión : timewindow
```

### 4.4 config_stress_tw_exec.json — Stress 20 agentes (outbound OFF) ← BASELINE

```
Agentes    : 20
Outbound   : enabled=FALSE
Congestión : timewindow
MD5 JSONL baseline verificado: 18502db7de9f33bdccf94db742c45dd8
Eventos esperados              : 9918
```

---

## 5. SUITE H — PIPELINE HEADLESS

Verifica que el pipeline completo (SimPy → JSONL → Excel + heatmap) se ejecuta
sin errores y produce todos los artefactos de salida.

---

### H-01 — Generación de replay con config demo

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Pipeline headless completo termina sin error y genera todos los artefactos |
| **Tipo** | Happy Path |
| **Precondiciones** | `config.json` intacto; `layouts/WH1 v2.tmx` y `layouts/Warehouse_Logic_v2.xlsx` presentes; entorno Python activo |
| **Pasos** | `python entry_points/run_generate_replay.py` |
| **Resultado esp.** | 1. Proceso termina con código 0. 2. Se crea `output/simulation_{TS}/` con los archivos: `replay_{TS}.jsonl`, `simulation_report_{TS}.json`, `simulation_report_{TS}.xlsx`, `warehouse_heatmap_{TS}.png`, `simulacion_completada_{TS}.json`, `raw_events_{TS}.json`, `timewindow_shadow_report_{TS}.json`, `congestion_report_{TS}.json`. 3. `replay_{TS}.jsonl` tiene > 5 000 líneas. 4. Stdout muestra `[OK]` o líneas de progreso sin `ERROR` ni `Traceback`. |
| **Estado** | PENDIENTE |

---

### H-02 — Estructura del JSONL

| Campo | Detalle |
|-------|---------|
| **Objetivo** | El JSONL contiene los tipos de evento esperados en proporciones razonables |
| **Tipo** | Happy Path |
| **Precondiciones** | H-01 aprobado; run más reciente disponible |
| **Pasos** | `python -c "import json, collections; lines=open('output/simulation_{TS}/replay_{TS}.jsonl').readlines(); cnt=collections.Counter(json.loads(l).get('type','?') for l in lines); [print(n,t) for t,n in cnt.most_common()]"` |
| **Resultado esp.** | Presencia obligatoria de tipos: `estado_agente`, `work_order_update`, `operation_completed`, `task_completed`, `work_order_completed`. Con outbound ON: también `truck_arrived`, `truck_departed`, `pallet_shipped`. Ningún tipo `?` representa > 1% del total. |
| **Estado** | PENDIENTE |

---

### H-03 — Excel de reporte generado y parseable

| Campo | Detalle |
|-------|---------|
| **Objetivo** | El archivo .xlsx existe y tiene las hojas esperadas |
| **Tipo** | Happy Path |
| **Precondiciones** | H-01 aprobado |
| **Pasos** | `python -c "import openpyxl; wb=openpyxl.load_workbook('output/simulation_{TS}/simulation_report_{TS}.xlsx'); print(wb.sheetnames)"` |
| **Resultado esp.** | Sin excepción. Imprime lista de hojas que incluye al menos una hoja de resumen. Tamaño del archivo > 5 KB. |
| **Estado** | PENDIENTE |

---

### H-04 — Heatmap PNG generado

| Campo | Detalle |
|-------|---------|
| **Objetivo** | El heatmap se genera sin errores de subprocess |
| **Tipo** | Happy Path |
| **Precondiciones** | H-01 aprobado; matplotlib disponible |
| **Pasos** | Verificar existencia y tamaño: `python -c "import os; p='output/simulation_{TS}/warehouse_heatmap_{TS}.png'; print(os.path.exists(p), os.path.getsize(p))"` |
| **Resultado esp.** | `True` y tamaño > 10 000 bytes. |
| **Estado** | PENDIENTE |

---

### H-05 — Ejecución con archivo de config alternativo

| Campo | Detalle |
|-------|---------|
| **Objetivo** | El runner acepta un config diferente mediante variable/flag de entorno |
| **Tipo** | Happy Path |
| **Precondiciones** | `config_calibrado_v1.json` presente |
| **Pasos** | Determinar el mecanismo de config alternativo (verificar argparse o env var en `run_generate_replay.py`). Ejecutar con ese mecanismo apuntando a `config_calibrado_v1.json`. |
| **Resultado esp.** | Run termina con código 0. `simulation_report_{TS}.json` muestra `time_per_cell: 1.0` en el bloque de configuración. |
| **Estado** | PENDIENTE |

---

### H-06 — Ejecución sin layout (error controlado)

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Si el layout TMX no existe, el sistema falla con mensaje claro (no traceback crudo) |
| **Tipo** | Edge Case |
| **Precondiciones** | Renombrar temporalmente `layouts/WH1 v2.tmx` a `layouts/WH1 v2.tmx.bak` |
| **Pasos** | `python entry_points/run_generate_replay.py`; restaurar el archivo después. |
| **Resultado esp.** | Proceso termina con código != 0. Stdout o stderr muestra un mensaje de error descriptivo (p.ej. `[ERROR] layout file not found` o similar). No se genera directorio de output. |
| **Estado** | PENDIENTE |

---

## 6. SUITE SIM — MOTOR DE SIMULACIÓN

Verifica el comportamiento interno del motor SimPy: despacho de WorkOrders,
picking, rutas, consumo de stock y métricas de rendimiento.

---

### SIM-01 — Tareas completadas > 0

| Campo | Detalle |
|-------|---------|
| **Objetivo** | El motor completa al menos una tarea de picking en la duración de la simulación |
| **Tipo** | Happy Path |
| **Precondiciones** | `config.json`; H-01 aprobado |
| **Pasos** | `python -c "import json; sr=json.load(open('output/simulation_{TS}/simulation_report_{TS}.json')); print(sr['resumen_ejecutivo'])"` |
| **Resultado esp.** | `Total de Tareas Completadas (unidades)` > 0. `Tiempo Total de Simulacion (segundos)` > 0. `Productividad (Tareas/Segundo)` > 0. |
| **Estado** | PENDIENTE |

---

### SIM-02 — Rendimiento de todos los agentes

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Todos los agentes configurados aparecen en el reporte con tareas > 0 |
| **Tipo** | Happy Path |
| **Precondiciones** | `config.json` (4 agentes); H-01 aprobado |
| **Pasos** | `python -c "import json; sr=json.load(open('output/simulation_{TS}/simulation_report_{TS}.json')); [print(a) for a in sr['rendimiento_agentes']]"` |
| **Resultado esp.** | Lista con 4 entradas (GroundOp-01, GroundOp-02, Forklift-01, Forklift-02). Cada una con campo de tareas completadas >= 0 (puede ser 0 si la simulación es corta). Al menos dos agentes con tareas > 0. |
| **Estado** | PENDIENTE |

---

### SIM-03 — Stock consumido coherentemente

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Cada `operation_completed` en el JSONL corresponde a un decremento de stock real |
| **Tipo** | Happy Path |
| **Precondiciones** | H-01 aprobado; `layouts/Warehouse_Logic_v2.xlsx` presente |
| **Pasos** | `python -c "import json; lines=open('output/simulation_{TS}/replay_{TS}.jsonl').readlines(); ops=[json.loads(l) for l in lines if json.loads(l).get('type')=='operation_completed']; print(len(ops), 'ops completadas'); print(ops[0] if ops else 'ninguna')"` |
| **Resultado esp.** | Número de `operation_completed` > 0. Cada evento tiene campos `agent_id`, `task_id`, `qty`. No hay qty negativa. |
| **Estado** | PENDIENTE |

---

### SIM-04 — Tiempo de simulación avanza monotónicamente

| Campo | Detalle |
|-------|---------|
| **Objetivo** | El campo `t` en todos los eventos JSONL es no-decreciente (causalidad SimPy) |
| **Tipo** | Happy Path |
| **Precondiciones** | H-01 aprobado |
| **Pasos** | `python -c "import json; ts=[json.loads(l).get('t',0) for l in open('output/simulation_{TS}/replay_{TS}.jsonl')]; violations=sum(1 for i in range(1,len(ts)) if ts[i]<ts[i-1]); print('violaciones de orden temporal:', violations)"` |
| **Resultado esp.** | `violaciones de orden temporal: 0` |
| **Estado** | PENDIENTE |

---

### SIM-05 — Dispatcher sin deadlock en run demo completo

| Campo | Detalle |
|-------|---------|
| **Objetivo** | La simulación termina (no cuelga) dentro de un tiempo razonable |
| **Tipo** | Happy Path |
| **Precondiciones** | `config.json` |
| **Pasos** | `python entry_points/run_generate_replay.py` con timeout de 5 minutos de pared. |
| **Resultado esp.** | El proceso termina antes de 5 minutos (típicamente < 60 s para el perfil demo). |
| **Estado** | PENDIENTE |

---

### SIM-06 — Generación estocástica vs. determinista

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Dos runs con `order_generation_mode: stochastic` producen recuentos similares pero distintos; un run con seed fija (si implementado) produce el mismo JSONL |
| **Tipo** | Edge Case |
| **Precondiciones** | `config.json` |
| **Pasos** | Ejecutar dos veces `python entry_points/run_generate_replay.py` y comparar el número de líneas de los JSONL. |
| **Resultado esp.** | Las dos ejecuciones producen entre 5 000 y 15 000 líneas cada una. El número de líneas puede diferir (estocasticidad). Los dos runs terminan sin error. |
| **Estado** | PENDIENTE |

---

## 7. SUITE ALLOC — ALLOCATION LAYER

Verifica la Iniciativa #1 (V12.1): asignación FCFS de stock real antes de
generar WorkOrders. Campo clave: `pallet_reserve_ok` en `outbound_metrics` y
ausencia de `pallet_reserve_fail`.

---

### ALLOC-01 — Stock asignado antes de crear WorkOrder (Happy Path)

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Todas las operaciones de picking tienen stock disponible al momento de la asignación |
| **Tipo** | Happy Path |
| **Precondiciones** | `config.json`; `Warehouse_Logic_v2.xlsx` con stock suficiente |
| **Pasos** | 1. `python entry_points/run_generate_replay.py`. 2. `python -c "import json; tw=json.load(open('output/simulation_{TS}/timewindow_shadow_report_{TS}.json')); ob=tw.get('outbound_metrics',{}); print('pallet_reserve_ok:', ob.get('pallet_reserve_ok',0)); print('pallet_reserve_fail:', ob.get('pallet_reserve_fail',0))"` |
| **Resultado esp.** | `pallet_reserve_ok` >= número de `operation_completed`. `pallet_reserve_fail` = 0 o ausente. |
| **Estado** | PENDIENTE |

---

### ALLOC-02 — Órdenes parciales (ship_partial)

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Cuando el stock disponible es menor que la cantidad solicitada, se crea una WorkOrder parcial (qty_allocated < qty_requested) y no falla |
| **Tipo** | Edge Case |
| **Precondiciones** | `config.json` con `fulfillment_policy: ship_partial`; Excel con al menos una ubicación con stock menor que el volumen de un pedido grande (80 unidades) |
| **Pasos** | 1. Run normal. 2. Buscar en JSONL eventos `work_order_update` con campo `is_partial: true` o `qty_allocated < qty_requested`. |
| **Resultado esp.** | Al menos un evento `work_order_update` con `is_partial: true` (si el mix de órdenes y stock lo permite). El sistema no lanza excepción. Las WorkOrders parciales son procesadas y completadas normalmente. |
| **Estado** | PENDIENTE |

---

### ALLOC-03 — Backorder visible en métricas

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Las órdenes que no pudieron ser completamente asignadas (backorder) quedan registradas en el reporte |
| **Tipo** | Happy Path |
| **Precondiciones** | `config.json`; stock intencionalmente bajo (editar Excel para reducir qty en una ubicación) |
| **Pasos** | 1. Run con stock reducido. 2. Verificar en `simulation_report_{TS}.json` o `timewindow_shadow_report_{TS}.json` la presencia de campo de backorder o `qty_backorder > 0`. |
| **Resultado esp.** | Campo de backorder presente con valor > 0. El sistema termina sin error. (Este test puede requerir preparación manual del Excel de datos.) |
| **Estado** | PENDIENTE |

---

### ALLOC-04 — FCFS: primera orden llegada, primera asignada

| Campo | Detalle |
|-------|---------|
| **Objetivo** | El orden de asignación de stock sigue FCFS (First Come First Served) según el timestamp de creación de la WorkOrder |
| **Tipo** | Happy Path |
| **Precondiciones** | H-01 aprobado |
| **Pasos** | `python -c "import json; lines=open('output/simulation_{TS}/replay_{TS}.jsonl').readlines(); wos=[json.loads(l) for l in lines if json.loads(l).get('type')=='work_order_update' and json.loads(l).get('status')=='created']; ts=[w.get('t',0) for w in wos]; print('WOs creadas:', len(ts)); print('orden mon. creciente:', all(ts[i]<=ts[i+1] for i in range(len(ts)-1)))"` |
| **Resultado esp.** | WorkOrders creadas con timestamps no-decrecientes (creación en orden FCFS). |
| **Estado** | PENDIENTE |

---

## 8. SUITE TW — CONGESTIÓN OPCIÓN C (SPACE-TIME PLANNER)

Verifica que el SpaceTimePlanner (time-window routing con ReservationTable)
funciona sin deadlocks, sin fallbacks al planner base, y que las métricas de
planificación son razonables.

---

### TW-01 — Cero deadlocks en run demo

| Campo | Detalle |
|-------|---------|
| **Objetivo** | `deadlock_incidents` = [] en el reporte de congestión |
| **Tipo** | Happy Path |
| **Precondiciones** | `config.json` (mode=timewindow, shadow=false) |
| **Pasos** | `python -c "import json; c=json.load(open('output/simulation_{TS}/congestion_report_{TS}.json')); print('deadlocks:', c.get('deadlock_incidents')); print('hardcap:', c['exclusion']['hardcap_incidents'])"` |
| **Resultado esp.** | `deadlock_incidents: []`. `hardcap_incidents: 0`. |
| **Estado** | PENDIENTE |

---

### TW-02 — Cero exec_fallbacks

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Ningún segmento de ruta cayó al pathfinder estático de respaldo |
| **Tipo** | Happy Path |
| **Precondiciones** | `config.json` |
| **Pasos** | `python -c "import json; tw=json.load(open('output/simulation_{TS}/timewindow_shadow_report_{TS}.json')); print('plans_failed:', tw['plans_failed']); print('exec_fallbacks:', tw['exec_fallbacks'])"` |
| **Resultado esp.** | `plans_failed: 0`. `exec_fallbacks: 0`. |
| **Estado** | PENDIENTE |

---

### TW-03 — Planes encontrados = planes solicitados

| Campo | Detalle |
|-------|---------|
| **Objetivo** | El planner resuelve el 100% de los segmentos solicitados |
| **Tipo** | Happy Path |
| **Precondiciones** | `config.json` |
| **Pasos** | `python -c "import json; tw=json.load(open('output/simulation_{TS}/timewindow_shadow_report_{TS}.json')); print('segments_planned:', tw['segments_planned']); print('plans_found:', tw['plans_found']); print('expansion_cap_hits:', tw['expansion_cap_hits'])"` |
| **Resultado esp.** | `plans_found` == `segments_planned`. `expansion_cap_hits: 0` (ningún plan alcanzó el límite de 20 000 expansiones). |
| **Estado** | PENDIENTE |

---

### TW-04 — Métricas de rendimiento del planner dentro de rango

| Campo | Detalle |
|-------|---------|
| **Objetivo** | El planner no introduce latencia excesiva en la simulación |
| **Tipo** | Happy Path |
| **Precondiciones** | `config.json`; run demo con 4 agentes |
| **Pasos** | `python -c "import json; tw=json.load(open('output/simulation_{TS}/timewindow_shadow_report_{TS}.json')); print('avg_plan_ms:', tw['avg_plan_ms']); print('max_plan_ms:', tw['max_plan_ms']); print('avg_expansions:', tw['avg_expansions'])"` |
| **Resultado esp.** | `avg_plan_ms` < 10 ms. `max_plan_ms` < 200 ms. `avg_expansions` < 500. (Referencia: run del 2026-06-10: avg=2.92 ms, max=118 ms, avg_exp=96.) |
| **Estado** | PENDIENTE |

---

### TW-05 — Cero reserve_overlaps en ReservationTable

| Campo | Detalle |
|-------|---------|
| **Objetivo** | El mecanismo de reserva de celdas espacio-temporales no genera solapamientos |
| **Tipo** | Happy Path |
| **Precondiciones** | `config.json` |
| **Pasos** | `python -c "import json; tw=json.load(open('output/simulation_{TS}/timewindow_shadow_report_{TS}.json')); print('reserve_overlaps:', tw['reserve_overlaps'])"` |
| **Resultado esp.** | `reserve_overlaps: 0` |
| **Estado** | PENDIENTE |

---

### TW-06 — Modo shadow (verificación sin colisiones reales)

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Con `shadow: true` el planner registra colisiones sin bloquear la simulación |
| **Tipo** | Edge Case |
| **Precondiciones** | Copia temporal de `config.json` con `congestion.timewindow.shadow: true` |
| **Pasos** | 1. Editar config temporal. 2. `python entry_points/run_generate_replay.py`. 3. Revisar `timewindow_shadow_report_{TS}.json`. |
| **Resultado esp.** | Run termina sin error. `table_overlap_violations` puede ser > 0 (colisiones sin resolver en modo shadow). `exec_fallbacks` puede ser 0 (planner aún planea, pero no bloquea). |
| **Estado** | PENDIENTE |

---

### TW-07 — Stress 20 agentes con outbound ON

| Campo | Detalle |
|-------|---------|
| **Objetivo** | El planner escala a 20 agentes sin deadlock y sin timeouts |
| **Tipo** | Happy Path / Stress |
| **Precondiciones** | `config_stress_tw_v2.json` |
| **Pasos** | `python entry_points/run_generate_replay.py` (usando config_stress_tw_v2.json). Verificar `congestion_report_{TS}.json` y `timewindow_shadow_report_{TS}.json`. |
| **Resultado esp.** | `deadlock_incidents: []`. `exec_fallbacks: 0`. `plans_failed: 0`. Run termina < 10 minutos. |
| **Estado** | PENDIENTE |

---

## 9. SUITE OB — OUTBOUND FASE 2

Verifica el subsistema Outbound completo implementado en F2.a-F2.d: FIFO de
camiones, poll-wait en carril, emisión de eventos al viewer web, y bloqueo de
celdas de staging para el planner A*.

---

### OB-01 — Camiones llegan y parten (Happy Path)

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Los eventos `truck_arrived` y `truck_departed` aparecen en el JSONL con frecuencia correcta |
| **Tipo** | Happy Path |
| **Precondiciones** | `config.json` (outbound enabled, policy=interval, truck_interval=20) |
| **Pasos** | `python -c "import json; lines=open('output/simulation_{TS}/replay_{TS}.jsonl').readlines(); arrived=sum(1 for l in lines if json.loads(l).get('type')=='truck_arrived'); departed=sum(1 for l in lines if json.loads(l).get('type')=='truck_departed'); print('arrived:', arrived, 'departed:', departed)"` |
| **Resultado esp.** | `arrived` == `departed` (todo camión que llega parte). Ambos > 0. La cantidad de camiones ≈ duración_simulación / truck_interval (±2 camiones). |
| **Estado** | PENDIENTE |

---

### OB-02 — Pallets embarcados en orden FIFO

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Los eventos `pallet_shipped` aparecen en orden de `t_staged` (First In First Out) |
| **Tipo** | Happy Path |
| **Precondiciones** | H-01 aprobado; run con outbound ON |
| **Pasos** | `python -c "import json; lines=open('output/simulation_{TS}/replay_{TS}.jsonl').readlines(); shipped=[json.loads(l) for l in lines if json.loads(l).get('type')=='pallet_shipped']; staged_ts=[p.get('t_staged',0) for p in shipped]; print('pallets shipped:', len(staged_ts)); print('FIFO order:', all(staged_ts[i]<=staged_ts[i+1] for i in range(len(staged_ts)-1)))"` |
| **Resultado esp.** | `FIFO order: True`. `pallets shipped` > 0. |
| **Estado** | PENDIENTE |

---

### OB-03 — pallet_reserve_ok = número de operaciones completadas

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Cada pallet staged tiene su reserva registrada |
| **Tipo** | Happy Path |
| **Precondiciones** | H-01 aprobado; run con outbound ON |
| **Pasos** | `python -c "import json; tw=json.load(open('output/simulation_{TS}/timewindow_shadow_report_{TS}.json')); ob=tw.get('outbound_metrics',{}); sr=json.load(open('output/simulation_{TS}/simulation_report_{TS}.json')); ops=int(sr['resumen_ejecutivo'].get('Total de Tareas Completadas (unidades)',0)); print('pallet_reserve_ok:', ob.get('pallet_reserve_ok',0), 'vs ops:', ops)"` |
| **Resultado esp.** | `pallet_reserve_ok` >= `ops completadas`. `pallet_reserve_ok` > 0. (Referencia: run 2026-06-10: 306 ops, 306 pallet_reserve_ok.) |
| **Estado** | PENDIENTE |

---

### OB-04 — Poll-wait en carril lleno (lane_full_wait)

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Cuando una columna de staging está llena, el operario espera (no salta silenciosamente) |
| **Tipo** | Edge Case |
| **Precondiciones** | Config con `zone_capacity_default` bajo (p.ej. 2) y alta demanda, o run con muchos agentes. Verificar `outbound_metrics` en el reporte. |
| **Pasos** | `python -c "import json; tw=json.load(open('output/simulation_{TS}/timewindow_shadow_report_{TS}.json')); ob=tw.get('outbound_metrics',{}); print('slot_wait_events:', ob.get('slot_wait_events',0)); print('slot_wait_time:', ob.get('slot_wait_time',0))"` |
| **Resultado esp.** | Si se generó contención: `slot_wait_events > 0` y `slot_wait_time > 0`. El sistema no crashea. (Referencia: run 2026-06-10 con config demo: 6 slot_wait_events, 267.8 s de espera acumulada.) |
| **Estado** | PENDIENTE |

---

### OB-05 — Camión vacío (sin pallets staged)

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Si un camión llega y no hay pallets, parte con `pallets_loaded: 0` sin error |
| **Tipo** | Edge Case |
| **Precondiciones** | Config con `truck_interval` muy bajo (p.ej. 1 s) para que los camiones lleguen antes de que se stageen pallets |
| **Pasos** | 1. Config temporal con `truck_interval: 1`. 2. Run. 3. Verificar JSONL para eventos `truck_departed` con `pallets_loaded: 0`. |
| **Resultado esp.** | Al menos un evento `truck_departed` con `pallets_loaded: 0` y `backlog: 0`. No hay excepción. |
| **Estado** | PENDIENTE |

---

### OB-06 — Capacidad de camión respetada

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Ningún camión carga más pallets que `truck_capacity` |
| **Tipo** | Happy Path |
| **Precondiciones** | `config.json` (truck_capacity=8) |
| **Pasos** | `python -c "import json; lines=open('output/simulation_{TS}/replay_{TS}.jsonl').readlines(); deps=[json.loads(l) for l in lines if json.loads(l).get('type')=='truck_departed']; overloads=[d for d in deps if d.get('pallets_loaded',0)>8]; print('departures:', len(deps), '| overloads:', len(overloads))"` |
| **Resultado esp.** | `overloads: 0`. Ningún `pallets_loaded` supera 8. |
| **Estado** | PENDIENTE |

---

### OB-07 — Staging no-transitable para el planner A*

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Los agentes no navegan A* a través de celdas de staging (F2.d); se mueven al entry_cell aledaño y hacen _jump_to |
| **Tipo** | Happy Path |
| **Precondiciones** | `config.json`; outbound ON; H-01 aprobado |
| **Pasos** | 1. Verificar en stdout del run la línea `[OUTBOUND] F2.d: N celdas de staging marcadas no-caminables en collision_matrix.` donde N > 0. 2. Verificar que los `estado_agente` en el JSONL para un operario durante una descarga muestran posición en entry_cell antes de las celdas de staging. |
| **Resultado esp.** | Mensaje F2.d presente en stdout con N > 0. No hay excepciones de pathfinding relacionadas con staging. |
| **Estado** | PENDIENTE |

---

### OB-08 — Outbound desactivado no afecta pipeline

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Con `outbound.enabled: false`, el pipeline funciona sin cambios en la lógica de picking |
| **Tipo** | No-Regresión |
| **Precondiciones** | `config_stress_tw_exec.json` (outbound=false) |
| **Pasos** | `python entry_points/run_generate_replay.py`. Verificar que no hay eventos `truck_*` ni `pallet_*` en el JSONL. Verificar que `collision_matrix` no fue modificada (mensaje F2.d no aparece). |
| **Resultado esp.** | JSONL sin `truck_arrived`, `truck_departed`, `pallet_shipped`. Sin mensaje `[OUTBOUND] F2.d`. Run termina sin error. |
| **Estado** | PENDIENTE |

---

## 10. SUITE CAL — CALIBRACIÓN C1-C5

Verifica que los perfiles de calibración (demo rápido vs. escala real 1:1) se
comportan coherentemente con sus parámetros de tiempo.

---

### CAL-01 — Perfil Demo: velocidad de simulación (C1)

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Con `time_per_cell=0.1`, los agentes completan muchas más tareas por segundo de simulación que con `time_per_cell=1.0` |
| **Tipo** | Happy Path |
| **Precondiciones** | `config.json` para demo; `config_calibrado_v1.json` para real |
| **Pasos** | Comparar `Productividad (Tareas/Segundo)` de dos runs: uno con config demo y otro con config_calibrado_v1.json. |
| **Resultado esp.** | Productividad demo ≈ 10× la productividad real (ratio aproximado de time_per_cell=1.0 vs 0.1). La duración de simulación en segundos es ~10× mayor en el perfil real para el mismo número de órdenes. |
| **Estado** | PENDIENTE |

---

### CAL-02 — Escala real 1:1 (C2): tiempo de celda = 1 s

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Con el perfil calibrado, 1 celda = 1 m y 1 s simulación = 1 s real |
| **Tipo** | Happy Path |
| **Precondiciones** | `config_calibrado_v1.json` |
| **Pasos** | 1. Run con config_calibrado_v1.json. 2. Verificar en reporte que `time_per_cell: 1.0`. 3. Medir tiempo entre dos `estado_agente` consecutivos de un mismo agente en movimiento: delta_t / pasos_de_ruta ≈ 1.0 s/celda. |
| **Resultado esp.** | `time_per_cell` confirmado en configuración del reporte. Delta de tiempo entre eventos de movimiento ≈ 1.0 s por celda (±0.1 s). |
| **Estado** | PENDIENTE |

---

### CAL-03 — Forklift más rápido que GroundOperator (C3)

| Campo | Detalle |
|-------|---------|
| **Objetivo** | El Forklift tiene speed_factor_forklift=0.5 (el doble de rápido en escala real), reflejado en menor tiempo de recorrido |
| **Tipo** | Happy Path |
| **Precondiciones** | `config_calibrado_v1.json` (speed_factor_forklift=0.5) |
| **Pasos** | Comparar en `rendimiento_agentes` el tiempo promedio por tarea de Forklift vs. GroundOperator para rutas de longitud equivalente. |
| **Resultado esp.** | Tiempo promedio por tarea Forklift < Tiempo GroundOperator (dado que Forklift es más rápido en traslado). Diferencia visible en el reporte. |
| **Estado** | PENDIENTE |

---

### CAL-04 — Picking time y horquilla presentes en eventos (C4)

| Campo | Detalle |
|-------|---------|
| **Objetivo** | El tiempo de picking por línea (15 s) y el tiempo de horquilla (8 s) se aplican en las operaciones correspondientes |
| **Tipo** | Happy Path |
| **Precondiciones** | `config_calibrado_v1.json` (picking_time=15.0, horquilla=8.0) |
| **Pasos** | Analizar en JSONL eventos consecutivos de tipo `operation_completed` para un agente tipo GroundOperator: el tiempo entre inicio y fin de una operación de una sola línea debería incluir los 15 s de picking más el tiempo de recorrido. Para Forklift: incluye 8 s de horquilla. |
| **Resultado esp.** | Duración de operación de picking (GroundOperator, ruta corta) >= 15 s. Duración de operación con horquilla (Forklift) >= 8 s. |
| **Estado** | PENDIENTE |

---

### CAL-05 — Outbound en escala real: loading_time por pallet (C5)

| Campo | Detalle |
|-------|---------|
| **Objetivo** | El tiempo de carga de un camión es `loading_time × n_pallets` (90 s por pallet en escala real) |
| **Tipo** | Happy Path |
| **Precondiciones** | `config_calibrado_v1.json` (loading_time=90, truck_capacity=26) |
| **Pasos** | 1. Run con config_calibrado_v1.json. 2. En JSONL, buscar un evento `truck_arrived` seguido de `truck_departed` con `pallets_loaded=N`. 3. Calcular delta_t = t_departed - t_arrived. |
| **Resultado esp.** | `delta_t ≈ 90 × N` segundos (tolerancia ±1 s). Para un camión completo (26 pallets) ≈ 2340 s. |
| **Estado** | PENDIENTE |

---

## 11. SUITE WEB — INTERFAZ WEB

Verifica la interfaz web FastAPI: configurador, generación de replay desde el
browser, replay viewer, y KPIs de outbound.

---

### WEB-01 — Servidor arranca en puerto 8000

| Campo | Detalle |
|-------|---------|
| **Objetivo** | El servidor FastAPI levanta sin error |
| **Tipo** | Happy Path |
| **Precondiciones** | Python con FastAPI, uvicorn y pydantic instalados. Puerto 8000 libre. |
| **Pasos** | `python web_prototype/server.py` (o `start_server.bat`). En otra terminal: `curl http://localhost:8000/health` o abrir en browser. |
| **Resultado esp.** | Respuesta HTTP 200 en `/health` o `/`. Stdout del servidor muestra `Uvicorn running on http://0.0.0.0:8000`. Sin `ImportError` ni `ModuleNotFoundError`. |
| **Estado** | PENDIENTE |

---

### WEB-02 — Configurador carga y muestra config actual

| Campo | Detalle |
|-------|---------|
| **Objetivo** | El endpoint GET `/api/config` devuelve la configuración activa |
| **Tipo** | Happy Path |
| **Precondiciones** | Servidor WEB-01 corriendo |
| **Pasos** | `curl http://localhost:8000/api/config` |
| **Resultado esp.** | JSON válido con campos `outbound`, `congestion`, `tiempos`, `agent_types`, `total_ordenes`. Valores coinciden con `config.json`. |
| **Estado** | PENDIENTE |

---

### WEB-03 — Generación de replay desde el browser

| Campo | Detalle |
|-------|---------|
| **Objetivo** | El endpoint POST `/api/run` (o equivalente) dispara un run headless y devuelve el path del JSONL |
| **Tipo** | Happy Path |
| **Precondiciones** | Servidor WEB-01 corriendo |
| **Pasos** | Desde el configurador web (http://localhost:8000), hacer click en "Generar Replay" o equivalente. Esperar respuesta. |
| **Resultado esp.** | Respuesta JSON con campo `replay_file` o similar apuntando a un archivo `.jsonl` recién generado. El archivo existe en disco. |
| **Estado** | PENDIENTE |

---

### WEB-04 — Replay viewer muestra eventos en el mapa

| Campo | Detalle |
|-------|---------|
| **Objetivo** | El visor web carga el JSONL y muestra movimiento de agentes en el mapa |
| **Tipo** | Happy Path |
| **Precondiciones** | Servidor WEB-01 corriendo; al menos un run generado; WEB-03 aprobado |
| **Pasos** | Abrir el visor (p.ej. http://localhost:8000/viewer). Cargar el JSONL. Presionar Play. |
| **Resultado esp.** | Los agentes aparecen en el mapa en posición inicial. Al avanzar el tiempo, los agentes se mueven. No hay errores JS en consola del browser. |
| **Estado** | PENDIENTE |

---

### WEB-05 — KPIs outbound visibles en viewer

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Las métricas de camiones (Trucks) y pallets embarcados (Shipped) se actualizan en el visor |
| **Tipo** | Happy Path |
| **Precondiciones** | Run con outbound ON; WEB-04 aprobado |
| **Pasos** | En el viewer, avanzar hasta un punto donde ya hubo truck_departed con pallets. Verificar el panel de KPIs. |
| **Resultado esp.** | Métrica "Trucks" muestra un número > 0. Métrica "Shipped" muestra un número > 0. Los valores aumentan al avanzar el tiempo en el visor. |
| **Estado** | PENDIENTE |

---

### WEB-06 — Endpoint /api/snapshot devuelve bloque outbound

| Campo | Detalle |
|-------|---------|
| **Objetivo** | El snapshot de estado incluye los campos outbound en la respuesta JSON |
| **Tipo** | Happy Path |
| **Precondiciones** | Servidor corriendo; run con outbound ON cargado en el viewer |
| **Pasos** | `curl "http://localhost:8000/api/snapshot?t=500"` (ajustar t a un punto donde ya hay trucks). |
| **Resultado esp.** | JSON de respuesta contiene `metrics.outbound` con subcampos `trucks_dispatched`, `pallets_shipped`, `backlog`. |
| **Estado** | PENDIENTE |

---

### WEB-07 — Configurador guarda cambios en config.json

| Campo | Detalle |
|-------|---------|
| **Objetivo** | El endpoint PUT/POST `/api/config` actualiza `config.json` en disco |
| **Tipo** | Happy Path |
| **Precondiciones** | Servidor WEB-01 corriendo |
| **Pasos** | 1. `curl -X POST http://localhost:8000/api/config -H "Content-Type: application/json" -d '{"total_ordenes": 99}'`. 2. Verificar `config.json`: `python -c "import json; print(json.load(open('config.json')).get('total_ordenes'))"`. |
| **Resultado esp.** | `config.json` muestra `total_ordenes: 99`. Respuesta HTTP 200. |
| **Estado** | PENDIENTE |

---

## 12. SUITE MIG — MIGRACIÓN SQLITE

Verifica la migración de datos desde Excel hacia la base SQLite (`warehouse.db`).

---

### MIG-01 — Migración completa sin error

| Campo | Detalle |
|-------|---------|
| **Objetivo** | `run_migration.py` termina sin excepción y crea/actualiza `warehouse.db` |
| **Tipo** | Happy Path |
| **Precondiciones** | `layouts/Warehouse_Logic_v2.xlsx` presente (fuente canónica). Python con sqlite3 y pandas disponibles. |
| **Pasos** | `python run_migration.py` |
| **Resultado esp.** | Proceso termina con código 0. `warehouse.db` existe con tamaño > 0. Stdout muestra mensajes de migración exitosa sin `[ERROR]`. |
| **Estado** | PENDIENTE |

---

### MIG-02 — Tablas presentes en warehouse.db

| Campo | Detalle |
|-------|---------|
| **Objetivo** | La base de datos contiene las tablas esperadas con registros |
| **Tipo** | Happy Path |
| **Precondiciones** | MIG-01 aprobado |
| **Pasos** | `python -c "import sqlite3; conn=sqlite3.connect('warehouse.db'); cur=conn.cursor(); cur.execute(\"SELECT name FROM sqlite_master WHERE type='table'\"); print([r[0] for r in cur.fetchall()])"` |
| **Resultado esp.** | Lista de tablas no vacía. Al menos una tabla con datos de stock/SKU (verificar con `SELECT COUNT(*) FROM <tabla_stock>`). |
| **Estado** | PENDIENTE |

---

### MIG-03 — Fuente canónica correcta (no data/)

| Campo | Detalle |
|-------|---------|
| **Objetivo** | La migración lee `layouts/Warehouse_Logic_v2.xlsx` (raíz), NO `data/layouts/Warehouse_Logic.xlsx` |
| **Tipo** | No-Regresión |
| **Precondiciones** | `run_migration.py` disponible |
| **Pasos** | `grep -n "xlsx" run_migration.py` — verificar el path que se lee en la línea relevante. |
| **Resultado esp.** | La ruta referenciada en `run_migration.py` corresponde a `layouts/Warehouse_Logic_v2.xlsx` (raíz del proyecto). Si aún apunta a `data/layouts/Warehouse_Logic.xlsx` (bug conocido en CLAUDE.md sección 4), el test marca FALLIDO y se documenta para corrección. |
| **Estado** | PENDIENTE |

---

### MIG-04 — Idempotencia de la migración

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Ejecutar la migración dos veces no duplica registros |
| **Tipo** | Edge Case |
| **Precondiciones** | MIG-01 aprobado |
| **Pasos** | 1. `python run_migration.py`. 2. Anotar COUNT(*) de la tabla principal. 3. `python run_migration.py` de nuevo. 4. Verificar COUNT(*). |
| **Resultado esp.** | COUNT(*) es igual en ambas ejecuciones. |
| **Estado** | PENDIENTE |

---

## 13. SUITE REG — NO-REGRESIÓN

Verifica que los cambios de V12.1 no alteran el comportamiento de la simulación
cuando los flags nuevos están desactivados.

---

### REG-01 — Baseline md5: outbound OFF, 20 agentes

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Con `config_stress_tw_exec.json` (outbound=OFF), el JSONL producido tiene el mismo md5 que el baseline establecido |
| **Tipo** | No-Regresión |
| **Precondiciones** | `config_stress_tw_exec.json` intacto. Baseline md5 = `18502db7de9f33bdccf94db742c45dd8` (9918 eventos). NOTA: este hash corresponde al body del JSONL sin líneas de metadata de encabezado si las hay — verificar el protocolo exacto de hashing antes de ejecutar. |
| **Pasos** | 1. `python entry_points/run_generate_replay.py` con config_stress_tw_exec.json. 2. `md5sum output/simulation_{TS}/replay_{TS}.jsonl` (o `certutil -hashfile ... MD5` en Windows). |
| **Resultado esp.** | Hash MD5 == `18502db7de9f33bdccf94db742c45dd8`. Si el hash difiere por razones de timestamp en cabecera, usar `grep -v "^#"` para filtrar metadatos antes del hash. |
| **Estado** | PENDIENTE |

---

### REG-02 — Número de eventos sin outbound

| Campo | Detalle |
|-------|---------|
| **Objetivo** | El conteo de líneas del JSONL con outbound=OFF es igual al baseline |
| **Tipo** | No-Regresión |
| **Precondiciones** | `config_stress_tw_exec.json` |
| **Pasos** | `wc -l output/simulation_{TS}/replay_{TS}.jsonl` o `python -c "print(len(open('output/simulation_{TS}/replay_{TS}.jsonl').readlines()))"` |
| **Resultado esp.** | Número de líneas = 9918 (baseline). Tolerancia: ±0 si la simulación es determinista con la misma seed. Si es estocástica, documentar rango observado. |
| **Estado** | PENDIENTE |

---

### REG-03 — Sin tipos de evento outbound con flag OFF

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Con outbound=OFF, no aparecen eventos `truck_arrived`, `truck_departed` ni `pallet_shipped` |
| **Tipo** | No-Regresión |
| **Precondiciones** | `config_stress_tw_exec.json` |
| **Pasos** | `python -c "import json; lines=open('output/simulation_{TS}/replay_{TS}.jsonl').readlines(); ob_types={'truck_arrived','truck_departed','pallet_shipped'}; found=[json.loads(l).get('type') for l in lines if json.loads(l).get('type') in ob_types]; print('eventos outbound encontrados:', found)"` |
| **Resultado esp.** | `eventos outbound encontrados: []` |
| **Estado** | PENDIENTE |

---

### REG-04 — collision_matrix sin modificar con outbound OFF

| Campo | Detalle |
|-------|---------|
| **Objetivo** | El bloque F2.d no modifica la collision_matrix cuando outbound está desactivado |
| **Tipo** | No-Regresión |
| **Precondiciones** | `config_stress_tw_exec.json` |
| **Pasos** | Ejecutar run y verificar que el mensaje `[OUTBOUND] F2.d: N celdas de staging marcadas no-caminables` NO aparece en stdout. |
| **Resultado esp.** | Línea F2.d ausente en stdout. |
| **Estado** | PENDIENTE |

---

### REG-05 — Sin degradación de rendimiento del planner

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Con outbound ON, el `avg_plan_ms` no aumenta más de un 20% respecto al baseline con outbound OFF |
| **Tipo** | No-Regresión |
| **Precondiciones** | Dos runs: uno con config_stress_tw_exec.json (off) y otro con config_stress_tw_v2.json (on) |
| **Pasos** | Comparar `avg_plan_ms` de los dos `timewindow_shadow_report_{TS}.json`. |
| **Resultado esp.** | Incremento de `avg_plan_ms` < 20% entre outbound=OFF y outbound=ON para el mismo volumen de agentes. |
| **Estado** | PENDIENTE |

---

### REG-06 — ASCII limpio en stdout (Ley 4)

| Campo | Detalle |
|-------|---------|
| **Objetivo** | El stdout de cualquier run no contiene caracteres no-ASCII que puedan causar UnicodeEncodeError en cp1252 |
| **Tipo** | No-Regresión |
| **Precondiciones** | Cualquier config |
| **Pasos** | `python entry_points/run_generate_replay.py 2>&1 | python -c "import sys; data=sys.stdin.buffer.read(); bad=[b for b in data if b>127]; print('non-ASCII bytes:', len(bad))"` |
| **Resultado esp.** | `non-ASCII bytes: 0`. (Los acentos en comentarios de código no cuentan si no se imprimen; solo importa lo que llega a stdout/stderr.) |
| **Estado** | PENDIENTE |

---

## 14. CHECKLIST DE ACEPTACIÓN DE RELEASE

Antes de cualquier merge a `main` o entrega de milestone, completar en orden:

```
[ ] REG-01  Baseline md5 confirmado
[ ] REG-02  Conteo de eventos baseline
[ ] REG-03  Sin tipos outbound con flag OFF
[ ] REG-04  collision_matrix sin modificar con flag OFF
[ ] REG-06  ASCII limpio en stdout

[ ] H-01    Pipeline headless completo
[ ] H-02    Estructura JSONL
[ ] H-03    Excel generado
[ ] H-04    Heatmap generado

[ ] SIM-01  Tareas completadas > 0
[ ] SIM-04  Tiempo monotónico
[ ] SIM-05  Sin deadlock (tiempo acotado)

[ ] ALLOC-01 Stock asignado (pallet_reserve_ok)
[ ] ALLOC-02 Órdenes parciales (si aplica)

[ ] TW-01   Cero deadlocks
[ ] TW-02   Cero exec_fallbacks
[ ] TW-03   Planes = segmentos

[ ] OB-01   Truck arrived/departed
[ ] OB-02   FIFO pallets
[ ] OB-06   Capacidad respetada
[ ] OB-08   Outbound OFF = sin cambios

[ ] WEB-01  Servidor arranca
[ ] WEB-05  KPIs outbound visibles

[ ] MIG-01  Migración sin error
[ ] MIG-03  Fuente canónica correcta
```

---

*Fin del documento. Actualizar el campo Estado de cada caso tras cada ciclo de
validación. Registrar en `docs/PROGRESO_INICIATIVA_3.md` los resultados de cada
suite cuando se ejecute.*
