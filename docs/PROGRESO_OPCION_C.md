# PROGRESO INICIATIVA #2 — OPCION C (Time-Window / Reservation Routing)

> Documentacion viva. Las sesiones se cortan por limite de tokens: este doc
> permite retomar EXACTAMENTE donde se quedo. Se actualiza tras CADA paso.
> Rama: `feature/allocation-layer-v12.1`. Respaldo previo: commit `7d3e782`.
> Alcance autorizado AHORA: **solo Fase 0 + Fase 1** (NO F2 sin OK del Director).

## Estado de fases
- [x] F0 — Andamiaje y flag `mode: timewindow` (sin cambio de comportamiento) — HECHO
- [ ] F1 — ReservationTable + A* espacio-temporal en modo SOMBRA (planifica, no ejecuta)
- [ ] (F2+ — NO autorizado todavia)

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
- [ ] Backup + commit local F0.

### Fase 1 — Planner en sombra
- [ ] `ReservationTable` completo (is_free, reserve+assert, swap, purga, invariante).
- [ ] `SpaceTimePlanner.find_path_st` (A* continuo mover/esperar, octil reusada, cortes).
- [ ] Inyeccion sombra en `operators` (planifica+reserva; ejecuta estatica).
- [ ] Reporte shadow (`timewindow_shadow_report.json`) en `event_generator`.
- [ ] Validacion: 0 solapes en planes, coste/ms reportado, sim real sin cambios.
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
