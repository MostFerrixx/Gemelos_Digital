# PROGRESO INICIATIVA #2 — OPCION C (Time-Window / Reservation Routing)

> Documentacion viva. Las sesiones se cortan por limite de tokens: este doc
> permite retomar EXACTAMENTE donde se quedo. Se actualiza tras CADA paso.
> Rama: `feature/allocation-layer-v12.1`. Respaldo previo: commit `7d3e782`.
> Alcance autorizado AHORA: **solo Fase 0 + Fase 1** (NO F2 sin OK del Director).

## Estado de fases
- [x] F0 — Andamiaje y flag `mode: timewindow` (sin cambio de comportamiento) — HECHO
- [x] F1 — ReservationTable + A* espacio-temporal en modo SOMBRA — HECHO
- [~] F2 — Ejecucion segun plan ST — IMPLEMENTADA y validada PARCIALMENTE.
      Movimiento libre de conflicto por construccion (0 moving+moving, termina, 0 freeze)
      PERO I1!=0 por permanencia NO reservada (parados: idle/picking/lifting/unloading).
      DIAGNOSTICO ABIERTO -> requiere decision del Director (ver seccion F2 abajo). SIN COMMIT.
- [~] F2b — STANDING RESERVATIONS (intento del arreglo natural) — PROBADO y REVERTIDO.
      REGRESO I1 (81 -> 116). PARADO segun instruccion #3 (no parchear a ciegas). Causa
      raiz aislada: la meta de descarga es UNA celda (3,29) compartida por los 20 agentes
      (reservar solo dirige al planner, NO impide ocupar la meta fisica) + el parking de
      idle los mete al corredor de trafico. Requiere DECISION del Director (zona aforo-k).
      Detalle completo en seccion "FASE 2b" abajo. Working dir RESTAURADO a F2 (I1=81). SIN COMMIT.
- [ ] (F3+ — NO autorizado)

## Convenciones de validacion
- No-regresion: flag off (y tambien `mode:timewindow` en sombra) => `.jsonl`
  byte-identico al baseline salvo la linea-1 (header con timestamp/config).
- Escenario de validacion: archivo de ordenes de PRODUCCION
  (`uploads/orders_ordenes_prueba_real.json`) NO esta en el sandbox; se usa
  el de prueba real `uploads/orders_test_sandbox.json` (modo determinista),
  el mismo que ya usan los `config_stress_*.json`. Aclarado explicitamente.
- Backups de archivos vivos modificados -> `_backup_iniciativa2/opcionC_fase_N/`.

---

## CHECKLIST DETALLADO

### Fase 0 — Andamiaje
- [x] `congestion_manager.py`: propiedad `timewindow_active`; `timewindow` en ACTIVE_MODES + `TIMEWINDOW_MODE`.
- [x] `config.json`: bloque `congestion.timewindow` (shadow, clearance, dt_wait, max_expansions, plan_horizon, allow_diagonal).
- [x] `reservation_table.py`: modulo esqueleto (firmas, sin logica).
- [x] `spacetime_planner.py`: modulo esqueleto (firmas, sin logica).
- [x] `warehouse.py`: instanciacion gateada por `timewindow_active` (table+planner, reusa pathfinder).
- [x] `operators.py::_recorrer_tramo`: hook gateado `_timewindow_shadow_plan` (F0 = stub no-op) antes del lazo estatico.
- [x] Validacion no-regresion: off vs timewindow => cuerpo .jsonl byte-identico (md5 9d9d8544..., diff vacio). Solo difiere linea-1 (header/config). Ambas: 9685 eventos, sim_end_t=262, terminan, sin freeze.
- [x] Backup + commit local F0. Backup en `_backup_iniciativa2/opcionC_fase_0/` (gitignored).
      **Commit F0 = `421b20f`** (10 files, +783/-3). Verificado (git cat-file OK).

### Fase 1 — Planner en sombra
- [x] `ReservationTable` completo: is_free (con clearance), reserve (verifica invariante,
      cuenta overlap_violations, NO inserta si pisa), can_swap (aristas dirigidas),
      reserve_move, release_agent, purge_before. Intervalos ordenados por t_in (bisect).
- [x] `SpaceTimePlanner.find_path_st`: A* espacio-temporal continuo (mover dur=0.1*speed /
      esperar dt_wait), heuristica = octil del Pathfinder REUSADA convertida a cota
      inferior de tiempo (admisible), estados cuantizados (round t), tie-break por heap,
      corte por max_expansions, filtro cardinal/diagonal. + plan_and_reserve_shadow
      (release+plan+reserve+metricas) + shadow_report.
- [x] Inyeccion sombra en `operators._timewindow_shadow_plan` (PURO: sin yield/eventos;
      planifica+reserva; la ejecucion sigue la ruta estatica) -> .jsonl no cambia.
- [x] Reporte shadow (`timewindow_shadow_report_<ts>.json`) escrito en `event_generator`.
- [x] VALIDACION (config_stress_tw.json, 20 agentes, layout real WH1, orders_test_sandbox):
      * No-regresion: body .jsonl byte-identico al baseline (md5 9d9d8544...). Sim termina
        t=262, sin freeze. SOMBRA no altera el movimiento (confirmado).
      * Planner: 72 tramos, 70 planes hallados, 2 fallidos (artefacto de sombra: la
        posicion real estatica del agente cae a veces dentro del intervalo PLANIFICADO de
        otro agente -> is_free del start falla; inofensivo, solo se loguea). **0 solapes**
        (table_overlap_violations=0, reserve_overlaps=0) => invariante de disjuncion OK.
      * Coste planificacion: avg=12.0ms/plan, max=143.5ms; avg_expansiones=318, max=5497,
        cap_hits=0; esperas insertadas=2.
      * Determinismo: .jsonl identico en doble corrida; shadow_report identico en TODAS
        las metricas logicas (solo varian los campos *_ms, que son wallclock).
- [ ] Backup + commit local F1.

### Fase 2 — Ejecucion segun plan ST (IMPLEMENTADA; validacion PARCIAL)

CAMBIOS DE CODIGO (vivos):
- [x] `spacetime_planner.py`: extraido `_plan_reserve_core` (planifica+reserva+mide,
      devuelve el plan). `plan_and_reserve_shadow` (F1) ahora es wrapper del core
      (metricas identicas). NUEVO `plan_and_reserve` (F2) devuelve el plan a ejecutar.
      NUEVO `reserve_dwell(cell, t_in, dwell, agent)` para permanencia (aun NO cableado).
      Metricas: +exec_segments, +exec_fallbacks.
- [x] `operators.py`: NUEVO generador `_timewindow_execute_plan` (reserva el plan y lo
      SIGUE: `yield env.timeout(t_sig - t_act)` por paso; esperas = celda repetida; sin
      espera reactiva). En `_recorrer_tramo` rama no-cell: gate por `timewindow_shadow`
      (True->sombra F1; False->ejecucion F2). Si el plan falla -> cae al estatico
      (fallback 4.2, contado en exec_fallbacks). Flag off => rama intacta (byte-identico).
- [x] `config_stress_tw_exec.json`: mode:timewindow, shadow:false, allow_diagonal:false
      (CARDINAL, F2 por plan), staggered_start:true (dispersion F2 = condicion inicial sana).

VALIDACION (config_stress_tw_exec.json, 20 agentes, WH1, orders_test_sandbox; cap 600s):
| Criterio                         | Resultado                         | Estado |
|----------------------------------|-----------------------------------|--------|
| Termina sola (sin cap wallclock) | sim_end_t=268, terminated=True    | OK     |
| Freeze                           | False (wall 28.6s)                | OK     |
| Throughput                       | 126 WO, 0.47 WO/simT (>0)         | OK     |
| Planes hallados / fallidos       | 72 / 0  (las 2 fallas de SOMBRA desaparecieron) | OK |
| exec_segments / fallbacks        | 72 / 0  (ningun fallback estatico)| OK     |
| reserve_overlaps / table_overlap | 0 / 0  (INV disjuncion intacto)   | OK     |
| Co-ocupaciones moving+moving     | 0  (garantia central CUMPLIDA)    | OK     |
| Watchdog stalls                  | 0 (en timewindow ni arranca)      | OK     |
| Coste planner (ejecucion)        | avg=2.79ms, max=36ms, exp avg=124, cap_hits=0 | OK |
| No-regresion flag OFF            | body .jsonl md5=9d9d8544 (==baseline), 9685 ev, t=262 | OK |
| **I1 = 0 (co-ocupacion total)**  | **I1 = 81 (startup 20, max_concurrent 8 en depot)** | **FALLA** |

DIAGNOSTICO EXACTO de I1=81 (instrumentando `_record_cooccupation` por estado de los
ocupantes, sin tocar la sim):
- Por par de estados: idle+moving=56 (69%); moving+picking=14; lifting+moving=5;
  resto=6 (apilamiento idle/unloading en el depot, concurrencia hasta 8).
- **Cero moving+moving.** TODA co-ocupacion involucra a un agente PARADO que NO reservo
  su celda (idle/picking/lifting/unloading); el agente en movimiento sigue su plan
  reservado y "pisa" al parado porque el planner no sabia que estaba ahi.
- Por celda: 100% concentradas en el embudo del depot/staging y su pasillo
  (2,27)=14 (3,27)=9 (4,27)=8 (3,29)=7 (2,28)=6 ... [staging1/depot=(3,29)].

CONCLUSION (causa raiz, NO bug de ejecucion):
- El ruteo espacio-temporal cumple su garantia: 0 colisiones entre agentes en
  movimiento, 0 deadlock, 0 freeze, termina, planes nunca fallan, coste barato.
  El "embudo del deposito" que antes congelaba YA NO produce deadlock de movimiento.
- I1!=0 se debe EXCLUSIVAMENTE a la PERMANENCIA NO RESERVADA: los agentes parados no
  apartan su huella espacio-temporal, asi que el planner enruta a otros a traves de
  ellos. Es el modelado de permanencia del plan (3.2 / 4.6), que NO entra en el alcance
  de "ejecucion segun el plan en _recorrer_tramo" (F2 estricto).
- Descomposicion: (a) permanencia DETERMINISTA (picking/lifting/unloading ~19-25 casos)
  -> reservable YA con `reserve_dwell` (plan 3.2, dwell conocido). (b) IDLE en el depot
  (~56 casos + aforo concurrencia 8) -> el depot/staging es UNA celda donde varios
  agentes ociosos/terminados se aparcan; duracion idle desconocida; el plan DIFIERE esto
  a "zona con aforo" (4.6 / 2.13-C, fase posterior). Aun reservando (a), el grueso (b)
  persiste => I1=0 estricto exige resolver el aforo del depot (fuera del F2 deferido).

DECISION PENDIENTE DEL DIRECTOR (no parcheo a ciegas, Ley #1 + instruccion de PARAR):
  Opcion 1: extender F2 con `reserve_dwell` para permanencia determinista (picking/
            lifting/unloading) -> baja I1 a ~56 (solo idle), mide el residual real.
  Opcion 2: ademas dispersar el aparcamiento IDLE en andenes del depot (reusar la
            dispersion F2) y/o modelar aforo -> apunta a I1=0 pero ya toca diseno de
            permanencia/aforo (roza fase posterior; pedir alcance explicito).
  Opcion 3: redefinir el criterio: aceptar que "0 colisiones REALES" = 0 moving+moving
            (cumplido) y tratar agentes parados como no-colision (son aparcamiento, no
            choque). I1 quedaria como metrico de aforo, no de colision.
  SIN COMMIT hasta decidir. Backup de archivos vivos F2 -> pendiente de la decision.

---

## FASE 2b — STANDING RESERVATIONS (intento del arreglo natural) -> REGRESION -> REVERTIDO

OBJETIVO: completar el modelo de reservas haciendo que un agente en estado NO-movil
(idle/picking/lifting/unloading/stagger) mantenga una reserva de su celda actual, para
que el SpaceTimePlanner esquive a los parados. Hipotesis: bajaria I1 hacia 0.

CAMBIOS PROBADOS (todos gateados a mode:timewindow + shadow:false; flag off NO-OP):
- Helpers en `BaseOperator`: `_tw_exec_planner` (gate), `_tw_hold_cell(dwell)` (reserva
  determinista via `reserve_dwell`), `_tw_idle_hold(span)` (reserva rodante en idle con
  release_agent+reserve por ciclo), `_tw_parking_cell` (BFS off-staging por spawn_index),
  `_tw_return_to_park` (navegar a parking tras el tour).
- Cableado: dwell en picking (Ground), lift+pick+bajad