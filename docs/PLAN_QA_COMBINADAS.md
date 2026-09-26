# PLAN DE QA — Pruebas combinadas y réplica de configuraciones

> **Documento vivo** (pedido del Director, 2026-09-26). Última parte del QA de
> la configuración web (`docs/PLAN_QA_CONFIGURACION_WEB.md`, sección 7). Se
> cambia **todo a la vez** —almacén (mapa + Excel), carga, flota/personas,
> estrategias, tiempos, inbound/outbound, zonas— y cada escenario se **guarda
> como configuración** (réplica BK-36) para comprobar después que, al cargarla
> desde otro estado, todo vuelve y funciona igual.

## 0. Estado

**Ejecutado 2026-09-26.** Fase 1: 21/21 corridos; 19 PASAN, C-14 y C-17 fallan
por dos hallazgos abiertos (BK-40, H-59). Fase 2 (réplica): 21/21 cargas
correctas desde otro almacén/estado; mismos resultados que en la Fase 1.
Hallazgos nuevos: **H-53 a H-59** (5 corregidos, 1 parcial, 1 abierto).
**Resultados:** sección 6.

## 1. Método

### 1.1 Cómo se arma cada escenario (por la web, con clics reales)

Con `scripts/qa/capturas_web.py` (Chrome real a 1440×900, clics de mouse,
teclado, archivos por el selector real):

1. **Almacén**: si el escenario usa otro almacén que el que está en uso, se
   sube su Excel por "Examinar" y se aplica con **Aplicar Excel** (la web
   valida que encaje con el mapa).
2. **Configuración**: se **importa** un `.json` preparado para el escenario
   (botón Importar, archivo real) con el mapa y el Excel del almacén.
3. **Toques a mano**: 1 a 3 controles propios del escenario se cambian con
   clics/teclado (así la prueba pasa también por la edición en pantalla, y el
   N1 verifica que esos cambios llegan a la corrida).
4. **Guardar** como configuración `QA-C-nn <descripción>` (réplica completa).
5. **Run Simulation** (clic real), se espera el fin y se verifica.

### 1.2 Niveles de verificación

- **N1** — la configuración que recibió la corrida (metadata del `.jsonl`)
  tiene lo que se armó en pantalla (incluidos los toques a mano).
- **N2** — el comportamiento del motor (eventos del `.jsonl`, métricas) cumple
  los criterios del escenario.
- **N3** — muestreo del visor (posiciones del visor = JSON) en escenarios con
  otro mapa.
- **R** — réplica: al cargar la configuración guardada **desde otro estado**
  (otro almacén en uso, otra configuración en pantalla) vuelven su mapa, sus
  datos y sus parámetros, y la corrida vuelve a cumplir los criterios.

### 1.3 Criterios comunes (aplican a TODOS los escenarios salvo que se diga)

| Código | Criterio |
|---|---|
| K1 | La corrida termina sin el vigilante de no-progreso ni errores |
| K2 | Todas las tareas quedan `staged` (o las fallidas/backorders esperables del escenario) |
| K3 | Cada tarea la hace un equipo que puede atender su área (mapa de equipo por área) |
| K4 | Con anti-colisión activa: 0 co-ocupaciones **fuera de la ventana de arranque** (invariante BK-15; se lee de `congestion_report`) |
| K5 | Los agentes que corren son exactamente los de la flota configurada |
| K6 | Las descargas ocurren en celdas de las zonas de salida DEL almacén en uso (con outbound, una zona de una celda se agranda a 8: se reconstruye con `build_zone_cells`; el guardado WO-PU descarga en el rack, no cuenta) |
| K7 | Ninguna tarea aparece dos veces en el mismo recorrido (agregado tras H-53) |

## 2. Almacenes disponibles

Cruzados con los validadores de la web (H-43):

| Almacén | Mapa | Excel | Datos |
|---|---|---|---|
| **A** canónico | `WH1 v3.tmx` 32×43 | `Warehouse_Logic_v3.xlsx` | 384 ubicaciones · 7 carriles de 2×10 (filas 30-39) · 3 muelles · catálogo (5 clases) |
| **B** viejo | `WH1.tmx` 30×30 | `Warehouse_Logic.xlsx` | 360 ubicaciones · 7 zonas de **una celda** en la fila 29 (la última) · 3 muelles · catálogo |
| **C** intermedio | `WH1 v2.tmx` 30×42 | `Warehouse_Logic_v2.xlsx` | 360 ubicaciones · 7 carriles de 2×10 (filas 29-38) · **sin catálogo ni muelles** |

`Almacen_Grande.tmx`, `Almacen_Pequeño.tmx` y `Layout_Corredor_Central.tmx`
están dañados (ni el simulador ni la validación los abren) → hallazgo, no se
usan. Los mapas `test*.tmx` y `Warehouse_personalizado1.tmx` no tienen Excel.

## 3. Fase 1 — Escenarios

Notación de flota: T = operario a pie (GroundOperator), M = montacargas.
Salvo que se diga: estocástico 300 órdenes, mezcla canónica, Ejecución de
Plan, Tour Mixto, anti-colisión activa, estaciones activas, outbound e inbound
apagados, perfil Demo.

### Almacén A (canónico)

| ID | Qué se cambia | Resultado esperado (además de K1-K6) |
|---|---|---|
| **C-01** | Nada: configuración canónica (control) | 300 pedidos, ~600 tareas staged; descargas solo en (3,30)/(4,30) (100% carril 1); 4 agentes; 0 co-ocupaciones |
| **C-02** | Optimización Global + **Tour Simple** + reparto 30/30/40 en zonas 1-3 + **outbound ON** (camión cada 90 s, capacidad 8) *(X.1)* | Ningún recorrido mezcla zonas; ningún camión mezcla zonas; solo se usan las zonas 1-3 en proporción ±8 pp; pallets despachados = tareas; ningún camión con más de 8 |
| **C-03** | **Cercanía** radio 5 + montacargas con prioridades High 1 / Special 2 *(X.2)* | Los montacargas solo hacen High/Special; hay expansiones de radio (radio chico casi nunca encuentra trabajo cerca de la descarga, H-13); se documenta qué manda: la compatibilidad de área filtra primero, el radio después |
| **C-04** | Fórmula de pick y clases canónicas, variabilidad OFF *(X.3)* | Cada pick dura exactamente `(10 + 2·q + 0,15·kg) × mult + recargo`, con mínimo 5 (muestra de ≥20 picks, error < 0,01 s) |
| **C-05** | **Variabilidad ON** (CV 0,25) *(X.4)* | Picks idénticos (mismo SKU y cantidad) duran distinto; CV observado 0,15-0,35; un A/B de la configuración consigo misma con igual semilla da IDÉNTICO |
| **C-06** | **Velocidad por carga ON** + capacidad terrestre **300** *(X.5)* | Pasos de un operario cargado más lentos que vacío (a igual celda de tiempo); ningún terrestre lleva más de 300; montacargas exentos |
| **C-07** | **Determinista** con archivo de 70 pedidos con `destino` (TIENDA_1..7) + **Destino → Zona** (tienda k → zona k) + **Tour Simple** *(X.6)* | Cada tienda sale entera por su zona; cada recorrido tiene una sola zona; 70 pedidos |
| **C-08** | **Inbound** estocástico (3×4, cada 300 s) + **Recepción primero** + slotting **cercana** + flota **1+1** *(X.7)* | Espera pallet→operario chica (< 600 s) y el picking termina más tarde que en C-01; 12 pallets guardados; 2 agentes |
| **C-09** | **Anti-colisión OFF** + flota **4+4** *(X.8)* | Co-ocupaciones > 0 (muchas); el visor las dibuja; 8 agentes |
| **C-10** | Perfil **Real** (1 s/celda) + **outbound ON** *(X.9)* | Duración ≥ 5× la de C-01; camiones con separación de ~90 s + carga; todos los pallets despachados |
| **C-11** | **Equipo por área**: Area_Special → GroundOperator; capacidades terrestre 200 / montacargas 800 *(X.10)* | Las tareas de Area_Special las hacen terrestres; Area_High solo montacargas; ninguna tarea de un área supera la capacidad del equipo que la atiende |
| **C-12** | **Personas y equipos** (Ana, Beto: transpaleta; Carla: grúa; Dario: trilateral para Special) + **Zonas por pasillo** (Ana 1-4, Beto 5-8, ayudar en otras ON) + **Rutas a piquear** 10 + reparto 7 zonas iguales | Agentes = Ana, Beto, Carla, Dario; Special solo Dario; Ana sale de los pasillos 1-4 solo cuando su zona se agotó; cada pedido en un solo carril; 7 carriles usados |
| **C-13** | **Perfiles + estacionamiento** (EST-1) + cambio por **umbral** 3 + **inicio de turno** en estacionamientos | Al menos un cambio de equipo; ninguna tarea de altura se recoge con transpaleta; los que tienen equipo con estacionamiento arrancan a ≤ 6 celdas de él |
| **C-14** | **Cupo por pasillo** = 1 + flota **4+4** + reparto en 7 zonas | Nunca hay 2 operarios a la vez en un mismo pasillo (verificado por posiciones); la corrida termina |
| **C-15** | **Inbound determinista** (ASN) + **cross-docking** + liberación **camión completo** + pedidos deterministas con faltantes (800 u SKU029, 340 u SKU046) | Se crean `WO-XD`; fill-rate efectivo > apertura; los pallets de un camión quedan disponibles juntos |

### Almacén B (viejo, zonas de una celda)

| ID | Qué se cambia | Resultado esperado |
|---|---|---|
| **C-16** | Almacén B con parámetros canónicos | Mapa 30×30 en la corrida; descargas en (3,29) (zona 1, una celda, un solo puesto); termina; el visor dibuja 30×30 (H-28) |
| **C-17** | B + **inbound** estocástico + **Recepción primero** + **outbound ON** + reparto 7 zonas | Muelles (3,1), (15,1), (27,1) en uso; todos los pallets guardados y despachados; descargas solo en las 7 celdas de la fila 29 |
| **C-18** | B + **Optimización Global** + flota **4+4** + mezcla **100% extra grande** + reparto 7 zonas | Todas las tareas de clase extra grande; picks largos (≥ 61 s); las 7 zonas usadas |

### Almacén C (sin catálogo ni muelles)

| ID | Qué se cambia | Resultado esperado |
|---|---|---|
| **C-19** | Almacén C con parámetros canónicos | Aviso de que las clases de la mezcla no tienen SKUs → mezcla uniforme; todos los SKU clase GENERAL (pick sin multiplicador de clase); termina; descargas en la fila 29 de los carriles |
| **C-20** | C + **inbound ON** | Aviso de que no hay muelles → inbound se desactiva; termina sin camiones de entrada |
| **C-21** | C + **Determinista** (archivo con SKUs existentes y uno inexistente) + **Todo o Nada** | El pedido con el SKU inexistente se descarta entero; el resto se sirve |

## 4. Fase 2 — Réplica (cargar lo guardado desde otro estado)

| ID | Prueba | Resultado esperado |
|---|---|---|
| **R-01** | Para CADA configuración guardada en la Fase 1, partiendo de un estado distinto (otro almacén aplicado y otra configuración en pantalla): **Cargar** (clic real) | Aviso "cargada tal cual se guardó"; formulario = lo guardado (flota, estrategia, toques a mano); la base en uso = datos de SU almacén (conteos y coordenadas de zonas/muelles); el mapa del formulario es la copia de la réplica |
| **R-02** | Tras cada carga de R-01: **Run** | Vuelve a cumplir los criterios de su escenario |
| **R-03** | Cargar C-16 (almacén B) → **Aplicar** → A/B "Actual" vs "QA-C-16", 3 réplicas, semilla fija | IDÉNTICO en todos los KPI |
| **R-04** | Igual con C-19 (almacén C) y C-12 (almacén A con personas) | IDÉNTICO |
| **R-05** | Borrar una réplica en uso por `config.json` | La web lo impide con el mensaje |
| **R-06** | Cierre: cargar "Canonico v3 (referencia)" + restaurar `config.json` | Gate de regresión PASS (datos y configuración canónicos intactos) |

## 5. Hallazgos previos a la ejecución

| # | Descripción | Estado |
|---|---|---|
| P-1 | Tres mapas de `layouts/` están dañados (Almacen_Grande, Almacen_Pequeño, Layout_Corredor_Central) | Confirmado: son esqueletos de una fila; la web ya los rechaza con un mensaje claro → **BK-38** (poda, con OK del Director) |
| P-2 | "Aplicar Excel" sin subir archivo usa el `sequence_file` de `config.json`, aunque la pantalla dice "el Excel configurado arriba" (el del formulario) | Confirmado en el código → **H-54, corregido** |

## 6. Resultados

Corridas por la web con clics reales (`scripts/qa/capturas_web.py`), guardadas
como `QA-C-nn ...` (réplica). Verificación automática sobre el `.jsonl` de cada
corrida (K1-K7 + criterios propios). Fin = duración simulada (s).

### 6.1 Fase 1 — escenarios

| ID | Resultado | Evidencia principal | Hallazgos |
|---|---|---|---|
| C-01 | **PASA** | 624 tareas staged; descargas solo en (3,30)/(4,30); 4 agentes; 0 co-ocupaciones | H-53 (salía en el control: 29 tareas repetidas) |
| C-02 | **PASA** (tras H-53) | 1.er intento FALLA: 19 pallets despachados dos veces. Tras corregir: 610 despachados = 610 tareas; 88 camiones, ninguno mezcla zonas ni lleva > 8; zonas 1-3 = 31,7 / 24,7 / 43,7 % | **H-53** |
| C-03 | **PASA** | Cercanía radio 5; montacargas solo High/Special | — |
| C-04 | **PASA** | 608/608 picks = fórmula exacta (error < 0,05 s) | — |
| C-05 | **PASA** | Con variabilidad solo 5/618 picks coinciden con la fórmula (los demás varían alrededor de la media) | — |
| C-06 | **PASA** | Terrestres cargan hasta 300; mediana 0,2 s/paso cargado vs 0,1 vacío | — |
| C-07 | **PASA** (tras H-55) | 1.er intento: la importación perdió el modo determinista y el archivo. Tras corregir: 70 pedidos, cada tienda en su zona, 26 recorridos de una sola zona | **H-55** |
| C-08 | **PASA** | 12 pallets guardados; espera pallet→operario 414 s; 2 agentes | — |
| C-09 | **PASA** | 12.932 instantes con dos agentes en la misma celda (contados desde el replay; el motor no calcula la métrica sin la capa: OBS); control C-01 = 0 | — |
| C-10 | **PASA** (criterio corregido) | 1,0 s/celda a pie y 0,5 montacargas medidos paso a paso. El "≥ 5× duración" era un error del plan: caminar es el 2 % del tiempo en C-01 (domina el pick) → 6.664 s → 12.036 s | BK-39 |
| C-11 | **PASA** | Special la hacen terrestres (107); carga máxima 200 / 800, nunca más | — |
| C-12 | **PASA** | Ana, Beto, Carla, Dario; cada pedido en un carril; 7 carriles. "Ayudar en otras zonas" no se ejercitó: el trabajo a pie se agotó a la par (3.611 / 3.631 s) y lo que queda es de altura | — |
| C-13 | **PASA** | 1 cambio de equipo en EST-1; todos arrancan junto al estacionamiento. 1 co-ocupación en t = 0 (dentro de la ventana de arranque, OBS) | — |
| C-14 | **FALLA (parcial)** | Con cupo 1 entraba un segundo operario con el primero adentro. H-56 lo bajó de 85 a 30 entradas; el resto (espera y cruce de pasillos ajenos) necesita diseño | **H-56**, BK-40 |
| C-15 | **PASA** | 2 `WO-XD`; fill-rate 90,1 → 93,2 %; los pallets de cada camión quedan disponibles juntos. 1.er intento sin archivo de pedidos: el servidor borraba `uploads/` al arrancar | **H-57** |
| C-16 | **PASA** | Almacén B aplicado por la web; mapa 30×30; descargas en la fila 29 | — |
| C-17 | **FALLA** | Inbound completo (12 pallets), 585 despachados, 7 zonas. 2 co-ocupaciones al salir de un carril de descarga sobre otro que esperaba en la boca. Zonas de una celda agrandadas a 8 sin aviso | **H-58**, **H-59** |
| C-18 | **PASA** | 715/715 tareas extra grande; 715/715 picks = fórmula | — |
| C-19 | **PASA** | 386/386 picks sin multiplicador de clase (GENERAL); `[STOCHASTIC][WARN]` por cada clase sin SKUs | — |
| C-20 | **PASA** | 0 eventos de inbound; `[INBOUND][WARN] ... sin muelles - inbound se DESACTIVA` | — |
| C-21 | **PASA** | Todo o nada: ORD-006 (SKU inexistente) descartado entero; 29 pedidos servidos | — |

### 6.2 Fase 2 — réplica (R-01 / R-02)

Cada `QA-C-nn` se cargó con clics reales (Cargar) desde OTRO estado: otro
almacén en uso (A↔B↔C) u otra configuración en pantalla. Se comprobó:
parámetros del formulario = los de la corrida de la Fase 1 (sin diferencias);
mapa, Excel y archivos apuntan a la copia de la réplica con el MISMO contenido
(sha256); la base en uso = la base de la réplica (tabla por tabla). Luego se
corrió de nuevo y se re-verificó.

| Resultado | Detalle |
|---|---|
| **21/21 cargas correctas** | Parámetros, mapa, datos y archivos (2 a 4 por réplica, incluidos los de pedidos y ASN) |
| **Mismos criterios que la Fase 1** | 19 PASAN; C-14 y C-17 fallan igual (BK-40, H-59) |
| **Deterministas: misma duración al segundo** | C-07 1.137 s, C-15 3.664 s, C-21 402 s |
| Estocásticos | Duración ±5-22 % (la web corre sin semilla fija; la comparación con semilla es la del A/B, R-03/R-04) |

### 6.3 Fase 2 — A/B, borrado y cierre (R-03 a R-06)

| Prueba | Resultado | Evidencia |
|---|---|---|
| **R-03** | **PASA** | Cargar QA-C-16 (almacén B) → Aplicar → A/B "Actual" vs "QA-C-16" (3 réplicas, semilla 1000): los 6 KPI **IDENTICO** (503 tareas, 6.507 s, 280,7 tareas/h) |
| **R-04** | **PASA** | Igual con QA-C-19 (almacén C) y QA-C-12 (personas): **IDENTICO** en todos los KPI |
| **R-05** | **PASA** | Eliminar la réplica en uso (QA-C-12 aplicada): la web lo impide ("La configuración vigente (config.json) usa archivos de esta réplica...") y no se borra nada |
| **R-06** | **PASA** (tras H-60) | Cargar "Canonico v3 (referencia)" → Aplicar → datos canónicos; con `config.json` del repo, gate byte-idéntico PASS. En el camino apareció **H-60**: Aplicar mezclaba y dejaba `personas`/`equipos`/`zonas_picking` de C-12 en `config.json`. Corregido y verificado con clics reales |

### 6.4 Hallazgos de estas pruebas

| # | Severidad | Qué | Estado |
|---|---|---|---|
| H-53 | CRÍTICO (motor) | La misma tarea entraba dos veces al recorrido (también en el canónico: 29 de 624) | Corregido, baseline nuevo |
| H-54 | MEDIO | Aplicar Excel usaba el Excel/mapa de `config.json`, no el de la pantalla (P-2) | Corregido |
| H-55 | ALTO | Importar/cargar perdía el modo de pedidos, el archivo y la política | Corregido |
| H-56 | MEDIO (realismo) | Cupo por pasillo: el lugar se soltaba antes de salir del pasillo | Parcial (85 → 30); resto BK-40 |
| H-57 | ALTO | El servidor borraba `uploads/` al arrancar, incluido lo que usa `config.json` | Corregido |
| H-58 | OBS | Zona de salida de una celda agrandada a 8 sin aviso | Corregido (aviso + manual) |
| H-59 | MEDIO (realismo) | Salida del carril de descarga sobre otro que espera en la boca (almacén B + outbound) | Abierto → BK-25 F2 / BK-30 |
| H-60 | ALTO | Aplicar dejaba claves de la configuración anterior en `config.json` | Corregido |

Observaciones sin hallazgo: sin anti-colisión el motor no calcula la métrica
de co-ocupaciones (C-09, se contó desde el replay); dos operarios registrados
en la misma celda en t = 0 junto al estacionamiento (C-13, dentro de la
ventana de arranque); el canónico usa el perfil Demo (BK-39).

**Método — lecciones:** no correr `pytest` durante una tanda por la web (sus
corridas escriben en `output/` y el arnés tomó una como si fuera de la web);
los archivos de prueba en `uploads/` se pierden si el servidor se reinicia
(ahora solo se conservan los que usa `config.json`).

