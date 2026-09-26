# Diseño INIT-13 — Realismo calibrable (Fases A y B)

> **Estado:** PROPUESTA para aprobación del Director (2026-09-26).
> **Origen:** `docs/INVESTIGACION_SIMULADORES_Y_PLAN_REALISMO.md` (investigación
> con fuentes). Aquí va el **qué** y el **por qué** de cada feature; el **cómo**
> se detalla en el plan de cada entrega cuando se apruebe.

---

## 1. Propósito

**Que un cliente vea a su propia operación reproducida en el simulador, con
sus números, y le crea.**

Hoy el simulador responde "¿qué pasaría si...?", pero no puede probar que
parte de la realidad. Un cliente que conoce su almacén mira el primer
resultado, lo compara con su experiencia y, si no coincide, descarta todo lo
demás. La industria lo resuelve así: se construye el modelo de la operación
actual, se lo alimenta con días reales y se muestra, día por día, **real
contra simulado con un margen de error acordado de antemano** (Sargent, Law).
La referencia pública es Amazon: 9,5 % de error en throughput contra 8.228
turnos reales.

Para eso hacen falta dos cosas, que son las dos fases de este diseño:

- **Fase A — Prueba contra la realidad.** Traer los datos reales del cliente,
  medir su operación con las mismas reglas con que medimos la simulación,
  compararlas y ajustar los parámetros hasta que coincidan en días que el
  ajuste no vio.
- **Fase B — Reloj completo.** Modelar lo que hoy falta en el turno
  (descansos, suplementos, preparación, altura, aceleración, diferencias entre
  personas). Entre 25 y 40 % del turno real no existe en el modelo. Sin eso,
  ninguna calibración cierra honestamente: el optimizador compensaría con
  parámetros imposibles.

**La promesa que queremos poder hacerle al cliente:**
> "Con tu layout, tus pedidos de estos N días y tu dotación, el simulador
> reproduce la duración de tus turnos y tus líneas por hora con un error de
> X % en días que no usamos para ajustarlo. Estos son los días, uno por uno."

## 2. Principios que rigen el diseño

1. **Realismo primero.** Si la calibración necesita un valor físicamente
   imposible (caminar a 3 m/s, picks de 1 s), no se acepta: se reporta como
   error de estructura del modelo y se investiga qué falta.
2. **Configurable y visible.**
   - Todo parámetro nuevo vive en `config.json`, se edita en la web y se
     registra en `config_schema.py`.
   - Los datos maestros nuevos (nivel, altura) viven en el Excel y la base.
   - Cada supuesto automático avisa con `[WARN]`.
3. **Las mismas definiciones para lo real y lo simulado.** Un KPI se calcula
   con **un solo código** tanto sobre el registro del cliente como sobre el
   replay. Si no, comparamos peras con manzanas.
4. **Neutro por defecto.** Cada feature llega apagada o con valores que
   reproducen el comportamiento actual. El gate byte-idéntico no se mueve
   hasta que el Director decida encenderla en el canónico.
5. **Los datos del cliente no se versionan.** Viven en `data/clientes/<cliente>/`,
   que queda en `.gitignore`, igual que `warehouse.db` y `uploads/`.
6. **Calibrar y validar son cosas distintas.** Los días del cliente se parten
   antes de empezar: unos se usan para ajustar y los otros quedan reservados
   para validar, sin mirarlos antes.

## 3. El recorrido del usuario (cómo se usa)

Nace una pestaña nueva en la web, **"Validación con datos reales"**, que guía
cinco pasos:

```
1. Subir datos del cliente   -> registro de operación (CSV) + registro de turnos
2. Revisar                   -> el validador muestra días, operarios, errores y avisos
3. Medir la realidad         -> KPIs reales por día (mismas reglas que la simulación)
4. Calibrar                  -> estudio automático sobre los días de calibración
5. Validar e informar        -> días reservados: real contra simulado, error,
                                 banda, curvas + informe para el cliente
```

Cada paso deja un resultado guardado. Un "estudio de validación" se puede
reabrir y rehacer, como hoy un estudio de optimización.

---

## 4. Fase A — Prueba contra la realidad

### A1. Registro de operación: formato estándar + importador

**Por qué:** cada WMS exporta distinto. Si definimos UN formato propio y
simple, el trabajo por cliente se reduce a un conversor de su export a
nuestro formato. Todo lo demás queda igual para todos.

**Qué es:** dos archivos CSV.

*Registro de movimientos* (una fila por movimiento confirmado; revisado el
2026-09-26 con lo que exportan de verdad SAP EWM, Manhattan e Infor, ver
`docs/PEDIDO_DE_DATOS_CLIENTE.md`):

| Columna | Obligatoria | Uso |
|---|---|---|
| `documento` (pedido o entrega), `linea` | sí | Identidad |
| `producto`, `cantidad` | sí | Qué y cuánto (cruza con el maestro de productos) |
| `origen`, `destino` | sí | Ubicaciones (cruzan con el maestro de ubicaciones) |
| `usuario` | sí | Quién |
| `hora_confirmacion` | sí | La marca que tienen todos los WMS |
| `hora_inicio` | no | SAP e Infor la tienen. Sin ella se usa la confirmación anterior del mismo usuario ("de escaneo a escaneo") |
| `ola`, `recurso` o `equipo` | no | Si vienen, se usan |

**Las etapas NO se piden: se deducen.** El tipo de ubicación de origen y de
destino (maestro de ubicaciones: picking, reserva, pulmón, estación, muelle)
dice qué fue cada movimiento: rack → pulmón es un pick, pulmón → muelle es un
traslado. Las tareas "en el lugar" que no generan movimiento (empaque, film)
no quedan en ningún WMS con hora propia. Se toman de la pregunta 3 del pedido
de datos (tiempo aproximado) o de la diferencia entre llegada y salida en la
estación.

**Conversores por sistema.** El export de cada WMS trae sus propios nombres de
columna (`CONFIRMED_AT_WH`, `EDITDATE`, ...). Hay un conversor por sistema
(SAP EWM, Infor, Manhattan) que lo traduce al formato de arriba. Se hace una
vez y sirve para todos los clientes de ese sistema.

*Registro de turnos* (una fila por persona y día): `fecha`, `operario`,
`equipo`, `entrada`, `salida` y descansos (`inicio`, `duracion`, repetible).

**El importador:**
- Valida contra los datos maestros: SKU o ubicación inexistentes, horas
  desordenadas, operarios sin turno, líneas fuera del turno. Cada problema
  dice qué corregir y dónde.
- Muestra un resumen: días, líneas por día, operarios por día y cobertura
  (qué % de las líneas se puede reproducir).
- Genera, **por día**:
  - un archivo de pedidos para el modo determinista, con la hora de
    liberación y la ubicación real;
  - la dotación del día (las `personas` con su equipo y su horario);
  - el estado inicial.

**Cambios en el motor** (opt-in, sin estas columnas nada cambia):
- **Hora de liberación por pedido:** una tarea no es elegible antes de esa
  hora. Es el mismo mecanismo que ya usan las olas
  (`dispatcher._wo_elegible_por_ola`), pero por pedido.
- **Ubicación fija por línea:** se usa la ubicación que se usó en la
  realidad, no la que elegiría el stock. Si no, el viaje simulado no es el real.
- **Dotación con horario:** cada persona entra y sale a su hora. Se engancha
  con `inicio_turno` y con el turno de B1.

**Decisión de diseño:** la simulación reproduce las **entradas** (qué
pedidos, cuándo y quién trabajó), **no** las decisiones (quién tomó cada
pedido). Así se valida también el despacho. Si hace falta aislar una
diferencia, queda como variante futura "reproducir la asignación real".

### A2. Medición de la realidad (KPIs con las mismas reglas)

**Por qué:** es el principio 3. La comparación solo vale si "líneas por hora"
significa exactamente lo mismo en los dos lados.

**Qué es:** un módulo único, `core/kpis_operacion.py`, que recibe una lista
de eventos normalizados (pedido, línea, operario y hora de cada pick y de
cada entrega) y calcula:

| KPI | Definición |
|---|---|
| Duración del turno | Primera liberación → última línea terminada |
| Líneas por hora | Líneas / duración |
| Líneas por persona-hora | Líneas / suma de horas presentes (del registro de turnos) |
| Tiempo por pedido | Liberación → última línea del pedido (mediana, p90 y distribución) |
| Utilización por operario | Tiempo con tarea / tiempo presente |
| Curva acumulada | Líneas terminadas contra hora del día |

La misma función se aplica al registro del cliente y al replay (`.jsonl`) de
la simulación.

### A3. Comparador real contra simulado

**Por qué:** es lo que el cliente ve y lo que lo convence.

**Qué es:**
- Por cada día: KPI real, KPI simulado (media e intervalo de confianza con N
  semillas), diferencia en % y si cae dentro de la banda acordada (verde o
  rojo).
- Resumen: error WAPE global por KPI.
- Curvas acumuladas, real y simulada, superpuestas.
- Distribución del tiempo por pedido (real contra simulado).
- Una vista "a ciegas" con curvas sin rotular, para que el supervisor del
  cliente diga cuál es la real (el test de Turing de Sargent).
- Reporte exportable a Excel (hoja por día + resumen) y una página imprimible
  para presentar.

**La banda de aceptación** es un parámetro del estudio, acordado con el
cliente **antes** de ver los resultados. Propuesta: ±5 % en duración y
líneas por hora, ±10 % en tiempo por pedido.

### A4. Extracción de tiempos desde el registro ("minería de tiempos")

**Por qué:** calibrar a ciegas es lento y engañoso. Si el registro ya nos
dice cuánto tarda un pick de verdad, empezamos cerca.

**Qué hace:**
- Para cada operario, el intervalo entre dos confirmaciones consecutivas se
  descompone así:
  `intervalo = viaje estimado + pick + otros`.
  El viaje estimado es la distancia del mapa (nuestro A*) por la velocidad
  del equipo.
- Agrupa por clase de manejo, por nivel (con B3) y por operario, y ajusta
  distribuciones (Kolmogorov-Smirnov).
- Detecta intervalos largos (descansos, esperas) y los separa, para que no
  inflen el pick.
- **Salida:** valores sugeridos para `pick_time_model`, clases, velocidad
  efectiva, suplemento PFD y habilidad por operario, cada uno con su
  dispersión. Los valores no se aplican solos: se proponen y el usuario los
  acepta.

**Límite honesto:** el WMS no registra trayectorias. Viaje y pick se separan
con un supuesto (la ruta más corta). Si el cliente tiene posicionamiento en
tiempo real (RTLS), se reemplaza el supuesto por la medición (futuro).

### A5. Calibración automática

**Por qué:** hay parámetros que no salen directo del registro (congestión,
suplementos, preparación). Un estudio de optimización los ajusta para que los
KPIs simulados coincidan con los reales.

**Qué es:**
- Un **tipo nuevo de estudio en el optimizador actual** (Optuna,
  `src/tools/optimizer.py`), con la misma pestaña, el mismo runner, la misma
  tabla de trials y el mismo botón Detener.
- **Parámetros:** los de B (turno, suplementos, preparación, velocidades,
  aceleración, habilidad), cada uno con **rango físicamente plausible**
  predefinido y editable.
- **Objetivo:** WAPE ponderado de los KPIs de los días de calibración + una
  distancia entre distribuciones de tiempo por pedido.
- **Partición de días:** 60–70 % para calibrar, el resto reservado, sin
  mirarlo hasta el final.
- **Semillas:** N por día, con intervalo de confianza del 95 %.
- **Salida:**
  - una configuración calibrada, guardada como réplica (BK-36) con nombre
    "Cliente X — calibrada";
  - un reporte de sensibilidad (qué parámetro mueve cada KPI).
- **Aviso:** si el mejor ajuste queda contra el borde de un rango ("la
  velocidad pide ir más lejos que el máximo plausible"), la web lo marca en
  rojo: falta modelar algo.

### A6. Prueba sin cliente: "cliente sintético"

**Por qué:** no podemos esperar a tener un cliente para saber si A1-A5
funcionan.

**Qué es:**
1. Se toma una configuración con parámetros **ocultos** (por ejemplo, pick
   base 13 s y PFD 12 %) y se simulan 15 días.
2. Del replay se genera un registro de operación con el formato de A1,
   agregando ruido realista.
3. Ese registro se pasa por el flujo completo, partiendo de otros parámetros.
4. **El flujo tiene que recuperar los valores ocultos** dentro de una
   tolerancia, y la validación en días reservados tiene que dar verde.

Es la prueba de aceptación automática de la fase A, y queda como test.

---

## 5. Fase B — Reloj completo

Cada feature tiene un valor neutro que reproduce el comportamiento actual.
Los valores de referencia sugeridos vienen de la investigación, con su fuente
en la web junto a cada campo.

### B1. Turno, descansos y suplementos

**Por qué:** es lo que más separa el turno simulado del real: 9–20 % de
suplementos + descansos + arranque y cierre. Hoy vale 0 %.

**Qué es:** un bloque `turno` en `config.json`, con card en la web:
- **Horario del turno** (inicio y fin) y **descansos** (hora y duración,
  varios). Con el registro de turnos de A1, cada persona tiene los suyos.
- **Qué hace el operario al llegar el descanso:** termina el recorrido en
  curso (recomendado) o lo corta. Va a la zona de descanso: un estacionamiento
  o una celda de espera, **sin estorbar**.
- **Arranque y cierre:** minutos al inicio (login, tomar equipo) y al final.
- **Suplemento PFD** (%): multiplica los tiempos de trabajo netos, como en
  cualquier estándar (tiempo estándar = normal × (1 + PFD)). Referencia:
  personal 5 %, fatiga 3–5 %, demora 2–4 %.

**Visible:** el visor muestra a los operarios "en descanso" y el tablero
reporta el tiempo por categoría (trabajo, viaje, espera, descanso, arranque y
cierre). Es lo que el cliente espera ver.

### B2. Preparación por recorrido y método de captura

**Por qué:** en las dos descomposiciones clásicas del tiempo del picker,
"preparación" y "otros" suman 15–25 %. El método (papel, RF, voz, luz) cambia
segundos por línea, y el cliente suele querer comparar tecnologías.

**Qué es:**
- `tiempos.preparacion`: segundos al **empezar** un recorrido (tomar carro o
  pistola, leer la lista) y al **terminarlo** (dejar carro, cerrar), por tipo
  de equipo.
- `tiempos.metodo_captura`: el método elegido y sus segundos por línea, con
  una tabla editable (papel, RF, voz, pick-to-light) y valores de referencia
  con su fuente.
- Queda listo para un A/B "RF contra voz" sin tocar nada más.

### B3. Altura y nivel de las ubicaciones

**Por qué:** hoy la horquilla tarda 8 s fijos, a 1 m o a 10 m. En la
realidad, a 6 m son más de 20 s solo de mástil. El picker a pie también
tarda distinto agachado o estirado; es la variable que más usan los
estándares de ingeniería (MTM y MOST: recargo por postura).

**Qué es:**
- **Datos maestros:** columna nueva `nivel` en la hoja `PickingLocations`
  (y en la base y en la tabla editable de la web). Sin la columna, todo queda
  en nivel 1 y el tiempo es el actual, con `[WARN]`.
- **Configuración de niveles:** altura en metros por nivel y recargo de
  postura por nivel para el operario a pie (agacharse en el nivel bajo,
  estirarse en el alto).
- **Por equipo:** velocidad de elevación y de descenso, con carga y sin
  carga. Referencia de hojas técnicas: reach truck 0,28–0,43 m/s.
- **Tiempo de horquilla** = altura / velocidad de elevación + altura /
  velocidad de descenso. Reemplaza los 8 s fijos cuando hay niveles.
- **Validación:** avisa si una ubicación de altura es atendida por un equipo
  sin elevación (esto ya existe como regla de equipo por área) o si la altura
  supera la elevación máxima del equipo (dato nuevo por equipo).

### B4. Aceleración, frenado y giros

**Por qué:** todos los simuladores comerciales usan un perfil trapezoidal:
acelerar, ir a velocidad crucero y frenar. En recorridos cortos, que son la
mayoría en un almacén, la velocidad máxima casi no se alcanza. Nuestra
velocidad constante subestima el viaje corto y sobreestima el largo.

**Qué es:**
- Por equipo: aceleración y frenado (m/s²) y velocidad en giros o dentro de
  pasillo.
- El tiempo de cada tramo se calcula con el perfil: las primeras y últimas
  celdas son más lentas y cada giro frena.

**Riesgo principal:** el planificador espacio-temporal reserva cada celda con
una duración fija por paso (`time_per_cell × speed`). Con el perfil, **cada
paso tiene su propia duración**. El plan y la ejecución deben usar el mismo
perfil o reaparecen choques. Es la entrega más delicada de la fase: va última
y con tests de invariantes (0 co-ocupaciones) sobre los 21 escenarios de QA.

### B5. Diferencias entre operarios

**Por qué:** entre personas hay ±10–16 % de diferencia (Matusiak, De Koster y
Saarinen, 2017). Si todos rinden igual, el modelo no puede reproducir un día
con un novato ni explicar por qué un turno rindió menos.

**Qué es:**
- Un multiplicador de **habilidad** por persona o grupo (en `personas`).
- Una **rampa de aprendizaje** opcional: semanas desde el ingreso → 70 %, 85 %
  y 100 % del estándar (práctica de LMS).
- A4 sugiere la habilidad de cada operario a partir de su registro.
- La fatiga dentro del turno queda **fuera** por ahora: la evidencia
  cuantitativa es débil y B1 (descansos + PFD) ya la cubre en promedio.

---

## 6. Qué se toca (mapa de impacto)

| Pieza | Features |
|---|---|
| `order_strategies.py` (archivo de pedidos) | A1: hora de liberación, ubicación fija |
| `dispatcher.py` | A1: elegibilidad por hora de liberación; B1: no asignar en descanso |
| `operators.py` | B1: descansos, arranque y cierre, PFD; B2: preparación y método; B3: horquilla por altura, postura; B4: perfil de velocidad; B5: habilidad |
| `spacetime_planner.py`, `reservation_table.py` | B4: duración por paso |
| `core/fleet.py`, `inicio_turno.py` | A1 y B1: dotación con horario |
| `data_manager.py`, importador, Excel | B3: columna `nivel` |
| **Nuevo** `core/kpis_operacion.py` | A2 (compartido real y simulado) |
| **Nuevo** `tools/registro_operacion.py` | A1 importador y validador, A4 minería, A6 cliente sintético |
| `tools/optimizer.py` + `optimization_runner.py` | A5: estudio tipo "calibración" |
| Web: pestaña nueva "Validación con datos reales" + cards en Estrategias y Flota | A1-A5, B1-B5 |
| `config_schema.py`, `MANUAL_CONFIGURACION.md` | Todas |
| `tests/` | Tests unitarios por feature + prueba de aceptación A6 |

## 7. Plan de ejecución (decidido por Cerebellum, 2026-09-26)

El Director delegó el orden. Criterio: **construir primero lo que todo lo
demás usa y nunca programar dos veces lo mismo.**

| # | Etapa | Qué se construye | Por qué va en este lugar |
|---|---|---|---|
| **E1** | Base de medición | Formato "registro de movimientos" + conversor **simulación → registro** + indicadores calculados SOBRE el registro + generador de **cliente sintético** (registro de la simulación + ruido) | Es la pieza que usan todas las demás. Si la simulación produce el mismo formato que el cliente, los indicadores se programan una sola vez y el cliente sintético sale casi gratis. Cuando llegue el Task Path, el conversor solo emite más filas |
| **E2** | Carga de datos del cliente | Importador + validador + conversores SAP EWM, Infor y Manhattan (probados con archivos sintéticos con sus columnas reales) + **pantalla "Validación con datos reales"** (subir, revisar, indicadores reales por día) | Necesita E1. El formato ya está validado contra lo que exportan los 3 sistemas |
| **E3** | Reproducir un día | En el motor: hora de liberación por pedido, ubicación fija por línea, **turno único** (dotación con horario + descansos + arranque/cierre + PFD) y **puntos de enganche "antes/después de cada recorrido"** | Descansos y dotación con horario son el mismo objeto "turno": se hacen juntos. Los enganches van **alrededor** del recorrido, no dentro del de picking, así sobreviven al Task Path |
| **E4** | Comparador | Botón "Simular este día", real contra simulado, curvas, diferencia, informe | Necesita E1-E3 |
| **E5** | Task Path + estaciones | INIT-11 F3 + F4 (plan revisado contra el mapa v3) + preparación por tipo de paso (B2) usando los enganches de E3 | Antes de calibrar: en un centro de distribución de varias etapas, la calibración no cierra sin la estructura |
| **E6** | Tiempos reales y calibración | Minería de tiempos (A4) + calibración automática (A5) + prueba de recuperación con el cliente sintético | Con la estructura completa, se calibra una sola vez |
| **E7** | Altura + ritmo por persona | Nivel por ubicación (horquilla, postura) + habilidad por operario | Afinan segundos; no cambian la estructura |
| **E8** | Aceleración y giros | Perfil trapezoidal (toca el planificador) | La más delicada, al final, con tests de invariantes |
| E9 | Tránsito (fase C) | Esperas que no estorban, pasillo con cola afuera, detector de bloqueos | Después, con la base medible de E1 |

**Cada etapa cierra con** tests, gate (PASS o cambio intencional explicado),
QA con clics reales en la web y documentación. Cada etapa es neutra por
defecto: sin datos nuevos, el simulador hace lo mismo que antes.

## 8. Riesgos

- **Datos reales sucios o incompletos** (horas que faltan, operarios
  compartiendo usuario). Lo mitigan el validador de A1, que dice qué
  corregir, y la cobertura mínima para aceptar un día.
- **Sobreajuste:** que la calibración "aprenda" los días en vez de la
  operación. Lo mitigan los días reservados y los rangos físicos (principio 1).
- **B4 rompe el invariante de 0 choques.** Va última, con tests de
  invariantes y apagada por defecto.
- **Rendimiento:** la calibración corre muchas simulaciones de días
  completos. Hoy una corrida tarda ~30–60 s: 30 trials × 10 días × 3 semillas
  son horas. Se mitiga con trials en paralelo (el optimizador ya soporta
  varios procesos) y empezando con pocos días.
- **Diferencias que no son de tiempos** (reposición, faltantes, cortes de
  camión). Se detectan porque la calibración no cierra en ciertos días, y se
  documentan para la fase D.

## 9. Decisiones (2026-09-26)

1. **Alcance y orden:** aprobados. El Director delegó el orden de ejecución
   (sección 7).
2. **Datos reales:** por ahora no hay cliente piloto. Se avanza con el
   **cliente sintético**, y los conversores de SAP EWM, Infor y Manhattan se
   prueban con archivos sintéticos que usan sus columnas reales.
3. **Margen de error:** no se compromete todavía. Primero se reduce el error
   lo más posible (cliente sintético y primer piloto). Con cada cliente, el
   margen se fija **antes** de mostrarle sus resultados.
4. **Formato:** registro de movimientos propio + un conversor por WMS
   (explicado y aceptado). El pedido de datos para el cliente está en
   `docs/PEDIDO_DE_DATOS_CLIENTE.md`.
5. **Descanso:** el operario termina el recorrido en curso y después va al
   descanso (práctica habitual; queda configurable).
