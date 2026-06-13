# PLAN + BITACORA — FASE 2: PROCESO DE CAMION REAL (despacho outbound)

> Documento VIVO de PLANIFICACION (Ley #1: plan antes que codigo). NO contiene
> codigo definitivo. Requiere OK del Director antes de implementar.
> Rama: `feature/allocation-layer-v12.1`. Convenciones: ASCII.
> Contexto: `PLAN_INICIATIVA_3_DESPACHO_OUTBOUND.md` (spec original, secciones
> 3.4 y Fase 2), `PROGRESO_INICIATIVA_3.md` (estado real al dia).

## 1. OBJETIVO Y PORQUE

Hoy los pallets desaparecen solos a los 10s (`_outbound_scaffold_release`,
proxy temporal). Fase 2 = reemplazarlo por el DESPACHO REAL: un proceso de
camion que llega por politica configurable, retira hasta C pallets, libera los
slots y sus reservas-obstaculo, y emite eventos al jsonl. Esto convierte el
muelle en un sistema con dinamica real (backlog, ocupacion, backpressure) y es
el corazon del producto de la Iniciativa #3.

## 2. ESTADO DE PARTIDA (verificado)

- `OutboundProcess` (outbound.py L213): esqueleto con politica/params leidos
  del config; `run()` stub. `event_generator` YA arranca el proceso si
  `outbound_enabled` y `outbound_process is not None` (hoy None => no-op).
- `_outbound_place_pallet` (operators.py): crea Pallet, ocupa DockSlot, reserva
  la celda como obstaculo (mini-fix: 306/306 ok con `ignore_agents={self.id}`),
  y arranca el SCAFFOLD. **El Pallet NO se registra en ningun lado** (vive en
  el closure del scaffold) -> F2 necesita un registro central.
- Carriles F1.3: si la columna se llena, el gruero hace `break` y deja WOs sin
  depositar (hoy casi no pasa porque el scaffold recicla rapido). Con camion
  real la saturacion SI ocurrira -> hay que definir la espera.
- Config `outbound` (perfil DEMO config.json): `dispatch_policy` "interval",
  `truck_interval` 20.0, `truck_capacity` 8, `loading_time` 2.0, `dwell_scaffold` 10.0.
  Config `outbound` (perfil REAL config_calibrado_v1.json — C4 ACTUALIZADO):
  `truck_interval` 3600 s (1 camion/hora/puerta), `truck_capacity` 26 (trailer 53 ft),
  `loading_time` 90 s/pallet (por pallet; ver decision 3.5a), `dwell_scaffold` 300 s,
  `slot_poll_dt` 1.0 s.
- Telemetria persistida en el timewindow report JSON (outbound_metrics).

## 3. DECISIONES DE DISENO (a aprobar)

### 3.1 Camion ABSTRACTO (MVP, igual que el plan original)
No se mueve por la grilla: consume pallets y libera slots/reservas. El camion
fisico en puerta de muelle es Fase 3. No toca el A* ni la tabla salvo los
`release_agent("PALLET:...")`.

### 3.2 Un solo proceso global, FIFO por antiguedad
Un OutboundProcess que sirve TODAS las zonas: cada llegada retira hasta C
pallets en orden FIFO por `(t_staged, pallet_id)` (determinista). Con el
escenario tipico (distribucion a 1 staging) equivale a camion por staging; el
camion por-staging queda como evolucion (las zonas y el registro ya quedan
preparados). FIFO == "fondo primero" en la geometria v2 (el fondo se llena
primero y esta del lado del muelle), asi que el orden es fisicamente sensato.

### 3.3 El scaffold NO se borra: queda como politica
`dispatch_policy: "scaffold"` = comportamiento F1.3 actual (release a los
`dwell_scaffold` seg). `"interval"` = camion real. Default en config: interval.
Beneficios: rollback de 1 palabra en config.json, y A/B directo para comparar.
(`"batch"` y `"schedule"` del plan original: NO en este pase; el codigo deja el
dispatch por politica preparado.)

### 3.4 Registro central de pallets
`almacen.staged_pallets`: lista (orden de insercion = t_staged) de Pallets en
estado "staged". `place_pallet` registra; el camion saca. Tambien
`almacen.pallets_by_id` si hace falta lookup. Estructuras deterministas (list,
no set).

### 3.5 Ciclo del camion (politica interval)
```
cada truck_interval seg:
  truck_arrived (evento)
  tomar hasta C pallets FIFO de staged_pallets
    (si 0 pallets: truck_departed inmediato, contar truck_idle_arrivals)
  yield timeout(loading_time * n_pallets)   # POR PALLET (ver 3.5a)
  por cada pallet: status=shipped, slot.release(),
    rt.release_agent("PALLET:<id>"), evento pallet_shipped
  truck_departed (evento) + metricas (trucks_dispatched, backlog restante)
```

#### 3.5a Decision: loading_time POR PALLET (no total) — C4
La hoja de investigacion (INVESTIGACION_TIEMPOS_REALES_OPERACION.md sec 3.5)
establece 60-120 s POR PALLET en un montacargas dock-trailer. El plan original
usaba loading_time como TOTAL (2 s para 8 pallets = irreal). Decision:
implementar POR PALLET desde F2.a. En el codigo: `yield timeout(loading_time *
n_pallets_tomados)`. El config ya tiene loading_time=90 en el perfil calibrado.

#### 3.5b Analisis de estabilidad a escala REAL (C4)
Con perfil calibrado (config_calibrado_v1.json):
- Tasa de DESPACHO: C=26 pallets / T=3600 s = 0.0072 pallets/s neto.
  Ciclo real del camion: 3600 s espera + 90*n_tomados carga. Con n=26
  (trailer lleno): ciclo = 3600 + 2340 = 5940 s, tasa = 0.0044 pallets/s.
- Tasa de DEPOSITO con 4 agentes (escenario v2, 150 ordenes, escala real):
  el escenario completo dura un turno parcial (~2-4 h sim). A ~90 lineas/h por
  agente y con la proporcion de ordenes por tipo, la tasa de pallets depositados
  es del orden de 0.003-0.010 pallets/s pico. ESTABLE a escala real.
- El escenario de SATURACION (stress) ahora es T pequeno (ej. T=120 s) o muchos
  agentes (20), no el default. El slot_wait_alert=600 s avisa cuando un gruero
  lleva 10 min esperando slot.
- El VALOR del simulador con escala real: con 4 agentes y 150 ordenes, los pallets
  se acumulan durante ~2 h y el camion llega cada hora con capacidad de vaciar el
  muelle de una vez. Se ve la DINAMICA REAL: pico de ocupacion antes del camion,
  valle despues. Eso es exactamente el fenomeno que el Director quiere mostrar.

Nota: con perfil DEMO (config.json) la dinamica no es comparable (T=20 s, C=8,
loading_time=2 s total), pero sirve para demos rapidas donde la escala no importa.

### 3.6 Columna llena: el gruero ESPERA EN EL CARRIL (no break)
Sustituir el `break` por espera con poll (`slot_poll_dt`) hasta que el camion
libere una celda de SU columna. Es el comportamiento fisico real (la cola se
forma dentro y fuera del muelle) y el forzante que hace VISIBLE el cuello
expedicion vs picking. Anti-deadlock: la espera no toma recursos nuevos (el
carril ya es suyo) y el camion corre en paralelo => siempre progresa. Metrica
nueva: `lane_full_wait_time/events`.

### 3.7 Eventos al jsonl
`truck_arrived`, `truck_departed`, `pallet_shipped` via
`almacen.registrar_evento` (mismo canal que todo). RIESGO a validar: que el
visor web y el replay Pygame IGNOREN tipos de evento desconocidos sin romperse
(chequeo previo en el codigo del viewer ANTES de emitir; si no los toleran,
gate de emision con `outbound.emit_truck_events: false` por default).

### 3.8 Transito por columnas de staging (hallazgo del mini-fix) — F2.d
El planner usa columnas de staging vacias como atajo (causa de los 179 fallos
del hold de descarga y de trafico irreal). Fix propuesto: tratar las celdas de
staging como NO transitables para el A* SALVO para el agente cuyo destino esta
en esa columna (costo infinito condicional o filtro en vecinos). Es cirugia en
el camino delicado (planner Opcion C) -> sub-paso APARTE, con validacion plena
de no-regresion, y SOLO tras F2.a-c estables. Beneficio esperado: holds ~0
fallos, trafico realista bordeando el muelle.

## 4. PLAN DE EJECUCION (sub-pasos; cada uno compila + valida + commit)

### F2.a Registro + camion interval + scaffold como politica  -> [ ]
Archivos: `outbound.py` (OutboundProcess.run real, FIFO, eventos OFF por
default), `warehouse.py` (staged_pallets + instanciar OutboundProcess si
enabled y policy != scaffold), `operators.py` (place_pallet registra pallet;
scaffold SOLO si policy == "scaffold").
Validar: policy=scaffold => comportamiento F1.3 identico; policy=interval =>
termina, trucks_dispatched>0, pallets_shipped==staged (al final backlog 0),
0 fallbacks, determinista (2 corridas), metricas en report JSON.

### F2.b Espera en carril con columna llena  -> [ ]
`operators.py`: break -> espera con poll + metricas lane_full_*.
Validar: escenario saturado (T grande o C chico) => sin deadlock, termina,
esperas medidas; escenario normal => sin cambio.

### F2.c Eventos truck_*/pallet_shipped al jsonl  -> [ ]
Previo: leer el manejo de eventos desconocidos en el visor web y replay_engine.
Si toleran: emitir (flag `emit_truck_events`, default true). Si no: default
false + nota. Validar: replay se ve bien en el navegador con eventos activos.

### F2.d Staging no-transitable para el planner (fidelidad)  -> [ ]
Sub-paso aparte con mini-plan propio (toca pathfinding). Validar: holds fail
~0, 0 fallbacks/cap_hits, I1 no empeora, OFF byte-identico.

### F2.e Cierre  -> [ ]
Docs (PROGRESO + COMO_FUNCIONA seccion 7) + backup _backup_iniciativa3/fase_2/
+ commit. Baseline OFF byte-identico: pendiente de verificar con md5 cuando
vuelva el sandbox (o el Director corre el snippet de hash que le pase).

## 5. RIESGOS Y MITIGACIONES
- **Visor rompe con eventos nuevos** -> chequeo previo + flag de emision (3.7).
- **Saturacion bloquea el fin de la sim** -> la espera en carril progresa
  siempre que el camion corra; test de saturacion explicito (F2.b).
- **Regresion con outbound off** -> todo gateado igual que F0/F1; baseline md5.
- **Determinismo** -> interval fijo, FIFO por (t_staged, id), sin sets.
- **Runner web pierde stdout y falla 1/2 arranques** (hallazgos previos) ->
  validar SIEMPRE leyendo el report JSON de disco, no el log; reintentar runs.

## 6. VALIDACION EMPIRICA PARA EL DIRECTOR (al final)
1. Toggle outbound ON + Run Simulation -> Watch Replay: los pallets se quedan
   y CADA T seg desaparecen hasta C de golpe (el camion se los llevo) — visible
   porque los grueros vuelven a usar esas celdas despues.
2. Report JSON: trucks_dispatched > 0, pallets_shipped == pallets_staged,
   pallet_reserve_fail ausente/0.
3. Con dispatch_policy="scaffold" en config.json: comportamiento de hoy.

## 7. BITACORA DE EJECUCION (lo mas reciente abajo)
- [PLAN REDACTADO] Pendiente OK del Director para F2.a.
- [C4 ACTUALIZADO] Defaults de escala real incorporados al plan (seccion 2 y 3.5):
  truck_capacity 8->26, truck_interval 20->3600, loading_time 2 total->90 s/pallet,
  dwell_scaffold 10->300, slot_poll_dt 0.1->1.0. Decision de diseno formalizada:
  loading_time es POR PALLET desde F2.a (sec 3.5a). Analisis de estabilidad a
  escala real agregado (sec 3.5b): tasa deposito ~0.003-0.010 pallets/s con 4
  agentes, tasa despacho ~0.0044/s ciclo lleno => ESTABLE con perfil calibrado.
  Este plan ya esta listo para implementar F2.a sobre la escala real.
