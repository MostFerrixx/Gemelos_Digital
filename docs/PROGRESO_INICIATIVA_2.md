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
- [HECHO] F1.1 Crear `src/subsystems/simulation/conge