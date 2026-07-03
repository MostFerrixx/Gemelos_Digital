# HANDOFF — Gemelo Digital de Almacen
# Estado operativo para nueva sesion de Cerebellum

**Generado:** 2026-06-18  ·  **Actualizado:** 2026-06-29
**Por:** Cerebellum (sesion de traspaso)
**Rama activa:** `feature/allocation-layer-v12.1`  ·  **HEAD:** `fd0a41d`
**Estado:** Limpio — sincronizado con main. Sin commits pendientes.
**Ultimo hito:** INIT-4 COMPLETO (C1 tiempos de pick, C2 prioridad/SLA Opcion C,
C3 olas). Ver docs/PLAN_INIT4.md. Proxima accion sugerida: seccion 5.

---

## 1. QUE ES EL PROYECTO

Simulador de gemelo digital de almacen (Warehouse Digital Twin).
- **Motor:** SimPy (eventos discretos, headless) -> archivo `.jsonl` -> visualizador Pygame + analitica Excel.
- **Web:** FastAPI en puerto 8000 — configurador + runner + visor de replay.
- **Entidades:** GroundOperator (picking manual), Forklift (carga pesada), WorkOrders (SKU de rack a staging).
- **NO hay simulacion en vivo**: el flujo siempre es headless -> jsonl -> replay.

Stack: Python / SimPy / Pygame / PyQt6 / pytmx / pandas / Optuna / FastAPI / SQLite.
> NOTA: FastAPI/uvicorn/pydantic YA estan en requirements.txt (lineas 24-27); un pip install limpio levanta el servidor web.

---

## 2. ARQUITECTURA — CADENA VIVA

```
entry_points/run_generate_replay.py
  -> src/engines/event_generator.py          (headless SimPy -> .jsonl + Excel + heatmap)

entry_points/run_replay_viewer.py
  -> src/engines/replay_engine.py            (Pygame viewer)

entry_points/run_optimization.py
  -> src/tools/optimizer.py                  (Optuna)

web_prototype/server.py  (FastAPI :8000)     (configurador web + runner + viewer web)
  -> start_server.bat / server_manager.py / start_hidden.py

run_migration.py
  -> src/subsystems/database/               (Excel -> SQLite warehouse.db)
```

Nucleo de simulacion SANO: `src/subsystems/simulation/`
  warehouse.py, dispatcher.py (DispatcherV11), operators.py, order_strategies.py,
  data_manager.py, assignment_calculator.py, route_calculator.py,
  pathfinder.py, layout_manager.py

Archivos VIVOS fuera de src/ (no borrar sin pensar):
  simulation_buffer.py, visualizer.py, configurator.py,
  server_manager.py, start_hidden.py

Codigo MUERTO (ignorar en features; objetivo en limpieza futura):
  legacy/**, src/shared/**, utils/ (raiz), tools/configurator.py,
  tools/visualizer.py, tools/inspect_tmx.py, gran parte de tests/

web_dashboard/ (puerto 8001): HUERFANA pero el Director quiere revisarla antes de decidir.

Fuente de datos canonica = RAIZ (config.json, layouts/WH1.tmx, layouts/Warehouse_Logic.xlsx).
El arbol data/ es una migracion abandonada que solo lee codigo muerto.

---

## 3. GIT — ESTADO ACTUAL

**Rama:** `feature/allocation-layer-v12.1`
**HEAD:** `f3a3ec5` (local y remote identicos)
**main:** `f3a3ec5` (sincronizado via fast-forward; `git rev-list --count main..feature` = 0)

No hay commits pendientes de push ni merge.

### Log completo de la rama (mas reciente primero)

```
f3a3ec5  chore(ui): eliminar botones stub E6/E7 (BK-05 cerrado)
7efc9c7  docs(handoff): actualizar estado post-sesion 2026-06-27
41ddc22  refactor(p2): extraer agent_process a BaseOperator (Template Method)
413888c  feat(gate): WAREHOUSE_SEED via env var para reproducibilidad determinista
b990964  refactor(logging): print() -> logging por nivel en hot-path del motor
0e6d3dd  feat(ui): D-13 tokens compartidos + D-15 marcadores de eventos + D-16 no-color
902877a  feat(ui): D-14 stepper numerado de pestanas en el configurador
23b374b  feat(dev): anti-cache en estaticos del front
8cc7f8d  feat(init-5): exponer nivel de servicio / backorders en visor, API y Excel
e2c6293  feat(qa3): mapa explicito work_area_equipment como fuente de verdad
19e8829  fix(bk-04): cerrar grietas QA-1/QA-2/QA-3
e50b924  docs(qa): QA adversarial de BK-04 -- 2 grietas halladas
1bb24a3  fix(bk-04): prevenir areas sin agente (cobertura) + flota por defecto valida
0fa64e3  feat(ui): exponer truck_interval en configurador + bajar default a 90
bb53c8e  docs(handoff): reflejar push+merge hechos; validar KPIs outbound G15/G16
ba55f27  chore(limpieza): sanear indice FUSE, borrar junk y actualizar docs desfasados
...      (historico anterior ya en main; ver git log para detalle)
```

---

## 4. LO QUE SE HIZO (HISTORIAL POR SESION)

### Sesion 2026-06-27 (commits f3a3ec5..b990964)

**Logging refactor — Punto 1** (`b990964`)
~186 prints convertidos a logging por nivel en hot-path:
- `event_generator.py` (58 prints → INFO), `dispatcher.py` (86 → DEBUG/INFO/WARN/ERROR),
  `operators.py` (42 → DEBUG/INFO/WARN).
Salida en produccion: de miles de lineas a ~800 milestones.
La linea critica para Watch Replay (`.jsonl` generado) queda como INFO.

**Gate WAREHOUSE_SEED** (`413888c`)
Variable de entorno `WAREHOUSE_SEED=42` fija `random.seed()` antes de la sim.
Sin la variable: comportamiento estocastico de produccion (sin cambio).
Gate byte-identico: SHA256 = `a4ae8d4e9f7dd444...` (5,379,372 bytes) en dos corridas.

**Template Method — Punto 2** (`41ddc22`)
`BaseOperator.agent_process()` extrae el ciclo pull-based completo (PASO 1-6).
`_do_picking_at()` es hook abstracto; `GroundOperator` y `Forklift` lo implementan.
Resultado: -296 lineas en operators.py (1772→1476, -16.7%).
Gate byte-identico post-refactor: SHA256 = idem baseline.

**E6/E7 eliminados — Punto 3** (`f3a3ec5`)
Botones stub "Generar Plantilla TMX" / "Poblar SKUs Aleatorios" quitados de
`index.html` y `app.js`. Tarjeta "Acciones de Datos" queda con un solo boton real.
BK-05 cerrado en BACKLOG.md.

---

### Sesiones previas (antes de 2026-06-27)

**D-13..D-16** (`0e6d3dd`, `902877a`)
Design tokens compartidos configurador/viewer, stepper numerado de tabs,
event markers en scrubber de timeline, fix accesibilidad no-color (WCAG AA).

**anti-cache estaticos** (`23b374b`)
Query string `?v=<timestamp>` en referencias CSS/JS para evitar reload forzado.

**INIT-5 — nivel de servicio** (`8cc7f8d`)
Backorders/fill-rate expuestos en visor web (KPI "Servicio"), API
(`/api/snapshot`, `/api/state`, `/api/metrics`) y hoja Excel "Nivel de servicio".
Fuente: `core/replay_utils.build_service_level_summary(almacen)`.
En modo estocastico (sin validacion de stock) muestra N/A.

**BK-04 + QA-1/2/3** (`1bb24a3`, `e50b924`, `e2c6293`, `19e8829`)
- Fix preventivo: flota por defecto asigna work_areas validas a Forklift.
- Mapa explicito `work_area_equipment` en `work_area_calculator.py` como fuente de verdad.
- QA adversarial cerro 3 grietas: motor valida arranque, flota vacia detectada, tipo de equipo validado.
- Outbound termina correctamente cuando no hay mas WOs.

**truck_interval en UI** (`0fa64e3`)
Campo expuesto en configurador; default bajado a 90 seg (antes 300, causaba sim sin trucks visibles).

**Allocation Layer V12.1** (base de la rama)
Asignacion de stock real FCFS antes de crear WorkOrders.
`data_manager.py::get_available_stock()`, `warehouse.py::WorkOrder`
(qty_requested/qty_allocated/is_partial), `order_strategies.py`.
`fulfillment_policy: "ship_partial"` en config.json.

**Fixes de estrategias** (H-5, BK-01, H-6)
- H-5 (`c4c772f`): alias "Ejecucion de Plan" reconocido por el dispatcher.
- BK-01 (`bcdb264`, `76f1e21`): Cercania + radio_cercania + expansion expuestos en UI.
- H-6 (`8a2fe86`): radio blando elimina deadlock de Cercania con radio restrictivo.
- BK-03 (`dd5c729`): greedy nearest-neighbor descartado con evidencia experimental.

**D-03..D-12 + limpieza** (sesiones anteriores)
Sidebar colapsable/iconos, fleet cards, inline validation, KPIs jerarquicos,
colores de seccion, notificaciones. Cuarentena de 40+ archivos basura.

---

## 5. PENDIENTES Y PROXIMOS PASOS

### Backlog activo (ver docs/BACKLOG.md para detalle completo)

| Item | Estado | Esfuerzo estimado |
|------|--------|-------------------|
| **BK-02** — FIFO Estricto en UI | EN REPENSAR (diseno pendiente del Director) | ~15 min cuando se decida |
| **web_dashboard/** (puerto 8001) | PENDIENTE DECISION (Director quiere revisarla) | Depende de decision |
| **INIT-1** — Picking por ubicacion real + reservas en BD | Pendiente | Alto |
| **INIT-3** — Reparar optimizador Optuna | Pendiente | Bajo-Medio |
| **INIT-4** — Prioridad de ordenes / SLA / olas | Pendiente | Medio |
| **WOs sobredimensionadas** | Pendiente (falsifica KPIs) | Bajo (fix defensivo) |

Ver `docs/antiguos/ANALISIS_PROFUNDO_INICIATIVAS.md` para descripcion completa de INIT-1/3/4.

**BK-02 — FIFO Estricto en UI** (EN REPENSAR)
El motor lo implementa correctamente. No se expone porque el Director quiere redefinir
primero que deberia hacer FIFO operacionalmente.

**web_dashboard/** (PENDIENTE DECISION)
Puerto 8001. Ruta de replay rota. Parece huerfana; el Director quiere revisarla
antes de decidir si se conserva, se repara o se elimina.

**INIT-1 — Picking por ubicacion real**
Hoy el allocation layer asigna la WO a una ubicacion de picking elegida al azar
dentro del area, aunque ese SKU no este ahi. La tabla `inventory(location_id, ...)`
en warehouse.db ya tiene la informacion; falta usarla en `order_strategies.py`.

**INIT-3 — Optimizador Optuna**
Los nombres de estrategia y parametros del optimizador estan desalineados del motor
real. Resultado: el optimizador puede estar probando configuraciones que el motor ignora.

**INIT-4 — Prioridad / SLA / olas + tiempos de pick** — HECHO 2026-06-29
Commits 91dd6c0 (C1 tiempos escalables), c27dacb (C2 prioridad Opcion C),
fd0a41d (C3 olas). Todo opt-in con gate byte-identico. Ver docs/PLAN_INIT4.md.
Diferido: KPI de SLA vencido en el reporte (no bloqueante).

**WOs sobredimensionadas**
En `warehouse.py::_validar_y_ajustar_cantidad`: si `sku.volumen > max_capacity`,
`unidades_por_viaje = 0` → bucle infinito (o la WO se marca 'staged' con qty=0).
Fix: forzar minimo 1 unidad por viaje; marcar WOs imposibles como 'failed' (no 'staged').

### Issues conocidos (no criticos)
- `warehouse.db-shm` / `warehouse.db-wal`: archivos WAL de SQLite, aparecen como
  untracked pero ya estan en .gitignore.

---

## 6. DOCUMENTACION VIGENTE

| Archivo | Estado | Descripcion |
|---|---|---|
| `CLAUDE.md` | ACTUALIZADO 2026-06-27 | Identidad, arquitectura, leyes, estado actual |
| `AUDITORIA.md` | Vigente (mayo 2026) | Diagnostico estructural completo del repo |
| `docs/HANDOFF.md` | ACTUALIZADO 2026-06-27 | Este archivo — estado operativo para nueva sesion |
| `docs/BACKLOG.md` | ACTUALIZADO 2026-06-27 | BK-01..BK-05 + INIT-5 cerrados; BK-02/INIT-1/3/4/WOs pendientes |
| `docs/VALIDACION_UI_WEB.md` | ACTUALIZADO 2026-06-27 | 60 controles; E6/E7 eliminados, D1 resuelto |
| `docs/PROPUESTA_MEJORA_DISENO_UI.md` | ACTUALIZADO 2026-06-27 | D-01..D-16 implementadas |
| `docs/PRUEBAS_E2E_SISTEMA.md` | Referencia (2026-06-13) | Catalogo de 53 casos E2E |
| `docs/RESULTADOS_PRUEBAS_E2E.md` | Referencia (2026-06-13) | Resultados: 40 PASS, 0 FAIL, 3 WARN |
| `docs/COMO_FUNCIONA_EL_PROGRAMA.md` | Referencia | Descripcion operativa del sistema |
| `docs/VISION_PRODUCTO.md` | Referencia | Vision y roadmap de alto nivel |
| `docs/INSTRUCCIONES_LAYOUT_PERSONALIZADO.md` | Referencia | Tileset y estructura de layouts TMX |
| `docs/INSTRUCCIONES_PROYECTO_COWORK.md` | Referencia | Metodologia atemporal del proyecto |
| `docs/antiguos/` | ARCHIVO HISTORICO | Planes/bitacoras de iniciativas completadas |

---

## 7. PROTOCOLO ANTI-FUSE (para Cerebellum)

El sandbox corre en Linux pero el proyecto esta en un mount FUSE de Windows.
Restricciones del mount:
- `rm` / `os.remove()` -> "Operation not permitted"
- `git` normal (add/commit/push) -> bloqueado por index.lock / HEAD.lock
- Escritura: SOLO funciona con `shutil.copy2(src, dst)` (sobreescritura)

Solucion para commits (bypass de bajo nivel):
```bash
git hash-object -w <archivo>           # genera blob hash
export GIT_INDEX_FILE=/tmp/idx_xx
git read-tree <parent-commit-hash>     # carga arbol del padre en indice temporal
git update-index --cacheinfo 100644,<hash>,<ruta>   # actualiza entradas
TREE=$(git write-tree)
COMMIT=$(echo "mensaje" | git commit-tree $TREE -p <parent-hash>)
echo $COMMIT > .git/refs/heads/<branch>   # actualiza rama directamente
unset GIT_INDEX_FILE
```

Solucion para edicion de archivos:
```python
# En /tmp (Linux nativo):
# 1. Editar el archivo
# 2. shutil.copy2('/tmp/archivo', '/sessions/.../mnt/Gemelos Digital/archivo')
```

Para push a GitHub: el sandbox no tiene red saliente. El Director debe hacer el push
desde su terminal Windows.

---

## 8. CONFIG.JSON — DEFAULTS SEGUROS (estado post-experimentos)

```json
{
  "dispatch_strategy": "Ejecucion de Plan",
  "radio_cercania": 100,
  "radio_expansion_paso": 50,
  "radio_max_expansiones": 5,
  "cercania_tour_mode": "cost",
  "total_ordenes": 300,
  "num_operarios_terrestres": 2,
  "num_montacargas": 2
}
```
`cercania_tour_mode: "cost"` es el default seguro post-BK-03. El valor `"greedy_nn"`
existe como opcion pero no se recomienda (ver BK-03 descartado).
