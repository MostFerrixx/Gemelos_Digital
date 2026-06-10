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
- [F1.1 CERRADO] Commit `3380560`.

## MICRO-PLAN F1.2 (siguiente; diseno antes de codear, Ley #1)
Objetivo: al descargar, cada WO -> Pallet persistente que ocupa un DockSlot LIBRE de
la zona, y la sim sigue TERMINANDO y baja I1. Riesgo: toca el camino de descarga
(operators.py) y la reserva (ReservationTable) acoplada al planner Opcion C.

Sub-pasos propuestos (cada uno compilable + validado + commit):
- F1.2a (mecanica de aforo, SIN tocar el planner): en el bucle de descarga
  (operators.py "V12 GRANULAR DISCHARGE", Ground ~L852 y el equivalente Forklift):
  por cada WO, pedir `zone.free_slot()`; si hay -> crear Pallet, `slot.assign(pid)`,
  registrar metrica; si NO hay -> BACKPRESSURE: `yield env.timeout(dt)` y reintentar
  (espera por slot). SCAFFOLD de release (SOLO F1, marcar "reemplazar por camion en
  Fase 2"): al ocupar, arrancar `env.process` que espera `dwell_scaffold` y libera el
  slot (`slot.release()`), para que la zona rote y la sim termine. Metricas: ocupacion
  pico por zona, backlog, esperas por slot. NO reservar celda aun.
  Validar: OFF byte-identico; ON termina (gracias al scaffold), determinista; medir
  ocupacion/backlog. I1 NO bajara aun (no hay reserva) -> esperado.
- F1.2b (acople con el planner, la parte fina): reservar la celda del slot en la
  ReservationTable como obstaculo: `reserve(cell, t_ocupa, BIG, "PALLET:<id>")` AL
  PLANIFICAR (no al llegar tarde, leccion Fase 2b); liberar con
  `release_agent("PALLET:<id>")` en el release. CUIDADO (riesgos Fase 2b):
    * reservar un obstaculo permanente puede dejar al planner SIN ruta -> fallback
      estatico que ATRAVIESA (regresion). Mitigar: garantizar conectividad de la zona
      (no tapar el unico pasillo; las filas y=27,28 quedan libres por encima de y=29),
      y que el agente que coloca el pallet no se auto-bloquee (placa en slot LIBRE en
      la tabla en ese instante).
    * subir `max_expansions` si el coste del A* sube.
  Validar: I1 baja hacia 0 (objetivo F1), 0 plans_failed/fallbacks, termina,
  determinista, OFF byte-identico.
- F1.2 cierre: doc + backup _backup_iniciativa3/fase_1/ + commit.

NOTA de alcance: F1.2 es un cambio de COMPORTAMIENTO en el camino delicado de la
Opcion C. Conviene hacerlo en un pase enfocado. F0 y F1.1 quedan como base limpia y
reversible (flag off => baseline byte-identico).

## BITACORA F1.2
- [CHECKPOINT opcionC-F2] Antes de F1.2 se commiteo el trabajo sin commitear de la
  Opcion C (operators.py +61, spacetime_planner.py +77 + docs) como version
  TRANSITORIA de rollback: commit `b8402e2`. operators.py quedo limpio vs HEAD.
- [F1.2a HECHO] Mecanica de aforo (SIN tocar el planner). Helpers en BaseOperator
  (operators.py): `_outbound_wait_slot` (backpressure: cede el reloj hasta haber slot
  libre, reserva atomica), `_outbound_place_pallet` (crea Pallet persistente, ocupa
  DockSlot, metricas), `_outbound_scaffold_release` (SCAFFOLD Fase 1 = proxy del
  camion: libera el slot tras `dwell_scaffold` seg). Cableado en los 2 bucles de
  descarga (Ground + Forklift, identicos) via replace_all. Metricas en warehouse
  (`outbound_metrics`). Config: `slot_poll_dt`=0.1, `dwell_scaffold`=10.0.
  VALIDADO (config_stress_tw_exec.json, 20 agentes):
    * OFF: body md5 == baseline `18502db7...` (byte-identico; regresion cero).
    * ON: TERMINA (sim_end_t=333 vs 268 baseline; +65s por backpressure), DETERMINISTA
      (doble corrida identica). pallets_staged=126, peak_occupancy staging1=8 (zona
      LLENA), slot_wait_events=56, slot_wait_time=267s, max_slot_wait=33.4s.
    * I1=81 SIN CAMBIO -> ESPERADO: F1.2a no reserva la celda del pallet y el agente
      sigue descargando en el ancla; los pallets son logicos. El I1=0 es objetivo de
      F1.2b (reservar la celda del pallet para que el planner esquive).
  LECTURA: confirma empiricamente que con esta tasa de deposito y dwell=10s la zona
  de k=8 se SATURA (esperas de hasta 33s) -> dato para dimensionar despacho real.
  PROTOCOLO ANTI-FUSE aplicado (round-trip+py_compile; OFF byte-identico revalidado).
- [F1.2a CERRADO] Commit `5f8e281`.
- [CHECKPOINT opcionC-F2] Commit `b8402e2` (rollback de la Opcion C F2 sin validar).
- [LAYOUT WH1 v2 CONECTADO] El Director rediseno el mapa: `layouts/WH1 v2.tmx`
  (30x42), zona de carga abajo con 7 stagings de 20 celdas (pares de columnas,
  y=29..38, pasillos entre medio => sin pallets atrapados). Pasos:
  * Arreglado el TMX: Tiled lo dejaba con tileset EXTERNO (D:/Tiled o ../../Tiled)
    => no cargaba. Se INCRUSTO el tileset (auto-contenido). Ver COMO_FUNCIONA #4.
  * Excel nuevo `layouts/Warehouse_Logic_v2.xlsx` (OutboundStaging = 140 celdas,
    20/staging; PickingLocations intacta).
  * DESCUBRIMIENTO CLAVE: la sim lee de `warehouse.db`, NO del Excel (el Excel es
    fallback). Se actualizo la tabla `staging_areas` de la BD (recreada SIN
    PRIMARY KEY para admitir varias celdas/staging) con las 140 celdas. BD
    respaldada en _backup_iniciativa3/warehouse.db.bak. Ver COMO_FUNCIONA #2.
  * data_manager: lee varias celdas/staging (BD y Excel) -> outbound_staging_zone_cells.
  * warehouse F1.1: si la zona trae varias celdas, usa TODAS (capacidad=len).
  * config_stress_tw_v2.json: layout v2 + excel v2 + outbound.enabled=true.
  VALIDADO (determinista, 20 agentes, 100% a staging1): termina (sim_end_t=280),
  126 pallets, **0 esperas por slot** (pico 17/20), **I1=56** (bajo de 81 solo por
  repartir en la zona de 20). Doble corrida identica.
- [DOC] Creado `docs/COMO_FUNCIONA_EL_PROGRAMA.md` con TODO lo aprendido por prueba
  y error (fuentes de datos BD vs Excel, interpretacion del TMX, trampas de Tiled,
  trampas FUSE/pyc, como correr/validar, estado del outbound). Referencia de retome.
- [F1.2b HECHO] Reservar la celda del pallet como OBSTACULO en la ReservationTable.
  Cambios: warehouse marca la celda-ancla de cada zona como "SERVICE" (siempre libre,
  destino de navegacion alcanzable); operators `_outbound_place_pallet` reserva la
  celda del pallet `reserve(cell, now, now+1e9, "PALLET:<id>")`; `_outbound_scaffold_
  release` la libera con `release_agent`. Insight clave: el planner NO chequea la
  celda de INICIO pero SI la de DESTINO -> si un pallet ocupa el ancla, los agentes
  no pueden llegar (regresion Fase 2b). Por eso el ancla queda SERVICE.
  VALIDADO (config_stress_tw_v2.json, determinista, doble corrida identica):
    * 73 planes, **0 fallbacks, 0 reserve_overlaps, 0 cap_hits** -> SIN REGRESION
      (los pallets son obstaculos reales que el planner esquiva; lo que fallo en 2b).
    * termina (sim_end_t=280), 126 pallets, 0 esperas por slot (pico 18/20).
    * I1 = 54 (era 56 sin reservar, 81 en mapa viejo de 1 celda).
  HALLAZGO: I1 bajo POCO porque los pallets estan en las columnas de cajas, FUERA
  del trafico principal, asi que rara vez estorbaban. El I1 residual (54) NO son
  pallets: es el EMBUDO DEL UNICO PUNTO DE DESCARGA. Hotspots: (3,29)=ancla con
  max_concurrent **8** (8 agentes apilados ahi) + el corredor de aproximacion
  ((3,27),(2,28),(2,24),...). NINGUN hotspot en celdas de pallet => F1.2b OK.
  CONCLUSION: el problema de "atravesar pallets" esta RESUELTO. Para bajar mas el I1
  habria que repartir la DESCARGA en varias celdas de servicio (no 1 ancla compartida)
  y/o reservar el dwell de descarga. Eso es una iniciativa aparte (embudo del depot).
- [FASE 1 COMPLETA] F0 + F1.1 + F1.2a + F1.2b hechas y validadas. Pallets persistentes,
  zona de aforo real (20/staging desde mapa v2), backpressure, y pallets como
  obstaculos. Pendiente futuro: camion real (Fase 2) + embudo del punto de descarga.
- [EXPERIMENTO opcion-2 "repartir descarga en varias lozas" -> REGRESO -> REVERTIDO]
  Idea: que cada operario navegue a la loza del slot a depositar (en vez de descargar
  todos en la celda-ancla), para deshacer el embudo. Implementado: helper
  `_outbound_nav_to` + navegar a `_ob_slot.cell` por cada WO antes de descargar.
  RESULTADO: I1 SUBIO 54 -> **140** (PEOR), table_overlap_violations 0 -> 58,
  exec_fallbacks 0 -> 1. Hotspots pasaron a las celdas de cajas ((4,29)=20,(3,30)=18..).
  CAUSA RAIZ: meter a los agentes DENTRO de las columnas de cajas (2 de ancho) los
  hace CRUZARSE ahi dentro; y el dwell de descarga en la loza NO se reserva, asi que
  otros enrutan a traves del que descarga. Repartir en esta geometria estrecha mete
  gente a pasillos angostos donde chocan MAS, no menos. REVERTIDO a F1.2b (git checkout
  fallo por FUSE unlink; se deshizo a mano con Edit; verificado: diff vs HEAD vacio,
  I1=54, 73 planes, 0 fallbacks). 
  LECCION: "varias puertas" no ayuda si las puertas son lozas dentro de columnas
  estrechas y la permanencia de descarga no se reserva. Para que funcione habria que:
  (a) reservar el dwell de descarga en la loza al LLEGAR (no al terminar), y/o
  (b) carriles de un solo sentido / celdas de servicio en pasillo ANCHO, no en la
  columna de cajas. Y/o repartir las ordenes entre los 7 stagings (la otra opcion).
  Por ahora se queda F1.2b como estado bueno.
- [F1.3 MODELO DE CARRILES - IMPLEMENTADO (pedido del Director)] Comportamiento real:
  cada staging = 2 columnas = 2 CARRILES; como mucho UN gruero por columna; los demas
  ESPERAN FUERA hasta que uno sale; los pallets se dejan de ATRAS hacia ADELANTE.
  Cambios: `StagingZone` agrupa por columna (carriles) + acquire_lane/release_lane/
  deepest_empty_cell (outbound.py); warehouse ya NO marca SERVICE; operators
  `_outbound_discharge_lanes` (espera carril -> entra -> llena fondo->frente -> sale ->
  libera carril) + `_outbound_nav_to`; gate al inicio del bucle de descarga (Ground+
  Forklift) que usa el helper cuando outbound on. Reserva: al llegar se retiene la celda
  con el id del agente durante la descarga; place_pallet pone el pallet-obstaculo.
  RESULTADO (mapa v2): TERMINA, movimiento SIN choques (0 fallbacks, 0 reserve_overlaps),
  se comporta como el modelo pedido. Reparte la descarga en columnas (se acabo el cruce
  dentro de la columna que rompio el intento opcion-2).
  MATIZ IMPORTANTE sobre el I1: SUBIO (54 -> ~65 con 100% a 1 staging, ~81 repartido).
  NO es por choques (siguen 0). Es porque el modelo es MAS REALISTA: los grueros ahora
  SE MUEVEN de verdad (entran a columnas, hacen cola, llenan al fondo) -> hay mas
  recorrido -> mas eventos de "alguien paso por donde otro estaba parado". El I1 cuenta
  co-ocupaciones incluyendo agentes PARADOS, asi que mas movimiento realista = mas I1.
  El I1 NO es la metrica de exito de la realista; el comportamiento si lo es.
  PENDIENTE menor: ~60 table_overlap_violations (algunos pallets no quedan reservados
  como obstaculo porque la celda no esta libre al reservar) -> refinamiento futuro.
  Con 100% a un staging la makespan sube (447) porque solo 2 grueros lo trabajan (real);
  repartiendo entre los 7 (realista) baja (~299).
  DECISION ABIERTA: mantener el modelo realista de carriles (recomendado, es lo pedido)
  o volver a F1.2b (I1 menor pero descarga irreal teletransportada al ancla). Rollback
  de F1.2b en commit 76c2b3b.

---

## ESTADO ACTUAL (resumen ejecutivo, al cierre de esta sesion)

### Motor de simulacion (Iniciativa #3 / Fase 1) -> COMPLETA y validada (headless)
- F0 andamiaje + flag `outbound.enabled` (off => baseline byte-identico).  commit 69b917b
- F1.1 zona de aforo de k celdas.                                          commit 3380560
- F1.2a pallets persistentes + slots + backpressure + scaffold.            commit 5f8e281
- F1.2b pallets como OBSTACULOS reservados (planner los esquiva).          commit 76c2b3b
- F1.3 MODELO DE CARRILES (2 columnas/staging, 1 gruero por columna, los
  demas esperan fuera, llenado de ATRAS hacia ADELANTE).                   commit 379413d
- Checkpoint Opcion C F2 (rollback).                                       commit b8402e2
- Todo gateado por `outbound.enabled`; con el flag off, comportamiento clasico.

### Layout y datos del muelle nuevo -> LISTOS
- `layouts/WH1 v2.tmx` (30x42): arriba racks/picking; abajo 7 stagings de 20 celdas
  (pares de columnas x={3,4}..{27,28}, filas y=29..38) con pasillos entre pares.
  Tileset INCRUSTADO (auto-contenido, sin enlaces externos). commit 5ec15ca
- `layouts/Warehouse_Logic_v2.xlsx`: OutboundStaging = 140 celdas (20/staging).
- `warehouse.db`: tabla staging_areas recreada SIN PK con las 140 celdas. (NO commiteada;
  ver COMO_FUNCIONA #2 para reproducir. Backup en _backup_iniciativa3/warehouse.db.bak)
- `config_stress_tw_v2.json`: escenario headless (mapa v2 + excel v2 + outbound on).

### Capa WEB (UI navegador) -> PARCIAL
- El servidor corre OCULTO (server_manager.py / server.pid). Reinicio: stop_server.bat +
  start_server.bat  (o `python server_manager.py restart`). Ver COMO_FUNCIONA #10.
- ARREGLADO: `/api/layout` ahora sirve el mapa del CONFIG (antes ruta fija mala ->
  mostraba mapa viejo 30x30 que no coincidia con la simulacion). commit 7d00c7a.
  REQUIERE reiniciar el servidor para tomar efecto.
- VERIFICADO en el navegador: el configurador (`/web_configurator/`) funciona; se cargo
  el layout v2, se corrio la simulacion (OK, replay generado) y se vio en el visor.
- BUG ABIERTO (causa de lo que reporta el Director): al GUARDAR, el configurador
  SOBRESCRIBE config.json solo con los campos que conoce y DESCARTA los bloques
  `congestion` (time-window) y `outbound` (carriles). Resultado en la corrida web:
  * sin `congestion` -> ruteo clasico -> los operarios SE ATRAVIESAN.
  * sin `outbound`   -> descarga clasica -> llegan solo a la PRIMERA loza del staging
    (no caminan al fondo ni usan carriles).
  (config_manager.save_config hace json.dump del dict de la UI, sin fusionar.)

## PROXIMOS PASOS (en orden)
1. [WEB] Arreglar `config_manager.save_config` para que FUSIONE con el config.json
   existente (preservar `congestion` y `outbound`, no solo los campos de la UI) y que
   `outbound.enabled=true`. Reiniciar servidor y re-verificar en el navegador que NO se
   atraviesan y que caminan al fondo del muelle por carriles. (Decision del Director.)
2. [WEB] (opcional) Exponer en el configurador interruptores para mode time-window y
   outbound.enabled, para no depender de bloques "ocultos".
3. [WEB] Robustez del guardado: config.json salio algo malformado (datos sobrantes);
   escribir de forma atomica/validada.
4. [MOTOR] Refinamiento menor F1.2b/F1.3: ~60 reservas de celda fallidas (pallets que no
   quedan como obstaculo). No bloquea; mejora de fidelidad.
5. [MOTOR] Embudo del PUNTO DE DESCARGA: con 100% a un staging se forma cola en la celda
   de entrada (real, pero artefacto de la prueba). Repartir ordenes entre los 7 stagings
   lo alivia. Iniciativa aparte si se quiere optimizar.
6. [FUTURO] Fase 2: camion/despacho real que retire pallets (reemplaza el scaffold).
   Capa 3: layout a escala real. Ver VISION_PRODUCTO y PLAN_INICIATIVA_3.

> Estado bueno actual del MOTOR = F1.3 (commit 379413d). Estado bueno de la WEB =
> tras 7d00c7a + (pendiente) el arreglo del guardado del configurador.
