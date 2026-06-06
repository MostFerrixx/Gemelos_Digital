# PROGRESO INICIATIVA #3 — SUBSISTEMA OUTBOUND (aforo de staging + despacho)

> Documentacion VIVA. Las sesiones se cortan por limite de tokens: este doc
> permite retomar EXACTAMENTE donde se quedo. Se actualiza tras CADA paso.
> Plan completo: `docs/PLAN_INICIATIVA_3_DESPACHO_OUTBOUND.md`.
> Analisis de aforo: `docs/ANALISIS_STAGING_AFORO.md`.
> Vision: `docs/VISION_PRODUCTO.md`.

## CONTEXTO DE RETOME (leer primero al reanudar)
- Rama: `feature/allocation-layer-v12.1` (HEAD al iniciar I3 = `64a4d7f`, docs).
- Alcance AUTORIZADO por el Director AHORA: **Fase 0 + Fase 1** (NO Fase 2 sin OK).
- Decision tomada: Opcion 3 (despacho REAL con pallets persistentes).
- Filosofia: todo detras de flag `config.json["outbound"]["enabled"]`; con el
  flag OFF (default), comportamiento BYTE-IDENTICO al baseline.

## LINEA BASE DE NO-REGRESION (capturada antes de tocar codigo)
- Config de validacion: `config_stress_tw_exec.json` (20 agentes, WH1,
  `uploads/orders_test_sandbox.json`, mode:timewindow exec).
- Generador de jsonl (sin analytics): `/tmp/gen_jsonl.py` (en sandbox; recrear si
  hace falta: crea EventGenerator, corre el loop, llama `volcar_replay_a_archivo`).
- **Baseline body md5 (sin linea-1 header) = `18502db7de9f33bdccf94db742c45dd8`**
- Baseline: 9918 eventos, 9920 lineas, sim_end_t=268.0.
- Criterio Fase 0: con flag off, el body del jsonl debe dar ESTE md5 exacto.

---

## DETALLE DE FASE 0 (spec exacta, aprobada para implementar)

Objetivo: andamiaje + flag, CERO cambio de comportamiento. Solo se anade codigo
gateado y aditivo; nada se ejecuta con el flag off.

### 0.1 config.json — bloque nuevo `outbound` (Ley #3: fuente de verdad)
Anadir al config canonico `config.json` (y a `config_stress_tw_exec.json` para
validar). Schema:
```
"outbound": {
  "enabled": false,            // master flag; false => comportamiento actual
  "dispatch_policy": "interval",   // "interval" | "batch" | "schedule" (Fase 2)
  "truck_interval": 20.0,      // T: segundos entre camiones (politica interval)
  "truck_capacity": 8,         // C: pallets por camion
  "loading_time": 2.0,         // segundos de carga por camion
  "zone_capacity_default": 8,  // k por defecto si la zona no esta definida en Excel
  "slot_wait_alert": 60.0      // umbral de espera-por-slot para alerta (detector)
}
```
Con `enabled:false`, NINGUN parametro se usa (solo se leen y guardan).

### 0.2 Modulo nuevo `src/subsystems/simulation/outbound.py` (skeletons)
Clases con firma y docstring, SIN logica activa (Fase 0):
- `class Pallet`: atributos `id, wo_id, order_id, staging_id, cell, t_staged,
  volumen, status` (status inicial "staged"). Metodo `to_dict()`.
- `class DockSlot`: `cell, occupied_by(None)`; metodos `is_free()`, `assign(pid)`,
  `release()`.
- `class StagingZone`: `staging_id, slots(list[DockSlot])`; `free_slot()`,
  `occupancy()`. Construible desde lista de celdas.
- `class OutboundProcess`: firma del proceso SimPy (`__init__(env, almacen,
  config)`, metodo generador `run()` que en Fase 0 es un stub que NO hace nada /
  ni se arranca). Logica real = Fase 2.
ASCII-only en prints/logging (Ley #4).

### 0.3 warehouse.py — lectura gateada (patron identico al de congestion)
En `AlmacenMejorado.__init__`, tras el bloque congestion/timewindow (~L238),
anadir:
```
self.outbound_config = configuracion.get('outbound', {'enabled': False})
self.outbound_enabled = bool(self.outbound_config.get('enabled', False))
self.staging_zones = {}      # {staging_id: StagingZone}; se puebla solo si enabled
self.outbound_process = None # se instancia solo si enabled (Fase 2)
if self.outbound_enabled:
    # Fase 0: construir zonas desde data_manager (no arranca camion).
    from .outbound import StagingZone
    zones = self.data_manager.get_outbound_staging_zones() if self.data_manager else {}
    self.staging_zones = {sid: StagingZone(sid, cells) for sid, cells in zones.items()}
    print(f"[OUTBOUND] Fase0 zonas: {{sid: len(z.slots)}}")  # ascii
```
Con `enabled:false`, `staging_zones={}`, `outbound_process=None` => nada cambia.

### 0.4 data_manager.py — accessor aditivo (NO tocar el existente)
Anadir metodo nuevo (no modifica `get_outbound_staging_locations` ni los loaders):
```
def get_outbound_staging_zones(self):
    # Fase 0: deriva zonas desde outbound_staging_locations (1 celda/id hoy).
    # Fase 1: el loader poblara varias celdas por id desde la hoja Excel.
    return {sid: [cell] for sid, cell in self.outbound_staging_locations.items()}
```
Aditivo puro; solo lo llama codigo gateado. Comportamiento existente intacto.

### 0.5 event_generator.py — arranque gateado (no-op en Fase 0)
Tras el arranque del watchdog (~L169), anadir:
```
# INICIATIVA #3 / Fase 0: arranque del proceso outbound (solo si enabled).
# Fase 0 = no se arranca nada (OutboundProcess.run es stub). El gate queda listo.
if getattr(self.almacen, 'outbound_enabled', False) and \
   getattr(self.almacen, 'outbound_process', None) is not None:
    self.env.process(self.almacen.outbound_process.run())
```
Con flag off, la condicion es falsa => no se arranca => byte-identico.

### 0.6 operators.py — punto de injerto gateado (no-op en Fase 0)
NO se toca el bucle de descarga en Fase 0 (riesgo de regresion). El injerto real
(crear Pallet + reservar slot) es Fase 1. Fase 0 deja documentado el lugar:
bucle "V12 GRANULAR DISCHARGE" (~L852-877 Ground; equivalente en Forklift).

### 0.7 Validacion Fase 0
1. Imports OK: `python3 -c "import outbound"` (via sys.path) sin error.
2. Regenerar jsonl con `config_stress_tw_exec.json` (outbound off por default o
   bloque enabled:false) => body md5 == `18502db7de9f33bdccf94db742c45dd8`.
3. Sim termina, 9918 eventos, sim_end_t=268.
4. Backup de archivos vivos -> `_backup_iniciativa3/fase_0/`. Commit local.

---

## CHECKLIST FASE 0  -> COMPLETADA Y VALIDADA
- [x] config.json + config_stress_tw_exec.json: bloque `outbound` (enabled:false)
- [x] src/subsystems/simulation/outbound.py (Pallet, DockSlot, StagingZone, OutboundProcess skeleton)
- [x] warehouse.py: lectura gateada + construccion de zonas (solo si enabled)
- [x] data_manager.py: get_outbound_staging_zones (aditivo)
- [x] event_generator.py: arranque gateado (no-op Fase 0)
- [x] Validacion: imports OK (los 4 archivos compilan con py_compile)
- [x] Validacion: body md5 == baseline (flag off) = `18502db7...` (codigo nuevo EJECUTADO,
      print "[OUTBOUND] desactivado" confirmado en log con bytecode fresco)
- [x] Smoke test enabled:true => construye 7 zonas {1:1..7:1}, termina, md5 == baseline
      (nada consume las zonas aun en F0)
- [x] Backup + commit local Fase 0

## CHECKLIST FASE 1 (siguiente; NO empezar sin terminar F0)
- [ ] Loader: parsear varias celdas por staging_id desde la hoja Excel
- [ ] Pallet persistente al descargar (crea Pallet, ocupa DockSlot)
- [ ] Reserva del slot en ReservationTable (dwell abierto) al PLANIFICAR el retorno
- [ ] Asignacion de slot libre + backpressure (espera reservada) si zona llena
- [ ] Sin camion aun (medir backlog/pico; validar I1=0 con permanencia reservada)
- [ ] Metricas: ocupacion de muelle, backlog, espera por slot
- [ ] Validacion + commit

---

## BITACORA (cronologica, lo mas reciente abajo)
- [INICIO I3] Creados plan (`PLAN_INICIATIVA_3_DESPACHO_OUTBOUND.md`) y vision
  (`VISION_PRODUCTO.md`). Commit `64a4d7f`.
- [BASELINE] Capturado baseline de no-regresion ANTES de tocar codigo:
  body md5 `18502db7de9f33bdccf94db742c45dd8`, 9918 eventos, sim_end_t=268,
  con `config_stress_tw_exec.json`. Generador: `/tmp/gen_jsonl.py`.
- [F0] Detalle de Fase 0 redactado. Implementado: outbound.py (entidades), bloque
  config outbound en config.json + config_stress_tw_exec.json (enabled:false),
  gates en warehouse.py / data_manager.py / event_generator.py.
- [F0 INCIDENTE FUSE - IMPORTANTE PARA RETOMAR] La herramienta Edit (host) dejo
  los 3 archivos editados TRUNCADOS al final en la VISTA del mount Linux (warehouse
  657, data_manager 937, event_generator 364, cortados a media linea) => py_compile
  fallaba. Sintoma enganoso: la 1a "validacion" dio md5==baseline pero porque corrio
  con .pyc CACHEADO (codigo viejo). LECCION/PROTOCOLO para el resto de la iniciativa:
    1) Tras CADA Edit/Write de codigo: `python3 -m py_compile <archivo>` para confirmar
       que NO quedo truncado (el re-Read del host esta cacheado y MIENTE).
    2) Si py_compile falla por truncado: round-trip `mv f f.rt && mv f.rt f` (rename
       puro, no copia bytes) fuerza a FUSE a re-resolver -> vuelve a verse completo.
    3) Invalidar __pycache__ antes de validar (mv de los dirs __pycache__) y correr con
       `PYTHONDONTWRITEBYTECODE=1` para NO ejecutar bytecode viejo.
  Aplicado: round-trip a los 3 -> compilan OK; markers de edit presentes; pycache movido.
- [F0 VALIDADO] Con bytecode fresco: print "[OUTBOUND] desactivado" CONFIRMA que el
  codigo nuevo ejecuta. body md5 = `18502db7de9f33bdccf94db742c45dd8` == baseline
  (flag off). Smoke enabled:true => zonas {1:1..7:1}, termina, md5==baseline. F0 OK.
- [F0 CERRADO] Backup en _backup_iniciativa3/fase_0/ + commit `69b917b`.
- [F1.1 HECHO] Zona de aforo de k celdas. `build_zone_cells` en outbound.py
  (anillos Chebyshev deterministas, banda del muelle primero, excluye anclas y
  celdas ya usadas => zonas SIN solape). warehouse.py expande cada ancla a
  k=zone_capacity_default usando collision_matrix del layout. NO se parsea Excel
  multi-fila (la hoja tiene 1 fila/id); si en el futuro la hoja define varias
  celdas por id, se usan tal cual (rama len(cells)>=k). VALIDADO: OFF byte-identico;
  ON construye 7 zonas de 8, termina, md5==baseline (la descarga aun NO consume las
  zonas, por eso identico). Geometria staging1 = [(3,29),(2,29),(4,29),(2,28),(3,28),
  (4,28),(1,29),(5,29)] todas caminables. PROTOCOLO ANTI-FUSE aplicado (round-trip+
  py_compile tras cada edit; outbound.py y warehouse.py se truncaron y se restauraron).
- [F1.1] Pendiente: commit. Luego F1.2 (pallet persistente + reserva slot + backpressure).
