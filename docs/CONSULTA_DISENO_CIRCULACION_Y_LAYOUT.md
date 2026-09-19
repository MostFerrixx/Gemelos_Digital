# Consulta de diseno — circulacion en zonas de descarga y modelo de layout

> Encargo para un consultor externo (Fable 5.1), redactado el 2026-09-19.
> El consultor lee este archivo y el codigo del repositorio, y deja su
> propuesta en `docs/PROPUESTA_DISENO_CIRCULACION_Y_LAYOUT.md`.
> No debe modificar codigo: solo analizar y proponer.

## 1. Contexto minimo

Simulador de almacen (gemelo digital). Esta hecho con SimPy, eventos discretos
sobre una grilla de celdas. El motor corre sin interfaz, escribe un `.jsonl` y
un visor web lo reproduce. El configurador es web (FastAPI) y escribe
`config.json`, que es la unica fuente de verdad de la configuracion. Hoy el
layout viene de dos lugares:

- un mapa `.tmx` de Tiled (`layouts/WH1.tmx`): grilla y transitabilidad;
- un Excel (`layouts/Warehouse_Logic.xlsx`), importado a `warehouse.db`:
  ubicaciones, zonas de descarga (outbound staging) y muelles.

Leer primero `CLAUDE.md`. Contiene la arquitectura, el codigo vivo y el muerto,
y las reglas. Hay tres innegociables:

- solo ASCII en el codigo;
- toda clave nueva de config se registra en `src/core/config_schema.py`;
- existe un gate de regresion byte-identico con semilla 42.

**Principio rector del producto, en este orden:**

1. Realismo: lo que no puede pasar en un almacen fisico es un bug, aunque
   mejore los indicadores.
2. Configurabilidad: nada fijo en el codigo que el cliente no pueda ajustar
   desde la web.
3. Usabilidad: lo invisible se hace visible; una configuracion incoherente
   avisa con un mensaje que dice que corregir.

## 2. El problema que dispara la consulta (QA H-15 / BACKLOG BK-25)

La zona de descarga admite **un solo operario a la vez**. En WH1, la zona 1
esta en (3,29), contra el borde inferior. Frente a las zonas hay un pasillo
transversal de 3 filas (y=27..29). Justo encima de la zona hay racks (x=3..4,
y=22..26). Las bocas de los pasillos de picking dan a la fila 27.

Los operarios que llegan a descargar mientras la zona esta ocupada se quedan
donde los freno la ruta: pegados a la zona, en (2,29), (4,29) y (3,28). Esas
son las unicas salidas del que esta descargando. Se forma un bloqueo circular.
Tras 10 minutos simulados de reintentos, el motor se rinde, avanza por la ruta
fija y vuelve a haber dos agentes en la misma celda.

Evidencia (flota 4+4, todo el trabajo va a la zona 1, semilla fija):

- 28 rendiciones del planificador;
- 32 co-ocupaciones, 26 de ellas en (3,29), con hasta 6 agentes juntos;
- 50.643 esperas de replanificacion;
- duplicar la flota casi no acorta la corrida (6.756-7.178 s contra ~7.300 s
  con 2+2).

Tambien aparece, mas leve, con la flota 2+2 y una descarga lenta de 60 s. Ver
`docs/PLAN_QA_CONFIGURACION_WEB.md`, secciones 9 y 10.

## 3. Lo que ya se conversó (propuestas sobre la mesa)

**Idea del Director:**

- Las celdas a los costados de cada zona de descarga, (2,29) y (4,29) en la
  zona 1, son **salidas de un solo sentido**. Solo se sale de la zona por ahi.
  Nadie entra por ellas, nadie se detiene en ellas y nadie deja mercaderia.
- Se entra solo por la celda de arriba, (3,28), y quien espera turno lo hace
  en esa entrada.
- Asi el que descarga siempre tiene salida y no molesta a quien espera.

**Complementos que propuso el asistente:**

- **Fila de espera** por orden de llegada. La primera celda es la entrada;
  las siguientes se alejan de la zona, sin cortar el paso ni tapar bocas de
  pasillo ni desembocaduras de salidas. Si la fila esta llena, los que sobran
  esperan en las zonas de espera que ya existen (`zonas_espera`,
  `subsystems/simulation/idle_zones.py`) y se los llama por turno.
- **Generalizar** el mecanismo como reglas de circulacion por celda: sentido
  permitido y "prohibido detenerse". Esas reglas las respetan los dos
  buscadores de rutas (`pathfinder.py`, A* estatico, y `spacetime_planner.py`,
  SIPP/A* espacio-temporal con `reservation_table.py`).
- **Entrada, salidas y fila se deducen solas** para cualquier layout. El
  cliente las ajusta a mano por zona desde la web, con validacion contra el
  mapa. Una capa del visor las muestra.
- **Puestos de descarga simultaneos** por zona (configurable): se dejan para
  despues.
- **Fase B**: pasillos de picking o de transito de un solo sentido, definidos
  por el cliente. Hay dos consecuencias conocidas:
  - las distancias dejan de ser simetricas (hay que revisar el armado y el
    orden de los recorridos: `route_calculator.py`,
    `assignment_calculator.py`, `dispatcher.py`);
  - hay riesgo de trampas (celdas desde donde no se puede volver), asi que
    hace falta validar la conectividad fuerte del mapa.

**Pregunta de fondo del Director:** conviene resolver esto ya, o priorizar
antes la migracion del layout (`.tmx` + Excel) a un modelo de almacen propio.
Esa migracion es INIT-10; ver `docs/BACKLOG.md` y `docs/ANALISIS_LAYOUTS.md`.
Horizonte de INIT-10: mezaninas, cintas, sorters, OSR/GTP, alineacion con el
estandar LIF (VDMA).

Recomendacion actual del asistente:

1. Hacer H-15 primero. La logica de circulacion no depende del formato del
   layout, pero las reglas se guardan con un esquema compatible con el modelo
   futuro.
2. Hacer ya la etapa 1 de INIT-10 (validar mapa contra Excel).
3. Dejar el QA del bloque 6 (Layout y Datos) para despues de INIT-10.

## 4. Preguntas para el consultor

1. **Diseno de la circulacion en la descarga.** La idea del Director mas los
   complementos, es la mejor solucion realista? Que hacen los almacenes
   reales y los simuladores profesionales (AnyLogic, FlexSim, etc.) para la
   cola frente a una estacion de descarga?
   - Proponer el mecanismo: turnos, fila, llamado desde las zonas de espera,
     garantia de salida.
   - Explicar como se integra con el planificador espacio-temporal sin
     reintroducir bloqueos. Considerar los dos modos: outbound apagado (una
     celda por zona) y outbound encendido (carril de varias celdas,
     `outbound.py`, `warehouse.py`).
2. **Reglas de circulacion generales.** Como modelar sentido y "prohibido
   detenerse" por celda (o por arista) de forma que sirvan para la Fase B?
   - Que cambia en el A* estatico, en el SIPP y en la tabla de reservas?
   - Como tratar las distancias asimetricas en el armado y el orden de los
     recorridos?
   - Como validar la conectividad fuerte y explicarle al cliente que celda la
     rompe?
3. **Deduccion automatica en layouts arbitrarios.** Como deducir entrada,
   salidas y fila de cada zona en cualquier mapa, incluidos los casos
   degenerados: zona en rincon, pasillo de 1 celda, zonas pegadas entre si?
   Que hacer cuando no hay solucion?
4. **Donde viven estas reglas.** Opciones: `config.json` (como `zonas_espera`
   y `estacionamientos` hoy), una hoja del Excel, capas de objetos del `.tmx`,
   o el modelo propio de INIT-10. Recomendacion y esquema de datos concreto,
   pensado para migrar sin redisenar.
5. **Orden de trabajo.** H-15 antes o despues de INIT-10 (etapa 2)? Con que
   alcance minimo para no tirar trabajo? Si INIT-10 va primero, cual seria el
   esqueleto del modelo de datos que ya contemple la circulacion?

## 5. Codigo a leer (punto de partida)

- `src/subsystems/simulation/operators.py`: llegada a la descarga, espera y
  replanificacion (`_recorrer_tramo`, `_timewindow_execute_plan`,
  `_esperar_sin_estorbar`, `_outbound_nav_to`).
- `src/subsystems/simulation/spacetime_planner.py` (`find_path_st`,
  `plan_and_reserve`), `reservation_table.py` (`is_free`, `can_swap`),
  `pathfinder.py` (`find_path`).
- `src/subsystems/simulation/idle_zones.py`: reglas de celdas de espera y la
  verificacion de que no se corte el mapa.
- `src/subsystems/simulation/warehouse.py`: armado de planificador, zonas de
  espera y outbound. `outbound.py`: carriles de descarga.
- `src/core/config_schema.py`, `web_prototype/config_manager.py`: validacion.
- Documentos: `CLAUDE.md`, `docs/STATE.md`, `docs/BACKLOG.md` (BK-15, BK-22,
  BK-25, INIT-10), `docs/ANALISIS_LAYOUTS.md`,
  `docs/PLAN_QA_CONFIGURACION_WEB.md`.

## 6. Entregable esperado

Un archivo `docs/PROPUESTA_DISENO_CIRCULACION_Y_LAYOUT.md` con:

1. Resumen ejecutivo en castellano simple, para el Director (sin jerga).
2. La solucion recomendada para H-15, con alternativas descartadas y por que.
3. El diseno de las reglas de circulacion y su esquema de datos.
4. La recomendacion de orden entre H-15 e INIT-10, con justificacion.
5. Un plan por fases, con archivos a tocar, riesgos, como medir el exito
   (co-ocupaciones, rendiciones, duracion con la flota 4+4) y que tests
   agregar.
6. Dudas que necesiten decision del Director.
