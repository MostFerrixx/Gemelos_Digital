# 📊 PLAN EXHAUSTIVO: DASHBOARD WORLD-CLASS PARA MODO REPLAY

**Fecha:** 2025-10-07  
**Objetivo:** Crear un dashboard profesional, moderno y funcional para el modo replay que se posicione a la izquierda del layout.

---

## 🔍 ANÁLISIS DEL ESTADO ACTUAL

### ✅ Dashboard que **SÍ FUNCIONA** (DashboardOriginal)
**Ubicación:** `src/subsystems/visualization/dashboard.py` (líneas 509-900)
**Tecnología:** Pygame nativo (sin pygame_gui)
**Usado en:** Modo simulación (simulation_engine.py)

**Características actuales:**
- ✅ **Panel lateral de 400px** con fondo oscuro (#1E1E2E)
- ✅ **Título:** "Dashboard de Agentes" (font 28px)
- ✅ **Métricas de Simulación:**
  - Tiempo: formato HH:MM:SS (ej: "00:00:27")
  - WorkOrders: "X/Y" (completadas/totales)
  - Tareas Completadas: número entero
  - Progreso: "X.X%" con barra visual naranja
- ✅ **Lista de Operarios** (máx 10):
  - ID: agent_id
  - Estado: con colores semánticos (naranja=discharging, azul=moving, gris=idle)
  - Posición: (x, y)
  - Tareas: número
- ✅ **Sección de Controles:**
  - ESPACIO - Pausar/Reanudar
  - +/- - Velocidad
  - D - Toggle Dashboard
  - M - Métricas consola
  - X - Exportar datos
  - ESC - Salir

**Fuentes utilizadas:**
- `font_titulo`: 28px (título principal)
- `font_seccion`: 22px (títulos de secciones)
- `font_texto`: 18px (datos y métricas)
- `font_pequeno`: 16px (detalles y controles)

**Colores:**
- Fondo: `#1E1E2E` (oscuro elegante)
- Texto: `#E6E6FA` (blanco suave)
- Borde: `#2D2D44` (gris oscuro)
- Barra progreso: `#FFA500` (naranja)

---

### ❌ Dashboard que **NO FUNCIONA** (ModernDashboard)
**Ubicación:** `src/subsystems/visualization/dashboard_modern.py`
**Tecnología:** pygame_gui
**Usado en:** Intento de integración en replay_engine.py

**Problemas identificados:**
1. ❌ **No se renderiza correctamente** en el replay viewer
2. ❌ **Falta integración completa** con estado_visual
3. ❌ **Métricas incompletas** (faltan algunas del dashboard original)
4. ❌ **Ticker row poco legible** (fuentes muy pequeñas)
5. ❌ **Cards de operarios no se actualizan** correctamente
6. ❌ **Tema JSON complejo** pero no totalmente aprovechado

---

## 🎯 PROBLEMA RAÍZ IDENTIFICADO

### ¿Por qué no funcionaron los cambios?

**Análisis línea por línea del código:**

1. **En `replay_engine.py` línea 139-144:**
```python
dashboard_rect = pygame.Rect(
    0,            # x: inicio del panel izquierdo ✅ CORRECTO
    0,            # y: coordenada relativa (0) ✅ CORRECTO
    440,          # width: ancho del panel ✅ CORRECTO
    window_height  # height: altura completa ✅ CORRECTO
)
```
✅ El `dashboard_rect` SÍ está bien posicionado a la izquierda.

2. **En `replay_engine.py` línea 155:**
```python
self.dashboard_gui = ModernDashboard(self.ui_manager, dashboard_rect)
```
✅ La instanciación es correcta.

3. **En `replay_engine.py` línea 324:**
```python
self.pantalla.blit(scaled_surface, (440, 0))
```
✅ El layout SÍ se desplaza a la derecha.

4. **PERO... el problema está en ModernDashboard:**

**En `dashboard_modern.py` línea 103-108:**
```python
self.main_panel = pygame_gui.elements.UIPanel(
    relative_rect=pygame.Rect(self.rect.x, self.rect.y, self.rect.width, self.rect.height),
    manager=self.ui_manager,
    container=None,
    object_id="modern_main_panel"
)
```

**🔥 PROBLEMA CRÍTICO:** 
- El `main_panel` usa coordenadas RELATIVAS pero se crea con `container=None`
- En pygame_gui, cuando `container=None`, las coordenadas son ABSOLUTAS
- Pero dentro del panel, los elementos hijos usan coordenadas relativas AL PANEL
- **Hay un conflicto de coordenadas que causa que el panel no se renderice donde debe**

**Además:**
- ModernDashboard no implementa `update_data()` completamente
- Faltan métricas críticas del dashboard original
- El diseño de cards es bonito pero no funcional

---

## 🏗️ SOLUCIÓN PROPUESTA: DASHBOARD HÍBRIDO WORLD-CLASS

### Estrategia: **"Lo mejor de ambos mundos"**

**Combinar:**
1. ✅ **Funcionalidad y layout** de `DashboardOriginal` (funciona perfecto)
2. ✅ **Estilo visual moderno** del tema JSON existente
3. ✅ **Simplicidad de Pygame nativo** (más control, menos bugs)
4. ✅ **Diseño profesional** con cards, sombras y colores semánticos

---

## 📐 ESPECIFICACIÓN DETALLADA DEL NUEVO DASHBOARD

### **Nombre:** `DashboardWorldClass`
### **Tecnología:** Pygame nativo (como DashboardOriginal) + estilos modernos
### **Ubicación:** `src/subsystems/visualization/dashboard_world_class.py` (nuevo archivo)

---

### **SECCIÓN 1: HEADER**
**Posición:** Panel izquierdo (x=0), superior
**Altura:** 60px
**Contenido:**
```
┌──────────────────────────────────────────┐
│  🎯 Dashboard de Agentes                 │
│  Sistema de Monitoreo en Tiempo Real     │
└──────────────────────────────────────────┘
```
**Estilos:**
- Título: Font 24px, color #CDD6F4, bold
- Subtítulo: Font 14px, color #A6ADC8
- Fondo: gradiente vertical (#1E1E2E → #313244)
- Borde inferior: 2px sólido #89B4FA (accent azul)

---

### **SECCIÓN 2: TICKER ROW (KPIs RÁPIDOS)**
**Posición:** Debajo del header
**Altura:** 50px
**Contenido:** 4 KPIs en fila horizontal
```
┌────────────────────────────────────────────────────┐
│  ⏰ Tiempo      📊 WIP    📈 Utilización  🚀 Throughput │
│  00:00:27       5/10      85%            2.5/min      │
└────────────────────────────────────────────────────┘
```
**Estilos:**
- Fondo: #313244
- Cada slot: width 100px, padding 8px
- Label: Font 11px, color #BAC2DE
- Value: Font 14px, color #E6E6FA, bold
- Separadores: líneas verticales 1px #45475A

---

### **SECCIÓN 3: MÉTRICAS DE SIMULACIÓN (CARDS)**
**Posición:** Debajo del ticker
**Altura:** 240px (2 filas de 2 cards)
**Contenido:** 4 cards con métricas principales
```
┌─────────────────┐  ┌─────────────────┐
│  ⏰ Tiempo       │  │  📦 WorkOrders   │
│  00:00:27       │  │  1 / 81         │
└─────────────────┘  └─────────────────┘

┌─────────────────┐  ┌─────────────────┐
│  ✅ Tareas      │  │  📈 Progreso     │
│  0              │  │  1.1%           │
└─────────────────┘  └─────────────────┘
```
**Estilos por card:**
- Dimensiones: 180x110px
- Fondo: #313244
- Borde: 2px redondeado (radius 12px), color #45475A
- Sombra: 4px blur, rgba(0,0,0,0.3)
- Icon: 20px, color según tipo de métrica
- Label: Font 12px, color #BAC2DE
- Value: Font 22px, color #E6E6FA, bold

**Iconos semánticos:**
- ⏰ Tiempo: color #89B4FA (azul)
- 📦 WorkOrders: color #A6E3A1 (verde)
- ✅ Tareas: color #FAB387 (naranja)
- 📈 Progreso: color #94E2D5 (teal)

---

### **SECCIÓN 4: BARRA DE PROGRESO VISUAL**
**Posición:** Debajo de las cards
**Altura:** 40px
**Contenido:**
```
┌────────────────────────────────────────────┐
│  Progreso General                          │
│  ▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  1.1% │
└────────────────────────────────────────────┘
```
**Estilos:**
- Header: Font 14px, color #CDD6F4
- Barra: height 20px, radius 10px
- Fondo barra: #1E1E2E
- Relleno: gradiente horizontal (#A6E3A1 → #94E2D5)
- Borde: 2px #45475A
- Porcentaje: Font 13px, color #BAC2DE, alineado a la derecha

---

### **SECCIÓN 5: ESTADO DE OPERARIOS (LISTA SCROLLABLE)**
**Posición:** Debajo de la barra de progreso
**Altura:** Dinámica (hasta el final del panel)
**Contenido:** Lista de operarios con scroll
```
┌──────────────────────────────────────────────────┐
│  Estado de Operarios                             │
├──────────────────────────────────────────────────┤
│  🟢 GroundOperator_1                             │
│     Estado: discharging  Pos: (2,24)  Tareas: 0 │
│                                                   │
│  🔵 Forklift_2                                   │
│     Estado: moving       Pos: (8,27)  Tareas: 0 │
│                                                   │
│  🟡 Forklift_3                                   │
│     Estado: working      Pos: (8,27)  Tareas: 0 │
│  ...                                              │
│  [scroll]                                         │
└──────────────────────────────────────────────────┘
```
**Estilos:**
- Header: Font 16px, color #CDD6F4, bold
- Fondo: #1E1E2E
- Cada operario:
  - Card: height 60px, padding 10px
  - Fondo hover: #313244
  - Icon estado: 16px (círculo coloreado)
  - ID: Font 14px, color #E6E6FA
  - Detalles: Font 12px, color #BAC2DE
- Scroll bar: width 8px, color #45475A

**Colores de estado (círculo + texto):**
- 🟢 idle: #BAC2DE (gris claro)
- 🔵 moving: #A6E3A1 (verde)
- 🟡 working: #FAB387 (naranja)
- 🔴 discharging: #F38BA8 (rojo/rosa)
- 🟣 loading: #89B4FA (azul)
- ⏳ waiting: #CBA6F7 (púrpura)
- ❌ error: #F38BA8 (rojo)

---

### **SECCIÓN 6: FOOTER (CONTROLES)**
**Posición:** Final del panel (fixed bottom)
**Altura:** 120px
**Contenido:**
```
┌─────────────────────────────────────────┐
│  ⌨️ Atajos de Teclado                   │
│  ─────────────────────────────────────  │
│  SPACE  Pausar/Reanudar                 │
│  +/-    Velocidad                       │
│  D      Toggle Dashboard                │
│  ESC    Salir                           │
└─────────────────────────────────────────┘
```
**Estilos:**
- Fondo: #313244
- Borde superior: 2px #45475A
- Header: Font 13px, color #BAC2DE
- Tecla: Font 12px, color #89B4FA, bold, background #1E1E2E, padding 4px
- Descripción: Font 12px, color #E6E6FA

---

## 💻 IMPLEMENTACIÓN TÉCNICA

### **Arquitectura de Clases**

```python
class DashboardWorldClass:
    """
    Dashboard World-Class para modo replay con diseño profesional.
    
    Características:
    - Posicionamiento flexible (izquierda/derecha)
    - Diseño moderno con cards y colores semánticos
    - Lista scrollable de operarios
    - Todas las métricas del dashboard original
    - Pygame nativo (sin pygame_gui) para máximo control
    """
    
    def __init__(self, panel_width=440, panel_position='left'):
        # Configuración
        self.panel_width = panel_width
        self.panel_position = panel_position
        
        # Colores del tema moderno
        self.colors = self._load_color_scheme()
        
        # Fuentes
        self.fonts = self._init_fonts()
        
        # Estado interno
        self.visible = True
        self.scroll_offset = 0
        self.max_operators_visible = 8
        
    def _load_color_scheme(self) -> dict:
        """Carga esquema de colores del tema JSON"""
        pass
    
    def _init_fonts(self) -> dict:
        """Inicializa todas las fuentes necesarias"""
        pass
    
    def render(self, surface: pygame.Surface, estado_visual: dict, offset_x: int = 0):
        """
        Renderiza el dashboard completo.
        
        Args:
            surface: Superficie pygame donde dibujar
            estado_visual: Dict con datos actuales
            offset_x: Offset horizontal para posicionamiento
        """
        if not self.visible:
            return
        
        # 1. Fondo y borde
        self._render_background(surface, offset_x)
        
        # 2. Header
        y = self._render_header(surface, offset_x, 0)
        
        # 3. Ticker Row
        y = self._render_ticker_row(surface, offset_x, y, estado_visual)
        
        # 4. Metrics Cards
        y = self._render_metrics_cards(surface, offset_x, y, estado_visual)
        
        # 5. Progress Bar
        y = self._render_progress_bar(surface, offset_x, y, estado_visual)
        
        # 6. Operators List
        y = self._render_operators_list(surface, offset_x, y, estado_visual)
        
        # 7. Footer Controls
        self._render_footer(surface, offset_x, surface.get_height() - 120)
    
    def _render_background(self, surface, offset_x):
        """Renderiza fondo con gradiente"""
        pass
    
    def _render_header(self, surface, offset_x, y) -> int:
        """Renderiza header con título y subtítulo"""
        pass
    
    def _render_ticker_row(self, surface, offset_x, y, estado_visual) -> int:
        """Renderiza fila de KPIs rápidos"""
        pass
    
    def _render_metrics_cards(self, surface, offset_x, y, estado_visual) -> int:
        """Renderiza 4 cards de métricas principales"""
        pass
    
    def _render_card(self, surface, x, y, width, height, icon, label, value, color):
        """Helper para renderizar un card individual con sombra"""
        pass
    
    def _render_progress_bar(self, surface, offset_x, y, estado_visual) -> int:
        """Renderiza barra de progreso con gradiente"""
        pass
    
    def _render_operators_list(self, surface, offset_x, y, estado_visual) -> int:
        """Renderiza lista scrollable de operarios"""
        pass
    
    def _render_operator_row(self, surface, x, y, agent_id, agent_data, is_hovered):
        """Helper para renderizar una fila de operario"""
        pass
    
    def _render_footer(self, surface, offset_x, y):
        """Renderiza footer con controles"""
        pass
    
    def _draw_rounded_rect(self, surface, color, rect, radius=10, border_color=None, border_width=0):
        """Helper para dibujar rectángulos redondeados"""
        pass
    
    def _draw_gradient_rect(self, surface, rect, color1, color2, vertical=True):
        """Helper para dibujar rectángulos con gradiente"""
        pass
    
    def _draw_shadow(self, surface, rect, blur=4, offset=(2, 2), alpha=50):
        """Helper para dibujar sombras"""
        pass
    
    def get_state_color(self, state: str) -> tuple:
        """Retorna color semántico según estado del operario"""
        pass
    
    def get_state_icon(self, state: str) -> str:
        """Retorna icono según estado del operario"""
        pass
    
    def handle_mouse_event(self, event, offset_x):
        """Maneja eventos de mouse para scroll y hover"""
        pass
    
    def update_data(self, estado_visual: dict):
        """Actualiza datos internos si necesario (opcional)"""
        pass
```

---

## 🎨 HELPERS VISUALES

### **1. Rounded Rectangles con Sombra**
```python
def _draw_rounded_rect_with_shadow(self, surface, x, y, width, height, 
                                    bg_color, border_color, radius=12, 
                                    shadow_offset=(4, 4), shadow_alpha=80):
    """Dibuja rectángulo redondeado con sombra estilo material design"""
    # 1. Dibujar sombra (offset)
    shadow_rect = pygame.Rect(x + shadow_offset[0], y + shadow_offset[1], width, height)
    shadow_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.rect(shadow_surface, (*[0,0,0], shadow_alpha), (0, 0, width, height), border_radius=radius)
    surface.blit(shadow_surface, shadow_rect.topleft)
    
    # 2. Dibujar rectángulo principal
    rect = pygame.Rect(x, y, width, height)
    pygame.draw.rect(surface, bg_color, rect, border_radius=radius)
    
    # 3. Dibujar borde
    if border_color:
        pygame.draw.rect(surface, border_color, rect, width=2, border_radius=radius)
```

### **2. Gradientes Verticales/Horizontales**
```python
def _draw_gradient_rect(self, surface, rect, color1, color2, vertical=True):
    """Dibuja rectángulo con gradiente suave"""
    if vertical:
        for y in range(rect.height):
            ratio = y / rect.height
            r = int(color1[0] + (color2[0] - color1[0]) * ratio)
            g = int(color1[1] + (color2[1] - color1[1]) * ratio)
            b = int(color1[2] + (color2[2] - color1[2]) * ratio)
            pygame.draw.line(surface, (r, g, b), 
                           (rect.x, rect.y + y), 
                           (rect.x + rect.width, rect.y + y))
    else:
        for x in range(rect.width):
            ratio = x / rect.width
            r = int(color1[0] + (color2[0] - color1[0]) * ratio)
            g = int(color1[1] + (color2[1] - color1[1]) * ratio)
            b = int(color1[2] + (color2[2] - color1[2]) * ratio)
            pygame.draw.line(surface, (r, g, b), 
                           (rect.x + x, rect.y), 
                           (rect.x + x, rect.y + rect.height))
```

### **3. Iconos con Círculos Coloreados**
```python
def _draw_status_icon(self, surface, x, y, radius, color, alpha=255):
    """Dibuja círculo coloreado como indicador de estado"""
    # Círculo exterior (borde)
    pygame.draw.circle(surface, color, (x, y), radius + 2, width=2)
    
    # Círculo interior (relleno con alpha)
    icon_surface = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
    pygame.draw.circle(icon_surface, (*color, alpha), (radius, radius), radius)
    surface.blit(icon_surface, (x - radius, y - radius))
```

---

## 📦 INTEGRACIÓN EN REPLAY ENGINE

### **Modificaciones en `replay_engine.py`**

```python
# Línea 40: Agregar import
from subsystems.visualization.dashboard_world_class import DashboardWorldClass

# Línea 113-175: Reemplazar _inicializar_pygame_gui()
def _inicializar_dashboard_world_class(self):
    """
    Inicializa el dashboard world-class con pygame nativo.
    """
    print("[DASHBOARD] Inicializando Dashboard World-Class...")
    try:
        # Crear dashboard world-class con posición izquierda
        self.dashboard = DashboardWorldClass(
            panel_width=440,
            panel_position='left'
        )
        print("[DASHBOARD] Dashboard World-Class inicializado exitosamente")
    except Exception as e:
        print(f"[DASHBOARD ERROR] Error inicializando dashboard: {e}")
        print(f"[DASHBOARD ERROR] Tipo de error: {type(e).__name__}")
        import traceback
        print(f"[DASHBOARD ERROR] Traceback: {traceback.format_exc()}")
        self.dashboard = None

# Línea 323-324: Modificar renderizado
# ANTES:
# self.pantalla.blit(scaled_surface, (440, 0))

# DESPUÉS:
# 1. Dibujar dashboard a la izquierda (offset_x=0)
if self.dashboard:
    from subsystems.visualization.state import estado_visual
    self.dashboard.render(self.pantalla, estado_visual, offset_x=0)

# 2. Dibujar layout desplazado a la derecha
self.pantalla.blit(scaled_surface, (440, 0))
```

---

## 🧪 PRUEBAS Y VALIDACIÓN

### **Test 1: Renderizado Visual**
```bash
python entry_points/run_replay_viewer.py output/simulation_20250928_003114/replay_20250928_003114.jsonl
```
**Verificar:**
- ✅ Dashboard aparece en panel izquierdo (x=0)
- ✅ Layout aparece en panel derecho (x=440)
- ✅ No hay overlap entre dashboard y layout
- ✅ Todas las métricas se muestran correctamente
- ✅ Colores semánticos funcionan
- ✅ Scroll de operarios funciona

### **Test 2: Responsividad**
```python
# Probar con diferentes resoluciones
resoluciones = [(800, 800), (1024, 768), (1280, 720), (1920, 1080)]
for res in resoluciones:
    # Verificar que el dashboard se adapta
    pass
```

### **Test 3: Actualización de Datos**
```python
# Verificar que las métricas se actualizan en tiempo real
# Simular cambios en estado_visual y verificar que el dashboard refleja los cambios
```

---

## 📊 MÉTRICAS DE ÉXITO

### **Criterios de Aceptación**

1. ✅ **Funcionalidad:** Todas las métricas del dashboard original presentes
2. ✅ **Posicionamiento:** Dashboard en panel izquierdo sin overlap
3. ✅ **Diseño:** Aspecto visual profesional y moderno
4. ✅ **Rendimiento:** FPS estable (≥30fps) incluso con 10+ operarios
5. ✅ **Usabilidad:** Controles y shortcuts accesibles y claros
6. ✅ **Mantenibilidad:** Código limpio, documentado y fácil de extender

### **KPIs Técnicos**

- **Líneas de código:** ~800-1000 líneas (dashboard_world_class.py)
- **Tiempo de renderizado:** <10ms por frame
- **Memoria:** <50MB adicional
- **Compatibilidad:** Funciona en Windows, Linux, macOS

---

## 🚀 ROADMAP DE IMPLEMENTACIÓN

### **FASE 1: Estructura Base (2-3 horas)**
- [x] Crear archivo `dashboard_world_class.py`
- [ ] Implementar clase `DashboardWorldClass` con esqueleto
- [ ] Implementar `_init_fonts()` y `_load_color_scheme()`
- [ ] Implementar `_render_background()`
- [ ] Implementar `render()` con estructura básica
- [ ] Test: Verificar que aparece panel negro a la izquierda

### **FASE 2: Header y Ticker (1-2 horas)**
- [ ] Implementar `_render_header()` con título y subtítulo
- [ ] Implementar `_render_ticker_row()` con 4 KPIs
- [ ] Agregar helper `_draw_gradient_rect()`
- [ ] Test: Verificar que header y ticker se ven bien

### **FASE 3: Metrics Cards (2-3 horas)**
- [ ] Implementar `_render_metrics_cards()` con 4 cards
- [ ] Implementar `_render_card()` helper
- [ ] Agregar `_draw_rounded_rect_with_shadow()`
- [ ] Agregar iconos de métricas
- [ ] Test: Verificar que cards se ven profesionales

### **FASE 4: Progress Bar (1 hora)**
- [ ] Implementar `_render_progress_bar()` con gradiente
- [ ] Test: Verificar que la barra se llena correctamente

### **FASE 5: Operators List (2-3 horas)**
- [ ] Implementar `_render_operators_list()` con scroll
- [ ] Implementar `_render_operator_row()` con colores semánticos
- [ ] Agregar `_draw_status_icon()` helper
- [ ] Implementar `handle_mouse_event()` para scroll
- [ ] Test: Verificar scroll y hover funcionan

### **FASE 6: Footer (1 hora)**
- [ ] Implementar `_render_footer()` con controles
- [ ] Test: Verificar que los controles se muestran

### **FASE 7: Integración (1-2 horas)**
- [ ] Modificar `replay_engine.py` para usar nuevo dashboard
- [ ] Eliminar referencias a `ModernDashboard` antiguo
- [ ] Ajustar offset del layout a 440px
- [ ] Test: Ejecutar replay y verificar todo funciona

### **FASE 8: Pulido Final (1-2 horas)**
- [ ] Ajustar colores y fuentes según feedback
- [ ] Optimizar rendimiento si necesario
- [ ] Agregar comentarios y documentación
- [ ] Test final: Ejecutar batería completa de pruebas

---

## 📚 RECURSOS Y REFERENCIAS

### **Archivos Clave a Consultar**
1. `src/subsystems/visualization/dashboard.py` (DashboardOriginal) - Referencia funcional
2. `data/themes/dashboard_theme_modern.json` - Esquema de colores
3. `src/subsystems/visualization/state.py` - Estructura de estado_visual
4. `src/engines/replay_engine.py` - Integración en replay

### **Documentación Pygame**
- https://www.pygame.org/docs/ref/draw.html (Primitivas de dibujo)
- https://www.pygame.org/docs/ref/font.html (Manejo de fuentes)
- https://www.pygame.org/docs/ref/surface.html (Superficies y blitting)

### **Paleta de Colores (Catppuccin Mocha)**
```python
COLORS = {
    'primary_bg': (30, 30, 46),      # #1E1E2E
    'surface_bg': (49, 50, 68),      # #313244
    'accent_blue': (137, 180, 250),  # #89B4FA
    'accent_teal': (148, 226, 213),  # #94E2D5
    'accent_green': (166, 227, 161), # #A6E3A1
    'accent_orange': (250, 179, 135),# #FAB387
    'accent_red': (243, 139, 168),   # #F38BA8
    'accent_purple': (203, 166, 247),# #CBA6F7
    'text_primary': (205, 214, 244), # #CDD6F4
    'text_secondary': (186, 194, 222),# #BAC2DE
    'text_muted': (166, 173, 200),   # #A6ADC8
    'border_primary': (69, 71, 90),  # #45475A
    'border_secondary': (88, 91, 112)# #585B70
}
```

---

## ✅ CHECKLIST FINAL

Antes de dar por completado el dashboard:

- [ ] Código comentado y documentado
- [ ] Todos los métodos implementados
- [ ] Tests pasando (renderizado, actualización, scroll)
- [ ] Integración en replay_engine.py funcionando
- [ ] Performance aceptable (≥30fps)
- [ ] Sin errores en consola
- [ ] Todas las métricas visibles y actualizándose
- [ ] Colores semánticos correctos
- [ ] Scroll de operarios funcional
- [ ] Footer con controles visible
- [ ] Screenshot antes/después documentado
- [ ] Código subido a git

---

## 🎬 RESULTADO ESPERADO

**Screenshot simulado del dashboard final:**

```
┌──────────────────────────────────────────┐  ┌──────────────────────────────┐
│ 🎯 Dashboard de Agentes                  │  │                              │
│ Sistema de Monitoreo en Tiempo Real      │  │                              │
├──────────────────────────────────────────┤  │                              │
│ ⏰ Tiempo  📊 WIP  📈 Util  🚀 Through   │  │     LAYOUT DEL ALMACÉN      │
│ 00:00:27   5/10   85%     2.5/min       │  │                              │
├──────────────────────────────────────────┤  │                              │
│  ┌────────────┐  ┌────────────┐         │  │                              │
│  │ ⏰ Tiempo   │  │ 📦 WOs      │         │  │                              │
│  │ 00:00:27   │  │ 1/81       │         │  │      ░░░░░░░░░░░░░          │
│  └────────────┘  └────────────┘         │  │      ░ RACKS  ░░░          │
│  ┌────────────┐  ┌────────────┐         │  │      ░░░░░░░░░░░░░          │
│  │ ✅ Tareas   │  │ 📈 Progreso │         │  │                              │
│  │ 0          │  │ 1.1%       │         │  │      🤖 ← Operario          │
│  └────────────┘  └────────────┘         │  │                              │
├──────────────────────────────────────────┤  │                              │
│ Progreso General                         │  │                              │
│ ▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░  1.1%    │  │                              │
├──────────────────────────────────────────┤  │                              │
│ Estado de Operarios                      │  └──────────────────────────────┘
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  🟢 GroundOperator_1                     │
│     discharging  (2,24)  Tareas: 0      │
│  🔵 Forklift_2                           │
│     moving       (8,27)  Tareas: 0      │
│  🟡 Forklift_3                           │
│     moving       (8,27)  Tareas: 0      │
│  [scroll ↕]                              │
├──────────────────────────────────────────┤
│ ⌨️ Atajos de Teclado                     │
│ ──────────────────────────────────────   │
│ SPACE  Pausar/Reanudar                   │
│ +/-    Velocidad                         │
│ ESC    Salir                             │
└──────────────────────────────────────────┘
```

---

**FIN DEL PLAN**

Este dashboard combina:
✅ Funcionalidad probada de DashboardOriginal
✅ Diseño moderno y profesional
✅ Colores semánticos y UX clara
✅ Código mantenible y escalable

**Tiempo estimado de implementación:** 12-16 horas
**Complejidad:** Media-Alta
**Prioridad:** Alta

