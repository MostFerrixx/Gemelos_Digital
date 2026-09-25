# MANUAL DE CONFIGURACIÓN — Gemelo Digital de Almacén

Manual completo del configurador web: qué es cada control, qué valores admite
y **qué efecto real tiene en la simulación**.

**Última actualización:** 2026-09-07 (verificado contra la UI en ejecución y
contra el código del motor).

---

## 0. Cómo empezar

**Abrir el configurador:** levantar el servidor (`start_server.bat`) y entrar a
`http://localhost:8000/web_configurator/index.html`.

**Concepto clave — dónde vive la configuración.** El archivo `config.json` de
la raíz del proyecto es **la única fuente de verdad**: el motor solo lo lee, y
la UI solo lo edita. Por eso importa la diferencia entre estos dos botones:

- **Aplicar Configuración** — escribe lo que ves en pantalla al `config.json`
  real. Es lo que va a usar la próxima simulación. Hace backup automático y
  escritura atómica.
- **Guardar** — guarda la configuración con un nombre **junto con una réplica
  de todo lo que usa**: el mapa (con su imagen), los datos del almacén en uso
  (ubicaciones, productos, carriles, muelles y stock, incluidos los cambios
  hechos desde la web), el Excel, el archivo de pedidos y el ASN. **No** toca
  `config.json`. Sirve para tener escenarios ("Alta demanda", "Flota chica") y
  compararlos en Experimentos A/B.
- **Cargar** — vuelve a dejar todo **tal cual estaba al guardar**: pone esos
  datos como los datos en uso (los anteriores quedan respaldados en
  `warehouse.db.bak`) y el formulario apunta a las copias guardadas. Para que
  sea la configuración vigente, apretá **Aplicar**. Una configuración que está
  en uso en `config.json` no se puede eliminar.

Si configurás algo y no apretás **Aplicar**, la simulación seguirá usando la
configuración anterior.

**La ayuda está plegada.** Para que la pantalla quede limpia, las explicaciones
de cada control están ocultas: el botón **ⓘ** junto a una etiqueta o al título
de una tarjeta la despliega ahí mismo, y **Acerca de esta sección** abre la
introducción de cada pestaña. El botón **? Ayuda** de la barra superior muestra
u oculta toda la ayuda de una vez (el navegador lo recuerda). Los avisos y
errores nunca se pliegan.

### La barra superior

En pantallas de menos de ~1760 px de ancho, las acciones secundarias
(**Restart, Default, Importar, Gestionar, Cargar, Guardar y Abrir Visor**) se
muestran **solo con su ícono**; al pasar el mouse aparece su nombre. Las dos
acciones principales (**Run Simulation** y **Aplicar Configuración**) siempre
muestran su texto.

| Botón | Qué hace |
|---|---|
| **Restart** | Reinicia el servidor web. Útil si la UI queda en un estado raro. |
| **Default** | Restaura el formulario a los **valores de fábrica** (`config_default.json`, o el preset que marques como predeterminado en Gestionar). No aplica nada hasta que apretes Aplicar. |
| **Importar** | Carga un `.json` de configuración desde tu disco al formulario. |
| **Gestionar** | Administra los presets guardados (renombrar, borrar, marcar predeterminado). |
| **Cargar** | Trae un preset guardado al formulario. |
| **Guardar** | Guarda el formulario actual como preset con nombre y descripción. |
| **Abrir Visor** | Abre el visor en otra pestaña con **la última simulación corrida** (si no hay ninguna, abre el visor vacío para importar una). |
| **Run Simulation** | Lanza la simulación con lo que ves en pantalla, **sin modificar el `config.json`** (usa una copia temporal). |
| **Aplicar Configuración** | Escribe el `config.json` canónico. **Este es el que "manda".** |

> ### Sobre "Run Simulation" y tu configuración
>
> **Corre lo que ves en pantalla, sin modificar el `config.json`.** Al apretar
> Run, la configuración del formulario se copia a un archivo temporal y la
> simulación usa esa copia. Así podés probar variantes libremente: el archivo
> del proyecto solo cambia cuando apretás **Aplicar Configuración**.
>
> Eso sí: la configuración **se valida igual** antes de correr. Si algo está
> mal (un porcentaje que no suma 100, la flota vacía), la simulación no
> arranca y el error te dice qué corregir.

### Las 8 pestañas

Se agrupan en dos bloques. **Configuración** (1-3) es el uso cotidiano;
**Avanzado** (4-8) son archivos, subsistemas opcionales y herramientas de
análisis.

---

# PESTAÑA 1 — Carga de Trabajo

Define **cuánto trabajo** hay que hacer y **de qué tipo**.

## Modo de Generación de Órdenes

Es la decisión más importante de esta pantalla: de dónde salen los pedidos.

| Opción | Para qué sirve |
|---|---|
| **Estocástico (Aleatorio)** | El simulador **inventa** los pedidos según una mezcla de tipos de producto que vos definís. Ideal para pruebas de capacidad, estrés y comparar estrategias sin depender de datos reales. |
| **Determinista (Archivo)** | Los pedidos salen de un archivo `.json`/`.csv` **real**. Ideal para reproducir un día concreto de la operación, o para validar el modelo contra lo que pasó de verdad. |

Al elegir **Determinista** aparecen estos controles:

- **Zona de carga de archivo** — arrastrás el `.json`/`.csv` con los pedidos.
- **Política de Cumplimiento** — qué hacer cuando un pedido tiene un ítem
  inválido (por ejemplo, un SKU que no existe en el catálogo):
  - **Envío Parcial (Ship Partial):** procesa los ítems válidos y descarta solo
    los inválidos. El pedido sale incompleto pero sale.
  - **Todo o Nada (Fill or Kill):** si un solo ítem falla, se descarta el pedido
    entero. Más estricto; refleja clientes que no aceptan envíos parciales.
- **Vista Previa de Validación** — antes de correr te muestra cuántas órdenes,
  ítems y SKUs se leyeron, y cuántos SKUs faltan en el catálogo, con el detalle
  de exclusiones. **Conviene mirarlo siempre**: si aparecen muchos SKUs
  faltantes, el archivo o el catálogo Excel están desalineados.

## Volumen General (solo en modo Estocástico)

- **Total de Órdenes** — cuántos pedidos se generan en la corrida. Es la palanca
  directa de carga de trabajo. Subirlo satura la flota; bajarlo la deja ociosa.

## Distribución por Clase de Manejo (solo en modo Estocástico)

Cinco porcentajes — **Pequeño, Mediano, Voluminoso, Pesado, Extra grande** — que
**deben sumar 100%** (la insignia arriba a la derecha lo valida en vivo y
bloquea el guardado si no cierra).

Definen qué proporción de los pedidos generados cae en cada clase de producto.
**Importante:** acá solo se controla *la mezcla*. La física real de cada clase
(volumen en m³, peso en kg) vive en la hoja `SkuCatalog` del Excel, no acá.

Por qué importa: una operación con 40% de "Extra grande" se comporta de forma
completamente distinta a una con 40% de "Pequeño" — cambian los tiempos de pick,
cuántas unidades entran por viaje y qué equipo hace falta.

---

# PESTAÑA 2 — Estrategias

El **cerebro** de la operación: cómo se decide qué hace cada operario y cuánto
tarda en hacerlo.

## Lógica de Despacho

### Estrategia de Asignación

Define cómo se elige la **primera** tarea de cada recorrido (el resto del
recorrido se arma siguiendo la secuencia de picking del Excel en los tres casos).

| Opción | Cómo decide | Cuándo conviene |
|---|---|---|
| **Optimización Global** (recomendado) | Evalúa **todas** las tareas compatibles y elige la primera por **costo** (minimiza el desplazamiento desde donde está parado el operario). | Es el default sensato: minimiza caminata muerta. |
| **Ejecución de Plan (Filtro por Prioridad)** | Ignora el costo: toma la tarea con el **número de secuencia más bajo** del área prioritaria. Sigue el plan del Excel al pie de la letra. | Cuando querés que el almacén respete un orden de recorrido planificado, aunque implique caminar más. |
| **Cercanía (Asignación por Proximidad)** | Solo considera tareas dentro de un **radio** alrededor del operario. | Para simular operaciones zonificadas, donde cada operario atiende su sector. |

Con **Cercanía** se despliegan tres campos adicionales:

- **Radio de cercanía (celdas)** — el operario prioriza tareas dentro de este
  radio. Default: 100. Es una *preferencia*, no una pared: si no encuentra nada,
  amplía.
- **Paso (celdas)** — cuánto se amplía el radio en cada intento fallido.
  Default: 50.
- **Máx. expansiones** — cuántas veces puede ampliar antes de rendirse y mirar
  todo el almacén. Default: 5. Con **0** no expande nunca.

## Configuración de Tours

### Tipo de Tour

| Opción | Qué hace |
|---|---|
| **Tour Mixto (Multi-Destino)** | Un mismo viaje puede juntar pedidos que van a **distintas zonas de salida**. Más eficiente en recorrido. |
| **Tour Simple (Un Destino)** | Cada viaje agrupa solo pedidos de **una misma zona de salida**. Menos eficiente al caminar, pero deja la mercadería ya separada por destino. |

Es un intercambio clásico: eficiencia de picking contra orden en el muelle.

## Motor Avanzado

- **Ruteo anti-colisión (time-window)** — los agentes **reservan espacio y
  tiempo** en su ruta y se esquivan entre sí, en vez de atravesarse como
  fantasmas. Apagado = ruteo clásico. Encendido es más realista y revela
  congestión en pasillos angostos (**activo en la configuración canónica**).
  Desde la corrección BK-15 (septiembre 2026) garantiza que **nunca haya dos
  operarios en la misma celda**: protege también a quien está quieto
  (pickeando varias tareas en el mismo lugar, descargando o esperando), y si al
  momento de entrar a una celda hay alguien, el que llega espera y replanifica.
  El costo es real: donde antes dos máquinas trabajaban a la vez en el mismo
  hueco del rack (imposible), ahora una espera a la otra.

  **Dónde esperan los operarios sin trabajo.** Quien no tiene tarea camina a
  una **celda de espera** y queda ahí como un obstáculo fijo: los demás lo
  rodean, nunca estorba. Por defecto el simulador elige esas celdas solo
  (bordes de los corredores, cerca de las zonas de descarga, nunca un punto de
  pick, una descarga, un muelle o sus accesos, ni una celda que corte el paso).
  Se pueden definir a mano con el bloque `zonas_espera` del archivo de
  configuración (rectángulos `x, y, ancho, alto`), que se valida contra el mapa
  con esas mismas reglas. Por ahora no tiene control en esta pantalla.
- **Subsistema outbound (carriles de carga)** — modela el muelle de salida en
  serio: pallets persistentes, un operario por columna, llenado de atrás hacia
  adelante. Apagado, la descarga es instantánea en el punto de entrega.

Al activar outbound aparecen:

- **Intervalo de camión (s)** — cada cuántos segundos llega un camión a retirar
  pallets. Más bajo = más camiones = el muelle se vacía más rápido. Default: 90.
- **Capacidad del camión (pallets)** — cuántos pallets carga un camión por
  viaje, siempre de **una sola zona de staging**. Default: 8.

## Tiempos de Operación

### Perfil de velocidad

| Opción | Qué significa |
|---|---|
| **Demo — rápido** | ~10× más rápido que la realidad. Para presentaciones: la simulación "se ve" avanzar. Valores: 0.1 s/celda, factor montacargas 0.8, horquilla 2 s. |
| **Real — calibrado** | Escala real, 1 celda = 1 metro, con benchmarks de industria (operario 1 m/s, montacargas 2 m/s). Valores: 1.0 s/celda, factor 0.5, picking 15 s/línea, horquilla 8 s. |
| **Personalizado** | Se selecciona solo cuando tus valores no coinciden con ninguno de los dos anteriores. |

**Para tomar decisiones de negocio usá "Real".** "Demo" sirve para mostrar.

Este bloque afecta al **desplazamiento** por el almacén, no al tiempo de
levantar productos (eso es la sección siguiente).

Campos individuales (el perfil los completa, pero podés editarlos a mano):

- **Tiempo por celda — Operario (s/celda)** — cuánto tarda un operario a pie en
  cruzar una celda del mapa.
- **Factor velocidad Montacargas** — multiplica el tiempo del operario. **Menor
  = más rápido.** 0.5 significa el doble de velocidad que una persona.
- **Tiempo de horquilla — Montacargas (s)** — subir/bajar la horquilla en cada
  operación. Es el costo de trabajar en altura.

## Tiempo de Pick por Producto

Cuánto tarda el operario en **levantar un producto del rack**. Ojo con la
distinción, porque es la confusión más común:

| | Qué mide | Dónde se configura |
|---|---|---|
| **Tiempo de pick** | Levantar el producto del rack | Acá |
| **Tiempo de descarga** | Dejarlo en la zona de salida | Flota de Agentes, por grupo |

Son dos momentos distintos del recorrido, por eso están separados.

La fórmula:

```
(base + s/unidad × cantidad + s/kg × peso) × multiplicador de clase + recargo de clase
```

> **¿Querés un tiempo fijo, igual para todo producto?** Poné ese valor en
> *Base por pick* y dejá los demás campos en 0. (Hasta septiembre de 2026 había
> un campo aparte para esto, "Tiempo de picking por línea"; se retiró porque no
> tenía efecto mientras la fórmula tuviera base, que es el caso normal. Los
> archivos de configuración viejos que lo usaban siguen funcionando igual.)

- **Base por pick (s)** — acercarse, escanear, posicionarse. Calibrado: 10 s.
- **Por unidad (s/u)** — cada unidad extra del mismo SKU. Calibrado: 2 s.
- **Por volumen** — término opcional; normalmente 0, porque el efecto del tamaño
  ya lo captura la clase de manejo.
- **Por peso (s/kg)** — el "factor fatiga": un artículo de 85 kg agrega ~13 s.
  Calibrado: 0.15 s/kg.
- **Mínimo (s)** — piso absoluto: ningún pick puede tardar menos.

## Clases de Manejo

Una grilla con seis filas — las cinco clases más **GENERAL (sin clase)**, que
aplica a los SKU que no tienen clase asignada. Cada una con tres campos:

- **Mult. de tiempo** — multiplica el tiempo de pick. Un "Extra grande" con 2.2
  tarda más del doble que un artículo estándar.
- **Recargo (s)** — segundos fijos que se suman (maniobra, ayuda de un segundo
  operario).
- **Pack (s)** — tiempo extra de **empaque en la descarga**. 0 = sin empaque.

Valores por defecto: Pequeño 0.8 / Mediano 1.0 / Voluminoso 1.3 (+3 s) / Pesado
1.5 (+5 s) / Extra grande 2.2 (+15 s).

## Velocidad según Carga *(opcional, apagado por defecto)*

Modela que **una persona cargada camina más lento** (dato biomecánico real:
1.35 m/s vacío → 1.10 m/s con 22 kg).

- **Reducción por kg** — cuánta velocidad se pierde por kilo. Calibrado: 0.0084.
- **Reducción máxima (0–0.9)** — piso de velocidad. Con 0.5, ni el operario más
  cargado baja del 50% de su paso normal.
- **Aplicar también a montacargas** — por defecto **NO**, porque el peso lo
  carga la máquina, no el cuerpo del operario.

## Variabilidad Humana *(opcional, apagado por defecto)*

Los tiempos dejan de ser un promedio fijo y pasan a seguir una distribución
Log-Normal (nunca negativa, con cola hacia la derecha).

- **Coeficiente de variación (CV)** — dispersión relativa. 0.25 = variación
  humana típica; 0.5 = operación muy irregular.

**Por qué encenderlo:** los promedios deterministas **sobreestiman la capacidad**
y esconden cuellos de botella. La corrida sigue siendo reproducible bajo la
misma semilla, así que los experimentos A/B siguen funcionando.

## Zonas de Picking por Pasillo *(opcional, apagado por defecto)*

Cada pasillo de picking es una zona. El simulador los deduce del mapa y los
numera de izquierda a derecha (en WH1 v3 hay 8). Como en un WMS de mercado, la
zona es un dato de la ubicación y **a quién le toca cada zona** es
configuración de la operación.

- **Asignación:** filas "quién → pasillos". *Quién* puede ser el id de un
  operario (`GroundOp-01`), su equipo o su tipo (`GroundOperator`,
  `Forklift`). *Pasillos* acepta listas y rangos: `1-3, 5`. Quien no figura
  trabaja en todo el almacén.
- **Si su zona no tiene trabajo, ayuda en otras:** encendido (recomendado),
  cuando a un operario no le queda nada en su zona toma trabajo de cualquier
  otra; apagado, se queda esperando. Ojo: si un área solo la puede hacer ese
  tipo de operario y nadie la tiene en su zona, sin esta casilla la corrida
  no termina.
- Un pasillo que no existe en el mapa se avisa en la consola (`[WARN]`); un
  texto que no se entiende bloquea la corrida con un mensaje.

Medido con 16 operarios (semilla 42): prácticamente igual que sin zonas
(2.714 s contra 2.652 s). Sirve para modelar una operación que ya trabaja por
zonas; no acelera sola.

## Cupo por Pasillo *(opcional, apagado por defecto)*

Cuántos operarios pueden estar a la vez dentro de un pasillo. El siguiente
espera afuera, en una celda donde no estorba, y entra cuando alguien sale.

- **Operarios por pasillo:** `0` = tantos como celdas de ancho tenga el
  pasillo (2 en WH1 v3).

Medido con 16 operarios: 3.345 s contra 2.652 s sin cupo (+26%). La capa
anti-colisión ya impide que se pisen; el cupo modela una regla de la
operación (por ejemplo, seguridad con montacargas).

---

# PESTAÑA 3 — Flota de Agentes

Quiénes trabajan, con qué capacidad y **dónde puede trabajar cada uno**.
Está organizada en tres tarjetas: **Equipo por Área**, **Operarios Terrestres**
y **Montacargas**.

## Generar Flota por Defecto

Botón en la cabecera de la tarjeta *Equipo por Área*. Crea de un saque una flota
estándar. Útil para arrancar. **Reemplaza la flota actual**, así que pide
confirmación.

- Arma un grupo de operarios a pie y uno de montacargas, de 2 agentes cada uno.
- Cada área va al grupo del equipo que indica el mapa *Equipo por Área*. Por
  eso la flota generada siempre cubre todas las áreas.
- Las prioridades se numeran 1, 2, 3… en el orden de las áreas del layout.
- Capacidad y tiempo de descarga: los de `fleet_defaults` si la configuración
  cargada los trae (hoy solo por Importar). Si no: 150 L y 5 s los operarios a
  pie, 1000 L y 5 s los montacargas.

## Tipo de equipo requerido por área

Un desplegable por cada área del almacén, con dos valores básicos:
**GroundOperator** (operario a pie) o **Forklift** (montacargas). Si la
configuración define **equipos** propios (ver más abajo), también aparecen
como opción, con su tipo entre paréntesis — por ejemplo
`trilateral (Forklift)`: así un área puede exigir un equipo concreto y no solo
"cualquier montacargas".

**Este es el control más importante de la pantalla, y conviene entender por qué.**
Es la fuente de verdad de qué equipo puede operar en cada área. Desde la
corrección BK-06 (septiembre 2026), **el mapa manda sobre todo lo demás**:

- Un operario a pie **no puede** recibir trabajo de un área asignada a
  montacargas, aunque en su lista de prioridades figure esa área. Antes sí podía,
  y eso permitía algo físicamente imposible: bajar mercadería de racks altos sin
  montacargas.
- El **tamaño de las tareas** de cada área se calcula con la capacidad del equipo
  que la atiende. Si un área es de montacargas, sus tareas se dimensionan para
  montacargas.

Si configurás un agente con prioridad en un área que no le corresponde, el motor
**avisa por consola** (`[WARN][CONFIG]`) y la ignora, en vez de degradar en
silencio.

> **Supuesto vigente a confirmar:** hoy el mapa asume que `Area_High` y
> `Area_Special` son 100% de montacargas y `Area_Ground` 100% de operarios a pie.
> Si en tu almacén real no es así, se corrige **acá mismo**, sin tocar código.
> Hoy el modelo admite **un solo tipo de equipo por área**; las áreas mixtas
> están pendientes (BK-07 en el backlog).

## Cobertura de áreas

Indicador en vivo, no editable. Marca en rojo las áreas del layout que quedaron
**sin ningún agente capaz**. Si hay áreas descubiertas o la flota está vacía,
**no se puede guardar ni correr** — es una protección para no lanzar una
simulación que se colgaría esperando a alguien que no existe.

## Aviso "Flota definida por personas y equipos"

Desde INIT-11 (septiembre 2026) el motor distingue a la **persona** del
**equipo** que maneja. Una configuración puede describir la flota así:

- **Equipos**: cada uno con su tipo base (GroundOperator o Forklift), su
  capacidad, su velocidad, el tiempo de horquilla y cuántas unidades hay.
- **Personas**: grupos con cantidad, nombres opcionales, el equipo que manejan,
  para qué equipos están habilitadas y sus prioridades por área.

El motor respeta tres reglas de realismo: la persona necesita un equipo
existente, tiene que estar habilitada para manejarlo y no puede haber más
personas con un equipo que unidades de ese equipo. Si algo no se cumple, no se
puede guardar y el mensaje dice qué corregir.

Cuando la configuración trae personas, **esa definición es la que usa el
motor**. La pestaña muestra la flota resultante con un aviso azul, pero
**editar los grupos aquí no tiene efecto**. La pantalla para editar personas y
equipos llega en una fase posterior del plan (F10); mientras tanto se definen
en el archivo de configuración.

## Perfiles de trabajo y estacionamientos de equipos

Una persona puede tener varios **perfiles**, en orden de prioridad. Cada perfil
dice qué tipo de tarea toma (hoy: *picking* y *guardado*) y con qué equipo. Al
terminar una tarea, la persona busca trabajo recorriendo sus perfiles en ese
orden.

Como cambiar de equipo cuesta tiempo real, hay una **regla de cambio**
configurable:

| Modo | Qué hace |
|---|---|
| `inmediato` | Vuelve a su perfil principal apenas hay trabajo ahí |
| `agotar` | Sigue en el perfil actual mientras le quede trabajo |
| `umbral` (por defecto, 3) | Sube a un perfil más prioritario solo si se acumularon N tareas |

En los tres modos, una persona sin nada que hacer termina tomando lo que haya:
quedarse parada no sería realista.

Los **estacionamientos** son puntos del mapa con capacidad y una lista de qué
equipos admiten. Para cambiar de equipo, la persona va hasta uno, deja el que
lleva y toma el otro, pagando el tiempo configurado en cada equipo
(`tiempo_cambio_s`, 30 s por defecto). Si no hay unidad libre de ese equipo o no
hay lugar donde dejar el suyo, ese perfil no se le asigna. Las coordenadas se
validan contra el mapa, igual que las zonas de salida y los muelles.

**Medido (17/09/2026)**, con 4 personas y la misma carga: con los pickers
atados a su equipo, la corrida terminó en 8.783 s y hubo 9.380 s de espera
acumulada; dándoles un segundo perfil y dejando una grúa libre en el
estacionamiento, terminó en 7.310 s (**17% menos**) con 3.346 s de espera.

## Aviso "Flota derivada de la configuración legacy"

Una configuración puede definir la flota de dos formas: **explícita** (lista los
grupos de agentes) o **por contadores** (solo dice "2 operarios y 2
montacargas"). La segunda es la forma histórica, y es como viene el
`config.json` canónico.

Cuando abrís una configuración de esa segunda forma, la pantalla reconstruye los
grupos automáticamente — consultándole al motor cuál sería la flota real — y te
muestra un aviso azul explicando de dónde salieron. Los grupos son **editables
como cualquier otro**, y al guardar quedan escritos de forma explícita.

> Antes de esta corrección, esa pantalla aparecía **vacía** con una
> configuración legacy y bloqueaba el guardado, aunque el motor corriera
> perfectamente. Si ves la pestaña vacía teniendo agentes configurados,
> es un síntoma de que algo falló al consultar el motor (mirá la consola del
> navegador).

## Grupos de agentes (Operarios Terrestres / Montacargas)

Se agregan con **+ Añadir Grupo**. Un "grupo" es un conjunto de agentes
idénticos. Cada grupo tiene:

- **Cantidad** — cuántos agentes de este tipo. La palanca más directa sobre la
  capacidad total del almacén.
- **Capacidad (L)** — cuánto volumen carga cada agente por viaje. Determina
  cuántas unidades entran antes de tener que volver a descargar, y también
  **cómo se dimensionan las tareas** de las áreas que atiende este tipo.
- **Tiempo de descarga (s)** — cuánto tarda en dejar la mercadería en la zona de
  staging. Es el tiempo de *entregar*, no el de *levantar del rack* (ese se
  configura en Estrategias).
- **Prioridades de Work Area** — filas de **Work Area** (desplegable con las
  áreas del layout) + **Prioridad** (número; **menor = más urgente**). Definen el
  orden en que el agente busca trabajo: primero agota su área de prioridad 1,
  después la 2, etc.

> Si el desplegable de Work Area aparece vacío, andá a la pestaña **Layout y
> Datos** y usá **Cargar Work Areas** para cargarlas.

---

# PESTAÑA 4 — Layout y Datos

De dónde salen el mapa y los datos maestros del negocio.

> ### Lo más importante de esta pantalla
>
> **El simulador no lee el Excel directamente.** Trabaja con una base de datos
> interna que se arma *a partir* del Excel. Por eso, si editás el Excel, los
> cambios **no tienen ningún efecto** hasta que apretás **Aplicar Excel**.
>
> La pantalla te avisa cuando esto pasa: si el Excel es más nuevo que los datos
> en uso, aparece una advertencia naranja.

## Archivos de Configuración

- **Archivo Layout (.tmx)** — el mapa físico del almacén (hecho con Tiled).
  Define pasillos, racks, muelles y zonas. Con **Examinar** podés subir uno
  nuevo: se valida (que se abra bien, tamaño y capas) **y que todas las
  ubicaciones, zonas de salida y muelles de los datos en uso queden dentro del
  mapa y sobre celdas transitables**. Si algo no cierra, se rechaza y el
  mensaje dice qué puntos fallan; si pasa, se actualiza la ruta.
- **Archivo de Secuencia (.xlsx)** — el Excel maestro: ubicaciones, secuencia de
  picking, catálogo de productos, zonas de salida y muelles. Con **Examinar**
  subís uno nuevo. **Subirlo no lo aplica**: primero te muestra qué contiene y
  si hay errores (hojas, columnas y coordenadas contra el mapa configurado: un
  carril sobre un rack o una ubicación fuera del mapa se rechazan); recién con
  **Aplicar Excel** pasa a usarse.

## Datos Maestros en Uso

Muestra lo que el simulador está usando **ahora mismo**: cuántas ubicaciones,
productos, zonas de salida y muelles. Debajo hay una tabla para revisarlos, con
selector, buscador y paginado. **Stock inicial por ubicación** muestra con cuánto
stock arranca cada corrida (el del último Excel aplicado). En las ubicaciones,
la columna *equipo (según Flota)* es el equipo que de verdad las atiende (son de solo lectura: las tablas grandes se editan
en el Excel, que es mejor herramienta para eso).

**Aplicar Excel** toma el archivo (el que subiste o el configurado arriba) y
reconstruye los datos del simulador. Antes de hacerlo te avisa, porque:

- **reinicia el stock inicial** al que diga el Excel, y
- **reemplaza las ubicaciones de zonas y muelles** que hayas ajustado a mano
  (ver más abajo).

Se hace una copia de seguridad automática de los datos anteriores antes de tocar
nada, y si la importación falla se restaura sola.

## Acciones de Datos

- **Cargar Work Areas** — carga en los desplegables de la pestaña Flota las
  áreas de trabajo **que usa el simulador** (las del último Excel aplicado). Si
  el Excel configurado trae áreas que todavía no se aplicaron, avisa. Ejecutalo
  después de aplicar un Excel nuevo.

## ¿Y las zonas y los muelles?

Sus **ubicaciones** (coordenadas) se pueden ajustar directamente, porque son
pocas: las zonas de salida en la pestaña *Outbound Staging* y los muelles en
*Inbound*, con el botón "Guardar ubicaciones". Recordá que aplicar el Excel de
nuevo las vuelve a los valores del archivo.

---

# PESTAÑA 5 — Outbound Staging

Por qué puerta sale cada pedido. Un camión se lleva pallets de **una sola zona
por viaje** (nunca mezcla rutas).

**Orden de precedencia** — un pedido elige su zona así, y el primero que aplica
gana:

1. Zona explícita en el archivo de órdenes.
2. Destino mapeado en **Destino → Zona** (abajo).
3. Reparto aleatorio por porcentaje.

## Rutas a Piquear (modo aleatorio)

Pestaña *Outbound Staging*. Cuántas rutas (o tiendas) se piquean en el turno.

- Con la casilla apagada, cada pedido aleatorio sortea su muelle por separado
  (el pedido entero sale por ese muelle; nunca se parte entre dos).
- Con la casilla encendida, el simulador crea esa cantidad de rutas y le ata
  cada una a un muelle. Todos los pedidos de una ruta salen por el mismo
  muelle, como pasa en la operación real con las rutas de reparto.
- El reparto por zona de abajo decide **cuántas rutas** le tocan a cada muelle:
  con 30% el muelle 1 se lleva el 30% de las rutas. Un muelle en 0% no recibe
  ninguna.

Es el equivalente, en modo aleatorio, del *Mapeo de destinos* que se usa con
pedidos de archivo.

## Reparto Aleatorio por Zona

Siete porcentajes (**Staging 1 a 7**) que **deben sumar 100%**. Es el último
recurso: se usa solo si el pedido no trae zona ni destino mapeado. Útil en modo
Estocástico, donde no hay destinos reales.

> Hoy la configuración canónica manda **100% a la zona 1**. Repartir el tráfico
> entre las 7 zonas reales es una decisión de negocio pendiente.

## Destino → Zona (por pedido)

Filas de **nombre de destino** (ej. `TIENDA_NORTE`) → **zona de staging (1-7)**.

Solo tiene efecto en modo **Determinista**, cuando el pedido trae el campo
`destino`. Los pedidos de un mismo destino **siempre salen agrupados**, sin
importar el reparto aleatorio. Es la forma de modelar rutas de reparto reales.

Si una fila tiene destino pero la zona está vacía o fuera de 1-7, la corrida
**no arranca** y el mensaje dice qué fila corregir (antes se ignoraba en
silencio y esos pedidos caían al reparto aleatorio).

---

# PESTAÑA 6 — Inbound (Recepción)

Todo lo anterior es **sacar** mercadería. Esta pestaña agrega **meterla**:
camiones que llegan a los muelles, descargan pallets y operarios que los guardan
(*putaway*).

**Con el inbound apagado, la simulación es solo de picking.**

- **Activar inbound (recepción + putaway)** — interruptor principal.

### Modo de llegadas

| Opción | Qué hace |
|---|---|
| **Determinista (archivo ASN)** | Cada camión, su hora y su contenido salen de un archivo. Escenario real y reproducible. |
| **Estocástico (intervalo fijo)** | Camiones sintéticos con SKUs muestreados del catálogo. Para prueba de estrés. |

- **Archivo ASN** *(modo determinista)* — JSON con la agenda de camiones
  (`truck_id`, `arrival_time` en segundos, líneas de SKU + cantidad, `dock_id`
  opcional). Ejemplo: `layouts/Inbound Test.json`.
- **Modo estocástico** — cuatro campos: **Intervalo entre camiones (s)**,
  **Cantidad de camiones**, **Pallets por camión**, **Unidades por pallet**. La
  agenda es finita: la simulación termina cuando todo lo recibido quedó guardado.
- **Descarga por pallet (s)** — cuánto tarda el camión en bajar cada pallet al
  muelle. El camión ocupa el muelle hasta bajar el último.
- **Cuándo se puede guardar cada pallet** — *Apenas se baja del camión*
  (default): cada pallet queda disponible para guardarse en cuanto toca el
  muelle. *Cuando se descargó el camión completo*: todos quedan disponibles
  juntos al terminar la descarga (operación que controla el camión contra el
  ASN antes de liberar). Con 10 pallets de 60 s, el primero espera 9 minutos
  más en el segundo modo.
- **Carga del pallet por el operario (s)** — cuánto tarda el operario en tomar el
  pallet del muelle antes de llevarlo a su ubicación.

### Prioridad de la flota compartida

Los mismos operarios hacen picking y putaway. Esto decide quién gana:

| Opción | Consecuencia |
|---|---|
| **Picking primero** | El putaway usa capacidad ociosa. Los pallets pueden esperar **horas** en el muelle si la flota está despachando. |
| **Recepción primero** | Los pallets se guardan apenas aterrizan, a costa del ritmo de picking. |

Compará ambos en Experimentos A/B con el KPI "espera pallet→agente".

### Cross-docking

**El stock del día rescata pedidos sin stock.** Solo en modo de pedidos
**Determinista**: si un pedido quedó sin stock al abrir y durante el día llega un
camión con ese SKU, se genera automáticamente el pick para cumplirlo en la misma
corrida. El KPI "fill-rate efectivo" muestra la mejora contra el fill-rate de
apertura.

> Si el modo de pedidos es Estocástico, la UI avisa que se desactivará solo: no
> hay pedidos reales que rescatar.

### Estrategia de Slotting

**Dónde se guarda cada pallet que llega.** Cada SKU vive en varias ubicaciones
posibles; la estrategia elige entre ellas. Es la palanca principal a comparar en
A/B.

| Opción | Lógica | Intercambio |
|---|---|---|
| **Fija por SKU** | Siempre el mismo slot (reposición clásica). | Predecible, pero puede implicar viajes largos. |
| **Más cercana al muelle** | Minimiza el viaje de guardado. | Guardás rápido hoy; podés pagarlo mañana al pickear. |
| **ABC por rotación** | Lo que más rota queda cerca del despacho. | Guarda más lento hoy, **pickea más rápido mañana**. |

---

# PESTAÑA 7 — Optimización

Búsqueda automática de la mejor configuración con Optuna. Corre N simulaciones
variando **flota, estrategia de despacho, tareas por tour y radio de cercanía**
(si aplica), buscando maximizar throughput contra costo.

- **Trials** — cuántas configuraciones distintas probar. Más = mejor resultado,
  más tiempo.
- **Jobs paralelos** — cuántas simulaciones a la vez. Limitado por tu CPU.
- **Costo Ground ($/h)** / **Costo Forklift ($/h)** — cuánto cuesta cada tipo de
  agente por hora. **Definen el intercambio**: si el montacargas es muy caro, el
  optimizador preferirá operarios a pie.
- **Penalización WO fallida ($)** — castigo por tarea no completada.
- **Penalización SLA vencido ($)** — castigo por pedido entregado después de su
  plazo. **Sin plazos (`due_time`) en los pedidos, no tiene efecto.**

El estudio corre en segundo plano; no hace falta dejar la pestaña abierta.
Muestra progreso, mejor score y los parámetros ganadores.

---


> **Qué cambia de verdad cada trial** (desde el 25/09): la cantidad de operarios
> a pie y de montacargas (repitiendo los grupos de la pestaña Flota, con su
> capacidad y prioridades), la estrategia y el tope de tareas por recorrido. El
> costo se calcula con la flota que realmente simuló. El primer trial es siempre
> tu flota actual. **Con menos de 11 trials la búsqueda es al azar**: para
> optimizar de verdad usá 30 o más. Una flota definida por *personas* (INIT-11)
> todavía no se puede optimizar: la pestaña lo avisa.
>
> **Tabla de trials:** debajo del mejor resultado se ve cada trial con la flota
> que pidió y la que se simuló de verdad (si alguna vez difieren, la fila se
> marca en rojo), la estrategia, el tope de tareas, las tareas por hora, el costo
> por hora y el puntaje. **Detener** corta el estudio: los trials que estaban
> corriendo quedan como "Falló o cortado".
>
> **Ojo con qué mide el puntaje:** tareas por hora dividido costo por hora, o
> sea **eficiencia**. Por eso suele ganar la flota más chica aunque tarde más.

# PESTAÑA 8 — Experimentos A/B

Compara **dos configuraciones** con rigor estadístico y dice si la diferencia es
**real** o **ruido aleatorio**.

**Por qué existe:** la simulación es estocástica. Dos corridas de la misma
configuración dan números distintos. Una sola corrida **no alcanza** para decidir.

- **Config A (referencia)** / **Config B (variante)** — "Actual" es el
  `config.json` vigente; el resto son los presets guardados con el botón
  **Guardar**.
- **Réplicas por config** — cuántas corridas de cada una. Más réplicas =
  veredicto más confiable pero más lento (~10-15 s por réplica). **Mínimo útil: 5.**
- **Semilla base** — ambas configuraciones usan **las mismas semillas**
  (pareadas), de modo que la diferencia observada sea de la configuración y no
  del azar.

Ejemplos de uso: comparar dos estrategias de slotting, "picking primero" contra
"recepción primero", o dos tamaños de flota.

---

# El Visor de Replay — "Saltar tiempos muertos"

El visor (botón **Abrir Visor**) reproduce una simulación ya corrida. En su
barra inferior, junto al selector de velocidad, hay una casilla:

**☐ Saltar tiempos muertos**  *(NN% sin movimiento)*

**El problema que resuelve.** En una corrida típica, **el ~94% del tiempo
simulado no se mueve ningún operario**: están haciendo picking, descargando o
esperando. Reproducida a 1x, esa corrida son ~145 minutos de los cuales solo
~8 tienen movimiento. Por eso el visor parece congelarse: no está trabado,
es que realmente no pasa nada durante minutos enteros.

**Qué hace.** Con la casilla activada, cuando la reproducción entra en un tramo
donde nadie se mueve, el reloj **salta directo al próximo instante con
movimiento**. El indicador al lado muestra el porcentaje de tiempo muerto del
replay, y avisa brevemente cada vez que salta ("saltando 227s sin movimiento").

**Qué NO hace.** No cambia la simulación ni los resultados: los KPIs, los
tiempos y los eventos son exactamente los mismos. Es solo la reproducción la
que omite las esperas — como adelantar los silencios de una grabación.

**Cuándo usarla.** Prendida para revisar una corrida completa rápido y ver
dónde hay actividad. Apagada cuando quieras medir el ritmo real de la
operación, porque justamente esas esperas son parte de lo que estás midiendo.

> Los saltos menores a 1 segundo no se omiten, para no perder continuidad.

---

# Apéndice A — Validaciones que bloquean

La UI impide guardar o correr si:

1. La **distribución por clase de manejo** no suma 100%.
2. El **reparto de staging** no suma 100%.
3. La **flota está vacía** o hay áreas del layout **sin ningún agente capaz**.

Son protecciones deliberadas contra simulaciones que se colgarían o darían
resultados sin sentido.

# Apéndice B — Flujo recomendado

1. **Layout y Datos** → cargá el mapa y el Excel; ejecutá **Cargar Work Areas**.
2. **Flota** → revisá el mapa de equipo por área, creá los grupos y verificá que
   la cobertura esté toda en verde.
3. **Carga de Trabajo** → elegí modo y volumen.
4. **Estrategias** → elegí perfil de velocidad (**Real** para decidir) y la
   lógica de despacho.
5. *(Opcional)* **Outbound Staging** / **Inbound** según lo que quieras modelar.
6. **Aplicar Configuración** → **Run Simulation** → **Abrir Visor**.
7. Para decidir entre dos opciones: guardá ambas como presets y usá
   **Experimentos A/B**. No decidas con una sola corrida.

# Apéndice C — Qué cambia el "comportamiento de referencia"

El proyecto tiene una prueba automática que verifica que el motor produzca
resultados **idénticos** ante la configuración canónica. Cualquier cambio que
apliques al `config.json` y que altere el comportamiento hará que esa prueba
falle — **lo cual es correcto y esperado** si el cambio fue intencional. En ese
caso hay que regenerar la referencia (tarea de desarrollo, no de configuración).

Los cambios más habituales que la alteran: total de órdenes, distribución de
clases, flota, estrategia de despacho, perfil de velocidad y reparto de staging.

---

*Referencias técnicas: `CLAUDE.md` (arquitectura y flags), `docs/STATE.md`
(estado vigente), `docs/PLAN_BK06_CAPACIDAD_AREA.md` (por qué el mapa de equipo
por área manda), `docs/antiguos/PLAN_INIT7_INBOUND.md` (contrato del inbound),
`docs/antiguos/PLAN_INIT8_TIEMPOS.md` (calibración de tiempos y fuentes).*
