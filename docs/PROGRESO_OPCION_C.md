# PROGRESO INICIATIVA #2 — OPCION C (Time-Window / Reservation Routing)

> Documentacion viva. Las sesiones se cortan por limite de tokens: este doc
> permite retomar EXACTAMENTE donde se quedo. Se actualiza tras CADA paso.
> Rama: `feature/allocation-layer-v12.1`. Respaldo previo: commit `7d3e782`.
> Alcance autorizado AHORA: **solo Fase 0 + Fase 1** (NO F2 sin OK del Director).

## Estado de fases
- [x] F0 — Andamiaje y flag `mode: timewindow` (sin cambio de comportamiento) — HECHO
- [x] F1 — ReservationTable + A* espacio-temporal en modo SOMBRA — HECHO
- [ ] (F2+ — NO autorizado todavia; requiere visto bueno del Director)

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

---

## BITACORA (cronologica, lo mas reciente abajo)

- [INICIO] Leido el plan completo `docs/PLAN_INICIATIVA_2_OPCION_C.md`. Rastreada
  la cadena viva: `pathfinder.py` (A* estatico, octil, get_neighbors orden fijo),
  `route_calculator.py` (`calculate_route` -> segment_paths), `operators.py`
  (`_recorrer_tramo` ~L333: rama no-cell byte-identica + rama F3 cell_exclusion;
  choke `_set_pos` ~L290; consumo de ruta ~L530/593 Ground, ~L924/987 Forklift),
  `congestion_manager.py` (ACTIVE_MODES, EXCLUSION_MODES, I1 instrument, F3 owner,
  watchdog), `warehouse.py` (~L195 init congestion), `event_generator.py`
  (~L211 loop, ~L259 write_report). Entorno: simpy/pandas/openpyxl/pytmx/pygame
  instalados; harness corre (20 agentes, termina en sim_t=262, ~32s wallclock).
  Bug FUSE confirmado: `rm`/`unlink` da EPERM; `mv` (rename) SI funciona -> se usa
  para round-trip y para limpiar `index.lock` stale (git commitea OK).
- [F0 HECHO] Andamiaje completo + no-regresion byte-identica. Commit `421b20f`.
- [F1 HECHO] ReservationTable + SpaceTimePlanner en sombra. 0 solapes sobre layout real,
  coste avg 12ms/plan, .jsonl byte-identico, determinista. Commit `<pendiente abajo>`.
- [NOTA F2] NO iniciada (requiere visto bueno del Director). F2 cambiaria la EJECUCION
  (_recorrer_tramo seguiria el plan en vez de la ruta estatica). El injerto ya existe.
