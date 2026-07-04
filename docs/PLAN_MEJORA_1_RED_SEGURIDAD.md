# PLAN MEJORA 1 — Red de seguridad automatizada
# Suite pytest + gate de regresion byte-identico en un comando

**Creado:** 2026-07-04 · **Autor:** Cerebellum · **Estado:** EJECUTADO 2026-07-04
(F1-F5 completas en rama `feature/mej-1-red-seguridad`; evidencia de cierre en
`docs/BACKLOG.md` seccion MEJ-1 y `docs/HANDOFF.md` seccion 4)
**Backlog:** MEJ-1 en `docs/BACKLOG.md` · **Orden acordado:** MEJ-1 -> MEJ-3 -> MEJ-2

---

## 1. OBJETIVO

Que el proyecto tenga, por primera vez, una red de seguridad automatizada:

1. **Suite pytest real** (unit tests de la logica critica del motor y de la
   validacion de config) que corre en segundos.
2. **Gate de regresion en un comando** (`python scripts/regression_gate.py`):
   corre la simulacion canonica con semilla fija y compara el SHA256 del `.jsonl`
   contra el baseline registrado. PASS/FAIL sin interpretacion humana.
3. (Opcional, F5) CI en GitHub Actions que ejecuta ambos en cada push.

**Fuera de alcance:** NO se toca ninguna linea de `src/` ni de `web_prototype/`.
Esta mejora solo AGREGA tests, scripts y configuracion de test. El propio gate
demuestra que el motor quedo intacto.

---

## 2. EVIDENCIA EMPIRICA (verificada 2026-07-04, esta sesion)

- **El baseline SE REPRODUCE HOY**, corrida real:
  - Comando: `WAREHOUSE_SEED=42` + `python entry_points/run_generate_replay.py`
    con el `config.json` canonico (incluye `congestion` activo).
  - Resultado: `replay_20260704_163041.jsonl`, **5.379.372 bytes**,
    SHA256 = `A4AE8D4E9F7DD444EB217AA60AC874CBB5B062A3E8CCFAAA908CF9F7D1E86C6E`
    (coincide con el baseline historico `a4ae8d4e…` de HANDOFF §8).
  - **Duracion: 27,4 s** en la maquina del Director -> el gate es barato,
    se puede correr en cada commit.
  - Entorno: Python 3.13.6, Windows 10.
- **pytest NO esta instalado** (esta en `requirements.txt` como dev-dep opcional
  pero el entorno actual no lo tiene): `python -m pytest` -> "No module named pytest".
- **`tests/` actual es 100% legacy**: `tests/bugfixes/` (fixes del dashboard PyQt6
  y de la tecla "O" del viewer Pygame), `tests/integration/` (dashboard/replay
  Pygame, event sourcing viejo), `tests/manual/`, `tests/unit/` (1 archivo de
  compatibilidad de config antiguo). Importan modulos archivados/borrados; no
  compilan contra la cadena viva. NO son red de seguridad (ya documentado en
  CLAUDE.md §4).

---

## 3. DECISIONES DE DISENO

**D1 — Baseline pineado en un archivo versionado.**
`tests/baseline.json` con `{sha256, size_bytes, seed, python_version, fecha,
descripcion}`. El gate lee de ahi; nunca hardcodear el SHA en el script.
Cuando un cambio de comportamiento sea INTENCIONAL (feature aprobada), el flujo
es: correr gate -> FAIL esperado -> regenerar baseline con flag explicito
(`--update-baseline`) -> commit del nuevo baseline JUNTO con la feature.

**D2 — Tests de helpers privados: SI, deliberadamente.**
Los metodos `_aplicar_prioridad_pedido`, `_pool_para_barrido`,
`_wo_elegible_por_ola`, `_allocate_across_locations`, etc. son la logica de
negocio real y son funciones casi puras (listas in/out). Testearlos direct o es
lo que da red de seguridad al proximo refactor. Son tests de caracterizacion:
pinean el comportamiento ACTUAL (incluidos bugs conocidos, marcados como tal).

**D3 — Sin SimPy real en los unit tests.**
`DispatcherV11.__init__` acepta `env, almacen, calculators, data_manager` como
`Any`. Se instancia con stubs triviales (`FakeEnv` con atributo `.now`,
`None`/`MagicMock` para el resto) + dict de config. Rapido y sin I/O.

**D4 — Cuarentena, no borrado, del tests/ legacy.**
`git mv tests/... _legacy/tests_gui/` (mismo criterio que `_legacy/gui_escritorio/`,
reversible). El nuevo `tests/` queda solo con la suite viva.

**D5 — El gate corre el proceso REAL, no una version instrumentada.**
`scripts/regression_gate.py` invoca `entry_points/run_generate_replay.py` por
subprocess con `WAREHOUSE_SEED=42` y el `config.json` canonico, localiza el
`.jsonl` recien generado en `output/`, computa SHA256 y compara. Cero
acoplamiento con el motor.

**D6 — Solo ASCII en todo el codigo nuevo** (Ley #4): tests, script del gate y
sus salidas usan `[OK]` / `[FAIL]` / `[WARN]`.

---

## 4. FASES DE IMPLEMENTACION

### F0 — Baseline verificado y registrado  [HECHO 2026-07-04 en esta sesion]
Corrida real reproduce el SHA historico (seccion 2). Al ejecutar el plan, F0 se
materializa creando `tests/baseline.json` con esos valores.

### F1 — Cuarentena del tests/ legacy
1. `git mv tests/bugfixes tests/integration tests/manual tests/unit _legacy/tests_gui/`
   (conservando subcarpetas; borrar `__pycache__` sueltos, que ya son basura no versionada).
2. Dejar `tests/__init__.py` fuera (el nuevo layout no lo necesita; pytest usa rootdir).
3. Actualizar `_legacy/README.md` con el movimiento y como revertirlo.

### F2 — Infraestructura pytest
1. `pip install pytest` (ya esta declarado en requirements.txt; solo falta instalarlo).
2. `pytest.ini` en la raiz:
   - `testpaths = tests`
   - `norecursedirs = _legacy basura archived output _backup_iniciativa2`
   - marker `gate` registrado (para el smoke opcional del gate via pytest).
3. `tests/conftest.py`:
   - Inserta `src/` en `sys.path` (mismo mecanismo que usan los entry_points,
     para que `from subsystems...` y `from core...` resuelvan).
   - Fixtures compartidas:
     - `fake_env` (objeto con `.now` seteable),
     - `base_config` (dict minimo de configuracion),
     - `make_wo` (factory de WorkOrders de juguete con `priority`, `due_time`,
       `wave_id`, `work_area`, `pick_sequence`, posicion — atributos verificados
       contra `warehouse.py::WorkOrder` real antes de escribir los tests),
     - `dispatcher_minimo` (DispatcherV11 con stubs, estrategia parametrizable).

### F3 — Suite de unit tests (catalogo)

**`tests/unit/test_dispatcher_prioridad.py`** (INIT-4 C2)
- PR-01: flag off -> `_aplicar_prioridad_pedido` devuelve la lista INTACTA
  (mismo orden, mismos objetos).
- PR-02: flag on -> conserva solo las WOs con menor `priority`.
- PR-03: empate de priority -> ordena por `due_time` ascendente; `due_time=None`
  va al final; orden estable.
- PR-04: `_pool_para_barrido` flag off -> todos los candidatos.
- PR-05: `_pool_para_barrido` con ancla priority>=99 -> no filtra.
- PR-06: `_pool_para_barrido` con ancla urgente -> solo WOs de la misma priority.

**`tests/unit/test_dispatcher_olas.py`** (INIT-4 C3)
- OL-01: `waves_enabled=False` -> siempre elegible.
- OL-02: WO sin `wave_id` -> elegible.
- OL-03: ola sin release definido -> elegible (defensivo).
- OL-04: `env.now < release` -> NO elegible; `env.now >= release` -> elegible.
- OL-05: normalizacion de claves de `release_times` (int vs str, valores no
  numericos ignorados) segun `__init__`.

**`tests/unit/test_dispatcher_estrategias.py`**
- ES-01: constructor lee estrategia/params del config (`dispatch_strategy`,
  `radio_cercania`, `radio_expansion_paso`, `radio_max_expansiones`,
  `cercania_tour_mode`, `max_wos_por_tour`) con sus defaults documentados.
- ES-02: `_estrategia_fifo` respeta orden de llegada, filtra por
  `can_handle_work_area` del operario (stub) y por elegibilidad de ola.
- ES-03 (H-5): el router `_seleccionar_work_orders_candidatos` acepta el alias
  corto "Ejecucion de Plan" y el largo "Ejecucion de Plan (Filtro por Prioridad)"
  sin caer al default. (Si el router exige mas estado del stub, degradar a test
  del mapeo de estrategia y documentarlo.)
- ES-04 (H-6): `_filtrar_por_radio` con radio restrictivo y expansion: verifica
  que expande por pasos hasta `radio_max_expansiones` en lugar de devolver vacio.

**`tests/unit/test_allocation.py`** (Allocation Layer V12.1, `order_strategies.py`)
- AL-01: `_coerce_int` / `_coerce_float` (None, str numerica, str basura, float,
  negativo) — pinear comportamiento actual.
- AL-02: `_allocate_across_locations`: stock exacto en una ubicacion.
- AL-03: split entre varias ubicaciones (orden de consumo determinista).
- AL-04: stock insuficiente -> asignacion parcial (`qty_allocated < qty_requested`)
  coherente con `fulfillment_policy="ship_partial"`.
- AL-05: stock cero -> exclusion/backorder segun comportamiento actual.

**`tests/unit/test_warehouse_cantidades.py`** (caracterizacion)
- WH-01: `_validar_y_ajustar_cantidad` con `sku.volumen <= max_capacity` ->
  unidades por viaje correctas.
- WH-02 (BUG CONOCIDO, pinear): `sku.volumen > max_capacity` -> comportamiento
  actual (qty 0 / 'staged'). Marcar con comentario "bug documentado en BACKLOG
  (WOs sobredimensionadas); actualizar este test cuando se aplique el fix".

**`tests/unit/test_web_config_validation.py`** (`web_prototype/config_manager.py`)
- CF-01: el `config.json` canonico de la raiz VALIDA ok (`validate_config` -> True).
  Usa los datos reales del repo (`layouts/Warehouse_Logic.xlsx`) — es barato y pinea
  el contrato config<->layout.
- CF-02 (QA-2): `agent_types` sin ningun agente -> rechazado.
- CF-03 (BK-04/QA-1): flota explicita que deja un area sin cobertura -> rechazado
  nombrando el area.
- CF-04 (QA-3): tipo de equipo incorrecto para el area (`work_area_equipment`) -> rechazado.
- CF-05: `radio_cercania` fuera de rango -> rechazado; `waves.release_times`
  > 1.000.000 -> rechazado (cap anti-hang documentado en HANDOFF §8).

**`tests/unit/test_service_level.py`** (`core/replay_utils.py`, INIT-5)
- SL-01: `build_service_level_summary` con almacen stub que expone
  `get_order_validation_result()` valido -> resumen con fill-rate correcto.
- SL-02: modo estocastico (sin validacion) -> `available=False`.

Meta de la suite: **~30-40 asserts, < 10 s de ejecucion, cero I/O de red y cero
SimPy real** (solo CF-01/CF-05 leen archivos del repo).

### F4 — Gate de regresion en un comando
1. `tests/baseline.json` (F0): sha256, size, seed=42, python 3.13.6, fecha,
   nota "config canonico con congestion timewindow activo".
2. `scripts/regression_gate.py`:
   - Lanza `entry_points/run_generate_replay.py` por subprocess con
     `WAREHOUSE_SEED=42` (env var) y cwd = raiz del proyecto.
   - Detecta la carpeta `output/simulation_*` creada por ESTA corrida (timestamp
     posterior al inicio, no "la mas reciente" a secas).
   - SHA256 + size del `.jsonl` -> compara contra baseline.
   - Salida: `[OK] GATE PASS ...` / `[FAIL] GATE FAIL esperado=... obtenido=...`
     y exit code 0/1. Duracion esperada ~30-60 s.
   - Flag `--update-baseline` (con confirmacion interactiva o `--yes`) para
     cambios de comportamiento INTENCIONALES.
   - Limpieza: opcion `--keep-output` (default: borra la carpeta de la corrida
     del gate para no ensuciar `output/`).
3. `tests/test_gate_smoke.py` marcado `@pytest.mark.gate` que invoca el script
   (excluido del run default via `-m "not gate"` en `pytest.ini` -> addopts).
4. Atajos: target `make test` / `make gate` en `Makefile` y comandos en `run.bat`.

### F5 — CI GitHub Actions  [APROBADA por el Director y VALIDADA EN VERDE 2026-07-04]
`.github/workflows/tests.yml`: en cada push/PR -> `pip install -r requirements.txt`
+ `pytest` + `python run_migration.py` + `python scripts/regression_gate.py`.
Validacion real destapo (y se corrigio) dos supuestos falsos del plan original:
- `warehouse.db` no existe en CI (no se versiona, Ley 7): sin ella el motor cae
  al fallback Excel y el SHA difiere -> la CI corre `run_migration.py` antes del
  gate. Verificado ademas que una BD recien migrada reproduce el baseline (sin
  deriva BD local vs Excel canonico).
- El supuesto "mismo SHA en Windows y Linux" era FALSO en crudo: el .jsonl se
  escribe en modo texto (CRLF vs LF; delta 11.880 bytes = numero de lineas).
  Fix: el gate hashea con EOL normalizado (CRLF->LF); el SHA normalizado de
  Windows coincidio EXACTO con el de ubuntu (`4a208831…`) -> determinismo
  multiplataforma probado (Python 3.13.6 local vs 3.13.14 CI). El motor NO se
  toco; el invariante del gate es "byte-identico modulo EOL".

---

## 5. RIESGOS Y MITIGACIONES

| Riesgo | Mitigacion |
|---|---|
| El SHA depende de la version de Python (orden de dict es estable, pero repr de floats/detalles podrian variar entre majors) | `baseline.json` registra la version; el gate emite `[WARN]` si la version local difiere de la del baseline |
| Tests acoplados a metodos privados se rompen en refactors legitimos | Es deliberado (D2): son la alarma. El refactor que cambia firmas actualiza los tests EN EL MISMO commit, y el gate valida que el comportamiento no cambio |
| `output/` se llena de corridas del gate | El gate borra su corrida por default (`--keep-output` para depurar) |
| CF-01 depende de `layouts/Warehouse_Logic.xlsx` real | Aceptado: es la fuente canonica versionada; si cambia el layout, el test DEBE reaccionar |
| Falso verde por pytest no instalado en otra maquina | `make test` falla ruidosamente si falta pytest; F5 (CI) elimina el factor maquina |

## 6. CRITERIOS DE ACEPTACION

1. `python -m pytest -q` -> verde, < 10 s, sin tocar `_legacy/` ni `output/`.
2. `python scripts/regression_gate.py` -> `[OK] GATE PASS` en ~30-60 s, exit 0.
3. Sabotaje de prueba (cambiar un default del dispatcher a mano, p.ej.
   `max_wos_por_tour` 20 -> 19): la suite o el gate DEBEN fallar; revertir.
4. `git diff` de la mejora NO contiene cambios en `src/` ni `web_prototype/`
   (solo `tests/`, `scripts/`, `pytest.ini`, `Makefile`/`run.bat`, `_legacy/`, docs).
5. Docs al dia: BACKLOG (MEJ-1 -> HECHO), HANDOFF, CLAUDE.md §4 (la frase
   "tests/ rota" se reemplaza por la referencia a la suite nueva).

## 7. ESTIMACION Y ORDEN

- F1+F2: ~30 min. F3: 1 sesion (lo mas largo: fixtures fieles a WorkOrder real).
- F4: ~45 min (la mecanica ya esta validada empiricamente en F0).
- F5: ~30 min + validacion en rama (solo si el Director lo aprueba).
- Total: **1-2 sesiones**. Todo en la rama `feature/allocation-layer-v12.1` o una
  rama nueva `feature/mej-1-red-seguridad` (recomendado, Ley #7).

## 8. VALIDACION EMPIRICA PARA EL DIRECTOR (al cierre)

```bat
python -m pytest -q                      :: verde, ~40 tests, <10 s
python scripts\regression_gate.py       :: [OK] GATE PASS sha=A4AE8D4E... (~30 s)
```
Y la prueba de fuego: pedir a Cerebellum el sabotaje controlado del punto 6.3 y
ver el gate ponerse rojo antes de revertir.
