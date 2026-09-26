# Pedido de datos al cliente (para validar el simulador con su operación)

> Documento para compartir con el cliente o con quien administre su WMS.
> Origen: investigación del 2026-09-26 sobre SAP EWM, Manhattan (WMOS/Active)
> e Infor WMS. Detalle técnico y fuentes al final.
> **Objetivo:** pedir lo mínimo, que se pueda sacar **sin programadores**, en
> una o dos tardes de trabajo de un supervisor o de un analista.

## Lo que pedimos (4 archivos + 5 preguntas)

**Período:** las últimas 4 a 8 semanas, con al menos una semana de alta
demanda. Datos recientes, porque los sistemas archivan lo viejo.

| # | Archivo | Qué contiene | De dónde sale (sin IT) |
|---|---|---|---|
| 1 | **Movimientos confirmados** | Una fila por movimiento confirmado: pedido o documento, producto, cantidad, ubicación de origen, ubicación de destino, usuario, **fecha y hora de confirmación** (y la de inicio, si la hay), ola | Pantalla de monitoreo o de tareas del WMS, exportada a Excel (ver tabla por sistema) |
| 2 | **Maestro de ubicaciones** | Código, zona, pasillo, **nivel**, tipo (picking, reserva, pulmón, muelle, estación) | Pantalla o reporte de ubicaciones, exportado |
| 3 | **Maestro de productos** | Código, descripción, unidad, medidas, peso, unidades por caja y por pallet | Pantalla o reporte de artículos, exportado |
| 4 | **Asistencia** | Persona, entrada, salida (y descansos, si se registran) | Reloj de asistencia o sistema de RR.HH. (casi nunca está en el WMS) |

Además, el **plano del almacén** (PDF o CAD).

**Las 5 preguntas:**
1. ¿Los movimientos se confirman con RF o voz **en el momento**, o en papel y
   después en lote? Si es en lote, la hora registrada no es la del trabajo.
2. ¿En qué zona horaria están las horas del archivo 1?
3. ¿Hay tareas **en el lugar** que no generan movimiento (empaque, film,
   etiquetado, control de calidad)? ¿Cuánto tardan aproximadamente, por pallet
   o por caja?
4. ¿Cuáles son los horarios de turno y de descanso habituales?
5. ¿Qué equipos se usan (a pie, transpaleta, apilador, reach, trilateral) y
   quién usa cada uno?

## Cómo sale el archivo 1 en cada sistema

| Sistema | Vía sin programador | Notas |
|---|---|---|
| **SAP EWM** | Warehouse Monitor `/SCWM/MON` → tareas de almacén confirmadas → filtrar por fechas → exportar a hoja de cálculo | Trae horas de creación, inicio y confirmación, usuario, bins de origen y destino, paso del proceso. Pedir las horas en **hora local** (la tabla guarda UTC). Por tablas (SE16) salen códigos internos: mejor el monitor |
| **Infor WMS** | Cualquier pantalla de lista (tareas o Transacciones de inventario) → Export to Excel | Las tareas guardan **hora de inicio y de fin**. El archivo de exportación se borra a las 24 h |
| **Manhattan Active** | Reporte de picking o de productividad en SCI, exportado a Excel | Tope de 100.000 filas por consulta: exportar por tramos de 1 a 5 días. Los volcados masivos (Data Stream) requieren a IT |
| **Manhattan WMOS** | El reporte de transacciones RF por usuario que ya usa el supervisor | Suele traer solo la hora de confirmación: el inicio lo inferimos nosotros |

## Lo que hacemos nosotros con eso (el cliente no tiene que hacerlo)

- **Etapas del proceso:** no las pedimos. Las deducimos del tipo de ubicación
  de origen y de destino: rack → pulmón es un pick, pulmón → muelle es un
  traslado.
- **Hora de inicio:** si no viene, se toma la confirmación anterior del mismo
  usuario (así lo hacen los sistemas de productividad, "de escaneo a escaneo").
- **Viaje contra tarea:** el viaje se estima con la distancia del plano.
- **Conversores por sistema:** tenemos (o armamos una sola vez) el traductor
  del export de cada WMS a nuestro formato.

## Qué NO pedimos al principio (solo si la validación lo exige)

- Consultas SQL o acceso a la base de datos.
- Cadenas completas de pedido → empaque → carga unidas por contenedor.
- Datos de posicionamiento (RTLS), video o telemetría de equipos.
- Estándares del módulo de productividad (Labor Management), si lo tienen.

## Fuentes (resumen)

- SAP EWM: campos de `/SCWM/ORDIM_C` ([ERPExplorer](https://www.erpexplorer.com/sap/s4/table/SCWM/ORDIM_C)),
  monitor ([SAP Learning](https://learning.sap.com/courses/exploring-business-processes-in-sap-ewm-for-sap-s-4hana-cloud-private-edition/using-the-warehouse-management-monitor)),
  UTC contra hora local ([KBA 3069177](https://userapps.support.sap.com/sap/support/knowledge/en/3069177)),
  POSC ([ITPFED](https://itpfed.com/understanding-ewm-process-oriented-storage-control/)).
- Infor: exportar a Excel ([Infor docs](https://docs.infor.com/wms/2023.x/en-us/useradminlib/sceintroug/bts1612893924313.html)),
  columnas STARTTIME y ENDTIME de TASKDETAIL (consulta pública de terceros, [thiscodeworks](https://www.thiscodeworks.com/tag/sql)).
- Manhattan: límites de SCI ([developer.manh.com](https://developer.manh.com/docs/reference/sci/limits/)),
  Data Stream ([developer.manh.com](https://developer.manh.com/docs/concept-guides/data-stream/)).
  El esquema de WMOS no es público: los nombres de tablas no están verificados.
- Práctica de consultoras y proveedores de sistemas de productividad (LMS):
  [OPSdesign](https://opsdesign.com/how-to-get-the-most-from-your-warehouse-design-consultant/),
  [Easy Metrics](https://www.easymetrics.com/warehouse-performance-management-platform/data-integrations/)
  (el WMS no ve entre el 30 y el 50 % de las horas: por eso pedimos asistencia).
