# STATE — Gemelo Digital de Almacen

> Este archivo se REESCRIBE ENTERO cada sesion (no acumula). Es la foto del
> presente, nada mas. Historial -> `docs/CHANGELOG.md`. Pendientes ->
> `docs/BACKLOG.md`. Identidad/reglas/arquitectura -> `CLAUDE.md`.

**Ultima actualizacion:** 2026-07-25

## Git

- `main` = `36fbc63` (actualizacion documental completa). Sin cambios nuevos.
- **Rama de trabajo: `fix/bk06-capacidad-area`** — BK-06 F0-F3 implementadas y
  validadas, SIN mergear. Esperando OK del Director para F4 (regenerar
  baseline) y para el merge.
- Baseline byte-identico vigente: **`sha256=2233b3c6...`, 10.039.862 bytes**,
  seed 42 (`tests/baseline.json`). **BK-06 lo rompe intencionalmente** (ver
  abajo); todavia NO se regenero.
- Limpieza 2026-07-25: borradas las ramas muertas de 2025
  `feat/realtime-workorder-dashboard` y `fix/configurator-tool`. Recuperables
  por tag: `archive/feat-realtime-workorder-dashboard`,
  `archive/fix-configurator-tool` (pusheados a origin).
- REGLA pinneada por tests BN-05 e IN-43: la metadata del .jsonl NO puede
  contener valores wall-clock (rompe el determinismo del gate).

## Red de seguridad

```
python -m pytest -q                # 207 passed (193 + 14 de BK-06), ~8s
python scripts/regression_gate.py  # FAIL esperado en esta rama (BK-06)
```

En `main` el gate da PASS. En `fix/bk06-capacidad-area` da **FAIL a proposito**:
el comportamiento cambio y el baseline nuevo aun no se genero (F4 pendiente de
OK del Director).

## LO IMPORTANTE DE ESTA SESION: BK-06

Bug de motor encontrado y corregido (F0-F3). Plan, RCA, numeros y validacion
completos en **`docs/PLAN_BK06_CAPACIDAD_AREA.md`** (leerlo antes de retomar).

**El bug:** la clave `capacity` alimentaba dos cosas desacopladas — la capacidad
fisica del operario y el divisor que dimensiona WOs por area. Con el canonico
(`agent_types: []`) la segunda quedaba ciega y dimensionaba TODAS las areas a
150, aunque las atendieran montacargas de 1000. Causa raiz: `work_area_equipment`
ya era la fuente de verdad de que equipo sirve cada area, pero **el hot-path de
simulacion no la consultaba**.

**El fix:** el mapa manda en el motor (`src/core/work_areas.py`), la capacidad
por area se deriva de la flota real tomando el minimo (`src/core/fleet.py`), y
el dispatcher ya no devuelve WOs que no caben.

**El trade-off, aprobado por el Director:** makespan 7440 -> 8783 s (+18,1%).
El baseline historico se lograba en parte con asignaciones **fisicamente
imposibles** (terrestres bajando mercaderia de racks altos); al prohibirlas, los
montacargas quedan como cuello de botella real. **Realismo > KPI historico**
(principio rector, `CLAUDE.md` 1.5). Las 626 WOs (vs 666) mueven el MISMO
volumen: son 40 viajes menos, no trabajo perdido.

**Hallazgo de negocio (BK-09):** con 2+3 montacargas el modelo realista ya
supera el baseline historico (6042 s, -18,8%); el optimo esta en 2+4 (4844 s,
-34,9%). La flota 2+2 esta sub-dimensionada.

## Decisiones del Director pendientes

1. **BK-06 F4:** autorizar `--update-baseline --yes` y el merge a main.
2. **BK-08 (alta):** confirmar con el almacen real que `Area_High`/`Area_Special`
   son 100% montacargas. Es un SUPUESTO activo del que dependen los numeros de
   BK-06. Si es falso, se corrige en config (tab Flota), sin codigo.
3. **BK-09:** decidir si se sube la flota de montacargas en el canonico.
4. **BK-07:** confirmar si existen areas mixtas (varios equipos por area).
5. **BK-05 — FIFO Estricto en UI (BK-02):** redefinir que deberia hacer FIFO.
6. **`outbound_staging_distribution` real** en el canonico (hoy 100% zona 1).
7. **INIT-6 Opcion C (clustering geografico):** solo con datos reales de
   geolocalizacion. No bloqueante.

## Que esta VIVO y ACTIVO ahora mismo (ademas de CLAUDE.md §3/§5)

- Congestion timewindow: activa en el canonico (no opt-in).
- INIT-8 nucleo (catalogo fisico + tiempos por clase/peso + mezcla por clase):
  ACTIVO. F3/F4 de INIT-8 e inbound completo: opt-in via config/UI.
- **BK-06 (en la rama):** `work_area_equipment` gobierna el motor; capacidades
  de flota configurables via el bloque nuevo opt-in `fleet_defaults`.
- INIT-4 (prioridad/SLA/olas), INIT-6, INIT-4b (KPI SLA), MEJ-BOTTLENECK,
  MEJ-SLA-OPT: opt-in o aditivos.
- MEJ-2 experiment runner + tab A/B. Optimizador Optuna CLI+web.
- Web: `server.py` + `app_state.py` + `routers/`. Tabs: Carga 1, Estrategias 2,
  Flota 3, Layout 4, Outbound Staging 5, Inbound 6, Optimizacion 7,
  Experimentos A/B 8.
- Robustez: excepcion a mitad de tour degrada por WO; watchdog de no-progreso.
- Disco: temporales en `temp_web/` (D, gitignoreado, purge 24h).

## Bugs conocidos (no criticos)

- `warehouse.db-shm` / `warehouse.db-wal`: WAL de SQLite, untracked pero ya en
  `.gitignore`.
- BK-05 (UX): guardar el canonico desde la UI lo bloquea el guard de flota
  vacia. DESBLOQUEADA la opcion (b) tras BK-06 (ver BACKLOG).
- La copia de `_expected_equipment_for_area` en `web_prototype/config_manager.py`
  y en `fleet-manager.js` sigue duplicada (el motor ya usa la fuente unica
  `src/core/work_areas.py`). Consolidar la web es deuda menor pendiente.
