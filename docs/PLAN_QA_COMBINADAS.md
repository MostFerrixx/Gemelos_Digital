# PLAN DE QA — Pruebas combinadas y réplica de configuraciones

> **Documento vivo** (pedido del Director, 2026-09-26). Última parte del QA de
> la configuración web (`docs/PLAN_QA_CONFIGURACION_WEB.md`, sección 7). Se
> cambia **todo a la vez** —almacén (mapa + Excel), carga, flota/personas,
> estrategias, tiempos, inbound/outbound, zonas— y cada escenario se **guarda
> como configuración** (réplica BK-36) para comprobar después que, al cargarla
> desde otro estado, todo vuelve y funciona igual.

## 0. Estado

**Objetivo inmediato:** ejecutar la Fase 1 (escenarios C-01 a C-21).
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
| K4 | Con anti-colisión activa: 0 co-ocupaciones (BK-29/BK-25) |
| K5 | Los agentes que corren son exactamente los de la flota configurada |
| K6 | Las descargas ocurren en celdas de las zonas de salida DEL almacén en uso |

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
| P-1 | Tres mapas de `layouts/` están dañados (Almacen_Grande, Almacen_Pequeño, Layout_Corredor_Central) | A registrar |
| P-2 | "Aplicar Excel" sin subir archivo usa el `sequence_file` de `config.json`, aunque la pantalla dice "el Excel configurado arriba" (el del formulario) | A verificar en la ejecución |

## 6. Resultados

(se completa durante la ejecución)
