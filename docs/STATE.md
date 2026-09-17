# STATE — Gemelo Digital de Almacen

> Este archivo se REESCRIBE ENTERO cada sesion (no acumula). Es la foto del
> presente, nada mas. Historial -> `docs/CHANGELOG.md`. Pendientes ->
> `docs/BACKLOG.md`. Identidad/reglas/arquitectura -> `CLAUDE.md`.

**Ultima actualizacion:** 2026-09-17

## Git

- `main` = todo integrado por fast-forward desde `feat/datos-maestros-web`
  (que incluye `feat/ui-flota-cards`), pusheado a origin.
- `main` = `6a18e44` (INIT-11 F0 y F1 integradas y pusheadas el 2026-09-17).
- Rama en curso: `feat/init11-f2-perfiles` (F2 hecha, sin mergear).
- Baseline byte-identico vigente: **`sha256=3a87a1c0...`, 15.930.197 bytes**,
  seed 42 (`tests/baseline.json`). Ultimo cambio: 2026-09-16, F0 (solo el
  campo `work_group` de los eventos). F1 no lo cambio.
- REGLA pinneada por tests BN-05 e IN-43: la metadata del .jsonl NO puede
  contener valores wall-clock.
- En Windows `core.autocrlf=true`: `config.json` puede figurar como modificado
  solo por finales de linea. Git y el gate normalizan; restaurar con
  `git checkout -- config.json` antes de commitear.

## Red de seguridad

```
python -m pytest -q                # 292 passed, 1 deselected (~10s)
python scripts/regression_gate.py  # GATE PASS esperado (baseline 3a87a1c0)
python scripts/check_equivalencia_personas.py  # INIT-11 F1: EQUIVALENTE (~1 min)
```

## Estado del configurador web (revisado el 2026-09-16)

Las 8 pestanas usan el mismo patron de tarjetas y controles; barrido automatico
sin controles con estilo nativo; claro/oscuro y 1280/1440 px verificados.
**Guardar sin cambios es un no-op exacto** (verificado extremo a extremo).

Novedades vigentes:
- **Datos maestros desde la web** (pestana Layout y Datos): subir/validar el
  Excel y el mapa, "Aplicar Excel" a `warehouse.db` con backup, aviso si el
  Excel quedo mas nuevo que la base, tablas de consulta, y edicion de las
  coordenadas de zonas (Outbound Staging) y muelles (Inbound) validadas contra
  el mapa. **Recordar: el motor lee `warehouse.db`, no el Excel.**
- "Run Simulation" corre sobre una copia temporal y no toca `config.json`.
- Visor con "Saltar tiempos muertos".
- Manual de usuario al dia: `docs/MANUAL_CONFIGURACION.md`.

## PROXIMO PASO: INIT-11 Task Path

Plan v2 en ejecucion: **`docs/PLAN_INIT11_TASK_PATH.md`** (6 pilares, 11 fases).
- **F0 = BK-12: HECHA** (`081e2a0`). El Work Group de cada orden sale del dato
  real; unico cambio en eventos = campo `work_group`.
- **F1: HECHA** (`277a9af`, en main). Personas + equipos, equivalencia exacta.
- **F2: HECHA** (sin mergear). Perfiles con prioridad, regla de cambio y
  estacionamientos. Medido: -16,8% de tiempo total con pickers polivalentes.
- **Siguiente: F3** -- task path basico (pick -> punto de transferencia ->
  staging). Es punto de control con el Director.
- Puntos de control con el Director: al cerrar F1, F3, F6 y F8.
- 4 decisiones menores en la seccion 10 del plan (con sugerencia).

## Decisiones del Director pendientes (no bloquean INIT-11)

1. **BK-08 (alta):** confirmar con el almacen real que Area_High/Area_Special son
   100% montacargas. Supuesto activo de BK-06.
2. **BK-09:** flota 2+2 sub-dimensionada (2+4 es el optimo medido).
3. **Reparto de `outbound_staging_distribution`** entre las 7 zonas (hoy 100% a
   la zona 1: todo el trafico converge en una esquina).
4. **BK-07:** areas mixtas. **BK-02:** FIFO en UI.
5. **INIT-10** (modelo de almacen propio, reemplazo de Tiled): analizado, en
   backlog para despues.

## Que esta VIVO y ACTIVO ahora mismo (ademas de CLAUDE.md §3/§5)

- Congestion timewindow: ACTIVA en el canonico.
- BK-06: `work_area_equipment` manda en el motor; capacidad por area derivada de
  la flota real. Fuentes unicas: `src/core/fleet.py`, `src/core/work_areas.py`.
- Canonico con `agent_types` explicito (2 terrestres + 2 montacargas).
- INIT-8 nucleo ACTIVO; F3/F4 e inbound opt-in.
- Web: `server.py` + `app_state.py` + `routers/` (configurator, master_data,
  replay, runners, system).

## Bugs conocidos (no criticos)

- **BK-10:** el boton "Restart" responde `success` pero no reinicia el proceso.
- Al reiniciar el servidor a mano puede quedar un proceso hijo de
  `multiprocessing` reteniendo el puerto 8000: hay que cerrarlo tambien.
- Deuda menor: copia de `_expected_equipment_for_area` en
  `web_prototype/config_manager.py` y `fleet-manager.js`.
- El visor no interpola posiciones entre snapshots (mitigado con "Saltar
  tiempos muertos").
- `docs/INSTRUCCIONES_LAYOUT_PERSONALIZADO.md` desactualizada (dice `picking`,
  el motor busca `picking_location`); se corrige en la etapa 1 de INIT-10.
