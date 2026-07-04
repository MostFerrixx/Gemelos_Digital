# VISION DE PRODUCTO — Gemelo Digital de Almacen (Warehouse Digital Twin)

> Documento de REFERENCIA estrategica. Define QUE es el producto, PARA QUIEN, y
> el NORTE a largo plazo. No es un plan de implementacion (esos viven en
> `docs/PLAN_INICIATIVA_*.md`); es la brujula contra la que se priorizan esas
> iniciativas. Documento vivo: se revisa cuando cambia el rumbo.

---

## 1. EL PRODUCTO EN UNA FRASE
Un **gemelo digital de almacen**: un simulador que reproduce, visualiza y
optimiza las operaciones logisticas de un almacen sobre su layout fisico real,
para detectar cuellos de botella y aumentar el throughput **sin tocar el almacen
de verdad**.

Version extendida: se modela el almacen como un mapa de celdas con racks, zonas y
agentes (operarios y montacargas) que ejecutan ordenes de trabajo (mover SKUs de
los racks al muelle). La simulacion es de **eventos discretos** (el tiempo avanza
por eventos, no por frames), corre headless, y produce un archivo de eventos que
alimenta la visualizacion y la analitica. Sobre esa base se prueban escenarios
"what-if": mas operarios, otro layout, otra politica de despacho, etc.

---

## 2. EL PROBLEMA QUE RESUELVE Y PARA QUIEN
**Para quien**: responsables de operaciones logisticas, jefes de almacen,
ingenieria de procesos y quien disena o redimensiona una instalacion.

**El problema**: las decisiones de almacen (cuanta flota, donde poner el muelle,
cuantas puertas, que politica de slotting o de despacho, como rutear) son caras y
arriesgadas de probar en la realidad. Hoy se deciden por intuicion o por hojas de
calculo estaticas que no capturan la dinamica (congestion, colas, cuellos
moviles). El gemelo permite **probar esas decisiones con datos, en minutos, antes
de invertir**.

**La promesa**: convertir preguntas de negocio en respuestas cuantitativas
reproducibles. Ejemplos de preguntas que el producto debe contestar:
- Cuantos operarios y montacargas necesito para X ordenes/dia?
- Donde esta el cuello: el picking, los pasillos, o el muelle?
- Cuantas posiciones de muelle y cuantas puertas de camion?
- Que politica de despacho (frecuencia/capacidad de camion) evita el colapso?
- Que layout rinde mas? Que pasa si crece la demanda un 30%?

---

## 3. PRINCIPIOS DE DISENO (lo que NO se negocia)
Estos principios ya rigen el codigo y deben sobrevivir a cualquier evolucion:
1. **Eventos discretos (SimPy), tiempo continuo.** El motor avanza por eventos en
   tiempo real (float), no por ticks. Es la base correcta para modelar colas y
   coordinacion fina.
2. **Separacion headless -> .jsonl -> viewer.** El motor calcula sin interfaz y
   emite un log de eventos; la visualizacion y la analitica lo consumen aparte.
   NO hay "live simulation" acoplada a la UI, y no se reintroduce.
3. **`config.json` es la unica fuente de verdad del backend.** La UI lo edita; el
   motor solo lo lee. Nada de configuracion duplicada en codigo.
4. **Prevenir mejor que curar.** La coordinacion de movimiento se garantiza por
   construccion (ruteo por reserva espacio-temporal, Opcion C), no por parches
   reactivos. La misma filosofia aplica a los nuevos subsistemas.
5. **Incremental, reversible, validado empiricamente.** Todo cambio grande va por
   fases detras de flag, con no-regresion byte-identica con el flag off y
   evidencia (no se da por hecho nada sin un log o captura).
6. **Fidelidad escalable.** El objetivo es realismo, pero la fidelidad se
   construye por capas: se valida el mecanismo barato y luego se escala el
   contenido. No "todo real de golpe".

---

## 4. ESTADO ACTUAL (honesto)
- **Motor de simulacion**: sano y principal (`src/subsystems/simulation/`).
- **Movimiento conflict-free**: la congestion (choques, freezes del arranque
  masivo) se resuelve por construccion con time-window routing (Iniciativa #2 /
  Opcion C): 0 colisiones entre agentes en movimiento, sin deadlock, termina.
- **Allocation Layer (V12.1)**: asignacion de stock real (FCFS) antes de crear
  WorkOrders; soporte de surtido parcial / backorder.
- **Outbound (Capa 2, Iniciativa #3)**: EN CURSO, motor hecho. Ya hay pallets
  persistentes, zona de aforo real (mapa WH1 v2: 7 stagings de 20 celdas), pallets
  como obstaculos que el planner esquiva, y descarga realista por CARRILES (2 columnas
  por staging, espera fuera, llenado de atras hacia adelante) -- Fase 1 completa y
  validada headless. PENDIENTE: integrarlo en la UI web (el configurador hoy descarta
  los bloques congestion/outbound al guardar) y la Fase 2 (camion/despacho real; hoy
  hay un scaffold temporal). Detalle vivo en docs/PROGRESO_INICIATIVA_3.md.
- **Layout**: de juguete (WH1, 30x30). Suficiente para validar mecanismos, lejos
  de una instalacion real.
- **Herramientas**: optimizador (Optuna), configurador + **viewer web** (FastAPI,
  unico frontend), reportes Excel + heatmap. Las GUI de escritorio (viewer Pygame,
  dashboard PyQt6, configurador Tkinter) fueron archivadas en
  `_legacy/gui_escritorio/`. La verdad es el codigo en `main` + working dir.

---

## 5. EL NORTE A LARGO PLAZO
Un gemelo digital de almacen **a escala real y fidelidad operativa**, capaz de
representar el ciclo logistico completo y de responder preguntas de diseno y
operacion con confianza. Las dimensiones de fidelidad del norte:

- **Fisica**: layouts a escala WMS (cientos x cientos de celdas, miles de
  ubicaciones), con zonas diferenciadas (recepcion/inbound, almacenamiento,
  picking, packing, staging/outbound, puertas de muelle) y cargas unitarias
  (pallets) como objetos reales con posicion y estado.
- **De flujo**: el ciclo completo —inbound (recepcion + putaway), almacenamiento
  y reabastecimiento (replenishment), picking, y outbound (consolidacion +
  expedicion con camiones y citas)— no solo el picking->staging actual.
- **De agentes**: flotas heterogeneas (operario terrestre, montacargas, reach,
  AGV) con velocidades, capacidades, prioridades de zona, turnos y, a futuro,
  recarga/averias (estocasticidad).
- **De inteligencia**: optimizacion multi-objetivo (slotting, asignacion de
  tareas, rutas, dimensionamiento de flota y muelle) y comparacion de escenarios
  what-if, apoyada en el motor de eventos.
- **De escala/rendimiento**: ruteo por reserva con ventana movil (WHCA*) para
  flotas grandes en mapas grandes, manteniendo el determinismo.
- **De interfaz**: configurador web + viewer + reportes/analitica (heatmaps,
  KPIs, dashboards) maduros, para que un usuario no tecnico opere el twin.

---

## 6. ROADMAP POR CAPAS (norte, sin fechas)
El orden refleja dependencias, no un calendario.

- **Capa 1 — Motor y movimiento (HECHO / EN CURSO).** Simulacion de eventos,
  movimiento conflict-free (Opcion C), allocation layer. Base solida.
- **Capa 2 — Outbound real (EN CURSO, Iniciativa #3).** Pallets persistentes,
  staging como zona de aforo (1 pallet/celda), proceso de despacho/expedicion con
  backpressure realista. Convierte el muelle en un cuello modelado, no escondido.
- **Capa 3 — Escala real.** Layouts y datos a escala de instalacion real;
  detona la ventana movil del ruteo. Aqui el twin empieza a parecerse a un
  almacen de verdad.
- **Capa 4 — Ciclo completo.** Inbound (recepcion + putaway) y replenishment, para
  cerrar el flujo de mercancia de extremo a extremo.
- **Capa 5 — Inteligencia y UI.** Optimizacion multi-objetivo, what-if, y una
  capa de interfaz/reportes madura para usuarios de negocio.
- **Capa 6 — Fidelidad avanzada.** AGV, turnos, estocasticidad (averias, tiempos
  variables), citas de camion, y demas realismo de operacion fina.

Regla de priorizacion: cada capa se valida como mecanismo en lo pequeno antes de
escalar su contenido; nada avanza sin no-regresion y evidencia.

---

## 7. ANTI-OBJETIVOS (lo que el producto NO es)
- **No** es un videojuego ni una animacion en tiempo real: el render es para
  analisis, derivado del log de eventos.
- **No** es una "live simulation" acoplada a la UI: la separacion headless ->
  jsonl -> viewer es sagrada.
- **No** busca fidelidad cosmetica por encima de la operativa: primero que los
  flujos y las decisiones sean correctos; lo visual viene despues.
- **No** duplica configuracion en codigo: `config.json` manda.

---

## 8. METRICAS DE EXITO DEL PRODUCTO (KPIs que el twin produce)
Estas son a la vez la salida util del producto y la prueba de su valor:
- **Throughput** (WorkOrders/ordenes por unidad de tiempo) y **makespan** (tiempo
  total de completar la carga).
- **Utilizacion de recursos**: ocupacion de operarios/montacargas, tiempo ocioso.
- **Cuellos**: ocupacion temporal de celdas/pasillos hotspot; ocupacion del
  muelle y espera por posicion de staging.
- **Calidad de coordinacion**: 0 colisiones (I1=0), 0 freezes, esperas insertadas
  y espera maxima por agente (equidad).
- **Outbound**: backlog de pallets, ocupacion del muelle, espera por slot,
  rendimiento de expedicion (pallets/camion, ociosidad de camion).
- **Costo computacional**: ms por planificacion de ruta, tamano de estado — para
  asegurar que el twin escala.

Un cambio de diseno "funciona" cuando mejora (o no empeora) estos KPIs con
evidencia reproducible, no por intuicion.

---

## 9. RELACION CON LOS PLANES TECNICOS
- `docs/PLAN_INICIATIVA_2_OPCION_C.md` — ruteo por reserva espacio-temporal
  (Capa 1: movimiento conflict-free).
- `docs/ANALISIS_STAGING_AFORO.md` — analisis con datos del aforo de staging
  (insumo de la Capa 2).
- `docs/PLAN_INICIATIVA_3_DESPACHO_OUTBOUND.md` — subsistema outbound: aforo +
  despacho real (Capa 2).
- `AUDITORIA.md` — mapa de codigo vivo vs muerto (higiene del proyecto).

<!-- FIN_DOCUMENTO -->
