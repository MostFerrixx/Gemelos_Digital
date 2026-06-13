# ANALISIS DE IMPACTO — CALIBRACION DE TIEMPOS REALES (doc de trabajo)

> Documento de ANALISIS + PLAN DE TRABAJO. Es el punto de partida del
> workstream "tiempos a escala real". Basado en
> `INVESTIGACION_TIEMPOS_REALES_OPERACION.md` (benchmarks y tabla de valores).
> Rama: `feature/allocation-layer-v12.1`. Convenciones: ASCII.
> Regla rectora: la calibracion debe ser un CAMBIO DE CONFIG, no de logica.
> Donde hoy hay constantes hardcodeadas, primero se llevan a config con
> DEFAULT = VALOR ACTUAL (cero cambio de comportamiento), y el perfil
> calibrado es un config nuevo. Asi el baseline byte-identico SOBREVIVE.

---

## 1. EL CAMBIO EN UNA FRASE

Pasar de la escala actual (~10x mas rapida que la realidad; celda sin tamano
definido) a: **1 celda = 1 m, 1 s sim = 1 s real**, con velocidades y tiempos
de operacion tomados de benchmarks de la industria.

## 2. MAPA COMPLETO DE LO AFECTADO

### 2.1 MOTOR — operators.py (impacto DIRECTO, requiere codigo)
- `TIME_PER_CELL` hardcodeado en 3 sitios: L763 (Ground), L1169 (Forklift),
  L632 (`_outbound_nav_to`, ademas pasa `time_per_cell=0.1` literal a
  `_recorrer_tramo`). -> Llevar a config (`tiempos.time_per_cell_ground` o
  derivar de `cell_size_m` / velocidad). Default = 0.1 (actual).
- `default_speed` (multiplicador de TIEMPO): Ground 1.0, Forklift 0.8 con
  COMENTARIO INVERTIDO (L1165 dice "mas lenta"; 0.8 = mas rapido). Calibrado:
  Forklift 0.5 (2x peaton). -> A config por tipo de agente; corregir comentario.
- `picking_duration = self.discharge_time` (L912 Ground, L1327 Forklift):
  picking y descarga COMPARTEN constante. -> Nueva clave
  `tiempo_picking_por_linea` (default = discharge_time para no cambiar nada;
  calibrado = 15 s).
- `LIFT_TIME = 2.0` (L1170, Forklift). -> A config (`tiempo_horquilla`,
  default 2.0; calibrado 8.0).
- `agent_types[].discharge_time` (por agente, viene de la UI de flota):
  calibrado Ground 12 s / Forklift 15 s. Es config puro, sin codigo.

### 2.2 NUCLEO TIME-WINDOW / CONGESTION (impacto INDIRECTO, el MAS DELICADO)
Los parametros del bloque `congestion` estan en SEGUNDOS y fueron afinados
para la escala vieja (celda = 0.1 s). Con celda = 1.0 s cambian de significado
relativo (verificado: se usan en operators, reservation_table, warehouse,
spacetime_planner, congestion_manager):
- `wait_timeout: 0.5` -> hoy = 5 celdas de viaje; en escala nueva = media
  celda. Revisar (probable ~5.0).
- `backoff_base/jitter: 0.1` -> idem (~1.0).
- `watchdog_window: 5.0` -> hoy 50 celdas; nuevo ~50.0 si se quiere la misma
  semantica.
- `spawn_offset: 0.3`, `timewindow.dt_wait: 0.1` -> dt_wait define la
  GRANULARIDAD de esperas del A*: con celdas de 1.0 s, dt_wait 0.1 multiplica
  x10 los pasos de espera explorables -> el costo del A* puede subir
  (max_expansions 20000 puede quedarse corto; vigilar `cap_hits`). Candidato:
  dt_wait 0.5-1.0 en el perfil calibrado.
- `outbound.slot_poll_dt: 0.1` y el poll de carril: granularidad de espera del
  muelle; subir a ~1.0 en perfil calibrado (menos eventos basura).
REGLA: NO se cambia logica; los valores van en el PERFIL calibrado y se
REVALIDA empiricamente (0 fallbacks, 0 overlaps del planner, terminacion,
determinismo). Este es el riesgo #1 del workstream.

### 2.3 OUTBOUND / FASE 2 (impacto en DEFAULTS del plan)
- `dwell_scaffold 10` -> en el perfil calibrado pierde sentido (el scaffold es
  proxy; si se usa, ~300-600 s para que la dinamica de aforo sea visible).
- PLAN_FASE2_CAMION_REAL.md queda DESACTUALIZADO en defaults: truck_capacity
  8 -> 26; loading_time 2 s total -> ~90 s POR PALLET (decision de diseno F2:
  por-pallet, no total); truck_interval 20 -> ~3600 s. La matematica de
  estabilidad (C/T vs tasa de deposito) cambia de escala pero el analisis es
  el mismo. -> Actualizar el plan ANTES de implementar F2.a.
- El test de saturacion de F2.b pasa de segundos a decenas de minutos
  simulados (sigue siendo instantaneo en headless).

### 2.4 GENERACION HEADLESS (impacto OPERATIVO menor)
- `event_generator.ejecutar` corre `env.run(until=now+1.0)` en bucle: la
  duracion simulada sube ~10x (de ~300 s a ~3000-10000 s) -> ~10x mas
  iteraciones del bucle Python. La generacion seguira siendo rapida (eventos
  discretos), pero medir; si molesta, subir el paso del bucle (no urgente).
- Watchdog de congestion (L166): ventanas en segundos -> revisar con 2.2.

### 2.5 REPLAY / VISORES (impacto UX)
- Replays de horas simuladas: el visor web tiene velocidades 1/2/5/10x ->
  anadir 30x/60x (trivial, select de index.html del visor). Pygame viewer:
  revisar sus controles de velocidad equivalentes.
- Formato de tiempo "HH:MM:SS" del dashboard: verificar que muestre bien >1 h.
- La densidad de eventos por segundo simulado BAJA (mismos eventos repartidos
  en mas tiempo): scrubbing e interpolacion del visor sin cambios.

### 2.6 ANALYTICS / KPIs (impacto POSITIVO, es el objetivo)
- analytics_engine: KPIs en segundos pasan a magnitudes reales (turnos, no
  minutos). Sin cambio estructural. El reporte Excel y el heatmap absorben.
- NUEVO test de realismo (del doc de investigacion 3.6): proporcion
  Tiempo_Viaje / Tiempo_Picking del reporte debe quedar ~50-60% viaje para un
  picker. Se convierte en CRITERIO DE ACEPTACION de la calibracion.
- Throughput/hora y lineas/hora pasan a ser comparables con benchmarks (80-150
  lineas/h case picking): segundo criterio de aceptacion.

### 2.7 OPTIMIZADOR (Optuna) — impacto LATENTE
`run_optimization.py` / `src/tools/optimizer.py` optimizan sobre makespan de
la escala vieja; sus espacios de busqueda/presupuestos asumen corridas cortas.
Con tiempos reales las corridas simuladas son mas largas (mismo costo CPU
aprox) pero los VALORES objetivos cambian de orden de magnitud. No bloquea
(el optimizador es herramienta aparte); marcar para revalidar cuando se use.

### 2.8 BASELINE DE NO-REGRESION (decision de estrategia)
- El baseline md5 `18502db7...` se definio con la escala vieja. ESTRATEGIA:
  (a) la config-ificacion (fase C1) usa defaults = valores actuales -> los
  configs existentes producen byte-identico -> EL BASELINE VIEJO SIGUE
  VALIDO para detectar regresiones de logica;
  (b) el perfil calibrado es un config NUEVO (`config_real_v1.json` o bloque
  `tiempos` en config.json) -> capturar un BASELINE NUEVO (md5 + metricas:
  makespan, I1, lineas/h) tras validarlo, y registrarlo en PROGRESO.
- Verificacion md5: sin sandbox, el Director corre el snippet de hash (se le
  entregara); o esperar a que vuelva el sandbox.

### 2.9 CONFIGURADOR WEB (impacto en UI, fase posterior del workstream)
- Claves nuevas (`cell_size_m`, bloque `tiempos`): el merge del guardado YA
  las preserva aunque la UI no las conozca (paso 1 de esta iniciativa). Sin
  riesgo de perdida.
- Exponer despues una seccion "Tiempos de operacion" (patron del paso 2:
  bloque completo desde currentConfig + defaults validados). Incluir el
  preset "modo demo" (valores rapidos actuales) vs "real".
- `validate_config` del backend: validar tipos del bloque nuevo (patron ya
  establecido).
- fleet-manager: defaults de discharge_time por tipo de agente (12/15) al
  crear flota nueva.
- web_dashboard/ (huerfana, no tocar) y dashboards muertos: sin impacto.

### 2.10 LO QUE NO SE AFECTA (verificado)
- `warehouse.db` / Excel: no almacenan tiempos de operacion (solo geometria,
  SKUs, stock). Cero impacto.
- Layouts TMX: la escala es una CONVENCION (cell_size_m en config); el mapa
  no cambia.
- Allocation Layer V12.1 (stock/backorder): logica de cantidades, no de
  tiempos. Cero impacto directo.
- jsonl/replay format: los eventos llevan timestamps; el formato no cambia.

## 3. PLAN DE TRABAJO PROPUESTO (fases; cada una con OK previo, Ley #1)

### C1. Config-ificacion NEUTRA (sin cambio de comportamiento)  -> [IMPLEMENTADA, pendiente validacion numerica]
Llevar a config: time_per_cell (x3 sitios), velocidad por tipo de agente,
tiempo_picking_por_linea, tiempo_horquilla, (poll dts). DEFAULTS = valores
actuales. Anadir `cell_size_m` (documental). Corregir comentario Forklift.
VALIDAR: config viejo => byte-identico al baseline `18502db7` (md5) y
solapes/fallbacks identicos en el escenario v2. ESTE PASO NO CAMBIA NADA
OBSERVABLE: solo habilita la calibracion como config puro.

### C2. PERFIL CALIBRADO + revalidacion del nucleo  -> [ ]
Crear el perfil con la tabla de la investigacion (seccion 4): celda 1 m,
Ground 1.0 s/celda, Forklift 0.5, picking 15 s, horquilla 8 s, descarga 12/15,
congestion re-escalada (wait_timeout ~5, backoff ~1, watchdog ~50, dt_wait
0.5-1.0, slot_poll ~1.0). Correr el escenario v2 determinista y VALIDAR:
termina, 0 fallbacks/cap_hits (subir max_expansions si hace falta), 0 solapes
de planner, determinista (2 corridas), y CRITERIOS DE REALISMO: ~50-60% del
tiempo del picker en viaje + lineas/hora dentro de 60-150. Capturar BASELINE
NUEVO (md5 + KPIs) y registrarlo.

### C3. Experiencia de uso  -> [ ]
Velocidades 30x/60x en el visor web (y revisar Pygame); verificar formato de
horas del dashboard; preset "demo" vs "real" disponibles en configuraciones.

### C4. Actualizar PLAN_FASE2 con defaults reales  -> [ ]
truck_capacity 26, loading_time por-pallet ~90 s, interval ~3600 s, dwell del
test de saturacion, y recien entonces arrancar F2.a sobre la escala real.

### C5. (Posterior) UI de tiempos en el configurador  -> [ ]
Seccion "Tiempos de operacion" con el patron del paso 2.

## 4. RIESGOS PRINCIPALES (resumen)
1. **Re-escalado del bloque congestion (2.2)**: el mas fino; mitigado por C1
   neutro + revalidacion empirica completa en C2 con metricas del planner.
2. **Costo del A\* por granularidad dt_wait**: vigilar cap_hits/avg_plan_ms;
   perilla max_expansions disponible.
3. **Baseline**: estrategia de doble baseline (2.8) lo resuelve.
4. **Runner web pierde stdout / falla 1 de 2 arranques**: validar SIEMPRE por
   el report JSON de disco; reintentar corridas (lecciones de la sesion
   anterior, ya documentadas en PROGRESO).
5. **Sandbox caido**: sin md5/py_compile propios; los hashes los corre el
   Director con snippet, py_compile se difiere o se hace al volver el sandbox.

## 5. CRITERIOS DE ACEPTACION DEL WORKSTREAM (medibles)
1. C1: md5 == baseline viejo con config viejo.
2. C2: corrida calibrada termina, determinista, 0 fallbacks, 0 cap_hits,
   0 solapes de planner; picker ~50-60% viaje; 60-150 lineas/h; makespan del
   escenario v2 en horas (orden de magnitud de un turno parcial).
3. C3: replay navegable comodo a 30x/60x.
4. PROGRESO_INICIATIVA_3 actualizado con el baseline nuevo y este doc.

## 6. BITACORA DEL WORKSTREAM (lo mas reciente abajo)
- [ANALISIS REDACTADO] Pendiente OK del Director para arrancar C1.
- [C1 IMPLEMENTADA] OK del Director recibido. Config-ificacion neutra completa:
  bloque `tiempos` en config.json + BaseOperator lee el bloque + 5 sitios de
  constantes hardcodeadas reemplazados en operators.py (Time_per_cell x3,
  LIFT_TIME, picking_duration x2, default_speed x2). Comentario invertido
  del Forklift (L1165) CORREGIDO. Compilacion py_compile OK. Protocolo anti-FUSE
  aplicado (round-trip mv; archivo 1705 lineas completo).
  PENDIENTE: correr config_stress_tw_v2.json y verificar metricas identicas al
  commit e57aa06 (pallet_reserve_ok=306, fail=0, table_overlap ~179, tramos ~480,
  exec_fallbacks=0). Luego commitear y marcar C1 cerrada.
