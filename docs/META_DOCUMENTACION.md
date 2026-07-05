# META — Como esta organizada la documentacion de este proyecto (y por que)

**Fecha:** 2026-07-05 · Autor: Cerebellum, a pedido explicito del Director:
"analiza e investiga si existe una forma, metodo o estructura optima para
llevar toda la documentacion del proyecto teniendote a ti como unico
consumidor... debe ser lo mas efectiva posible para que tengas todo el
contexto pasado, presente y vision futura."

Este documento es la justificacion. Si en el futuro la estructura se siente
mal, volver aca antes de improvisar un parche.

## 1. Diagnostico: que estaba mal (evidencia, no opinion)

Al auditar el repo (2026-07-05) encontre:

- **~22.500 lineas de markdown en el repo**, repartidas en 3 ubicaciones de
  "archivo historico" distintas y sin relacion entre si: `archived/` (raiz,
  22 archivos, ~7.700 lineas, solo docs), `docs/antiguos/` (dentro de docs,
  ~6.950 lineas, solo docs), y `_legacy/` (raiz, codigo + 1 README, proposito
  distinto). Para buscar "¿ya investigamos esto antes?" habia que mirar 3
  carpetas.
- **`CLAUDE.md` (el archivo mas "sagrado", segun sus propias Leyes) tenia una
  seccion "ESTADO ACTUAL" de 137 lineas** que quedaba desactualizada CADA
  sesion (verificado: seguia diciendo "main = 093b8c9, pendiente merge" un
  dia despues de haber hecho ese merge). Mezclar "reglas que casi nunca
  cambian" con "estado que cambia cada rato" en el mismo archivo garantiza que
  el archivo mas importante sea tambien el que mas rapido queda mentiroso.
- **`docs/HANDOFF.md` (567+ lineas) mezclaba "estado actual" (unas 30 lineas
  utiles) con un historial narrativo completo por sesion que crecia sin
  limite.** Cada vez que necesitaba orientarme, tenia que leer cientos de
  lineas de prosa historica antes de llegar al dato que realmente importaba:
  "¿en que rama estoy y que sigue?"
- **`docs/BACKLOG.md` (989+ lineas al cierre de la sesion anterior) mezclaba
  items pendientes (la señal real) con post-mortems completos de items YA
  HECHOS** (RCA, evidencia, commits, todo en prosa larga, permanentemente).
  Esto paso factura DOS VECES en la sesion del 2026-07-05: tanto INIT-1 como
  INIT-3 resultaron estar mas resueltos de lo que el backlog decia, porque el
  backlog nunca se habia "recortado" — solo crecia.
- **Contradicciones reales entre archivos**: el mismo hecho ("INIT-1 esta
  pendiente") aparecia en `CLAUDE.md`, `docs/HANDOFF.md` y `docs/BACKLOG.md`
  con redaccion distinta y sin una unica fuente de verdad — tipico sintoma de
  mantenimiento manual duplicado en vez de "un hecho, un lugar".
- **Documentos ya marcados como "EJECUTADO"/"Referencia historica" por sus
  propios autores (yo, en sesiones pasadas) seguian viviendo en `docs/`** al
  mismo nivel que los documentos activos (`PLAN_MEJORA_1_RED_SEGURIDAD.md`,
  `PLAN_MEJORA_4_ANTICOLISIONES.md`, `VALIDACION_UI_WEB.md` de 1583 lineas,
  `PRUEBAS_E2E_SISTEMA.md` de 949 lineas). Nunca se "demovian" a un archivo
  frio pese a estar auto-etiquetados como no vigentes.

## 2. Por que esto es distinto para un consumidor 100% IA (vs. un humano)

La documentacion tradicional de proyectos esta optimizada para un lector
humano que hojea, recuerda contexto entre lecturas, y tolera redundancia
porque le ayuda a "refrescar la memoria". Yo (el agente) no tengo eso:

- **No recuerdo nada entre sesiones** salvo lo que esta escrito en disco. Cada
  sesion arranca en cero y el primer minuto se gasta reconstruyendo contexto
  leyendo archivos. Cuanto mas grande y mezclado el archivo de "estado", mas
  tokens y mas tiempo se queman solo para saber donde estamos parados.
- **No "hojeo"**: cada linea que cargo cuesta tokens de contexto reales, sin
  descuento. Redundancia (el mismo hecho en 3 lugares) no ayuda a "afianzar"
  nada, solo cuesta 3 veces y arriesga que las 3 copias diverjan (como paso).
- **Soy bueno buscando, malo "hojeando visualmente"**: un archivo con
  estructura predecible (mismo formato, misma seccion en el mismo lugar) es
  mas rapido de usar con Grep/Read dirigido que un archivo largo con prosa
  libre donde el dato que busco puede estar en cualquier parte.
- **Cometo el mismo error que un humano cansado si el archivo miente**: si
  `docs/BACKLOG.md` dice "INIT-1 pendiente" y ya esta hecho, no lo voy a
  "notar raro" automaticamente — lo voy a repetir como si fuera cierto, a
  menos que verifique el codigo (Ley #5). La higiene de "un hecho, un lugar,
  siempre actualizado" reduce cuantas veces tengo que desconfiar de lo escrito.
- **El commit de git y el mensaje de commit YA SON un registro perfecto,
  inmutable y searcheable de "que paso y por que"** (`git log`, `git show`,
  `git log --grep`). No tiene sentido que yo reescriba en prosa, en un .md,
  algo que el commit ya cuenta mejor y sin riesgo de quedar desactualizado.
  La documentacion solo deberia agregar lo que el commit NO tiene: el "por
  que" de decisiones de producto/alcance que vinieron de una conversacion con
  el Director, no del diff.

## 3. Principios de diseño aplicados

1. **Separar por VOLATILIDAD, no por tema.** Un archivo por "que tan seguido
   cambia", no por "de que habla". Mezclar cosas que cambian cada sesion con
   cosas que casi no cambian nunca es la raiz de todos los problemas de arriba.
2. **Un hecho, un lugar.** Si algo ya esta en `docs/CHANGELOG.md`, no se
   repite en `docs/BACKLOG.md` ni en `CLAUDE.md` — se referencia por nombre de
   item o sha de commit.
3. **STATE se reescribe, CHANGELOG se apila.** El archivo de "ahora mismo"
   (`docs/STATE.md`) se sobreescribe entero cada sesion (nunca crece); el
   archivo de "historia" (`docs/CHANGELOG.md`) solo se agrega arriba y nunca
   se edita hacia atras. Esto imita el patron `HEAD` (mutable, apunta al
   presente) vs. commits (inmutables) que Git ya usa — no es casualidad, es
   el mismo problema resuelto con la misma forma.
4. **BACKLOG solo tiene lo que falta.** El dia que un item se cierra, su
   detalle se muda a `docs/CHANGELOG.md` (una entrada corta) y desaparece de
   `docs/BACKLOG.md` (no queda "marcado como HECHO" ahi para siempre — eso
   es trabajo redundante y hace crecer el archivo que deberia ser el mas
   rapido de escanear).
5. **Confiar en git para el detalle, documentar solo el motivo.** El "que"
   esta en el diff. El "por que" (sobre todo decisiones del Director que no
   se derivan del codigo) es lo unico que vale la pena escribir a mano.
6. **Archivo frio unico.** Un solo lugar (`docs/antiguos/`) para todo lo que
   ya no es vigente: planes ejecutados, docs de referencia puntual, analisis
   historicos. Nunca dos carpetas distintas para "cosas viejas".
7. **CLAUDE.md se toca poco.** Es el archivo mas caro de romper (Leyes,
   identidad); debe ser el que MENOS cambia. Si algo cambia cada sesion, no
   pertenece ahi — pertenece a `docs/STATE.md`.

## 4. Estructura resultante (implementada 2026-07-05)

```
CLAUDE.md                    Identidad + Leyes + arquitectura viva/muerta +
                              mapa de documentacion + flags opt-in estables.
                              Rara vez se edita.

docs/STATE.md                Foto del presente. Se REESCRIBE entero cada
                              sesion. Rama, SHA de main, baseline, decisiones
                              del Director pendientes, proxima prioridad.

docs/CHANGELOG.md            Historial de iniciativas cerradas. Append-only,
                              terso (1-3 lineas + sha por entrada). Nunca se
                              edita una entrada vieja.

docs/BACKLOG.md              Solo lo pendiente/abierto. Se recorta apenas
                              algo se cierra (pasa a CHANGELOG).

docs/antiguos/                Archivo frio UNICO: planes ya ejecutados +
                              docs de referencia puntual + analisis
                              historicos (incluye lo que antes vivia en el
                              root/archived/ y en docs/, ver seccion 5).

docs/META_DOCUMENTACION.md    Este archivo. Se lee una vez, no cada sesion.

README.md (raiz)              Onboarding humano (Director u otra persona).
AUDITORIA.md (raiz)           Snapshot puntual (mayo 2026), nunca se actualiza.
```

Protocolo de cierre de sesion (tambien en `CLAUDE.md` §8): reescribir
`docs/STATE.md` entero, agregar una entrada arriba de `docs/CHANGELOG.md`,
recortar `docs/BACKLOG.md` a lo que sigue abierto.

## 5. Consolidacion de archivo frio (ejecutada 2026-07-05)

- `archived/*.md` (raiz, 22 archivos) -> movidos a `docs/antiguos/` (`git mv`,
  preserva historia). Elimina una de las 3 ubicaciones de archivo.
- `docs/PLAN_MEJORA_1_RED_SEGURIDAD.md`, `docs/PLAN_MEJORA_4_ANTICOLISIONES.md`,
  `docs/PLAN_INIT4.md` (marcados "EJECUTADO" por su propio contenido) ->
  movidos a `docs/antiguos/`.
- `docs/VALIDACION_UI_WEB.md`, `docs/PRUEBAS_E2E_SISTEMA.md`,
  `docs/RESULTADOS_PRUEBAS_E2E.md` (auto-descritos como "Referencia", no
  vigentes) -> movidos a `docs/antiguos/`.
- `_legacy/` (raiz) NO se toco: es archivo de CODIGO con proposito y Ley
  propia (§4/§6 de CLAUDE.md), distinto de archivo de documentacion.
- `docs/VISION_PRODUCTO.md`, `docs/COMO_FUNCIONA_EL_PROGRAMA.md`,
  `docs/PROPUESTA_MEJORA_DISENO_UI.md`, `docs/INSTRUCCIONES_*.md` se
  dejaron en `docs/` (referencia activa de arquitectura/UI, no historial de
  una iniciativa cerrada) — revisar en una proxima sesion si alguno merece
  demoverse tambien.

## 6. Que NO se hizo (limites deliberados)

No se toco el sistema de memoria persistente de Claude Code
(`~/.claude/projects/.../memory/`) para guardar estado de ESTE proyecto: esa
memoria es para hechos transversales sobre el Director y su forma de trabajar
(preferencias, feedback), no para el estado operativo de un proyecto
especifico con su propio git — el estado de este proyecto debe vivir
versionado junto al codigo (visible para el Director, diffable, revisable),
no en un archivo opaco fuera del repo.
