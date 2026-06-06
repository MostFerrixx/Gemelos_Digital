# PROGRESO INICIATIVA #2 - CONGESTION (documentacion viva)

> Rama: feature/allocation-layer-v12.1
> Plan maestro: docs/PLAN_INICIATIVA_2_CONGESTION.md (leer ese para el diseno completo)
> Este doc se actualiza tras CADA paso. Si me corto por tokens, al releer esto se sabe
> exactamente que quedo HECHO y que falta.
> ASCII puro (Ley #4). Estados: PENDIENTE / EN PROGRESO / HECHO / BLOQUEADO.

---

## 0. ENTORNO DE VALIDACION (sandbox Linux)

- git BLOQUEADO en este entorno: NO se hacen commits aqui (los hace el Director en su PC).
  Checkpoint reversible = copia de archivos vivos a `_backup_iniciativa2/fase_N/`.
- Dependencias en sandbox (REINSTALAR al abrir sesion nueva, el sandbox es efimero):
  `pip install simpy pytmx pandas openpyxl numpy pygame --break-system-packages`
  Headless requiere: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy`.

- *** BUG DEL MOUNT (FUSE) - FIX CONFIRMADO ***: tras editar/reescribir un archivo de
  codigo desde el HOST, el mount del sandbox sirve una version STALE/TRUNCADA (py_compile
  falla con "unterminated string" aunque el host este perfecto). NO se resuelve solo ni con
  Write completo. FIX QUE FUNCIONA: desde el sandbox hacer un round-trip de rename del
  propio archivo, p.ej.:
    `cd .../simulation && mv operators.py _t.py && mv _t.py operators.py`
  Eso fuerza al FUSE a revalidar y servir el contenido fresco. Verificar luego con
  py_compile + grep de un marcador nuevo ANTES de ejecutar.
- ARCHIVOS NUEVOS (nombre nunca antes usado) SI sincronizan al instante (inode nuevo, sin
  cache). Por eso el harness de estres se creo como archivo nuevo.

- ANALYTICS LENTO: el pipeline completo (run_generate_replay) corre analytics + heatmap
  Excel con formato condicional; con 20 agentes eso tarda varios minutos (NO es freeze de
  la sim). Para validar SOLO la simulacion + co-ocupacion rapido, usar `_stress_harness.py`
  (reusa crear_simulacion y corre el loop SimPy sin analytics; ~30s con 20 agentes).
- IMPORTANTE - DATOS DE PRODUCCION NO ACCESIBLES EN SANDBOX:
  El order file de produccion `uploads/orders_ordenes_prueba_real.json` aparece en
  metadata pero su CONTENIDO no es legible desde el mount (bug host->mount). Por eso,
  segun instruccion del Director, se uso un ARCHIVO DE PRUEBA con SKUs REALES:
    - `uploads/orders_test_sandbox.json` (40 ordenes, 120 items, SKU001..SKU050 reales
      extraidos de `layouts/Warehouse_Logic.xlsx`, cantidades deterministas).
    - `config_test_congestion.json` = copia de config.json apuntando a ese order file
      (congestion.enabled=false, mode=off): se usa como gate de NO-REGRESION.
    - `config_test_instrument.json` = idem pero congestion.enabled=true, mode=instrument:
      se usa para medir co-ocupaciones (Fase 1) y como baseline de la prueba de estres.
  TODA validacion de fases se corre con `--config <uno de esos>`.
  El `config.json` de produccion queda intacto salvo el bloque `congestion` (enabled:false).

- Comando de validacion estandar (headless, end-to-end):
  ```
  SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
    python3 entry_points/run_generate_replay.py --config config_test_congestion.json
  ```

- BASELINES DE REFERENCIA:
  - `_backup_iniciativa2/baseline_ref/baseline_F0.jsonl` (pre-refactor): md5 f4f69188... (3507 lineas).
  - `_backup_iniciativa2/baseline_ref/baseline_postF0.jsonl` (post-F0): md5 064e0e2e... (3507 lineas).
  - GATE DE NO-REGRESION (enabled:false): el .jsonl debe ser md5 064e0e2e... byte a byte.
  - GATE DE OBSERVADOR PURO (mode:instrument): el .jsonl difiere SOLO en la line1 (header
    que hace echo del bloque config); lineas 2..3507 identicas al postF0
    (md5 de lineas2+ = 7f04ccbe...). Es decir, instrument NO cambia el comportamiento.

---

## 1. CHECKLIST POR FASE

### Fase 0 - Refactor lazo movimiento + leer config (SIN cambio de comportamiento) -> HECHA y VALIDADA
- [HECHO] F0.1 Extraer lazo celda-a-celda a BaseOperator._recorrer_tramo
- [HECHO] F0.2 Reusar helper en GroundOperator (picking-nav y staging-nav)
- [HECHO] F0.3 Reusar helper en Forklift (picking-nav y staging-nav)
- [HECHO] F0.4 Anadir bloque "congestion" a config.json + config_test (enabled:false) y leerlo en warehouse sin usarlo
- [HECHO] F0.5 VALIDAR: eventos de sim byte-identicos (solo difiere header line1). Gate OK.
- [HECHO] F0.6 Backup a _backup_iniciativa2/fase_0/

RESULTADO F0:
- Helper `_recorrer_tramo(segment_path, speed, on_before, on_after, time_per_cell)` en BaseOperator.
  Los 4 lazos (Ground picking/staging, Forklift picking/staging) usan `yield from`.
- Determinismo F0: 2 corridas -> mismo md5 064e0e2e...

### Fase 1 - Instrumentacion (medir co-ocupaciones) -> HECHA y VALIDADA (2026-06-02)
- [HECHO] F1.1 Crear `src/subsystems/simulation/congestion_manager.py` con clase
  `CongestionManager` (observador pasivo: enter/leave/move + conteo de co-ocupaciones,
  hotspots, ventana de arranque, muestras acotadas, write_report a JSON aparte).
- [HECHO] F1.2 Instanciar CongestionManager en warehouse.py (constructor, lineas ~195-208)
  a partir del bloque `congestion` de config.
- [HECHO] F1.3 Choke point unico de posicion `BaseOperator._set_pos(new_cell)` que notifica
  `cm.move(id, current_position, new_cell)` ANTES de actualizar. Lo usan: spawn (depot),
  `_recorrer_tramo` (cada celda), y los set de staging. Si la capa esta inactiva, _set_pos
  solo asigna => comportamiento byte-identico.
- [HECHO] F1.4 event_generator.py escribe el reporte de congestion (JSON aparte, NO toca el
  .jsonl) al final de la corrida si la capa esta activa (lineas ~252-256).
- [HECHO] F1.5 VALIDAR no-regresion (enabled:false): .jsonl md5 064e0e2e... EXACTO. OK.
- [HECHO] F1.6 VALIDAR observador puro (mode:instrument): solo line1 difiere; lineas 2..3507
  identicas (md5 7f04ccbe...). El replay NO cambia. OK.
- [HECHO] F1.7 Backup a _backup_iniciativa2/fase_1/.

RESULTADO F1 (BASELINE DE CO-OCUPACIONES, config_test_instrument.json):
- Co-ocupaciones totales: 18
- Co-ocupaciones en ventana de arranque (t<=5.0): 3
- Celdas distintas con co-ocupacion: 10
- Maximo de agentes simultaneos en una celda: 4
- TOP HOTSPOT: celda (3,29) -> 7 co-ocup, max 4 simultaneos.
  >>> Esto es el DEPOT FALLBACK del spawn (plan 2.2). Confirma EMPIRICAMENTE el
  >>> spawn-stacking: los agentes nacen apilados y se atraviesan. Es el "antes" que
  >>> Fase 2 debe derribar.
- Otros hotspots: (1,20)x3, y varias celdas con 1 co-ocup (cruces/pasillos).

### Fase 2 - Arranque escalonado + dispersion (PRUEBA DE ESTRES DE ARRANQUE) -> HECHA y VALIDADA (2026-06-02)
- [HECHO] F2.1 Stagger temporal: BaseOperator._spawn_stagger() -> el agente i espera
  `spawn_offset * spawn_index` antes de su primer movimiento. Generador SimPy (yield from).
- [HECHO] F2.2 Dispersion espacial: BaseOperator._spawn_lane() + _compute_departure_lanes()
  -> BFS cardinal DETERMINISTA desde el depot; el agente i toma candidates[i] (anden de
  salida distinto). En el preludio de agent_process (Ground y Forklift) ahora:
  spawn_cell = self._spawn_lane(depot); self._set_pos(spawn_cell); yield from _spawn_stagger().
- [HECHO] F2.3 spawn_index (0-based) asignado en crear_operarios en los 4 sitios (legacy
  ground/forklift Y agent_types ground/forklift). OJO: el primer Edit con replace_all solo
  alcanzo la rama legacy (indent 12); la rama agent_types (indent 16, LA QUE USA LA CONFIG
  REAL) se arreglo reescribiendo el archivo completo. Verificado: 4 sitios presentes.
- [HECHO] F2.4 GATING: todo detras de `congestion.enabled AND congestion.staggered_start`
  (NUEVA clave, default false). _f2_active() corta primero por enabled (Ley: flag off =>
  identico). Permite combinar con mode:instrument (medir) o mode:cell (F3+).
- [HECHO] F2.5 NO-REGRESION (enabled:false): .jsonl lines2+ = 7f04ccbe (solo line1 header
  difiere por la clave staggered_start anadida). Comportamiento byte-identico. OK.
- [HECHO] F2.6 PRUEBA DE ESTRES (20 agentes: 14 Ground + 6 Forklift, todos depot staging 1).
  Harness: `python3 _stress_harness.py <config> [cap_seg]`. Resultados:
    BASELINE (staggered_start=false): reproduce el spawn-stacking del fallo original:
      cooccup_startup(t<=5)=38, MAX_CONCURRENT en celda (3,29) = 20 (los 20 apilados!),
      cooccup_total=62. TERMINO=True, FREEZE=False, sim_end_t=262.
    F2 (staggered_start=true):
      cooccup_startup=12 (CAIDA 68%), max_concurrent global=8, cooccup_total=68.
      TERMINO=True, FREEZE=False, sim_end_t=267.
    >>> VERIFICACION DIRECTA DE DISPERSION: los 20 agentes nacen en 20 CELDAS DISTINTAS,
    >>> NINGUNA compartida (criterio duro de F2 CUMPLIDO). El residual de co-ocupacion es
    >>> TRANSITO + cola de descarga en staging (3,29) (F8, real), NO spawn-stacking.
    Config chica (4 agentes) pipeline COMPLETO end-to-end con F2 activo: cooccup_startup=0,
    sim termina (t=539), analytics+Excel OK -> la cadena headless no se rompe.
- [HECHO] F2.7 DETERMINISMO (I5): 2 corridas del stress F2 -> numeros identicos
  (startup=12, total=68, max=8, end_t=267).
- [HECHO] F2.8 Backup a _backup_iniciativa2/fase_2/.

NOTA F2: la exclusion de celda (F3) NO esta habilitada. En F2 los agentes AUN se atraviesan
(co-ocupacion en transito sigue existiendo, por diseno). Lo que F2 mata es el SPAWN-STACKING
(el epicentro del freeze). La prueba de estrES queda como REGRESION PERMANENTE para F3+.
CONFIGS DE PRUEBA: config_stress_baseline.json (stagger off) y config_stress_f2.json
(stagger on) = 20 agentes. config_test_f2_small.json = 4 agentes F2 activo (pipeline full).

### Fase 3 - Exclusion por celda + espera -> EN PROGRESO (2026-06-02)
DISENO (confirmado contra plan 4.1-4.4 / 6 Fase 3):
- mode:cell (gateado por enabled). Cada celda = recurso cap 1 via RESERVA PEREZOSA
  (dict owner {(x,y):agent_id} + simpy.Event por celda creado on-demand), no un
  simpy.Resource por celda (plan 4.2).
- PASO ATOMICO en BaseOperator._recorrer_tramo (UNICO lazo de movimiento, F0): por celda
  adquirir nxt ANTES de soltar cur (conserva la actual hasta tener la siguiente => anti-F10),
  esperar `yield release_event | timeout(W)` con reintento. REGLA DE ORO: sin celda libre =>
  ESPERA y REINTENTA, jamas congela ni aborta el tour (I3). wait_hard_cap como cota blanda
  (registra incidente y sigue esperando en ciclos acotados; nunca crash).
- INVARIANTE cell: un agente SIEMPRE posee su current_position. Se logra con claim de la
  celda de spawn + acquire-antes-de-release. Asi el metrico de co-ocupacion (enter()) ve la
  celda vacia => I1=0 si la exclusion es correcta.
- Teletransporte a staging (CB19): los fallbacks bare _set_pos (picking else y staging
  else/except) se cambian a _jump_to() que en cell mode hace release(cur)+_set_pos+claim(dest)
  (I1-safe). La navegacion normal a staging YA pasa por _recorrer_tramo (exclusion aplica).
- Watchdog F3 = DETECTOR/diagnostico (sin cesion; la cesion formal con aging es F5, plan 6).
  Detecta stall global (sin movimiento en watchdog_window con agentes activos) y lo registra
  en el reporte. La TERMINACION en caso de deadlock la garantiza el cap de wallclock del
  harness (freeze=True) => si pasa, reporto el sintoma y PARO (no parche apresurado).
- GATING: rama cell SOLO si enabled AND mode in (cell, cell+corridor). enabled:false =>
  rama original byte-identica (gate no-regresion). mode:instrument intacto (F1/F2).

CHECKLIST:
- [HECHO] F3.1 CongestionManager: owner dict + release events + try_acquire/release/
  claim/release_event + cell_exclusion + last_move_time/total_moves + incidentes + resumen F3.
- [HECHO] F3.2 _recorrer_tramo: rama cell (paso atomico, acquire-nxt-antes-de-release-cur,
  espera release|timeout W, reintento, hardcap blando). Rama off intacta (gating cell_exclusion).
- [HECHO] F3.3 spawn-claim (Ground/Forklift) + _jump_to en teleports (picking-else y
  staging else/except, ambos agentes). _set_pos sigue siendo solo metrico.
- [HECHO] F3.4 watchdog DETECTOR + hook arranque en event_generator (solo cell mode).
- [BLOQUEADO] F3.5 VALIDACION FALLIDA: ver RESULTADO F3 abajo. NO se cumple el criterio
  de paso (hay DEADLOCK -> la sim NO termina). Backup de la tentativa en fase_3/ como checkpoint.
CRITERIO DE PASO F3 (no avanzar a F4 sin esto): 0 freezes con exclusion activa, I1=0
co-ocupaciones reales, sim TERMINA (throughput>0), y flag off sigue byte-identico.

RESULTADO F3 (config_stress_f3.json, 20 agentes, mode:cell) -> *** FALLA: DEADLOCK ***
ENTORNO: el sandbox mata procesos en background entre llamadas y cada llamada bash tiene
tope ~45s, asi que las corridas largas se hacen sincronas con cap de wallclock bajo.
- EXCLUSION FUNCIONA (mecanica correcta): co-ocupaciones reales cayeron de 62 (baseline F2)
  a 1. I1 casi en verde. max_concurrent=2 (solo ese incidente).
- ESA 1 co-ocupacion = BUG DE CARRERA DE SPAWN (no de transito): incidente claim_conflict en
  celda (4,28) entre GroundOp-01 y GroundOp-08 en t=0.0. Causa: las celdas de spawn (andenes
  F2) son TODAS distintas (verificado: 20/20 distintas), PERO el ancla idx0 (GroundOp-01,
  SIN stagger) arranca a moverse en t=0 y ADQUIERE (4,28) -que esta en su path- ANTES de que
  GroundOp-08 (idx7) ejecute su _claim_spawn de (4,28). Mi `claim` es FORZADO -> sobrescribe
  al duenno real y corrompe el invariante (GroundOp-01 queda fisicamente en una celda cuyo
  owner es GroundOp-08). FIX correcto pendiente: el claim de spawn NO debe forzar; el ancla
  idx0 deberia tambien respetar exclusion o spawnear-y-quedarse hasta soltar. (Sub-bug menor;
  NO es la causa del freeze.)
- FREEZE / DEADLOCK (causa del fallo del criterio): 8 agentes quedan ACTIVOS sin moverse;
  el watchdog dispara STALL en bucle (stall_windows crece sin fin) y la sim NO termina
  (terminated=False, freeze=True por cap de wallclock; el reloj de SIM se dispara a t~60000
  porque los timeouts W siguen avanzando el tiempo sin que nadie progrese).
  GRAFO WAIT-FOR en el deadlock (embudo del depot, celdas ~(0..6, 26..29)):
    GroundOp-01 @(4,28) espera (4,27) <- bloqueada por GroundOp-13
    GroundOp-02 @(2,29) espera (2,28) <- bloqueada por GroundOp-06
    GroundOp-03 @(3,28) espera (3,27) <- bloqueada por GroundOp-07
    Forklift-01 @(6,29) espera (5,29) <- bloqueada por GroundOp-09
  Es ESPERA CIRCULAR clasica (Coffman completo: exclusion + hold-and-wait + no-preempt +
  ciclo). 20 agentes dispersados en un bloque 7x4 alrededor del depot deben drenar por el
  mismo embudo; sin CESION nadie suelta su celda. wait_hard_cap (30s) dispara y queda
  registrado, pero por diseno F3 el agente SOLO espera (no cede) => no se resuelve.
- DIAGNOSTICO: es EXACTAMENTE el modo de fallo previsto por el plan (F2 espera circular,
  F6 head-on, F10 hold-and-wait) cuya resolucion el plan asigna a FASE 5 (cesion por
  prioridad con aging + backoff + watchdog que fuerza cesion). El "watchdog basico" de F3
  que implemente es DETECTOR (deja traza) pero NO resuelve. Por tanto, con el alcance
  estricto de F3 (espera y reintenta, sin cesion ni repathing), el embudo del depot con 20
  agentes NO puede alcanzar "0 freezes".
- DECISION (por instruccion del Director: si falla, PARAR y reportar, no forzar parches):
  NO improviso cesion (es lo mas delicado y causa del freeze previo). Codigo F3 dejado en
  su sitio (gateado; flag off sigue siendo el camino seguro). Pendiente decision del Director.
- NO-REGRESION FLAG OFF: *** OK *** (verificada). Pipeline headless completo con
  config_test_congestion.json (enabled:false, mode:off): replay_*.jsonl = 3507 lineas,
  md5(lineas2+) = 7f04ccbece8be6e3a44ccbdd11e53bf9 == referencia 7f04ccbe (postF0/F2). La
  rama off es byte-identica: el codigo F3 NO toco el camino seguro (gating por cell_exclusion
  confirmado empiricamente).
- OPCIONES PARA DESBLOQUEAR (para discutir):
  A) Adelantar la CESION minima del watchdog (resolver ciclos forzando retroceso del de
     menor prioridad a una celda libre). Es potente pero es trabajo F5 y delicado.
  B) Reducir la presion del embudo en F2/F3: andenes de salida mas dispersos / cola de
     salida del depot (recurso cap-k) para que no nazcan 20 agentes apilados en 7x4.
  C) Seguir el plan: cerrar F3 como "exclusion mecanica correcta (I1 ok)" y mover la
     resolucion de deadlock a F4 (repathing, rodea atascos) + F5 (cesion). El criterio
     "0 freezes" se cumpliria recien con F4/F5.
  RECOMENDACION de Cerebellum: (B)+(C). Primero arreglar el sub-bug de spawn-claim (carrera)
  y bajar la densidad del embudo; luego F4/F5 para la resolucion formal. NO meter cesion a
  presion dentro de F3.

### Fase 4 - Repathing dinamico
- [PENDIENTE] F4.x

### Fase 5 - Deadlock formal + corredores/muelles
- [PENDIENTE] F5.x

---

## 2. BITACORA (que archivo, que cambie, resultado)

- [SETUP] Generado `uploads/orders_test_sandbox.json` y `config_test_congestion.json`.
  Baseline determinista verificado (md5 f4f69188...). Guardado en baseline_ref/.
- [F0] operators.py: + metodo BaseOperator._recorrer_tramo (helper unico de movimiento).
  Reemplazados los 4 lazos `for step_idx, step_position in enumerate(...)` por closures
  `_on_before/_on_after` + `yield from self._recorrer_tramo(...)`. Eventos identicos.
- [F0] warehouse.py: + lectura `self.congestion_config/congestion_enabled/congestion_mode`.
- [F0] config.json y config_test_congestion.json: + bloque `congestion` (valores plan 4.9).
- [F0] Backup vivos -> _backup_iniciativa2/fase_0/. VALIDADO.
- [F1] congestion_manager.py (NUEVO, 186 lineas): clase CongestionManager observador pasivo.
  API enter/leave/move (gated por .active), metricas de co-ocupacion, write_report a JSON.
- [F1] operators.py: + `_set_pos(new_cell)` choke point que llama cm.move(); usado por spawn
  (lineas 326/713), _recorrer_tramo (258) y staging (578/581/984/987). `move_to` (146) es
  placeholder muerto, no se usa en agent_process.
- [F1] warehouse.py (~195-208): instancia self.congestion_manager desde el bloque congestion.
- [F1] event_generator.py (~252-256): escribe congestion_report_<ts>.json si cm.active.
- [F1] NOTA: la sesion previa implemento TODO F1 pero se corto por tokens sin validar ni
  registrar. Esta sesion lo VALIDO: no-regresion OK (064e0e2e), observador puro OK (7f04ccbe),
  baseline de co-ocupaciones obtenido (18 total, hotspot depot (3,29) max 4). Reporte:
  output/simulation_<ts>/congestion_report_<ts>.json.
- [F1] Backup vivos -> _backup_iniciativa2/fase_1/. VALIDADO. Pasar a F2.
- [F2] operators.py: + spawn_index en __init__ (default 0); + helpers BaseOperator
  _f2_config/_f2_active/_compute_departure_lanes/_spawn_lane/_spawn_stagger; preludio de
  spawn de Ground y Forklift usa _spawn_lane + yield from _spawn_stagger; crear_operarios
  asigna spawn_index en los 4 sitios. Reescrito COMPLETO con Write para arreglar la rama
  agent_types y sincronizar el mount (+ rename round-trip para bust del cache FUSE).
- [F2] config.json + config_test_congestion.json + config_test_instrument.json: + clave
  `congestion.staggered_start=false`.
- [F2] NUEVOS: config_stress_baseline.json / config_stress_f2.json (20 agentes),
  config_test_f2_small.json (4 agentes F2), _stress_harness.py (validador rapido sin analytics).
- [F2] VALIDADO (no-regresion, estres 20 agentes, dispersion 20/20 distintos, determinismo,
  pipeline full 4 agentes). Backup -> _backup_iniciativa2/fase_2/.
- [F2] PROXIMO: Fase 3 (exclusion por celda + espera). Solo arrancar F3 con la prueba de
  estres en verde (ya lo esta). Criterio F3: 0 freezes CON exclusion, I1 (0 co-ocup reales),
  sim termina; watchdog resuelve cualquier deadlock. Reusar config_stress_f2.json con mode=cell.
- [F3] congestion_manager.py: + EXCLUSION_MODES, propiedad cell_exclusion, owner dict +
  release_events (reserva perezosa), try_acquire/release/claim/release_event,
  note_wait_episode/timeout/hardcap, _record_deadlock, watchdog_proc/start_watchdog,
  total_moves/last_move_time en move(), bloque "exclusion" en resumen(), deadlock_incidents
  en write_report. AST OK.
- [F3] operators.py: _recorrer_tramo con rama cell (paso atomico); + _claim_spawn y _jump_to
  en BaseOperator; spawn de Ground/Forklift llama _claim_spawn; teleports (picking-else y
  staging else/except) ahora usan _jump_to. _set_pos sin cambios (solo metrico). AST OK.
- [F3] event_generator.py: arranca watchdog tras crear operarios si cell_exclusion. AST OK.
- [F3] NUEVO config_stress_f3.json (= f2 con mode:cell). diag scripts en /tmp (efimeros).
- [F3] FIX FUSE aplicado (rename round-trip) a los 3 archivos antes de correr. Verificado AST.
- [F3] *** VALIDACION FALLIDA: DEADLOCK *** (ver RESULTADO F3 arriba). Exclusion mecanica OK
  (co-ocup 62->1; la 1 es carrera de spawn-claim), pero hay espera circular en el embudo del
  depot que F3 (sin cesion) no resuelve => sim no termina. PARADO segun protocolo. Pendiente:
  decision del Director (opciones A/B/C en RESULTADO F3) y correr no-regresion flag-off.
- [F3] Backup de la tentativa -> _backup_iniciativa2/fase_3/ (checkpoint del intento, NO es
  un cierre de fase: F3 sigue BLOQUEADA hasta resolver el deadlock).
