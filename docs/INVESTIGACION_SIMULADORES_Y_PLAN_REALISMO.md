# Investigación: cómo logran tiempos reales los simuladores de vanguardia, y cómo llevarlo a nuestro simulador

> Pedido del Director (2026-09-26): "si no le demostramos a un cliente que el
> simulador logra los mismos tiempos que su operación actual, con su layout y
> su configuración, no nos compra nada".
> Método: 5 investigaciones web en paralelo (simuladores comerciales,
> estándares de tiempos de ingeniería, tráfico multi-agente, calibración y
> validación, factores operativos) + cruce con el código vivo. Toda cifra
> lleva su fuente; lo que no se pudo confirmar dice **[no verificado]**.
> Estado: **PROPUESTA — espera decisiones del Director (sección 6)**.

## 0. Resumen ejecutivo

1. **La credibilidad no la da la física: la da la validación con datos del
   cliente.** Los proveedores serios construyen un modelo "as-is" de la
   operación actual, lo alimentan con los pedidos reales de días concretos
   (simulación "trace-driven") y muestran, día por día, real contra simulado
   con un margen de error acordado **antes** de empezar (Sargent, Law). La
   referencia pública más sólida es Amazon: su simulador de sortation, validado
   contra 8.228 turnos reales, tiene **9,5 % de error (WAPE) en throughput**.
   Hoy nosotros **no tenemos esta pieza**, y es la que vende.
2. **A nuestro reloj le falta entre un 25 y un 40 % del turno real.** No
   modelamos descansos, suplementos PFD (personal-fatiga-demora, 9–20 %),
   preparación por recorrido (tomar carro o pistola, dejar la carga: 15–25 %
   del picking) ni arranque y cierre de turno. Aunque calibráramos los
   parámetros que ya tenemos, el turno simulado saldría corto.
3. **La física de tiempos tiene tres huecos concretos:**
   - La horquilla tarda 8 s fijos, cuando en la realidad depende de la altura
     (a 6 m son más de 20 s solo de mástil).
   - No hay aceleración ni frenado.
   - No hay recargo por postura según el nivel (agacharse, estirarse), que es
     la variable que más usan los estándares de ingeniería.
4. **En tránsito vamos por el camino correcto.** El planificador A*
   espacio-temporal con reservas es el mismo enfoque de Simio, FlexSim y
   Visual Components. **No hay que reemplazarlo** (CBS, PIBT, LaCAM y la fuerza
   social no encajan con tiempo continuo y pasillos angostos). Hay que sumarle
   capas: lugares de espera que no estorben, pasillos como recurso con cola
   afuera, penalización de pasillos ajenos y un detector de bloqueos mutuos.
5. **Plan en 4 fases** (sección 5):
   - **A. Prueba contra la realidad:** importar el log del sistema de gestión
     del almacén (WMS), comparar real contra simulado y calibrar con el
     optimizador que ya tenemos.
   - **B. Reloj completo.**
   - **C. Tránsito realista.**
   - **D. Aguas abajo.**
   - Arrancaría por **A y B1-B2 en paralelo**.

## 1. Qué hacen los líderes (patrones comunes)

| Patrón | Quién | Nosotros hoy |
|---|---|---|
| Perfil **trapezoidal**: aceleración, velocidad crucero y frenado, con velocidad máxima por recurso | FlexSim, AnyLogic (1 m/s² por defecto), Plant Simulation (desde la versión 2606 también frena en curvas) | Velocidad constante por celda |
| **Tiempo vertical = altura / velocidad de elevación** (con y sin carga) | FlexSim "Lift Speed", AnyLogic "Elevation speed". Hojas técnicas: reach truck Toyota, elevación 0,28–0,43 m/s; Linde E20, 0,39–0,54 m/s | Horquilla fija de 8 s; las ubicaciones no tienen altura |
| **Velocidad según carga** (cargado o vacío) | Se cambia la velocidad al cargar y descargar (FlexSim, AnyLogic) | Existe para el operario (INIT-8 F3), desactivado por defecto |
| **Reserva de camino / recursos con capacidad** y detección de bloqueos mutuos | Simio Path Planner (reserva libre de bloqueos), FlexSim A* (reservas con sello de tiempo + trigger de bloqueo), Control Areas, AutoMod blocks | A* espacio-temporal con reservas (equivalente). Falta detectar bloqueos y el pasillo como recurso con cola |
| **Tiempos de tarea con distribuciones ajustadas a datos reales**, o empíricas cuando no ajustan | FlexSim + ExpertFit (40 distribuciones) | Fórmula + variabilidad Log-Normal; no se ajusta a datos del cliente |
| **Calibración con estándares de ingeniería**: viaje por coordenadas + velocidades medidas + paradas + elevación | Sistemas de gestión de personal (LMS: Manhattan, Blue Yonder, Takt) | Parcial (fórmula INIT-8) |
| **Validación del modelo actual (as-is)** con métricas de error | Amazon (WAPE 9,5 %), AWS ("calibrar contra el estado actual"), SimWell (el supervisor valida que "hace colas y se recupera como el edificio") | **No existe** |

Diferenciadores de vanguardia, que **no** recomiendo ahora:
- *Software-in-the-loop*, es decir conectar el WMS o el PLC real al gemelo:
  Emulate3D, Dematic iQ Virtual, SSI WAMAS Emulation Center y NVIDIA Mega con
  KION.
- Física y sensores renderizados: Omniverse.

Resuelven la puesta en marcha de automatización, no la pregunta del cliente
de hoy ("¿reproducís mis tiempos?").

Fuentes: FlexSim [Travel](https://docs.flexsim.com/en/19.0/WorkingWithTasks/Travel/KeyConceptsTravel/KeyConceptsTravel.html),
[A*](https://docs.flexsim.com/en/23.2/Reference/Tools/AStar/AStar.html),
[Transporter](https://docs.flexsim.com/en/24.1/Reference/3DObjects/TaskExecuters/Transporter/Transporter.html);
AnyLogic [TransporterFleet](https://anylogic.help/library-reference-guides/material-handling-library/transporterfleet.html),
[RackStore](https://anylogic.help/library-reference-guides/process-modeling-library/rackstore.html);
Siemens [Acceleration](https://docs.plm.automation.siemens.com/content/plant_sim_help/15.1/plant_sim_all_in_one_html/en_US/tecnomatix_plant_simulation_help/objects_reference_help/mobile_objects/transporter/dialog_window_of_the_transporter/tab_attributes/acceleration_transporter_text_box.html),
[2606](https://blogs.sw.siemens.com/tecnomatix/discover-whats-new-in-plant-simulation-2606/);
Simio [release notes](https://cdn.simio.com/software/SimioReleaseNotes261.pdf);
Amazon [arXiv 2603.24883](https://arxiv.org/html/2603.24883);
AWS [blog](https://aws.amazon.com/blogs/supply-chain/aws-simulation-and-digital-twin-to-increase-warehouse-productivity/);
NVIDIA [Mega](https://blogs.nvidia.com/blog/mega-omniverse-blueprint);
Toyota [RRE120-160B](https://toyotamaterialhandling-international.com/storage/9E79A1137100D33DD55E39F47122E2D7E41E83E5AB736F808A20BE071D7D69E4/a53545b796d242efad09e0073af4ffca/pdf/media/cb699845f18042f8b9dab5ea05b7e49c/RRE120-160B%20Datasheet.pdf%2014179.pdf);
Linde [E20](https://www.linde-mh.com/media/Datasheets/EN_ds_e20_e35_1252_en_a_0621_view.pdf).

## 2. Cómo se calcula un tiempo "de ingeniería" (lo que usa la industria)

- **Estándares predeterminados (MTM, MOST).** Descomponen el pick en
  elementos: viajar, caminar al hueco, agacharse o estirarse según el nivel,
  tomar, volver al equipo, colocar y confirmar. En la práctica se usan
  librerías de patrones prearmados. Ejemplo publicado: "tomar caja grande del
  nivel medio de un rack de 3 niveles" = 60 TMU = 2,16 s (1 TMU = 0,036 s).
  Kühne+Nagel armó su catálogo global de picking con MTM-UAS, con recargos por
  peso y por postura.
  [Logistics Viewpoints](https://logisticsviewpoints.com/2010/09/28/labor-standards-for-the-warehouse-what-are-predetermined-time-systems/),
  [MTM / Kühne+Nagel](https://mtm.org/en/references/kuehne-nagel).
- **Sistemas de gestión de personal (LMS).** Tiempo esperado = partes fijas
  por elemento (pick, escaneo, confirmación) + parte variable (distancia real
  entre ubicaciones del WMS, peso, volumen, equipo), con velocidad por equipo y
  ajuste por congestión. Ejemplo de Takt: 620 pies + 18 picks + 12 lb =
  14,2 min. [Takt](https://www.takt.io/guides/complete-guide-to-engineered-labor-standards-(els)),
  [Blue Yonder](https://info.blueyonder.com/workforce-labor-management/what-is-blue-yonder-warehouse-labor-management).
- **Suplementos PFD.** Tiempo estándar = tiempo normal × (1 + PFD). Personal
  ~5 %, fatiga 3–5 %, demora 2–4 %; total típico 9–20 %. El Departamento de
  Trabajo de EE. UU. exige un mínimo de 15 % para el pago a destajo.
  [SCDigest](https://www.scdigest.com/ontarget/13-07-17-1.php?cid=7230),
  [Wikipedia PFD](https://en.wikipedia.org/wiki/PFD_allowance).
- **En qué se va el tiempo de un picker:**
  - Tompkins: viaje 50 %, búsqueda 20 %, extracción 15 %, preparación 10 %,
    otros 5 %.
  - Frazelle (citado por Bartholdi & Hackman): viaje 55 %, búsqueda 15 %,
    extracción 10 %, papeles y otros 20 %.
  - [De Koster et al. 2007](https://pure.eur.nl/ws/portalfiles/portal/46713708/DesignandControl_2007.pdf),
    [Bartholdi & Hackman](https://www.warehouse-science.com/book/editions/wh-sci-0.98.1.pdf).
  - **Dato propio (seed 42, perfil Real):** caminando 10 %, picking 48 %,
    ocioso 29 %. El viaje está muy por debajo de la referencia. Ver el
    punto 4.3.
- **Referencias de productividad:**
  - WERC 2025, mejor de su clase: 70 líneas o más pickeadas y despachadas por
    persona-hora ([Yale/WERC](https://www.yale.com/globalassets/coms/yale/north-america/documents/white-papers/snack-drawer/YALE-1520_WERC-DC-Metrics-infographic.pdf)).
  - La voz ahorra 2–3 s por pick frente a RF (Lucas, proveedor).
  - Caminata de picker en modelos académicos: 1 m/s. Peatón libre: 1,4 m/s.

## 3. Cómo se demuestra ante el cliente (calibración y validación)

- **Sargent** separa cuatro niveles: validez de los datos, del modelo
  conceptual, del código y **validez operacional** (que la salida se parezca a
  la realidad). Tres reglas prácticas:
  - La precisión exigida se fija **antes** de construir el modelo, y se
    acuerda con el cliente.
  - Una parte de los datos históricos se usa para construir el modelo y el
    resto para probarlo.
  - Se hace el test de Turing: expertos del cliente tratan de distinguir la
    salida real de la simulada.
  - [WSC 2010](https://www.informs-sim.org/wsc10papers/016.pdf).
- **Law** llama *results validation* a comparar el modelo "as-is" con la
  realidad. Es la prueba que genera credibilidad. Sus ejemplos aceptados tienen
  **3–6 %** de diferencia. Desaconseja los tests t ingenuos (las salidas
  reales están autocorrelacionadas): lo que importa es si la diferencia cambia
  las conclusiones. [WSC 2022](https://informs-sim.org/wsc22papers/128.pdf).
- **Simulación trace-driven.** El modelo recibe exactamente los mismos pedidos
  y horarios que la realidad, así la comparación es "el mismo día" y mucho más
  potente. [Kleijnen, bootstrap](https://www.researchgate.net/publication/2572160_Validation_of_Trace-Driven_Simulation_Models_Bootstrap_Tests).
  **Ya tenemos el modo determinista**: es la base.
- **Calibración:**
  - Bayesiana con término de discrepancia (Kennedy & O'Hagan): no fuerza los
    parámetros a tapar errores de estructura.
  - ABC (calibración sin fórmula de verosimilitud) y optimización con distancia
    Kolmogorov-Smirnov o Wasserstein entre distribuciones.
  - Optuna ya se usa para calibrar simuladores de agentes.
  - **Regla nuestra (principio de realismo):** si la calibración pide una
    velocidad imposible, lo que falla es la estructura del modelo, no el
    parámetro.
- **Datos del cliente:**
  - El log del WMS (confirmación de pick por línea con hora, operario,
    ubicación y cantidad) **no trae la trayectoria**: el viaje se estima con la
    distancia del mapa, que es exactamente lo que calcula nuestro A*.
    [Dataset WMS](https://pmc.ncbi.nlm.nih.gov/articles/PMC12269467/).
  - Posicionamiento en tiempo real (RTLS por UWB, ~10 Hz) si existe.
  - Minería de procesos (process mining, con la librería PM4Py) para extraer
    tiempos por actividad.
- **Nota honesta:** ningún proveedor comercial publica su protocolo ni su
  umbral de validación. "Baseline ±5–10 %" es práctica habitual
  **[no verificado]**. Amazon (9,5 %) y los ejemplos de Law (3–6 %) son las
  referencias públicas.

## 4. Brechas de nuestro simulador (verificadas en el código)

### 4.1 Reloj del turno (lo que no existe)
| Factor | Peso típico | Hoy |
|---|---|---|
| Descansos + PFD | 9–20 % del turno | 0 % |
| Preparación por recorrido + "otros" | 15–25 % del picking | 0 % |
| Arranque y cierre de turno, trabajo indirecto | 5–10 % | 0 % |
| Olas y cortes de camión (ocio al final de cada ola) | 10–20 % de productividad **[no verificado, proveedor]** | Las olas existen; falta medir el ocio y atarlas al corte |
| Diferencias entre operarios | ±10–16 % (Matusiak 2017) | Todos rinden igual |
| Fatiga y aprendizaje | Fatiga 3–5 %; rampa 70/85/100 % las primeras 8 semanas (CognitOps) | No hay |
| Reposición y su interferencia | Variable; es la causa de faltantes y bloqueos | No hay |
| Empaque, consolidación y carga del camión | Define la hora real de cierre | Solo camión de salida |
| Cambio de batería (plomo-ácido) | 15–20 min por equipo y turno **[no verificado]** | No hay |

### 4.2 Física de tiempos
- **Las ubicaciones no tienen altura ni nivel:** la tabla `locations` no tiene
  columna z. Consecuencias: horquilla fija de 8 s, sin recargo por postura.
- **Sin aceleración ni frenado:** velocidad constante por celda.
- **Sin tiempo fijo por método de captura** (papel, RF, voz, luz).
- **Sin minería de tiempos** desde logs reales.

### 4.3 Nuestro reparto de tiempo no se parece al de referencia
Con semilla 42 y perfil Real, caminar es el 10 % del tiempo del operario;
Tompkins y Frazelle dicen 50–55 % de viaje. Parte se explica por el layout
compacto de WH1 v3 y porque el pick de 10 s + 2 s por unidad ya incluye
elementos que la referencia cuenta aparte. Pero es la primera señal que
miraría un cliente experto (face validity). **Hay que medirlo contra datos
reales antes de tocar nada.**

### 4.4 Tránsito
Ya tenemos lo esencial: reservas, 0 choques en el canónico y estaciones de
descarga con turno. Faltan:
- lugares de espera que no estorben, validados sobre el mapa;
- pasillo o boca de carril como recurso con capacidad y cola afuera (H-59,
  BK-40);
- penalización de pasillos ajenos;
- detector de bloqueos mutuos por grafo de espera, con KPI;
- reglas de derecho de paso (el peatón manda sobre el montacargas, según
  [OSHA](https://www.osha.gov/etools/powered-industrial-trucks/workplace/pedestrian-traffic)).

## 5. Plan de integración (propuesta INIT-13 "Realismo calibrable")

Todo configurable desde `config.json` y la web (Ley #3), apagado por defecto
hasta medirlo (el gate byte-idéntico no se rompe hasta la decisión), y con
`[WARN]` visibles.

### Fase A — Prueba contra la realidad (lo que vende) · ~2–3 semanas
- **A1. Importador del log del WMS** (CSV o Excel con formato estándar
  documentado). Arma el archivo de pedidos del día (modo determinista) y la
  dotación real (quién trabajó, con qué equipo, en qué horario). Valida contra
  los datos maestros.
- **A2. Comparador real contra simulado**, con pestaña en la web y un reporte
  para el cliente:
  - Por día: duración del turno, líneas por hora, líneas por persona-hora,
    tiempo por pedido (mediana y distribución), utilización por operario.
  - Curva acumulada de líneas por hora, real y simulada.
  - Error WAPE y banda de aceptación acordada (propuesta ±5 % en throughput y
    duración del turno, ±10 % en tiempo por pedido).
- **A3. Extracción de tiempos desde el log** (process mining liviano):
  - Tiempo entre confirmaciones consecutivas del mismo operario, menos el
    viaje estimado con nuestro A*, da el tiempo de pick real.
  - Se obtiene por operario, por clase de producto y por nivel, y se ajustan
    distribuciones (Kolmogorov-Smirnov).
- **A4. Calibración con Optuna** (ya integrado):
  - Se calibra sobre los días de calibración y se valida en días reservados,
    que no se miran antes.
  - Los parámetros se acotan a rangos físicamente plausibles.
  - Reporte de sensibilidad (qué parámetro mueve cada KPI).
- **Entregable comercial:** el informe "así reproducimos tu operación: día por
  día, real contra simulado, error X %".

### Fase B — Reloj completo · ~2 semanas
- **B1. Turno:** horario, descansos y almuerzo, arranque y cierre, suplemento
  PFD (%). Barato, y cubre el 15–30 % que hoy falta.
- **B2. Preparación por recorrido** (tomar carro o pistola, dejar la carga) +
  **tiempo fijo por método de captura** (papel, RF, voz, luz). Además permite
  al cliente comparar tecnologías con el A/B.
- **B3. Altura y nivel por ubicación:**
  - Columna nueva en el Excel y en la base.
  - Horquilla = altura / velocidad de elevación + altura / velocidad de
    descenso, con carga y sin carga.
  - Recargo por postura según nivel para el operario a pie.
- **B4. Aceleración y frenado** (perfil trapezoidal) + velocidad reducida en
  giros y pasillos. OJO: toca la duración por celda que usa el planificador
  espacio-temporal (las primeras y últimas celdas de cada tramo son más
  lentas). Es la tarea más delicada de esta fase.
- **B5. Habilidad por operario** (multiplicador) + rampa de aprendizaje
  opcional. La fatiga, ligada a los descansos, queda como opcional.

### Fase C — Tránsito realista · ~2 semanas (capas ya acordadas, ahora con respaldo)
- **C1. Lugares de espera que no estorban**, validados con `[WARN]` si caen
  sobre un camino de paso: es la condición con garantía formal de que no haya
  bloqueos mutuos, según Ma 2017 y Čáp 2015
  ([MAPD](https://arxiv.org/abs/1705.10868),
  [infraestructura válida](https://arxiv.org/abs/1501.07704)).
  Se suma **evacuación del ocioso**: cede el paso y va al refugio libre más
  cercano.
- **C2. Pasillo y boca de carril como recurso con capacidad**, al estilo de
  FlexSim Control Area y AutoMod blocks:
  - la cola se hace afuera;
  - "el que sale antes que el que entra";
  - los cupos se toman en orden global, para que nunca haya espera circular.
  - Resuelve H-59 y BK-40.
- **C3. Costos de guía** en el A*: penalizar pasillos ajenos y permitir
  sentidos únicos configurables (Chen 2024, WPPL, patente de Boston Dynamics).
- **C4. Detector de bloqueos mutuos + tablero de tránsito:** esperas por
  causa, cesiones y desvíos.
- **C5. Derecho de paso:** el peatón manda sobre el montacargas y no se
  adelanta en intersecciones.

### Fase D — Aguas abajo y reposición · a definir
Empaque y consolidación, carga del camión (1–1,5 min por pallet), reposición
con interferencia, errores de pick como KPI, cambio de batería.

### Lo que **no** recomiendo
- Reemplazar el planificador por CBS, PIBT o LaCAM. Suponen pasos síncronos y
  unitarios, que chocan con SimPy en tiempo continuo; es una inferencia
  nuestra.
- Fuerza social u ORCA: se bloquean en pasillos angostos.
- Motores de física o sensores tipo Omniverse.
- Conectar el WMS real (software-in-the-loop): sí más adelante, si un cliente
  lo pide.

## 6. Decisiones del Director

1. **Orden:** A + (B1, B2) en paralelo primero, luego A4, B3-B5, C y D.
   Recomendación: sí.
2. **¿Tenemos un cliente o un almacén piloto que nos preste logs del WMS**
   (10–20 días, incluidos días pico) y su registro de turnos? Sin datos reales,
   la fase A se construye con datos sintéticos y queda sin validar.
3. **Banda de aceptación** para presentar: propuesta ±5 % en throughput y
   duración del turno, ±10 % en tiempo por pedido.
4. **Formato del log** que pediremos: propongo un CSV estándar nuestro
   (pedido, línea, SKU, ubicación, cantidad, operario, equipo, hora de inicio y
   de confirmación) + un conversor por cliente.
