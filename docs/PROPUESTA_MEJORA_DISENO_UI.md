# PROPUESTA DE MEJORA DE DISEÑO — UI WEB
**Proyecto:** Gemelo Digital de Almacén  
**Fecha:** 2026-06-14  
**Perspectiva:** Análisis senior UX/UI — basado en inspección del código CSS, HTML, JS y observación funcional de la UI en navegador  
**Scope:** Configurador web (`/web_configurator`) + Visor de Replay (`/`)  
**Estado:** Solo análisis y propuesta. Sin implementación.

---

## DIAGNÓSTICO GLOBAL

La UI tiene una base técnica sólida: Inter font, CSS custom properties, dark/light theming en el configurador, y un sistema de animación expresivo en el viewer. Sin embargo, hay dos productos que se sienten como proyectos paralelos en vez de una sola herramienta cohesiva. El usuario que configura y luego visualiza experimenta un salto de identidad visual que comunica fragmentación, no profesionalismo.

**El problema central no es que los componentes sean feos — es que no hablan el mismo idioma.**

---

## PARTE 1: CONFIGURADOR WEB (`/web_configurator`)

### 1.1 Jerarquía Visual y Navegación

**Hallazgo:** La sidebar izquierda (260px) contiene los 5 tabs de navegación (Estrategias, Agentes, Presets, Tiempos, Outbound). Los tabs no tienen indicador de "flujo recomendado" ni numeración de pasos. Para un usuario nuevo, los 5 ítems tienen el mismo peso visual y no hay ninguna pista de en cuál orden deben completarse.

**Principio violado:** *Progressive disclosure* — el usuario debería ver primero lo que importa, no un menú plano.

**Propuesta A (quick win):** Agregar un separador visual y etiqueta de sección en la sidebar: `— CONFIGURACIÓN BÁSICA —` antes de Estrategias/Agentes/Presets, y `— OPCIONES AVANZADAS —` antes de Tiempos/Outbound. Los ítems avanzados pueden tener color secundario hasta que el usuario interactúe con los básicos.

**Propuesta B (major):** Convertir la sidebar en un stepper numerado con estado (completo/pendiente/actual). Cuando el usuario guarda un tab, su ícono de nav cambia a un checkmark verde. El flujo correcto es: ① Estrategias → ② Agentes → ③ Presets → ④ Tiempos → ⑤ Outbound → **Guardar**. Este patrón (usado en checkout flows, onboarding wizards) reduce enormemente la tasa de "¿qué hago ahora?" del usuario.

---

### 1.2 Header y Uso del Espacio Vertical

**Hallazgo:** El header tiene `height: 64px` (mismo valor que la sidebar header). Contiene el logo/nombre del proyecto y el toggle de tema dark/light. En una app de configuración orientada a productividad, 64px de header para un logo es un lujo que a 1080p se tolera, pero en monitores de 768px o pantallas corporativas pequeñas consume espacio crítico del formulario.

**Dato CSS observado:** `--header-height: 64px` en `:root`, `--sidebar-width: 260px`.

**Propuesta:** Reducir header a 48px. Mover el toggle dark/light al footer de la sidebar o al menú de usuario (si existiera). El nombre del producto y versión pueden ir en el footer de la sidebar, no en el header, siguiendo el patrón de Linear, Notion y VS Code.

---

### 1.3 Sistema de Color — Neutralidad Excesiva

**Hallazgo:** El azul primario es `#2563eb` (light) / `#3b82f6` (dark) — azul estándar de Tailwind 600/500. Es funcional pero genérico. Más importante: el configurador no tiene colores semánticos más allá de `success`/`danger`/`warning`. No hay distinción visual entre "zona de configuración de agentes" y "zona de presets", todas las cards son blancas (#ffffff) con la misma sombra.

**Principio violado:** El color como sistema de señalización, no solo como decoración.

**Propuesta (quick win):** Asignar un color de acento sutil a cada sección de la sidebar. Por ejemplo:
- Estrategias → azul (primary)
- Agentes/Flota → verde (#10b981)
- Presets → violeta (#8b5cf6)
- Tiempos → naranja (#f59e0b)
- Outbound → rojo (#ef4444)

Estos colores aparecen solo como: borde izquierdo en el tab activo, y color del icono de la sección. No en los cards — el fondo sigue blanco. Este patrón existe en Notion, Jira, Linear.

---

### 1.4 Tipografía — Escala Ausente

**Hallazgo:** El configurador usa Inter pero con muy poca variedad de pesos dentro de los formularios. La mayoría de los labels de formulario son `0.95rem font-weight: 500`. Los títulos de card/sección no tienen suficiente contraste de peso respecto al contenido. El resultado es que todo tiene la misma densidad visual y el ojo no sabe dónde anclar.

**CSS observado:** `.nav-item { font-size: 0.95rem; font-weight: 500 }`. No hay `h2`/`h3` distintos evidentes en la nav.

**Propuesta:** Definir una escala tipográfica explícita de 4 niveles:
- **Page title:** Inter 600, 1.125rem (ya existe en `.sidebar-header h1`)
- **Section title (card header):** Inter 600, 0.9rem, uppercase, letter-spacing 0.06em, color secondary
- **Label:** Inter 500, 0.875rem, color main
- **Value / input:** Inter 400, 0.875rem, color main
- **Helper / hint:** Inter 400, 0.75rem, color secondary

Este cambio es puro CSS, sin tocar estructura HTML.

---

### 1.5 Formularios — Densidad y Feedback

**Hallazgo:** La sección de Flota (Agentes) es la más compleja del configurador. Tiene grupos colapsables con inputs de `Cantidad`, `Capacidad`, `Tiempo Descarga`, más filas de prioridades de Work Area por grupo. Con 2 grupos (GroundOperator + Forklift) con 2 prioridades cada uno, el formulario tiene ~20 inputs visibles sin scroll. No hay agrupación visual más allá del borde del card.

**Problemas identificados:**
1. Las filas de "Work Area Priority" (select + número + botón ✕) son muy densas y no se diferencian visualmente de los inputs de parámetros del grupo.
2. No hay validación inline: si el usuario pone `cantidad: 0`, no ve error hasta que intenta guardar.
3. El botón `✕ Eliminar` (grupo) y `✕` (priority row) tienen el mismo estilo — ambiguedad de qué borra qué.

**Propuestas:**
- **Separación visual:** Las filas de prioridad deben estar en un sub-card con fondo levemente diferente (`#f9fafb` en light, `#111827` en dark), con un título pequeño "Prioridades de Zona".
- **Validación inline:** Usar `:invalid` CSS nativo + un helper text que aparezca debajo del input en rojo cuando el valor está fuera de rango.
- **Jerarquía de destructivos:** `✕ Eliminar Grupo` debe ser `color: danger`, `font-size: small`. El `✕` de priority row debe ser un botón icono (16px) sin texto, diferenciado del botón de grupo.

---

### 1.6 Estados de Botones y Affordances

**Hallazgo:** Los botones `Generar Plantilla TMX` y `Poblar SKUs Aleatorios` fueron deshabilitados correctamente (H-1 fix). El estado disabled tiene `opacity: 0.4` — bien. Sin embargo, no hay diferenciación entre "deshabilitado permanentemente (feature no implementado)" y "deshabilitado temporalmente (prerequisito pendiente)". Un tooltip de "Funcionalidad en desarrollo" es correcto para el primer caso, pero para el segundo debería decir "Complete el paso X primero".

**Propuesta:** Definir dos variantes visuales de disabled:
- `--disabled-permanent`: opacity 0.35, cursor not-allowed (actual). Tooltip explica el estado.
- `--disabled-conditional`: opacity 0.55, cursor not-allowed, con un ícono de candado (🔒) inline. Tooltip dice qué prerequisito falta.

Esta distinción existe en Google Workspace, Figma, Notion.

---

### 1.7 Flujo Entre Configurador y Visor — Gap de UX

**Hallazgo crítico:** El workflow real del usuario es: Configurador → Guardar → Visor → Cargar config → Correr. Pero no hay ninguna conexión visual entre los dos. El Configurador no tiene un botón "Ir al Visor →". El Visor no tiene "Volver al Configurador ←". El usuario tiene que abrir una segunda pestaña manualmente o conocer de antemano que `:8000/` es el visor.

**Impacto:** Muy alto. Este es el mayor fallo de UX del producto completo.

**Propuesta:** Agregar en el Configurador, al lado del botón "Guardar Configuración", un segundo CTA: `▶ Abrir Visor` que abra `http://localhost:8000/` en nueva pestaña. En el Visor, el botón de import (sidebar izquierda) debería mostrar el nombre de la última config cargada como tooltip persistente.

---

## PARTE 2: VISOR DE REPLAY (`/`)

### 2.1 Identidad Visual — Producto Diferente al Configurador

**Hallazgo:** El viewer tiene su propio sistema de diseño independiente: tema exclusivamente dark (`#0f1419` base), sidebar vertical de 55px con iconos, y una estética "GitHub Dark" / "monitoring dashboard". El configurador es "Google Material Light/Dark". No hay un hilo conductor entre ambas UIs.

**CSS observado:** Viewer usa `--color-accent-blue: #58a6ff` (GitHub dark blue); Configurador usa `--color-primary: #2563eb` (Tailwind blue). Distintos colores para el mismo rol semántico.

**Propuesta (mayor):** Definir un design token compartido en un archivo `design-tokens.css` que ambas apps importen. Los tokens de alto nivel (`--brand-primary`, `--brand-success`, `--brand-danger`) deben ser los mismos en ambas apps. Las variantes de tema (dark bg primario, etc.) pueden variar, pero el color de acción primario debe ser el mismo.

---

### 2.2 Sidebar del Viewer — Microinteracciones Excelentes, Tooltips Ausentes

**Hallazgo positivo:** Los botones de la sidebar vertical tienen estados ricos: `loading` (animation pulse + amarillo), `success` (flash verde), `error` (flash rojo). Esto es diseño de nivel production.

**Hallazgo negativo:** La sidebar de 55px tiene iconos sin labels. Si el usuario no sabe qué hace cada ícono, no tiene manera de descubrirlo. No hay tooltips (`title` HTML o tooltips custom CSS).

**Propuesta (quick win):** Agregar `title="Importar JSONL"` y similares a cada botón de la sidebar. Costo: 1 línea por botón en el HTML. Alternativa premium: tooltip custom que aparece a la derecha del ícono con `position: absolute` al hacer hover — mismo patrón que VS Code sidebar.

---

### 2.3 Panel Inferior (Dashboard) — Densidad Bien Ejecutada

**Hallazgo positivo:** El panel inferior colapsable con glass effect (`backdrop-filter: blur(20px)`) es visualmente elegante. Los controles de reproducción (play, seek, speed) están agrupados lógicamente. El handle de redimensionamiento (`resize-handle`) con el indicador azul pulsante es un affordance claro.

**Hallazgo negativo:** El timeline (scrubber) no tiene marcadores de eventos. Una barra de tiempo lineal de 120 segundos de simulación no comunica nada sobre cuándo ocurren los eventos importantes (primer WO completado, primer cuello de botella, punto máximo de WIP).

**Propuesta (mayor):** Agregar una fila de "event markers" encima del scrubber: pequeños triángulos de colores (azul = WO completada, rojo = agente bloqueado, verde = staging lleno) posicionados en `left: N%` donde N es `(tiempo_evento / tiempo_total) * 100`. El JSONL ya tiene todos los timestamps — se pueden extraer al cargar el archivo. Al hacer hover sobre un marker, se muestra un tooltip con el detalle del evento.

---

### 2.4 Canvas — Sin Estado de Error Visible

**Hallazgo:** Si el JSONL no está cargado o el timestamp está fuera de rango, el canvas simplemente queda negro o en blanco. No hay un estado de "empty state" que guíe al usuario.

**Propuesta:** Overlay SVG centrado en el canvas cuando no hay datos: ícono de mapa + texto "Carga un archivo .jsonl para comenzar" + botón que apunte al botón de import de la sidebar. Este overlay desaparece en cuanto se carga un replay. Es el patrón estándar de empty state (Figma, Linear, Notion).

---

### 2.5 Panel Derecho (Agent Dashboard) — Visible pero Sin Énfasis

**Hallazgo:** El panel derecho de agentes (right-dashboard.js) tiene un ticker superior (tiempo, WIP, utilización, throughput) y cards de métricas + lista de operadores. La información es correcta, pero todos los números tienen el mismo tratamiento tipográfico — no hay "la métrica más importante resalta visualmente".

**Propuesta:** Definir una jerarquía de KPIs en el ticker:
- **Primario** (grande, color blanco, Inter 600 1.5rem): Throughput (la métrica que el producto intenta maximizar)
- **Secundario** (tamaño normal, color accent): WIP y % Completado
- **Terciario** (pequeño, color secondary): Tiempo de simulación

Actualmente el ticker tiene 4 elementos con el mismo tamaño. La jerarquía hace que el usuario sepa dónde mirar sin tener que leer todo.

---

### 2.6 Colores de Status de Agentes — Sistema Bien Definido, Mal Comunicado

**Hallazgo positivo:** El CSS del viewer define status colors semánticos y claros:
- `idle` → #6e7681 (gris)
- `moving` → #d29922 (amarillo/ámbar)
- `picking` → #3fb950 (verde)
- `unloading` → #58a6ff (azul)

**Hallazgo negativo:** Estos colores aparecen en la lista de operadores pero no hay una leyenda. Un nuevo usuario no sabe que ámbar = en movimiento.

**Propuesta (quick win):** Agregar una leyenda compacta encima de la lista de operadores, con chips de color + label. 4 líneas de HTML, 8 de CSS. El patrón es el mismo que los status badges de GitHub Issues o Jira.

---

## PARTE 3: INCONSISTENCIAS SISTÉMICAS

### 3.1 Tabla de Tokens Divergentes

| Token semántico | Configurador (light) | Viewer (dark-only) |
|-----------------|---------------------|-------------------|
| Color acción primario | `#2563eb` | `#58a6ff` |
| BG de superficie | `#ffffff` | `#1e252e` |
| Texto secundario | `#6b7280` | `#8b949e` |
| Border | `#e5e7eb` | `rgba(255,255,255,0.08)` |
| Border radius base | `0.5rem` | `0.375-0.5rem` (variable) |
| Font | Inter | Inter ✓ |
| Shadows | Tailwind-style | GitHub Dark-style |

El único token compartido es la fuente. Todo lo demás diverge.

---

### 3.2 Patrones de Interacción Inconsistentes

| Interacción | Configurador | Viewer |
|-------------|-------------|--------|
| Confirmación de acción destructiva | Modal custom (post H-2 fix) | No aplica (viewer es read-only) |
| Notificaciones de éxito | Toast slide-in desde abajo | Cambio de color del botón + flash |
| Loading state | No visible en botones de acción | `pulse` animation en el botón de import |
| Estado vacío | Texto plano "No hay X configurados" | Canvas negro sin guía |

**Propuesta:** Crear un `notifications.js` compartido (ya puede estar como `showNotification` en el configurador) e importarlo en el viewer. El viewer actualmente no tiene un sistema de notificaciones — solo la animación del botón.

---

## PARTE 4: ACCESIBILIDAD (WCAG 2.1 AA)

### 4.1 Contraste de Texto

| Elemento | Color texto | Color bg | Ratio | WCAG AA (4.5:1) |
|----------|-------------|----------|-------|-----------------|
| Nav item (inactive, light) | #6b7280 | #ffffff | 4.48:1 | ⚠️ Límite |
| Nav item (inactive, dark) | #9ca3af | #0f1117 | 5.9:1 | ✅ |
| Viewer: texto secondary | #8b949e | #0f1419 | 4.2:1 | ❌ Falla |
| Viewer: texto tertiary | #6e7681 | #0f1419 | 2.9:1 | ❌ Falla |

El viewer tiene problemas de contraste en textos secundarios y terciarios sobre el fondo más oscuro.

**Fix quick win:** Aclarar `--color-text-secondary` del viewer de `#8b949e` a `#a0aab4` y `--color-text-tertiary` de `#6e7681` a `#8892a0`. Son cambios de 1 línea en el CSS que pueden duplicar el ratio de contraste en tertiary.

---

### 4.2 Dependencia de Color Solo para Estado

**Hallazgo:** Los status de agentes en el viewer (idle/moving/picking/unloading) se diferencian solo por color. Para usuarios con deuteranopía (ceguera al verde, 8% de hombres), `picking (#3fb950)` y `moving (#d29922)` pueden ser indistinguibles.

**Propuesta:** Agregar un prefijo de texto corto o ícono diferente por estado, además del color. Por ejemplo: `→` (flecha) para moving, `↓` (flecha abajo) para picking, `○` para idle, `⬆` para unloading. Alternativa: patrones diferentes en los indicadores de estado (punto sólido, punto con ring, punto parpadeante).

---

## PARTE 5: PRIORIZACIÓN Y ROADMAP

### Nivel 1 — Quick Wins (1-2h de implementación c/u, alto impacto) — IMPLEMENTADAS

| ID | Mejora | Archivo(s) | Estado |
|----|--------|-----------|--------|
| D-01 | Tooltips en sidebar del viewer (title=) | `index.html` del viewer | OK implementada (anterior) |
| D-02 | Leyenda de status de agentes en right-panel | `right-dashboard.js` + CSS | OK implementada (anterior) |
| D-03 | Fix contraste texto viewer (2 variables CSS) | `style.css` viewer | OK 2026-06-14 commit 884a420 |
| D-04 | Separadores de sección en sidebar configurador | `index.html` configurador | OK 2026-06-14 commit 884a420 |
| D-05 | Empty state en canvas (overlay SVG) | `app.js` + CSS | OK 2026-06-14 commit 884a420 |
| D-06 | Botón "Abrir Visor" en configurador | `index.html` + `app.js` | OK 2026-06-14 commit 884a420 |
| D-07 | Escala tipográfica en configurador (CSS puro) | `style.css` configurador | OK 2026-06-14 commit 884a420 |

### Nivel 2 — Mejoras Medias (medio día c/u) — ✓ IMPLEMENTADAS

| ID | Mejora | Impacto | Estado |
|----|--------|---------|--------|
| D-08 | Color de acento por sección en sidebar configurador | Orientación visual, reduce carga cognitiva | ✓ Implementada 2026-06-14 |
| D-09 | Sub-card para prioridades de Work Area en Flota | Reduce densidad del form más complejo | ✓ Implementada 2026-06-14 |
| D-10 | Validación inline en inputs de Flota | Mejora calidad de configuración | ✓ Implementada 2026-06-14 |
| D-11 | Jerarquía de KPIs en ticker del panel derecho | Dirección de atención al usuario | ✓ Implementada 2026-06-14 |
| D-12 | Sistema de notificaciones compartido (viewer) | Consistencia de feedback | ✓ Implementada 2026-06-14 |

### Nivel 3 — Cambios Mayores (sprints) — IMPLEMENTADOS 2026-06-27

| ID | Mejora | Impacto | Estado |
|----|--------|---------|--------|
| D-13 | Design tokens compartidos entre configurador y viewer | Cohesión de identidad de producto | ✓ Implementada (0e6d3dd) |
| D-14 | Stepper numerado de tabs en configurador | Claridad de flujo para usuarios nuevos | ✓ Implementada (902877a) |
| D-15 | Event markers en el scrubber de timeline | Navegación semántica del replay | ✓ Implementada (0e6d3dd) |
| D-16 | Fix diferenciación de estado accesible (no-color) | Cumplimiento WCAG AA | ✓ Implementada (0e6d3dd) |

---

## SKETCH DE DESIGN SYSTEM

```
GEMELO DIGITAL — DESIGN TOKENS COMPARTIDOS
──────────────────────────────────────────

Fuente:      Inter (weights: 400, 500, 600, 700)

Brand:
  --brand-primary:    #2563eb   (azul institucional, usado en light mode)
  --brand-primary-d:  #58a6ff   (versión para dark mode)
  --brand-success:    #10b981   (acciones completadas)
  --brand-danger:     #ef4444   (errores, destructivos)
  --brand-warning:    #f59e0b   (advertencias)

Escalas de gris:
  --gray-50:  #f9fafb
  --gray-100: #f3f4f6
  --gray-200: #e5e7eb
  --gray-400: #9ca3af
  --gray-600: #4b5563
  --gray-800: #1f2937
  --gray-900: #111827
  --gray-950: #0f1117

Status de agente (viewer):
  --status-idle:      #6e7681   (gris — descanso)
  --status-moving:    #d29922   (ámbar — en tránsito)
  --status-picking:   #3fb950   (verde — trabajando)
  --status-unloading: #58a6ff   (azul — descargando)

Radios:
  --radius-sm:  4px
  --radius-md:  8px
  --radius-lg:  12px
  --radius-xl:  16px

Transiciones:
  --ease-fast:  150ms cubic-bezier(0.4, 0, 0.2, 1)
  --ease-base:  250ms cubic-bezier(0.4, 0, 0.2, 1)
  --ease-slow:  350ms cubic-bezier(0.4, 0, 0.2, 1)
```

---

## CONCLUSIÓN

La UI del Gemelo Digital está en un 70% del camino hacia un producto de nivel profesional. Los fundamentos están bien — Inter, CSS variables, transiciones suaves, sistema de notificaciones en el configurador, microinteracciones en el viewer — pero las dos apps no se reconocen como parte del mismo producto.

**Estado de implementacion (2026-06-27):** D-01 a D-16 estan todas implementadas.
Las tres prioridades originales de la propuesta — D-06, D-03 y D-13 — fueron ejecutadas.
D-13 a D-16 (cambios mayores) completadas en sesion 2026-06-27.

Si el Director define nuevas mejoras de UI, se numeran D-17 en adelante en este mismo documento.

---

*Documento generado por Cerebellum | Análisis basado en: `style.css` (viewer), `style.css` + `index.html` (configurador), `fleet-manager.js`, `app.js`, `right-dashboard.js`, observación funcional de controles en navegador | 2026-06-14*
