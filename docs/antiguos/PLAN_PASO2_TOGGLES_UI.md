# PLAN (PREP) — PASO 2: TOGGLES DE CONGESTION/OUTBOUND EN EL CONFIGURADOR WEB

> Documento de PLANIFICACION (Ley #1). NO implementado. Redactado tras cerrar el
> paso #1 (fix del guardado, ver PLAN_FIX_GUARDADO_CONFIGURADOR.md) para que el
> paso 2 pueda arrancar sin re-descubrir nada. Convenciones: ASCII.
> Estado del repo al redactar: rama feature/allocation-layer-v12.1, fix paso #1
> implementado y verificado en navegador (pendiente commit del Director).

## 1. OBJETIVO
Que el usuario pueda encender/apagar desde la UI web:
- `congestion` (ruteo time-window; hoy bloque "oculto" en config.json), y
- `outbound.enabled` (modelo de carriles I3/F1.3),
sin depender de editar config.json a mano. El merge del paso #1 ya PROTEGE los
bloques; este paso los hace VISIBLES y controlables.

## 2. MAPA DEL CODIGO (verificado por lectura, 2026-06-09)

### Frontend (web_prototype/static/web_configurator/)
- `index.html`: las 5 pestanas (Carga de Trabajo / Estrategias / Flota / Layout
  y Datos / Outbound Staging) + clase del Simulation Runner. El auto-save de
  "Run Simulation" esta en `startSimulation()` (~L616): llama
  `window.configurator.serializeConfig()` y hace POST a `/api/configurator/config`.
- `app.js`: clase principal del configurador.
  * `loadConfiguration()` (~L404): GET `/api/configurator/config` y guarda el
    config COMPLETO en `this.currentConfig` (~L412) -> INCLUYE congestion y
    outbound aunque la UI no los muestre. Luego `loadConfigToForm()` (~L437).
  * `serializeConfig()` (~L488): construye el dict SOLO con los campos del
    formulario (por eso la UI nunca envia los bloques). AQUI se cablea el paso 2.
- `config-storage.js`: presets. POST `/api/configurator/config` tambien en ~L306
  (boton "Aplicar Configuracion"); presets en `/api/configurator/configurations`.
- `fleet-manager.js`: serializa agent_types (no se toca en paso 2).

### Backend (web_prototype/)
- `server.py` ~L253: `POST /api/configurator/config` -> `config_manager.save_config`.
- `config_manager.py::save_config`: MERGE SUPERFICIAL (paso #1) + escritura
  atomica. `validate_config` NO valida congestion/outbound (hoy pasan tal cual).
- Cambios en server.py/config_manager.py requieren REINICIO del servidor;
  cambios en static/ (JS/HTML) solo requieren recargar el navegador con
  Ctrl+F5 (cache). Reinicio: reiniciar_servidor.bat.

### Schema de los bloques (referencia canonica = config_stress_tw_v2.json)
- `congestion`: enabled(bool), mode("off"|"timewindow"|...), + ~10 parametros
  finos + sub-bloque `timewindow{shadow, clearance, dt_wait, max_expansions,
  plan_horizon, allow_diagonal}`. Valores validados F1.3: enabled=true,
  mode=timewindow, shadow=false, allow_diagonal=false, staggered_start=true.
- `outbound`: enabled(bool) + 8 parametros (truck_*, zone_capacity_default,
  slot_wait_alert, slot_poll_dt, dwell_scaffold).
- OJO semantica: `congestion.enabled=true` con `mode="off"` NO activa nada
  (el mode manda). El toggle de UI debe manejar el PAR (enabled+mode), no solo
  enabled. (Esto ya nos mordio: el .backup tenia enabled apagado + mode off.)

## 3. LA TRAMPA CRITICA: MERGE SUPERFICIAL + BLOQUES PARCIALES
El merge del paso #1 es por CLAVE DE PRIMER NIVEL (`dict.update`). Consecuencia:
**si la UI empieza a enviar `outbound` o `congestion`, lo que envie REEMPLAZA el
bloque ENTERO**. Si enviara solo `{"outbound": {"enabled": true}}` se perderian
truck_interval, dwell_scaffold, etc. REGLA INNEGOCIABLE para el paso 2:

> La UI debe enviar el bloque COMPLETO: partir de `this.currentConfig.<bloque>`
> (que ya tiene todo, viene del GET), mutar SOLO los campos que la UI controla
> (enabled / mode), e incluir el objeto completo en serializeConfig().

Alternativa descartable: hacer el merge RECURSIVO en el backend. Mas robusto en
teoria, pero cambia la semantica para TODAS las claves (p.ej. un dict que la UI
quiere reemplazar entero, como distribucion_tipos, ya no se reemplazaria) ->
riesgo de bugs sutiles. Recomendacion: NO tocar el merge; aplicar la regla del
bloque completo en el frontend. Si algun dia se quiere merge profundo, hacerlo
con lista explicita de claves deep-merge.

## 4. DISENO PROPUESTO (a aprobar por el Director antes de codear)
1. UI: en la pestana "Estrategias" (la mas afin), una seccion "Motor avanzado":
   - Toggle "Ruteo anti-colision (time-window)" -> controla el PAR
     congestion.enabled + congestion.mode ("timewindow"/"off"). Tooltip breve.
   - Toggle "Subsistema outbound (carriles de carga)" -> outbound.enabled.
   - (Opcional, fase posterior) inputs numericos para dwell_scaffold y
     zone_capacity_default. NO exponer los parametros finos del timewindow.
2. `loadConfigToForm()`: setear los toggles desde config.congestion/.outbound
   (default visual: ON si mode==timewindow / enabled==true).
3. `serializeConfig()`: incluir `congestion` y `outbound` COMPLETOS (regla #3),
   partiendo de `this.currentConfig` y aplicando el estado de los toggles.
   Si `this.currentConfig` no trae los bloques (config viejo), usar los DEFAULTS
   validados (copiar de config_stress_tw_v2.json, hardcode JS o endpoint).
4. Backend opcional (recomendado, barato): en `validate_config`, si vienen los
   bloques, validar tipos basicos (enabled bool, mode string en {off,timewindow}).
5. Validacion empirica (Ley #2):
   a) GET config -> toggles reflejan estado real.
   b) Apagar outbound + guardar -> config.json: outbound.enabled=false y el
      RESTO del bloque intacto (truck_interval etc. presentes).
   c) Encender ambos + Run Simulation -> replay con carriles (como P5 del paso 1).
   d) Cargar un PRESET VIEJO (sin bloques) + aplicar -> los bloques del
      config.json NO se pierden (el merge los preserva) y los toggles muestran
      el estado resultante tras recargar.
6. Riesgo colateral documentado: presets guardados ANTES del paso 1 no tienen
   los bloques; al cargarlos la UI debe tratar la ausencia como "usar defaults
   validados", no como "apagar".

## 5. CHECKLIST DE EJECUCION (cuando el Director de el OK)
- [x] Aprobar diseno (seccion 4) con el Director. (OK en conversacion)
- [x] index.html: card "Motor Avanzado" en tab Estrategias (toggle-timewindow,
      toggle-outbound, con help-text).
- [x] app.js: loadConfigToForm setea toggles (ausencia de bloque = ON/defaults);
      getDefaultAdvancedBlocks() (valores F1.3 de config_stress_tw_v2);
      serializeConfig envia bloques COMPLETOS desde this.currentConfig (o
      defaults), con REFUERZO: al encender time-window fuerza timewindow.shadow
      =false (un config viejo en variante shadow dejaria el toggle sin efecto).
      Verificado que los 3 caminos de guardado usan serializeConfig (auto-save
      de Run Simulation en index.html L616, Aplicar Configuracion en
      config-storage.js useConfiguration, presets).
- [x] config_manager.validate_config: validacion basica (enabled bool, mode en
      off/timewindow). OJO: NO compilada con py_compile (sandbox Linux caido,
      sin disco); revisada por lectura (sintaxis OK, archivo integro, 571
      lineas). Activa recien al REINICIAR el servidor.
- [x] Probar a)-d) en navegador -> RESULTADOS:
      a) PASS: card "Motor Avanzado" renderiza; ambos toggles ON reflejando el
         config.json real (ambos bloques enabled).
      b) PASS: outbound OFF + guardado (auto-save de Run Simulation) ->
         config.json: outbound.enabled=false y el RESTO del bloque INTACTO
         (truck_interval, dwell_scaffold, etc.); congestion intacta. Nota: el
         round-trip JS normaliza floats x.0 a enteros (30.0->30); equivalente
         para json.load de Python.
      c) PASS: outbound ON de nuevo + Run Simulation -> enabled=true, bloque
         completo, sim corre normal (9958 eventos; el conteo difiere del run
         con outbound off, consistente con el cambio de comportamiento).
      d) NO EJECUTADO (sin preset viejo a mano); cubierto POR DISENO: preset
         sin bloques -> loadConfigToForm pone toggles ON (ausencia=defaults) y
         serializeConfig envia defaults validados; el merge ademas preserva.
      El servidor arranco bien tras el reinicio del Director -> la validacion
      nueva de config_manager.py carga sin errores (riesgo py_compile CERRADO).
- [x] Actualizar PROGRESO_INICIATIVA_3.md + este doc con resultados.
- [ ] Commit (Director).
- [x] confirm() de "Aplicar Configuracion" ELIMINADO (OK del Director).
      Guardado directo + notificacion. VERIFICADO en navegador: el click ya no
      congela la pestana y el guardado preserva los bloques. Los OTROS 5
      confirm() del frontend (borrar preset, flota por defecto, cancelar sim,
      restart server x2) SE CONSERVAN a proposito: protegen acciones
      destructivas reales.

## 6. BITACORA DE EJECUCION
- [HALLAZGO UX/AUTOMATIZACION] El boton "Aplicar Configuracion" usa `confirm()`
  NATIVO (config-storage.js useConfiguration ~L296). Un dialogo nativo BLOQUEA
  el renderer entero: congela la pestana para CDP/automatizacion y explica los
  congelamientos vistos en P5 del paso 1 y aqui. MEJORA PROPUESTA (pendiente OK):
  reemplazar confirm() por guardado directo + notificacion (el guardado ya es
  seguro: hay backup + escritura atomica + merge). El auto-save de Run
  Simulation NO tiene confirm y es el camino que mas se usa.
- [2.1-2.3 HECHOS] HTML + JS + validacion backend implementados (detalle arriba).
  Pendiente verificacion en navegador: servidor caido al intentar probar.
- [RIESGO ABIERTO] config_manager.py editado SIN py_compile (sandbox caido).
  Si el servidor no arranca tras el reinicio, sospechar de ese archivo
  (rollback: git checkout -- web_prototype/config_manager.py y reiniciar).
