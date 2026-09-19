# BACKLOG — Gemelo Digital de Almacen
# Solo lo PENDIENTE. Lo cerrado vive en docs/CHANGELOG.md (no se repite aca).

Actualizado: 2026-09-18 · Responsable: Cerebellum

*(BK-15 CERRADO el 2026-09-18 -> CHANGELOG.)*

*(BK-05, BK-11 y el canonico migrado a `agent_types` explicito: CERRADOS el
2026-09-08 -> CHANGELOG. BK-06 CERRADA el 2026-09-07; de ella salieron BK-07,
BK-08 y BK-09, abiertos abajo. INIT-7 INBOUND completa F0-F5 el 2026-07-10;
INIT-8 TIEMPOS completa F1-F4 el 2026-07-11 con los 4 hallazgos AUD8-1..4
aplicados el 2026-07-12 -> todo en CHANGELOG.)*

## Indice (de un vistazo)

| Item | Estado | Prioridad | Esfuerzo | Bloqueo |
|------|--------|-----------|----------|---------|
| BK-07 — areas mixtas (varios tipos de equipo por area) | ABIERTO (2026-07-25) | Media | Medio | Confirmar con el cliente si existen areas mixtas |
| BK-08 — confirmar work_area_equipment con el almacen real | ABIERTO (2026-07-25) | **Alta** (supuesto activo) | Trivial (config) | Lectura del almacen real (Director/cliente) |
| BK-09 — flota 2+2 sub-dimensionada (hallazgo de negocio) | ABIERTO (2026-07-25) | Media | Trivial (config) | Decision de negocio del Director |
| BK-10 — el boton "Restart" responde success pero NO reinicia el servidor | ABIERTO (2026-09-07) | Baja | ~30 min | Ninguno |
| BK-24 — la estrategia "Cercania" casi no se distingue de "cualquier tarea" | ABIERTO (2026-09-19) | Media (diseno) | A definir | Decision de diseno (QA H-13) |
| BK-23 — el despacho manda un segundo equipo a una ubicacion ocupada | ABIERTO (2026-09-18) | Media (realismo/eficiencia) | A definir | Ninguno (sale de BK-15) |
| BK-13 — KPI "Tareas" del visor es un numero fabricado (x3) | ABIERTO (2026-09-18) | Media | Chico | Ninguno (QA H-02) |
| BK-14 — una corrida cancelada deja una carpeta a medias | ABIERTO (2026-09-18) | Baja | Chico | Ninguno (QA H-03) |
| BK-16 — el servidor del cliente se reinicia solo y cancela simulaciones | ABIERTO (2026-09-18) | Media | Chico | Ligado a BK-10 (Restart) (QA H-06) |
| BK-17 — mensajes de validacion en ingles | ABIERTO (2026-09-18) | Baja | Chico | Ninguno (QA H-08) |
| BK-18 — ruta absoluta del archivo de ordenes | ABIERTO (2026-09-18) | Baja | Chico | Ninguno (QA H-09) |
| BK-19 — con pocas tareas un solo operario se lleva todo el trabajo | ABIERTO (2026-09-18) | Media (realismo) | A definir | Decision de diseno del Director (QA H-10) |
| BK-20 — el fill rate ignora las lineas rechazadas | ABIERTO (2026-09-18) | Media (realismo) | Chico | Ninguno (QA H-11) |
| BK-21 — la vista previa de ordenes ignora la politica de cumplimiento | ABIERTO (2026-09-18) | Baja | Chico | Ninguno (QA H-12) |
| BK-22 — configuraciones del motor sin control en la web | ABIERTO (2026-09-18) | Media (configurabilidad) | Variable | Algunas estan planificadas (INIT-11 F10) |
| INIT-10 — modelo de almacen propio (reemplaza a Tiled como herramienta principal) | ANALIZADO (2026-09-16) | Alta (cimiento de automatismos y mezaninas) | Alto, por etapas | Plan detallado de la etapa 2 + OK del Director |
| **INIT-11 — Task Path: outbound en varios pasos (6 pilares)** | **PLAN v2 PROPUESTO (2026-09-16)** | **Alta (prioridad actual del Director)** | 2,5-3,5 semanas, 11 fases | OK del plan v2 (`docs/PLAN_INIT11_TASK_PATH.md`) |
| INIT-12 — Reposicion (replenishment) como tipo de tarea | IDEA (2026-09-16) | Media | No estimado | Despues de INIT-11 (usa perfiles y equipos) |
| BK-02 — FIFO Estricto en UI | EN REPENSAR | Baja | ~15 min | Diseno pendiente del Director |
| INIT-3 v3 — capacidades por agente en el optimizador | DIFERIDO | Baja | Medio | Ninguno, listo para tomar |
| INIT-6 Opcion C — clustering geografico de destinos | DIFERIDO | Baja | Alto (no estimado) | Requiere datos reales de geolocalizacion de clientes |
| Distribucion real de `outbound_staging_distribution` en config canonico | PENDIENTE DECISION | -- | Trivial (config) | Decision de negocio del Director, no un bug |

---

## BK-07 — areas mixtas (varios tipos de equipo por area)

**Hallazgo 2026-07-25 (BK-06 F1).** Hoy `work_area_equipment` es
`Dict[str, str]`: **un solo tipo de equipo por area**. Si en la operacion real
un area la atienden AMBOS tipos (p. ej. un rack bajo que puede trabajar tanto
un terrestre como un montacargas), el modelo actual no lo puede expresar: hay
que elegir uno y el otro queda excluido.

Propuesta robusta (no implementada): admitir `Dict[str, str | List[str]]` —
retrocompatible, un string sigue significando "solo ese tipo". La capacidad de
dimensionado del area ya esta preparada: `core.fleet.capacidades_por_area` toma
el **minimo** de los tipos compatibles, que es exactamente lo que corresponde
en un area mixta (toda WO debe caber en el equipo mas chico que pueda tomarla).
Habria que tocar: `work_areas.effective_work_area_priorities` (aceptar lista),
el validador web, `fleet-manager.js` y la UI del tab Flota.

Bloqueo: confirmar con el cliente si existen areas mixtas (ver BK-08). No
meterlo en BK-06 (decision del Director).

---

## BK-08 — confirmar `work_area_equipment` con el almacen real

**Supuesto activo, no verificado (2026-07-25).** Todo BK-06 asume que
`Area_High` y `Area_Special` son 100% de montacargas y `Area_Ground` 100%
terrestre, tal como dice el canonico. El Director no tiene todavia la lectura
del almacen real.

Impacto si el supuesto es falso: los numeros de BK-06 (makespan, reparto de
carga) cambian. **No requiere codigo**: se corrige editando el mapa en el tab
Flota — salvo que existan areas mixtas, que necesitan BK-07.

Accion: confirmar con el cliente que equipo atiende cada area fisicamente.

---

## BK-09 — la flota 2+2 esta sub-dimensionada (hallazgo de negocio)

**Medido en BK-06 F4 (2026-07-25), con seed 42 y el resto de la config igual.**
Variando SOLO `num_montacargas` sobre el modelo ya corregido:

| Flota | Makespan | vs baseline historico (7440 s) |
|---|---|---|
| 2+2 (canonico) | 8783 s | +18,1% |
| 2+3 | 6042 s | **-18,8%** |
| 2+4 | 4844 s | **-34,9%** |
| 2+5 | 4966 s | -33,3% (peor que 2+4: congestion) |

Con un solo montacargas mas, el modelo realista ya supera el baseline
historico; el optimo esta en 2+4. Es una decision de negocio del Director
(comprar/asignar equipos), no un bug. Cambiar el canonico rompe el baseline
intencionalmente. Insumo natural para el optimizador (INIT-3).

---

## INIT-10 — Modelo de almacen propio (Tiled deja de ser la herramienta principal)

**Analizado el 2026-09-16. Analisis completo, con fuentes: `docs/ANALISIS_LAYOUTS.md`.**
Anotado para implementar mas adelante (decision del Director).

**Por que.** El `.tmx` de Tiled (editor de videojuegos) aporta grilla,
transitabilidad y el dibujo del visor, pero:
- el almacen se describe DOS veces (las 360 ubicaciones estan en el mapa Y en el
  Excel; las del mapa solo se imprimen). Hoy coinciden 360/360, pero nada lo
  garantiza;
- crear un almacen es pintar celda por celda y despues cuadrar el Excel a mano;
- no tiene escala real ni conceptos de almacen;
- `docs/INSTRUCCIONES_LAYOUT_PERSONALIZADO.md` esta desactualizada (dice
  `picking`, el motor busca `picking_location`).

**Horizonte que lo vuelve necesario.** El Director quiere modelar a mediano
plazo mezaninas, cintas transportadoras, sorters, OSR y GTP. Nada de eso entra
en una grilla de baldosas (direccion, conexiones, varias salidas, pisos). Los
simuladores profesionales (AnyLogic, FlexSim) y el estandar LIF (VDMA, JSON en
metros, grafo de nodos/aristas/estaciones, multinivel) usan un modelo POR CAPAS.

**Decision de fondo:** disenar primero el MODELO DE DATOS del almacen (niveles,
almacenamiento, zonas, equipos, conexiones, enlaces entre niveles), aunque hoy
solo se implementen racks y pasillos. Alinear la parte de vehiculos con LIF.
No hace falta cambiar de lenguaje ni de motor (SimPy alcanza; 3D seria JS).

**Etapas:**
1. Validar mapa contra Excel al aplicar + corregir la guia (medio dia).
2. Disenar el modelo de datos y que el motor lo lea; Tiled pasa a importador de
   los 8 layouts existentes. **Es el cimiento.**
3. Editor web: generador de pasillos por parametros + pintura + colocar objetos.
4. Cintas transportadoras (base de sorters, GTP y OSR).
5. Sorters; despues OSR y GTP, cada uno como iniciativa propia.
6. Mezaninas: el ruteo hoy es de UN solo plano (celdas `(x, y)` en pathfinder y
   reservation_table); hay que extenderlo a `(nivel, x, y)` con conectores.
- A futuro: importar planos DXF (`ezdxf`).

**Advertencia:** GTP y OSR invierten el modelo actual (el producto va hacia la
persona). Tratarlos como cambio de paradigma, no como una funcionalidad mas.

**Siguiente paso cuando se retome:** plan detallado de la etapa 2 para aprobar.

---

## BK-10 — el boton "Restart" responde success pero NO reinicia el servidor

**Hallazgo colateral al arreglar BK-05 (2026-09-07).** `POST /api/system/restart`
devuelve `{"success": true, "message": "Server restart triggered. Reloading..."}`
pero el proceso sigue siendo el mismo (verificado por PID antes y despues: el
puerto 8000 lo seguia sirviendo el mismo `python.exe`, con el mismo
`StartTime`). Consecuencia practica: un cambio en el codigo del backend NO se
aplica aunque el usuario apriete "Restart"; hay que matar el proceso y volver a
levantarlo a mano.

Es engañoso justamente por el `success`: promete algo que no ocurrio (contra el
principio rector #3, hacer visible lo invisible). Arreglar el reinicio real, o
—si el reinicio en caliente no es viable— que la respuesta diga la verdad y la
UI indique que hay que relanzar el servidor manualmente.

Ver `web_prototype/routers/system.py`.

---

## Hallazgos del plan de QA de la configuracion web (2026-09-18)

Salieron de probar cada control de la web contra el simulador y el visor
(`docs/PLAN_QA_CONFIGURACION_WEB.md`, donde esta la evidencia completa de cada
uno; el codigo `H-xx` es el del plan). Los errores que se corrigieron en el
momento (H-01 y H-07) estan en el plan, no aca.

### BK-23 — el despacho manda un segundo equipo a una ubicacion ocupada

Salio al corregir BK-15. Con pocas ubicaciones distintas (ej. 100% extra
grande: 3 SKUs), el despacho le asigna a un montacargas tareas en el mismo
hueco del rack donde otro ya esta trabajando. Antes los dos trabajaban a la
vez en la misma celda (imposible); con BK-15 corregido, el segundo espera a
que el primero termine: la corrida pasa de 37.354 s a 57.168 s (+53%). En un
almacen real el segundo equipo recibiria otra tarea. El despacho no mira si la
ubicacion de la tarea esta ocupada o reservada por otro agente.

### BK-24 — la estrategia "Cercania" casi no se distingue de "cualquier tarea" (QA H-13)

Medido en el bloque 2 del QA. La estrategia funciona como esta programada (0
violaciones del radio en 128 recorridos), pero en la operacion modelada casi
no tiene efecto: (1) el radio por defecto (100 celdas) es mayor que cualquier
distancia de este mapa (~42 como maximo), asi que no filtra nada; (2) cada
recorrido termina en la zona de descarga, entonces la "cercania" se mide
siempre desde ahi: con radio 5, 61 de 64 recorridos no encontraron nada cerca
y cayeron al almacen completo. Ademas, segun el codigo
(`dispatcher._estrategia_cercania`), filtra por equipo compatible pero NO por
prioridad de area, a diferencia de Plan y Optimizacion Global (efecto no
verificado todavia). El radio se mide en linea recta, no por camino.

### BK-13 — el KPI "Tareas" del visor es un numero fabricado (QA H-02)

El panel del visor muestra "Tareas" = tareas completadas x 3. Es un valor fijo
heredado de la version de escritorio ("cada WO tiene 3 tareas"), que no mide
nada real: con 256 tareas completadas muestra 768. Esta en
`web_prototype/routers/replay.py` (`tareas_completadas = wo_completed * 3`).
Un usuario lo puede tomar como un dato del simulador.

### BK-14 — una corrida cancelada deja una carpeta a medias (QA H-03)

Si una simulacion se corta (se cierra la conexion, se reinicia el servidor),
queda una carpeta `output/simulation_*` con solo el Excel, sin el `.jsonl` ni
el resto de los archivos. No se distingue de una corrida valida a simple vista
y el visor no la puede abrir.

### BK-16 — el servidor del cliente se reinicia solo y cancela simulaciones (QA H-06)

`start_server.bat` lanza `web_prototype/server.py`, que corre uvicorn con
recarga automatica (`reload=True`) vigilando TODO el proyecto. Cualquier
cambio en un archivo `.py` (por ejemplo, actualizar el programa con git
mientras corre una simulacion) reinicia el servidor y cancela la corrida en
curso. Paso dos veces durante el QA. El boton **Restart** de la web depende de
ese mecanismo (toca `server.py` para provocar la recarga), por eso esta ligado
a BK-10. Para el QA se usa un servidor sin recarga (`web-qa` en
`.claude/launch.json`).

### BK-17 — mensajes de validacion en ingles (QA H-08)

La interfaz esta en espanol, pero los errores que devuelve el servidor al
validar salen en ingles (ej. "Distribution percentages must sum to 100%
(current: 90%)"). Vienen de `web_prototype/config_manager.validate_config`.

### BK-18 — la ruta del archivo de ordenes se guarda absoluta (QA H-09)

Al subir un archivo de ordenes, la configuracion guarda la ruta completa del
servidor (`D:\...\uploads\orders_x.json`). Un preset o un `config.json` con
modo determinista deja de funcionar si el proyecto se mueve de carpeta o de
maquina. La ruta la devuelve `/api/upload-orders`.

### BK-19 — con pocas tareas un solo operario se lleva todo el trabajo (QA H-10)

Con pocas tareas (10 a 34 en las pruebas), el primer operario de cada tipo que
pide trabajo arma un recorrido con todo lo que puede cargar y el otro queda
ocioso toda la corrida (QA-1.7: 700 s). Pasa con "Ejecucion de Plan" y el tope
de tareas por recorrido. En un almacen real el trabajo se repartiria. Es un
tema de realismo del despacho, no de configuracion.

### BK-20 — el fill rate ignora las lineas rechazadas (QA H-11)

En modo determinista con "Envio Parcial", si una linea de un pedido trae un
SKU inexistente se descarta, y el nivel de servicio queda en 100% porque esa
linea no cuenta como pedida. El cliente si la pidio y no la recibio, asi que
el indicador sobreestima el cumplimiento. Lo calcula `service_level` sobre lo
aceptado.

### BK-21 — la vista previa de ordenes ignora la politica de cumplimiento (QA H-12)

Con "Todo o Nada" y un item invalido, la vista previa sigue diciendo "10
Ordenes" y solo lista el SKU faltante: no avisa que el pedido completo se va a
descartar. La simulacion si lo descarta (correcto); lo que confunde es el
aviso previo.

### BK-22 — configuraciones del motor sin control en la web

Por el principio rector #2, lo que el cliente no puede ajustar desde la web es
un componente fantasma. Hoy el motor lee estas claves que la web no muestra
(desde H-01 al menos se conservan al correr y al guardar):
- `personas`, `equipos`, `perfiles`, `cambio_de_perfil`, `estacionamientos`
  (INIT-11; su editor es la fase F10 del plan).
- `zonas_espera` y `congestion.timewindow.replan_wait_s` / `replan_max_retries`
  (BK-15).
- `priority_dispatch_enabled` y `waves` (prioridad de pedidos y olas, INIT-4).
- `fleet_defaults` (BK-06).
- Parametros de la capa anti-colision (`congestion.spawn_offset`,
  `staggered_start`, `timewindow.*`) y del muelle de salida
  (`outbound.loading_time`, `zone_capacity_default`, `slot_wait_alert`,
  `slot_poll_dt`, `dwell_scaffold`, `dispatch_policy`).
- `tiempos.cell_size_m`, `tiempos.speed_factor_ground`.
- `cercania_tour_mode` (estrategia descartada en BK-03: evaluar si se elimina).

---

## INIT-6 Opcion C — clustering geografico automatico

**Contexto:** INIT-6 (Opciones A+B, staging por zona real + destino->staging_id)
esta HECHO -- ver `docs/CHANGELOG.md` 2026-07-05. Esto es solo la extension
opcional que quedo afuera.

Clustering geografico automatico de destinos -> staging_id. Requiere:
coordenadas reales de destino por pedido (hoy no existen), algoritmo de
clustering (ej. k-means) corrido al inicio de cada corrida/wave, y decidir si
las 7 zonas fisicas son suficientes o hace falta redefinir el layout. No
estimado -- depende de si el negocio va a tener datos reales de geolocalizacion.

---

## Distribucion real de `outbound_staging_distribution`

Ahora que el camion respeta la zona (INIT-6 Opcion A), tiene sentido repartir
el trafico entre las 7 zonas reales en vez de mandar 100% a la zona 1 (asi
esta el `config.json` canonico hoy). Es una decision de tuning de negocio del
Director, no un bug — cambiarla intencionalmente rompe el baseline byte-identico
y requeriria `--update-baseline --yes`.

---

## BK-02 — FIFO Estricto en UI

**Estado:** EN REPENSAR (nota del Director, 2026-06-15): no exponer todavia.
Hay que redefinir que deberia hacer FIFO operacionalmente antes de mostrarlo
en el configurador. El motor ya lo implementa correctamente
(`dispatcher._estrategia_fifo`, string `"FIFO Estricto"`); es una decision de
diseño de uso, no un problema tecnico.

---

## INIT-3 v3 — capacidades por agente en el optimizador

Unica pieza diferida que queda de INIT-3 (la UI web se completo en v2, ver
CHANGELOG 2026-07-05): **capacidades por tipo de agente en el espacio de
busqueda**. Requiere que el optimizador arme un `agent_types` explicito por
trial en vez de usar el fallback legacy (`num_operarios_terrestres`/
`num_montacargas`).

**ACTUALIZACION 2026-09-07: MUCHO MAS BARATO tras BK-06.** El bloqueo de fondo
era que la capacidad estaba HARDCODEADA en el fallback de `operators.py` (150 /
1000, no leida de config). Ya no: la flota se resuelve en
`core.fleet.resolver_flota` y las capacidades salen del bloque configurable
`fleet_defaults`. Ademas quedo probado que el canonico y su equivalente con
`agent_types` explicito dan resultados IDENTICOS, asi que el optimizador puede
generar flotas explicitas sin cambiar el comportamiento base. Sigue siendo un
cambio de representacion en `src/tools/optimizer.py`, pero ya no arrastra un
fix de motor. Insumo natural: BK-09 (la flota 2+2 esta sub-dimensionada; el
optimizador deberia encontrarlo solo).

---

*Para retomar cualquier item cerrado, buscar su commit en `docs/CHANGELOG.md`
o `git log --oneline --grep=<ITEM>`.*
