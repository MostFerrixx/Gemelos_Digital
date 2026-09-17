# ANALISIS — Como generar los layouts del almacen

**Fecha:** 2026-09-16
**Pregunta del Director:** ¿Tiled (`.tmx`) sigue siendo la mejor forma de
generar los layouts? ¿Hay alternativas mejores, incluso en otro lenguaje?
**Estado:** analisis y recomendacion. No se toco codigo.

---

## 1. Que hace HOY el `.tmx` en el proyecto (verificado en el codigo)

El `.tmx` es un mapa de **Tiled**, un editor de mapas para videojuegos 2D. El
proyecto le saca cuatro cosas:

| Uso | Donde | ¿Imprescindible? |
|---|---|---|
| Tamano de la grilla (hoy 30 x 30) | `layout_manager.py` | Si |
| Que celdas son transitables (propiedad `walkable` de cada baldosa) | `layout_manager._build_collision_matrix` | Si: de esto depende el ruteo |
| Donde hay racks de picking (baldosas `type=picking_location`) | `layout_manager._extract_picking_points` | **No: solo se imprime en consola** |
| El dibujo del mapa en el visor | `routers/replay.py` (`/api/layout`) | Si |

Tambien trae dos zonas generales y un punto de deposito en capas de objetos,
que el motor no usa para nada funcional.

### Hallazgo 1: el almacen se describe DOS veces

Las 360 ubicaciones de picking estan marcadas en el mapa **y** listadas en el
Excel maestro, cada una con sus coordenadas, en dos herramientas distintas. El
motor usa las del Excel; las del mapa solo se cuentan para un mensaje.

Verificado el 2026-09-16: **hoy coinciden exactamente** (360 de 360, ninguna de
mas en ningun lado). Pero **nada lo garantiza**: si alguien agrega un rack en
Tiled y no en el Excel (o al reves), nadie se entera. Es el mismo patron de
"piezas que no se hablan" que ya aparecio con el campo fantasma y con el Excel
que no se aplicaba.

### Hallazgo 2: crear un almacen nuevo es un proceso largo y fragil

1. Instalar Tiled (programa externo).
2. Crear un mapa con los parametros correctos y cargar el juego de baldosas.
3. **Pintar celda por celda.** El mapa actual tiene 900 celdas; un almacen real
   de 100 x 60 metros tendria 6.000.
4. Armar el Excel con cada ubicacion y **coordenadas que coincidan exactamente**
   con lo pintado.
5. Subirlo y aplicarlo desde la web.

El paso 4 es el mas propenso a errores y no tiene ninguna ayuda.

### Hallazgo 3: la guia esta desactualizada

`docs/INSTRUCCIONES_LAYOUT_PERSONALIZADO.md` dice que la baldosa de picking se
llama `picking`, pero el motor busca `picking_location`; y menciona baldosas
(`corridor`, `wall`) que no estan en el juego de baldosas. Alguien que la siga
al pie de la letra obtiene un mapa sin ubicaciones.

### Hallazgo 4: no hay escala real

Tiled trabaja en baldosas de 32 pixeles. Que "una celda es un metro" es una
convencion que vive en otra parte de la configuracion (`cell_size_m`). Los
planos reales de un almacen estan en metros.

---

## 2. Lo que Tiled hace bien (para ser justos)

- Gratis, maduro y estable.
- Formato abierto, con una libreria de Python solida (`pytmx`).
- Visual y flexible: sirve para almacenes irregulares.
- **Ya funciona**, y el proyecto tiene 8 layouts hechos con el.

El problema no es que Tiled sea malo. Es que **es una herramienta de
videojuegos usada para describir un almacen**, y eso choca con los tres
principios rectores:

- **Realismo:** no hay escala real ni conceptos de almacen (pasillo, nivel, rack).
- **Configurabilidad:** vive fuera de la web; el cliente no lo puede tocar desde
  la aplicacion.
- **Usabilidad:** hay que instalar otro programa, aprender baldosas y capas, y
  mantener a mano la coincidencia con el Excel.

---

## 3. Alternativas investigadas

### A. Otro editor de mapas de videojuegos (LDtk, OGMO, MapperMate)

LDtk es la alternativa mas citada a Tiled; MapperMate funciona en el navegador.
**No lo recomiendo:** cambia una herramienta de videojuegos por otra y deja
intactos los tres problemas de fondo (dos descripciones, sin escala, fuera de
la aplicacion). Mucho esfuerzo de migracion para ganar casi nada.

### B. Importar planos de CAD (DXF / DWG)

Es lo que hace el software profesional: FlexSim importa DWG y DXF como layouts
a escala real y alinea estanterias y cintas a las lineas del plano. En Python
existe `ezdxf`, una libreria madura para leer DXF.

- **A favor:** es lo que el cliente real ya tiene (el plano de su almacen). Escala
  real. Maximo realismo.
- **En contra:** los planos de CAD vienen "sucios" (capas con nombres arbitrarios,
  lineas sueltas, textos); convertirlos en una grilla con racks y pasillos
  requiere convenciones y mucho criterio por cliente. Es un proyecto en si mismo.
- **Veredicto:** muy valioso a futuro, cuando haya clientes reales con planos.
  No como primer paso.

### C. Editor de layouts dentro de la propia web del proyecto ← recomendada

Un editor en el configurador web, con dos modos:

1. **Generador por parametros** para el caso tipico. La mayoria de los almacenes
   son regulares: pasillos paralelos de racks. Se describen con pocos numeros:
   *cantidad de pasillos, largo de cada pasillo, ancho de pasillo, orientacion,
   donde estan los muelles y las zonas de salida*. Con eso se genera el mapa
   completo **y las ubicaciones de picking al mismo tiempo**.
2. **Pintura manual** sobre la grilla para los ajustes: una columna, una pared,
   un sector irregular.

Existen proyectos que van en esta linea (por ejemplo `s-w3i/layout-management`,
un editor de almacenes en grilla que arma zonas arrastrando rectangulos y genera
los pasillos solo; y herramientas web comerciales de arrastrar y soltar racks).

- **A favor:**
  - **Elimina la doble descripcion de raiz**: el mapa y las ubicaciones nacen
    juntos, del mismo lugar. Ya no pueden desalinearse.
  - Coherente con todo lo que se construyo: el cliente configura todo desde la web.
  - Un almacen regular se arma en segundos en vez de pintarlo celda por celda.
  - Puede trabajar en metros desde el principio.
- **En contra:**
  - Es el camino mas trabajoso.
  - El motor y el visor hoy leen el `.tmx` directamente; habria que hacer que
    lean un formato propio (JSON). Eso es trabajo, pero ordena la arquitectura:
    una sola representacion del almacen para el motor y para el visor.
- **Tiled no desaparece:** queda como **importador**. Los 8 layouts existentes
  siguen sirviendo y se convierten al formato nuevo.

### D. Quedarse con Tiled y cerrar sus agujeros

- Validar al aplicar que el mapa y el Excel coincidan (y avisar si no).
- Corregir la guia.
- Opcional: generar el Excel de ubicaciones a partir de lo pintado en el mapa,
  para que la coincidencia sea automatica.

Barato y util, pero la experiencia del cliente sigue siendo "instala Tiled y
pinta celda por celda".

---

## 4. ¿Otro lenguaje de programacion?

**No hace falta, y no lo recomiendo.** El lenguaje no es el cuello de botella:

- Un editor grafico interactivo se hace naturalmente en el navegador, con
  JavaScript y canvas — **que es exactamente lo que ya usa la web del proyecto**.
- El motor esta en Python y no necesita cambiar para esto.
- Sumar un tercer lenguaje agregaria otra pieza que instalar, mantener y conectar,
  que es justo el tipo de complejidad que se viene eliminando.

El problema es de **donde** vive el editor (afuera, en un programa de
videojuegos) y de **cuantas veces** se describe el almacen (dos), no del lenguaje.

---

## 5. Recomendacion

Un camino en tres etapas, de menor a mayor esfuerzo, donde cada una sirve por si
sola:

| Etapa | Que | Esfuerzo | Resuelve |
|---|---|---|---|
| **1. Ahora** | Opcion D: validar mapa contra Excel al aplicar + corregir la guia | Medio dia | El riesgo de desalineacion silenciosa |
| **2. La apuesta** | Opcion C: editor web con generador por parametros, formato propio, Tiled como importador | 1 a 2 semanas | La doble descripcion, la experiencia del cliente, la escala |
| **3. A futuro** | Opcion B: importar planos DXF | 1 a 2 semanas + depende de cada cliente | El caso de clientes reales con sus planos |

**Tiled ya no es la mejor opcion para el proposito del producto**, pero tampoco
hay que tirarlo: sirvio para arrancar, tiene inversion hecha, y como importador
sigue siendo util. La mejora real no viene de cambiar de editor, sino de que el
almacen se defina **una sola vez y desde la propia aplicacion**.

---

## 6. ACTUALIZACION — Automatismos y mezaninas a mediano plazo

El Director agrego un dato que cambia el analisis: a mediano plazo quiere
modelar **mezaninas** (pisos elevados) y **automatismos**: sorters, GTP
(goods-to-person), OSR (order storage & retrieval, shuttles) y cintas
transportadoras.

### 6.1 Por que esto no entra en una grilla de baldosas

Esos elementos **no son celdas pintadas**:

| Elemento | Que necesita describir |
|---|---|
| Cinta transportadora | Recorrido con **direccion**, velocidad, capacidad, donde empieza y termina |
| Sorter | Una entrada y **varias salidas**, con reglas de desvio |
| OSR / shuttles | Niveles de almacenamiento, vehiculos, elevadores, tiempos de ciclo |
| GTP | Estaciones de trabajo fijas; el producto **viaja hacia la persona** |
| Mezanina | **Otro piso**, conectado por escaleras, ascensores o cintas verticales |

Tiled solo sabe "que baldosa hay en cada celda". No puede expresar direccion,
conexiones entre equipos, varias salidas ni pisos conectados. Forzar esto
dentro de Tiled seria inventar convenciones fragiles encima de una herramienta
que no fue pensada para eso.

### 6.2 Como lo resuelven los simuladores profesionales

Los tres grandes coinciden en el mismo patron, y **ninguno usa una grilla de
baldosas**:

- **AnyLogic** (Material Handling Library): las cintas se conectan entre si y
  forman una *red*; los items van por la ruta mas corta dentro de ella. Para
  varios pisos usa elementos especificos: ascensores (*Lift*), *level gates* y
  *network ports*.
- **FlexSim**: cada cinta es un objeto con inicio y fin; se conectan por
  *transfers* y puertos (incluso "encajando" una contra otra); los ASRS son
  vehiculos que reciben tareas.
- **LIF** (Layout Interchange Format, del VDMA aleman, licencia MIT, v1.0.0 de
  2023): el **estandar abierto de la industria** para describir recorridos de
  AGV/AMR. Es JSON, con coordenadas **en metros**, basado en un **grafo** de
  nodos, aristas y estaciones, y soporta **varios pisos** (un layout por nivel,
  con `layoutLevelId`). No describe cintas ni sorters por dentro: solo lo que
  recorren los vehiculos.

El patron comun es un **modelo por capas**:

1. **Niveles** (cada piso es un plano).
2. **Objetos con geometria en metros** (racks, cintas, sorters, estaciones).
3. **Conexiones** entre objetos (un grafo: cinta -> sorter -> cinta).
4. **Redes de movimiento** para personas y vehiculos.
5. **Conectores entre niveles** (ascensores, escaleras, cintas verticales).

### 6.3 Lo que esto implica para nuestro motor (honestamente)

- **El motor de rutas es de un solo piso.** El pathfinder y la tabla de reservas
  anti-colision trabajan con celdas `(x, y)`; no existe el concepto de nivel.
  Las mezaninas no son solo un problema de layout: **requieren extender el
  ruteo a `(nivel, x, y)`** con conectores entre pisos. Es un cambio de motor
  importante.
- **Cada automatismo es un subsistema nuevo**, no solo un dibujo: necesita su
  logica (tiempos de ciclo, capacidad, colas, reglas de desvio). El layout solo
  los ubica y los conecta.
- **GTP y OSR invierten el modelo actual.** Hoy el simulador mueve personas
  hacia el producto; en esos sistemas el producto va hacia la persona. Conviene
  tratarlo como un cambio de paradigma, no como una funcionalidad mas.
- **SimPy alcanza.** Es simulacion de eventos discretos pura: una cinta es un
  transito con capacidad, un sorter es un enrutamiento, un OSR es un recurso con
  tiempos de ciclo. **No hace falta cambiar de motor ni de lenguaje.**
- **Visualizacion:** con varios pisos, un visor 2D con selector de nivel alcanza
  al principio. Un visor 3D seria un plus, no un requisito, y se hace con
  librerias de JavaScript (la misma tecnologia de la web actual).

### 6.4 Como cambia la recomendacion

La direccion **se confirma y se refuerza**: Tiled no va a poder acompanar esto.
Pero cambia el orden de las prioridades:

> **Lo mas importante es disenar primero el MODELO DE DATOS del almacen**,
> pensado desde ahora para niveles, equipos y conexiones, **aunque hoy solo se
> implementen racks y pasillos**. Si se construye un editor para la grilla
> actual y despues llegan las cintas, habria que rehacerlo todo.

Estructura propuesta (a detallar en un plan):

```
almacen
 +- niveles[]            (hoy: 1)
 |   +- grilla            espacio caminable (lo que el motor ya sabe usar)
 |   +- almacenamiento    racks y ubicaciones, generables por parametros
 |   +- zonas             staging, muelles, areas
 +- equipos[]            cintas, sorters, OSR, GTP (hoy: vacio; el esquema los admite)
 +- conexiones[]         grafo entre equipos (salida de A -> entrada de B)
 +- enlaces_entre_niveles[]   escaleras, ascensores, cintas verticales
```

Para la parte de vehiculos conviene **alinearse con LIF** (nodos, aristas,
estaciones, metros, un plano por nivel): es el estandar de la industria y abre
la puerta a importar y exportar con sistemas reales de AGV/AMR, que es
justamente como funcionan muchos GTP.

### 6.5 Plan por etapas actualizado

| Etapa | Que | Por que en este orden |
|---|---|---|
| **1** | Validar mapa contra Excel + corregir la guia | Barato; cierra el riesgo de hoy |
| **2** | **Disenar el modelo de datos del almacen** (con niveles, equipos y conexiones) y hacer que el motor lo lea. Tiled pasa a ser importador | Es el cimiento. Todo lo demas se apoya aca |
| **3** | Editor web sobre ese modelo: generador de pasillos + pintura + colocar objetos | Ya con un formato que no habra que tirar |
| **4** | **Cintas transportadoras** como primer automatismo | Son la base: sorters, GTP y OSR se conectan a cintas |
| **5** | Sorters, luego OSR y GTP, cada uno como iniciativa propia | Cada uno tiene su logica |
| **6** | **Mezaninas**: ruteo multinivel en el motor + visor por pisos | El cambio de motor mas profundo; conviene hacerlo con el modelo ya estable |
| **A futuro** | Importar planos DXF | Cuando haya clientes reales con planos |

---

## Fuentes

- FlexSim (importacion de DWG/DXF a escala): https://www.simplan.de/en/software/flexsim-the-powerful-3d-simulation-software-for-production-and-logistics/
- Autodesk FlexSim, simulacion de almacenes: https://www.flexsim.com/warehousing-simulation/
- Comparativa de software de simulacion de almacenes 2026: https://www.guideflow.com/blog/warehouse-simulation-software
- Alternativas a Tiled (LDtk, OGMO, MapperMate): https://alternativeto.net/software/tiled-map-editor , https://www.saashub.com/ldtk-alternatives
- Editor de almacenes en grilla (open source): https://github.com/s-w3i/layout-management
- Planificador web de almacenes: https://warehouse-planner.com/
- ezdxf (lectura de DXF en Python): https://github.com/mozman/ezdxf , https://ezdxf.readthedocs.io/
- AnyLogic Material Handling Library (cintas, multinivel): https://www.anylogic.com/features/libraries/material-handling-library/ , https://www.anylogic.com/blog/conveyors-using-the-material-handling-library-part-1/
- FlexSim, conexion de cintas y ASRS: https://docs.flexsim.com/en/20.2/ConnectingFlows/Conveyors/WorkingWithConveyors/WorkingWithConveyors.html , https://docs.flexsim.com/en/19.0/Reference/3DObjects/TaskExecuters/ASRSvehicle/ASRSvehicle.html
- LIF, Layout Interchange Format (VDMA): https://github.com/Intralogistics-2X-LIF/Layout-Interchange-Format , https://scaliro.de/en/lif/
- Editor open source de LIF: https://github.com/bekirbostanci/vda5050_lif_editor
- Cintas en SimPy: https://medium.com/zebrax/manufacturing-line-optimization-using-discrete-event-simulation-5090ecade303 , https://simpy.readthedocs.io/
