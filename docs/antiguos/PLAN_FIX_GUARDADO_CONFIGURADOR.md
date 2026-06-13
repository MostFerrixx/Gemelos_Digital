# PLAN + BITACORA — FIX GUARDADO DEL CONFIGURADOR WEB (paso #1 de PROGRESO_INICIATIVA_3)

> Documento VIVO. Se actualiza INMEDIATAMENTE tras cada sub-paso con resultados,
> para retomar exacto si se corta la sesion. Convenciones del repo: ASCII.
> Rama: `feature/allocation-layer-v12.1`. HEAD al iniciar: `a6143f1`.
> Contexto general: `docs/PROGRESO_INICIATIVA_3.md` (estado motor/web) y
> `docs/COMO_FUNCIONA_EL_PROGRAMA.md` (#5 protocolo FUSE, #10 capa web).

## 1. PROBLEMA (causa raiz, verificada)

`web_prototype/config_manager.py::save_config` (L58-93) hace
`json.dump(config_de_la_UI)` directo sobre `config.json`:
- SOBRESCRIBE el archivo solo con las claves que la UI conoce.
- La UI NO envia `congestion` (time-window) ni `outbound` (carriles) => se
  PIERDEN en cada guardado (y el guardado es automatico al dar Run Simulation).
- Consecuencia en corridas web: operarios se ATRAVIESAN (ruteo clasico) y
  descargan en la PRIMERA loza (sin modelo de carriles F1.3).
- VERIFICADO en vivo: el `config.json` actual YA NO tiene esos bloques.
  `config.json.backup` (creado por save_config antes del guardado destructivo)
  SI los tiene. `config_stress_tw_v2.json` tiene los bloques validados en F1.3.
- Ademas el guardado NO es atomico: `open('w')+json.dump` sobre FUSE explica el
  config malformado "con datos sobrantes" visto antes (proximo paso #3 del
  progreso; se integra a ESTE fix).

## 2. DECISIONES DE DISENO (analisis critico ya aprobado por el Director)

- **Merge superficial en save_config**: cargar config existente del disco y
  `merged.update(config_ui)`. Las claves que la UI envia ganan completas; las
  que NO envia (congestion, outbound, futuras) se PRESERVAN. Contrato de la
  capa de persistencia: "nunca borres lo que no manejas". Generico, sin
  whitelist hardcodeada.
- **Fallback ante config corrupto**: si `config.json` no parsea -> intentar
  `config.json.backup`; si tampoco -> guardar solo lo de la UI con
  `[CONFIG_MANAGER WARN]`. El guardado NUNCA debe fallar por un existente roto.
- **Escritura atomica**: escribir a `config.json.tmp` + `os.replace`. Parte
  integral del fix (no opcional): evita archivos a medias sobre FUSE.
- **Reparacion one-shot de config.json**: re-inyectar `congestion` y `outbound`
  con `enabled:true`, tomando como fuente `config.json.backup` (copia fiel),
  contrastada contra `config_stress_tw_v2.json` (valores validados F1.3).
- **Descartado**: arreglar el frontend (fragil, por-cliente) y defaults del
  motor (romperia la garantia flag-off=baseline byte-identico).
- **Deuda conocida (NO se resuelve aqui)**: `warehouse.db` es global; si en la
  UI se elige el mapa VIEJO `WH1.tmx`, las zonas de staging vienen igual de la
  BD con la geometria v2 (140 celdas, fuera del mundo 30x30). Ya estaba roto;
  el merge lo hace persistente. Anotar en PROGRESO_INICIATIVA_3.
- **Fix de fondo pendiente (paso #2 del progreso)**: exponer toggles de
  congestion/outbound en la UI. El merge es el contrato base; no lo sustituye.

## 3. PLAN DE EJECUCION (checklist vivo; [ ]=pendiente [x]=hecho con resultado en bitacora)

### P0. Revisar y mover docs obsoletos a `archived/`  -> [x] HECHO
Criterio: docs que describen problemas YA resueltos o artefactos eliminados
(enganan al retomar). Candidatos confirmados (headers revisados):
- `HANDOFF.md` e `INSTRUCCIONES.md` (raiz): auto-marcados "historico V11".
- `DOCUMENTO_IMPLEMENTACION_DOBLE_BARRIDO.md` (raiz): implementacion 2025-10
  ya integrada (DispatcherV11).
- `docs/INSTRUCCIONES_LAYOUTS.md`: dice "PyTMX no puede leer TMX de Tiled",
  FALSO hoy (resuelto incrustando tileset; COMO_FUNCIONA #4).
- `docs/TUTORIAL_EXPLICACION.md` y `docs/TILES_REFERENCE.md`: documentan
  `warehouse_tileset` (BORRADO del working dir).
- `docs/DYNAMIC_LAYOUTS_USER_GUIDE.md`: flujo Tiled viejo, superado por
  COMO_FUNCIONA #4.
SE QUEDAN: PLAN_INICIATIVA_1/2/3, PROGRESO_*, ANALISIS_*, INVESTIGACION_*,
PRUEBAS_GUI, INSTRUCCIONES_LAYOUT_PERSONALIZADO (tileset custom = el vivo),
VISION_PRODUCTO, COMO_FUNCIONA, AUDITORIA, README, CLAUDE.md.
NOTA: `docs/PROGRESO_OPCION_C.md` tiene +87 lineas SIN COMMITEAR -> NO tocar.
Mover con `mv` (git lo detecta como rename) y verificar `git status`.

### P1. Fix `save_config` (web_prototype/config_manager.py)  -> [x] HECHO
Reemplazar el cuerpo de guardado por:
1. Validar (igual que hoy).
2. Cargar existente: try config.json -> except try config.json.backup ->
   except {} con WARN. (Helper privado `_load_existing_for_merge`.)
3. `merged = existente; merged.update(config_ui)`.
4. Backup del existente (igual que hoy, ANTES de escribir).
5. Escritura atomica: `config.json.tmp` (json.dump) + `os.replace(tmp, real)`.
6. Log ASCII: `[CONFIG_MANAGER] Merge preservo bloques: <claves preservadas>`.
PROTOCOLO ANTI-FUSE tras editar: `python3 -m py_compile`; si trunca ->
round-trip `mv f f.rt && mv f.rt f` y recompilar.

### P2. Test del fix en sandbox (/tmp, sin tocar el repo)  -> [x] HECHO (4/4 PASS)
Copiar config_manager.py + un config.json con bloques a /tmp/test_cfg/.
Simular POST de la UI (dict SIN congestion/outbound, con claves UI completas):
- a) save_config -> exito; leer config.json: bloques PRESERVADOS + claves UI
  actualizadas.
- b) config.json corrupto (basura) + .backup valido -> guarda y preserva desde
  backup.
- c) config.json corrupto + sin backup -> guarda solo UI con WARN (no crashea).
- d) verificar que NO queda config.json.tmp residual y que el JSON es valido.

### P3. Reparacion one-shot del config.json REAL  -> [x] HECHO (con desviacion, ver bitacora)
1. Contrastar bloques congestion/outbound de config.json.backup vs
   config_stress_tw_v2.json; si difieren, manda el backup y se reporta.
2. Re-inyectar ambos bloques en config.json con outbound.enabled=true y
   congestion.enabled=true (mode timewindow). Escritura atomica via python.
3. Verificar: JSON valido + bloques presentes + resto de claves UI intactas.

### P4. Actualizar PROGRESO_INICIATIVA_3.md  -> [x] HECHO
- Marcar paso #1 como implementado (pendiente verificacion navegador Director).
- Integrar paso #3 (atomicidad) como hecho dentro de este fix.
- Anotar deuda "mapa viejo + BD v2".
- Referenciar este doc.

### P5. Entrega al Director (validacion empirica)  -> [x] VERIFICADO EN NAVEGADOR (por Cerebellum via Chrome)
1. Reiniciar servidor: `stop_server.bat` + `start_server.bat` (el server tiene
   config_manager en memoria; sin reinicio NO toma el fix).
2. Abrir `/web_configurator/`, cambiar cualquier campo, Run Simulation.
3. Chequeo: `python -c "import json;c=json.load(open('config.json'));print('congestion' in c, 'outbound' in c, c.get('outbound',{}).get('enabled'))"`
   -> debe imprimir `True True True` DESPUES de guardar desde la UI.
4. Watch Replay: los operarios NO se atraviesan; los grueros entran al staging
   por carriles (1 por columna, demas esperan fuera) y llenan de ATRAS hacia
   ADELANTE.
5. Si OK -> commit sugerido:
   `git add web_prototype/config_manager.py config.json docs/ HANDOFF.md INSTRUCCIONES.md DOCUMENTO_IMPLEMENTACION_DOBLE_BARRIDO.md archived/ && git commit -m "fix(web): save_config fusiona+escritura atomica (preserva congestion/outbound); repara config.json; archiva docs obsoletos"`
   (git en FUSE tira warnings "unable to unlink": inofensivos; locks zombi ->
   mv, ver COMO_FUNCIONA #5.)

## 4. BITACORA DE EJECUCION (lo mas reciente abajo)
- [INICIO] Plan redactado y aprobado en conversacion (analisis critico incluido:
  merge=contrato de persistencia, fallback corrupto, atomicidad integrada,
  fuente reparacion=backup, deuda BD-global anotada). Ejecucion NO iniciada aun.
- [P0 HECHO] Movidos a archived/ (7): HANDOFF.md, INSTRUCCIONES.md,
  DOCUMENTO_IMPLEMENTACION_DOBLE_BARRIDO.md, docs/{INSTRUCCIONES_LAYOUTS,
  TUTORIAL_EXPLICACION, TILES_REFERENCE, DYNAMIC_LAYOUTS_USER_GUIDE}.md.
  git status: viejas rutas en D, nuevas en ?? (rename se consolida al add).
  PROGRESO_OPCION_C.md NO tocado. OJO: git aviso "unable to unlink index.lock"
  -> puede haber lock zombi al commitear; limpiar con mv (COMO_FUNCIONA #5).
- [P1 HECHO] save_config: merge superficial (existente + UI encima) + log de
  claves preservadas + backup previo + escritura atomica (tmp + os.replace).
  Helper nuevo `_load_existing_for_merge` (fallback config.json -> .backup ->
  {} con WARN; nunca lanza). FUSE SI trunco el archivo (IndentationError L511);
  round-trip mv aplicado -> py_compile OK.
- [P2 HECHO] Test sandbox /tmp/test_cfg: 4/4 PASS. (a) merge preserva
  congestion/outbound y actualiza claves UI (300->555); (b) config corrupto +
  backup valido -> preserva desde backup; (c) corrupto sin backup -> guarda
  solo UI con WARN, no crashea; (d) sin .tmp residual, backup creado.
  Logs confirman mensajes esperados ("Merge preserved keys...", WARNs).
- [P3 HECHO - DESVIACION DEL PLAN, IMPORTANTE] El contraste revelo que
  config.json.backup NO era copia fiel del estado validado: tenia los bloques
  en estado APAGADO/shadow (congestion mode:"off", shadow:true,
  allow_diagonal:true, staggered:false; outbound enabled:false) -- es de una
  epoca anterior a la validacion F1.3. Usar el backup (regla original del plan)
  habria dejado el time-window APAGADO aunque enabled=true (mode manda).
  DECISION: fuente = `config_stress_tw_v2.json` VERBATIM (valores con los que
  se valido F1.3: mode timewindow, shadow off, diag off, staggered on;
  outbound enabled true). Inyectado atomico. VERIFICADO con asserts: bloques
  identicos al stress v2, JSON valido, 24 claves, claves UI intactas,
  layout=WH1 v2.tmx + excel v2.
  LECCION: "el backup es copia fiel" era falso; el backup rota en cada guardado
  y puede contener CUALQUIER estado historico. Para reparar, la referencia
  buena es el config de validacion, no el backup.
- [P4 HECHO] PROGRESO_INICIATIVA_3.md actualizado: paso 1 marcado implementado
  (pendiente verificacion Director), paso 3 absorbido (atomicidad), deuda 3b
  BD-global anotada, entrada en bitacora + referencia a este doc.
- [PENDIENTE - SIGUIENTE ACCION SI SE CORTA LA SESION] P5: el Director reinicia
  el servidor y verifica en navegador; si OK, ejecutar el commit sugerido en P5.
  No hay NADA mas de codigo pendiente de este fix.
- [P5 INCIDENTE REINICIO] Al reiniciar, start_server.bat aviso "puerto 8000 ya
  en uso". CAUSA: el branch con-PID-file de stop_server.bat hace
  `taskkill /PID x /F` SIN `/T` (no mata el arbol); el hijo que escucha en 8000
  sobrevive. WORKAROUND dado al Director: `del server.pid` + stop_server.bat
  (branch por-puerto, que SI usa /T) + start_server.bat.
  MEJORA FUTURA (no urgente): anadir /T al taskkill del branch con-PID-file.
- [P5 FIX stop_server.bat APLICADO] Parcheado: taskkill por PID-file ahora usa
  /F /T (arbol completo) + barrido de seguridad post-kill de cualquier proceso
  residual en :8000. (El zombi ACTUAL igual requiere el workaround manual del
  Director una vez: del server.pid + stop + start.)
- [P5 HERRAMIENTA] Creado `reiniciar_servidor.bat` (raiz): reinicio forzado en
  un clic = borra server.pid + mata arbol de todo proceso en :8000 + verifica
  puerto libre + llama start_server.bat. Pensado para el Director (yo no puedo
  ejecutar procesos en su Windows; mi shell es sandbox Linux).
- [P5 ZOMBI RESUELTO] El kill del PID en :8000 (9012) SI funciono; el [ERROR]
  del script era una CARRERA (verificaba el puerto antes de que Windows soltara
  el socket). Confirmado por el Director: tasklist/taskkill ya no encuentran
  el 9012. Script corregido: verificacion con 5 reintentos x 2s.
  SIGUIENTE: Director arranca con start_server.bat / reiniciar_servidor.bat y
  abre Chrome para que yo verifique en navegador.
- [P5 CORRECCION - SOCKET FANTASMA] El puerto :8000 sigue LISTENING a nombre del
  PID 9012 que YA NO EXISTE (tasklist/taskkill/Stop-Process: not found). No es
  proceso vivo: es socket huerfano retenido por WinNAT (Hyper-V/WSL/Docker).
  REMEDIO indicado al Director: `net stop winnat && net start winnat` (admin) y
  re-chequear netstat; si persiste -> REINICIAR la PC (garantizado). Luego
  reiniciar_servidor.bat / start_server.bat.

## 4b. RESULTADO DE LA VERIFICACION P5 (en navegador, sesion 2026-06-09)
Camino previo: reinicio de servidor fallo por (1) stop_server.bat sin /T (parcheado),
(2) socket FANTASMA en :8000 con PID muerto (WinNAT) -> resuelto REINICIANDO LA PC.
Sandbox Linux de Cerebellum se cayo (sin disco) a mitad de sesion -> se siguio con
herramientas de archivo directas (sin bash); pendiente de recuperarse en la proxima.
Verificacion via Claude-in-Chrome contra localhost:8000:
1. [OK] GUARDADO UI PRESERVA BLOQUES: click "Aplicar Configuracion" y el
   auto-save de "Run Simulation" -> config.json conserva congestion (timewindow)
   y outbound (enabled:true). Verificado leyendo el archivo tras cada guardado.
2. [OK] MOTOR WEB CON TIME-WINDOW: reporte del runner: 483 tramos planificados,
   0 fallidos, 0 cap_hits, esperas/plan 0.0. (La etiqueta "(SOMBRA, Fase 1)" del
   reporte es un print FIJO en event_generator.py L284, NO indica modo shadow.)
   "Solapes en reservas: 180" = table_overlap_violations, el refinamiento
   PENDIENTE conocido de F1.3 (pallets no reservados como obstaculo), no choques.
3. [OK] MODELO DE CARRILES VISIBLE EN REPLAY (mapa v2, 100% a staging 1):
   - dos grueros DENTRO de las columnas, UNO POR CARRIL, a profundidad (llegan
     al fondo; antes del fix descargaban todos en la primera loza).
   - agentes en espera quedan FUERA de la zona (arriba de las columnas).
   - nunca 2 agentes en el mismo carril en ningun frame muestreado.
   - replay completo: 311/311 WOs, termina (25:03), sin congelarse.
4. [INCIDENTE MENOR] La 1a pestana de Chrome se congelo (renderer) tras el primer
   click; el SERVIDOR siguio vivo (la API respondia). Se siguio en pestana nueva.
FALTA (opcional): confirmacion visual del propio Director + commit (ver P5.5).

## 5. ROLLBACK
- Codigo: `git checkout -- web_prototype/config_manager.py` (si FUSE bloquea
  checkout, deshacer a mano con Edit; ya paso antes, ver PROGRESO_I3).
- config.json: restaurar desde `config.json.backup`.
- Docs archivados: `mv archived/<doc> <ubicacion original>`.
