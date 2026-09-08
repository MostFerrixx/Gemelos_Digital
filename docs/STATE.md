# STATE — Gemelo Digital de Almacen

> Este archivo se REESCRIBE ENTERO cada sesion (no acumula). Es la foto del
> presente, nada mas. Historial -> `docs/CHANGELOG.md`. Pendientes ->
> `docs/BACKLOG.md`. Identidad/reglas/arquitectura -> `CLAUDE.md`.

**Ultima actualizacion:** 2026-09-08

## Git

- `main` = **`0a32cd2`**, pusheado a origin. Todo integrado por fast-forward.
- Baseline byte-identico vigente: **`sha256=4bcac137...`, 15.930.231 bytes**,
  seed 42 (`tests/baseline.json`). Regenerado el 2026-09-08 al migrar el
  canonico a `agent_types` explicito. Anterior: `95b59db0` (BK-06).
- Ramas muertas de 2025 borradas (2026-07-25), recuperables por tag:
  `archive/feat-realtime-workorder-dashboard`, `archive/fix-configurator-tool`.
- REGLA pinneada por tests BN-05 e IN-43: la metadata del .jsonl NO puede
  contener valores wall-clock (rompe el determinismo del gate).

## Red de seguridad (correr tras CUALQUIER cambio de motor)

```
python -m pytest -q                # 228 passed, 1 deselected (~10s)
python scripts/regression_gate.py  # GATE PASS esperado (baseline 4bcac137)
```

## El canonico, en su forma definitiva

`config.json` ya define la flota de forma **explicita** (`agent_types` con 4
agentes: 2 GroundOperator cap 150 en `Area_Ground` + 2 Forklift cap 1000 en
`Area_High`/`Area_Special`). Se acabo la forma legacy por contadores, que era
la raiz de BK-05 y de la via ciega de BK-06.

Verificado al migrar: los 35.020 eventos del replay quedaron identicos salvo el
campo `capacidad` (150 -> 1000 en los montacargas, 4.055 eventos), que era un
dato MAL mostrado por el visor. La simulacion no cambio; el visor ahora dice la
verdad.

**La congestion timewindow SIGUE ACTIVA en el canonico** (`enabled: true`,
`mode: "timewindow"`), tal como documenta `CLAUDE.md` 5. En esta sesion se creyo
por un momento que estaba apagada: era el archivo del disco alterado por el
auto-guardado de "Run Simulation" (BK-11), ya corregido.

## Ultimas iniciativas cerradas (detalle en CHANGELOG)

- **BK-11** — "Run Simulation" ya no pisa el `config.json`: corre sobre una copia
  temporal en `temp_web/`. El canonico solo cambia con "Aplicar Configuracion".
- **BK-05** — la pestana Flota materializa la flota legacy (endpoint
  `/api/configurator/resolve-fleet`, que usa `core.fleet.resolver_flota`) y ya
  se puede guardar. Sigue siendo util para configs viejas y presets.
- **Visor: "Saltar tiempos muertos"** — el ~94% del tiempo simulado no se mueve
  nadie; la casilla salta al proximo instante con movimiento
  (`GET /api/motion-times`).
- **Manual de usuario** del configurador: `docs/MANUAL_CONFIGURACION.md`.
- **BK-06** (2026-09-07) — `work_area_equipment` manda en el motor y la capacidad
  por area se deriva de la flota real. Plan: `docs/PLAN_BK06_CAPACIDAD_AREA.md`.

## Decisiones del Director pendientes

1. **BK-08 (ALTA) — confirmar `work_area_equipment` con el almacen real.** Todo
   BK-06 asume que Area_High/Area_Special son 100% montacargas. Es un SUPUESTO
   no verificado del que dependen los numeros. Si es falso se corrige en config
   (tab Flota), sin tocar codigo.
2. **BK-09 — la flota 2+2 esta sub-dimensionada.** Medido: 2+3 -> 6042 s,
   2+4 -> 4844 s (optimo), 2+5 empeora por congestion. Decision de negocio.
   Recomendacion de Cerebellum: NO tocar el canonico -- debe reflejar el almacen
   real del cliente y mostrarle el costo, no maquillar el KPI.
3. **BK-07 — areas mixtas** (varios tipos de equipo por area). Depende de BK-08.
4. **BK-02 — FIFO Estricto en UI:** redefinir que deberia hacer antes de
   exponerlo.
5. **`outbound_staging_distribution` real** en el canonico (hoy 100% zona 1).
6. **INIT-6 Opcion C (clustering geografico):** solo con datos reales de
   geolocalizacion. No bloqueante.

## Siguiente prioridad (sin decidir aun)

Candidatos: **INIT-3 v3** (capacidades por agente en el optimizador — quedo
mucho mas barato tras BK-06 y encontraria BK-09 solo; ademas el canonico ya
tiene la flota explicita que necesitaba), **BK-10** (~30 min, el boton Restart
no reinicia de verdad), las decisiones de arriba, o iniciativa nueva.

## Que esta VIVO y ACTIVO ahora mismo (ademas de CLAUDE.md §3/§5)

- Congestion timewindow: ACTIVA en el canonico (no opt-in).
- **BK-06:** `work_area_equipment` gobierna la compatibilidad agente-area en el
  motor; la capacidad de dimensionado por area se deriva de la flota real
  (minimo como red de seguridad). Fuentes unicas: `src/core/fleet.py` (flota) y
  `src/core/work_areas.py` (areas). Bloque opt-in `fleet_defaults` para las
  capacidades por defecto (antes hardcodeadas).
- INIT-8 nucleo (catalogo fisico + tiempos por clase/peso + mezcla por clase):
  ACTIVO. F3/F4 de INIT-8 e inbound completo: opt-in via config/UI.
- INIT-4 (prioridad/SLA/olas), INIT-6, INIT-4b (KPI SLA), MEJ-BOTTLENECK,
  MEJ-SLA-OPT: opt-in o aditivos.
- MEJ-2 experiment runner + tab A/B. Optimizador Optuna CLI+web.
- Web: `server.py` + `app_state.py` + `routers/`. Tabs: Carga 1, Estrategias 2,
  Flota 3, Layout 4, Outbound Staging 5, Inbound 6, Optimizacion 7,
  Experimentos A/B 8. Visor con "Saltar tiempos muertos".
- Robustez: excepcion a mitad de tour degrada por WO; watchdog de no-progreso.
- Disco: temporales en `temp_web/` (D, gitignoreado, purga 24h). Ahi van tambien
  los configs de corrida de BK-11 (`run_config_*.json`).

## Bugs conocidos (no criticos)

- **BK-10:** el boton "Restart" del configurador responde `success` pero NO
  reinicia el proceso (verificado por PID). Para aplicar cambios del backend hay
  que relanzar el servidor a mano. Ver BACKLOG.
- `warehouse.db-shm` / `warehouse.db-wal`: WAL de SQLite, untracked pero ya en
  `.gitignore`.
- Deuda menor: la copia de `_expected_equipment_for_area` en
  `web_prototype/config_manager.py` y en `fleet-manager.js` sigue duplicada. El
  motor ya usa la fuente unica `src/core/work_areas.py`.
- El visor no interpola posiciones entre snapshots (pide uno cada 250 ms de
  tiempo simulado y dibuja la celda cruda). Con "Saltar tiempos muertos" el
  sintoma principal desaparecio; animar el trayecto queda como mejora abierta.
