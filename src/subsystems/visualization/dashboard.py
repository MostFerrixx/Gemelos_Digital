# -*- coding: utf-8 -*-
"""
Visualization Dashboard - Dashboard lateral de metricas en Pygame

REFACTOR V11: DASHBOARD DE AGENTES
Dashboard lateral que muestra metricas de simulacion en tiempo real.
Lee datos exclusivamente desde estado_visual y renderiza UI en Pygame.

Nuevo diseño basado en imagen de referencia:
- Titulo: "Dashboard de Agentes"
- Seccion "Metricas de Simulacion": Tiempo, WorkOrders, Tareas, Progreso
- Seccion "Estado de Operarios": Lista detallada con ID, Estado, Posicion, Tareas

Autor: Claude Code (Refactor V11 - Dashboard de Agentes)
Estado: PRODUCTION - Refactorizacion completa implementada
"""

import pygame
import pygame_gui
from typing import Dict, List, Any, Optional

# Importar colores desde config (relative import dentro de src/)
from ..config.colors import (
    COLOR_DASHBOARD_BG,
    COLOR_DASHBOARD_TEXTO,
    COLOR_DASHBOARD_BORDE,
    COLOR_DASHBOARD_HIGHLIGHT,
    COLOR_AGENTE_IDLE,
    COLOR_AGENTE_TRABAJANDO,
    COLOR_AGENTE_MOVIENDO
)


# =============================================================================
# NUEVA ARQUITECTURA DE LAYOUT - FASE 1 REFACTORIZACION
# =============================================================================

class DashboardLayoutManager:
    """
    Gestor de layout responsivo para el dashboard "World Class".
    
    FASE 1 REFACTORIZACION: Sistema de layout jerarquico que calcula
    posiciones y dimensiones de todas las secciones del dashboard de forma
    dinamica y responsiva.
    
    Caracteristicas:
    - Calculo automatico de dimensiones de secciones
    - Layout responsivo que se adapta al tamano del contenedor
    - Separacion clara entre header, metrics, operators y controls
    - Validacion de limites para evitar overflow
    - Soporte para diferentes resoluciones de pantalla
    
    Responsabilidades:
    - Calcular rectangulos de todas las secciones
    - Validar que el layout cabe en el contenedor
    - Proporcionar acceso a dimensiones calculadas
    - Manejar casos edge (contenedores muy pequenos)
    
    Atributos:
        container_rect: Rectangulo del contenedor principal
        sections: Dict con rectangulos de cada seccion calculados
        margins: Margenes internos del layout
        min_section_heights: Alturas minimas por seccion
    """
    
    def __init__(self, container_rect: pygame.Rect):
        """
        Inicializa el layout manager con el rectangulo del contenedor.
        
        Args:
            container_rect: Rectangulo que define el area total disponible
        """
        self.container_rect = container_rect
        self.sections = {}
        
        # Configuracion de margenes y alturas minimas
        self.margins = {
            'horizontal': 15,  # Margen izquierdo y derecho
            'vertical': 10,    # Margen superior e inferior
            'section_spacing': 5  # Espacio entre secciones
        }
        
        self.min_section_heights = {
            'header': 50,      # Altura minima del encabezado
            'metrics': 100,    # Altura minima de metricas
            'operators': 150,  # Altura minima de operarios
            'controls': 60     # Altura minima de controles
        }
        
        # Calcular layout de todas las secciones
        self._calculate_section_layouts()
        
        print(f"[LAYOUT-MANAGER] Layout calculado para contenedor {container_rect.size}")
    
    def _calculate_section_layouts(self) -> None:
        """
        Calcula los rectangulos de todas las secciones del dashboard.
        
        Distribucion de secciones:
        1. Header: Altura fija (60px) - Titulo principal
        2. Metrics: Altura fija (120px) - Metricas de simulacion
        3. Operators: Altura dinamica - Tabla de operarios con scroll
        4. Controls: Altura restante - Controles y shortcuts
        
        El calculo es responsivo y se adapta al tamano del contenedor.
        """
        container_width = self.container_rect.width
        container_height = self.container_rect.height
        
        # Calcular ancho util (descontando margenes horizontales)
        usable_width = container_width - (2 * self.margins['horizontal'])
        
        # Calcular alturas disponibles
        total_fixed_height = (
            self.min_section_heights['header'] +
            self.min_section_heights['metrics'] +
            self.min_section_heights['controls'] +
            (3 * self.margins['section_spacing'])  # Espacios entre secciones
        )
        
        # Altura disponible para operarios
        operators_height = max(
            self.min_section_heights['operators'],
            container_height - total_fixed_height
        )
        
        # Calcular posiciones Y de cada seccion
        current_y = self.margins['vertical']
        
        # 1. SECCION HEADER
        self.sections['header'] = pygame.Rect(
            self.margins['horizontal'],
            current_y,
            usable_width,
            self.min_section_heights['header']
        )
        current_y += self.min_section_heights['header'] + self.margins['section_spacing']
        
        # 2. SECCION METRICS
        self.sections['metrics'] = pygame.Rect(
            self.margins['horizontal'],
            current_y,
            usable_width,
            self.min_section_heights['metrics']
        )
        current_y += self.min_section_heights['metrics'] + self.margins['section_spacing']
        
        # 3. SECCION OPERATORS (altura dinamica)
        self.sections['operators'] = pygame.Rect(
            self.margins['horizontal'],
            current_y,
            usable_width,
            operators_height
        )
        current_y += operators_height + self.margins['section_spacing']
        
        # 4. SECCION CONTROLS (altura restante)
        controls_height = container_height - current_y - self.margins['vertical']
        controls_height = max(self.min_section_heights['controls'], controls_height)
        
        # Asegurar que no exceda los limites del contenedor
        if current_y + controls_height > container_height:
            controls_height = container_height - current_y
        
        self.sections['controls'] = pygame.Rect(
            self.margins['horizontal'],
            current_y,
            usable_width,
            controls_height
        )
        
        # Validar que el layout es valido
        self._validate_layout()
    
    def _validate_layout(self) -> None:
        """
        Valida que el layout calculado es valido y no excede limites.
        
        FASE 2.5: Validacion mas flexible para contenedores pequenos
        
        Raises:
            ValueError: Si el layout excede los limites del contenedor
        """
        # Verificar que todas las secciones estan dentro del contenedor (validacion flexible)
        for section_name, section_rect in self.sections.items():
            # Verificar que la seccion no excede los limites del contenedor
            if (section_rect.right > self.container_rect.right or 
                section_rect.bottom > self.container_rect.bottom or
                section_rect.left < self.container_rect.left or
                section_rect.top < self.container_rect.top):
                raise ValueError(f"Seccion '{section_name}' excede limites del contenedor")
        
        # Verificar que no hay superposicion entre secciones
        section_list = list(self.sections.values())
        for i, rect1 in enumerate(section_list):
            for j, rect2 in enumerate(section_list[i+1:], i+1):
                if rect1.colliderect(rect2):
                    raise ValueError(f"Superposicion detectada entre secciones {i} y {j}")
        
        print("[LAYOUT-MANAGER] Layout validado exitosamente")
    
    def get_section_rect(self, section_name: str) -> pygame.Rect:
        """
        Obtiene el rectangulo de una seccion especifica.
        
        Args:
            section_name: Nombre de la seccion ('header', 'metrics', 'operators', 'controls')
            
        Returns:
            pygame.Rect: Rectangulo de la seccion solicitada
            
        Raises:
            KeyError: Si la seccion no existe
        """
        if section_name not in self.sections:
            available_sections = list(self.sections.keys())
            raise KeyError(f"Seccion '{section_name}' no encontrada. Disponibles: {available_sections}")
        
        return self.sections[section_name].copy()
    
    def get_all_sections(self) -> Dict[str, pygame.Rect]:
        """
        Obtiene todas las secciones calculadas.
        
        Returns:
            Dict[str, pygame.Rect]: Diccionario con todas las secciones
        """
        return {name: rect.copy() for name, rect in self.sections.items()}
    
    def update_container_size(self, new_rect: pygame.Rect) -> None:
        """
        Actualiza el tamano del contenedor y recalcula el layout.
        
        Args:
            new_rect: Nuevo rectangulo del contenedor
        """
        self.container_rect = new_rect
        self._calculate_section_layouts()
        print(f"[LAYOUT-MANAGER] Layout actualizado para nuevo tamano {new_rect.size}")
    
    def get_layout_info(self) -> Dict[str, Any]:
        """
        Obtiene informacion detallada del layout calculado.
        
        Returns:
            Dict con informacion del layout para debugging
        """
        return {
            'container_size': self.container_rect.size,
            'sections': {name: rect.size for name, rect in self.sections.items()},
            'total_height_used': sum(rect.height for rect in self.sections.values()) + 
                               (len(self.sections) - 1) * self.margins['section_spacing'],
            'available_height': self.container_rect.height,
            'margins': self.margins,
            'min_heights': self.min_section_heights
        }


class ResponsiveGrid:
    """
    Sistema de grid responsivo que se adapta al tamano del contenedor.
    
    FASE 1 REFACTORIZACION: Grid inteligente que calcula posiciones
    de celdas de forma dinamica y valida limites para evitar overflow.
    
    Caracteristicas:
    - Calculo automatico de tamano de celdas
    - Validacion de limites antes de crear elementos
    - Soporte para diferentes numeros de columnas
    - Manejo de overflow con excepciones informativas
    - Espaciado consistente y configurable
    
    Responsabilidades:
    - Calcular rectangulos de celdas individuales
    - Validar que las filas caben en el contenedor
    - Proporcionar navegacion entre filas
    - Manejar casos edge (contenedores muy pequenos)
    
    Atributos:
        container_rect: Rectangulo del contenedor del grid
        columns: Numero de columnas en el grid
        row_height: Altura de cada fila en pixeles
        cell_width: Ancho calculado de cada celda
        current_row: Fila actual para posicionamiento secuencial
        max_rows: Numero maximo de filas que caben en el contenedor
    """
    
    def __init__(self, container_rect: pygame.Rect, columns: int = 4, row_height: int = 25):
        """
        Inicializa el grid responsivo.
        
        Args:
            container_rect: Rectangulo del contenedor donde se dibujara el grid
            columns: Numero de columnas en el grid (default: 4)
            row_height: Altura de cada fila en pixeles (default: 25)
            
        Raises:
            ValueError: Si el contenedor es demasiado pequeno para el grid
        """
        self.container_rect = container_rect
        self.columns = columns
        self.row_height = row_height
        self.current_row = 0
        
        # Calcular dimensiones de celdas
        self._calculate_cell_dimensions()
        
        # Validar que el grid es viable
        self._validate_grid_viability()
        
        print(f"[RESPONSIVE-GRID] Grid {columns}x{self.max_rows} inicializado en {container_rect.size}")
    
    def _calculate_cell_dimensions(self) -> None:
        """
        Calcula las dimensiones de las celdas del grid.
        
        Considera margenes internos para evitar que las celdas toquen
        los bordes del contenedor.
        """
        # Margenes internos del grid
        internal_margin = 10  # 5px por lado
        
        # Calcular ancho disponible para celdas
        available_width = self.container_rect.width - (2 * internal_margin)
        
        # Calcular ancho de cada celda
        self.cell_width = (available_width - ((self.columns - 1) * 5)) // self.columns
        
        # Calcular altura disponible para filas
        available_height = self.container_rect.height - (2 * internal_margin)
        
        # Calcular numero maximo de filas
        self.max_rows = available_height // self.row_height
        
        # Margen interno para posicionamiento
        self.internal_margin = internal_margin
    
    def _validate_grid_viability(self) -> None:
        """
        Valida que el grid es viable con las dimensiones dadas.
        
        Raises:
            ValueError: Si el grid no es viable (muy pequeno)
        """
        if self.cell_width <= 0:
            raise ValueError(f"Ancho de celda invalido: {self.cell_width}px")
        
        if self.max_rows <= 0:
            raise ValueError(f"Numero maximo de filas invalido: {self.max_rows}")
        
        if self.columns <= 0:
            raise ValueError(f"Numero de columnas invalido: {self.columns}")
        
        print(f"[RESPONSIVE-GRID] Grid validado: {self.columns} columnas, {self.max_rows} filas max")
    
    def get_cell_rect(self, column: int, row: int = None) -> pygame.Rect:
        """
        Calcula el rectangulo de una celda especifica.
        
        Args:
            column: Columna de la celda (0-based)
            row: Fila de la celda (0-based). Si es None, usa current_row
            
        Returns:
            pygame.Rect: Rectangulo de la celda calculado
            
        Raises:
            ValueError: Si la columna o fila estan fuera de limites
        """
        # Usar fila actual si no se especifica
        if row is None:
            row = self.current_row
        
        # Validar limites
        if column < 0 or column >= self.columns:
            raise ValueError(f"Columna {column} fuera de limites [0, {self.columns-1}]")
        
        if row < 0 or row >= self.max_rows:
            raise ValueError(f"Fila {row} fuera de limites [0, {self.max_rows-1}]")
        
        # Calcular posicion de la celda
        x = self.container_rect.x + self.internal_margin + (column * (self.cell_width + 5))
        y = self.container_rect.y + self.internal_margin + (row * self.row_height)
        
        return pygame.Rect(x, y, self.cell_width, self.row_height - 2)
    
    def next_row(self) -> bool:
        """
        Avanza a la siguiente fila del grid.
        
        Returns:
            bool: True si hay espacio para la siguiente fila, False si se alcanzo el limite
        """
        self.current_row += 1
        has_space = self.current_row < self.max_rows
        
        if not has_space:
            print(f"[RESPONSIVE-GRID] Limite de filas alcanzado ({self.max_rows})")
        
        return has_space
    
    def reset_row(self) -> None:
        """
        Reinicia el contador de fila actual a 0.
        """
        self.current_row = 0
        print("[RESPONSIVE-GRID] Contador de fila reiniciado")
    
    def get_available_rows(self) -> int:
        """
        Obtiene el numero de filas disponibles desde la fila actual.
        
        Returns:
            int: Numero de filas disponibles
        """
        return max(0, self.max_rows - self.current_row)
    
    def can_fit_rows(self, num_rows: int) -> bool:
        """
        Verifica si se pueden agregar el numero especificado de filas.
        
        Args:
            num_rows: Numero de filas a verificar
            
        Returns:
            bool: True si caben las filas, False en caso contrario
        """
        return (self.current_row + num_rows) <= self.max_rows
    
    def get_grid_info(self) -> Dict[str, Any]:
        """
        Obtiene informacion detallada del grid para debugging.
        
        Returns:
            Dict con informacion del grid
        """
        return {
            'container_size': self.container_rect.size,
            'columns': self.columns,
            'max_rows': self.max_rows,
            'current_row': self.current_row,
            'cell_size': (self.cell_width, self.row_height),
            'available_rows': self.get_available_rows(),
            'internal_margin': self.internal_margin
        }
    
    def update_container_size(self, new_rect: pygame.Rect) -> None:
        """
        Actualiza el tamano del contenedor y recalcula el grid.
        
        Args:
            new_rect: Nuevo rectangulo del contenedor
        """
        self.container_rect = new_rect
        self.current_row = 0  # Reiniciar fila actual
        self._calculate_cell_dimensions()
        self._validate_grid_viability()
        print(f"[RESPONSIVE-GRID] Grid actualizado para nuevo tamano {new_rect.size}")


# =============================================================================
# CLASE PRINCIPAL DE DASHBOARD
# =============================================================================

class DashboardOriginal:
    """
    Dashboard lateral de metricas para simulacion en tiempo real (Pygame).

    REFACTOR V11: Nuevo diseño "Dashboard de Agentes" basado en imagen de referencia.
    
    Lee datos desde estado_visual y renderiza un panel lateral con:
    - Titulo: "Dashboard de Agentes"
    - Metricas de Simulacion: Tiempo (HH:MM:SS), WorkOrders (completadas/totales), 
      Tareas Completadas, Progreso (porcentaje + barra visual)
    - Estado de Operarios: Lista detallada con ID, Estado (con color), 
      Posicion (x,y), Tareas completadas

    Responsabilidades:
    - Renderizar UI del dashboard en superficie dada
    - Leer estado_visual (NO acceso directo a almacen/env)
    - Gestionar layout y geometria del panel
    - Formatear y colorear metricas
    - Renderizar barra de progreso visual
    - Mostrar lista detallada de operarios

    Atributos:
        panel_width: Ancho fijo del panel (400px)
        margen_izq: Margen izquierdo interno (15px)
        margen_derecho: Margen derecho interno (15px)
        y_inicial: Posicion Y inicial del contenido (20px)
        font_titulo: Fuente grande (28px) para titulo
        font_seccion: Fuente media (22px) para secciones
        font_texto: Fuente normal (18px) para datos
        font_pequeno: Fuente pequeña (16px) para detalles
        visible: Flag de visibilidad del dashboard
        max_operarios_mostrar: Limite de operarios en lista (10)
    """

    def __init__(self):
        """
        Inicializa el dashboard con fuentes, colores y configuracion del panel.

        Crea todas las fuentes necesarias con manejo de errores defensivo.
        Si pygame.font falla, las fuentes seran None y renderizado hara early return.
        """
        # Geometria del panel
        self.panel_width = 400
        self.margen_izq = 15
        self.margen_derecho = 15
        self.y_inicial = 20

        # Configuracion de visualizacion
        self.visible = True
        self.max_operarios_mostrar = 10

        # Colores (importados desde config.colors)
        self.color_fondo = COLOR_DASHBOARD_BG
        self.color_texto = COLOR_DASHBOARD_TEXTO
        self.color_borde = COLOR_DASHBOARD_BORDE
        self.color_highlight = COLOR_DASHBOARD_HIGHLIGHT

        # Inicializar fuentes con manejo de errores
        self._inicializar_fuentes()

        print("[DASHBOARD] DashboardOriginal inicializado (REFACTOR V11 - Dashboard de Agentes)")

    def _inicializar_fuentes(self):
        """
        Inicializa las fuentes de Pygame con manejo de errores.

        Intenta crear fuentes de diferentes tamanos. Si falla, almacena None
        y los metodos de renderizado usaran fallbacks (early return).

        Fuentes creadas:
        - font_titulo: 28px (titulo principal)
        - font_seccion: 22px (titulos de secciones)
        - font_texto: 18px (datos y metricas)
        - font_pequeno: 16px (detalles y controles)
        """
        try:
            self.font_titulo = pygame.font.Font(None, 28)
            self.font_seccion = pygame.font.Font(None, 22)
            self.font_texto = pygame.font.Font(None, 18)
            self.font_pequeno = pygame.font.Font(None, 16)
            print("[DASHBOARD] Fuentes inicializadas correctamente")
        except Exception as e:
            print(f"[DASHBOARD] Advertencia: No se pudieron inicializar fuentes: {e}")
            self.font_titulo = None
            self.font_seccion = None
            self.font_texto = None
            self.font_pequeno = None

    def actualizar_datos(self, estado_visual: Dict[str, Any]) -> None:
        """
        Pre-procesa datos desde estado_visual para optimizar renderizado.

        NOTA: En la implementacion actual (V1), este metodo es OPCIONAL.
        Todo el procesamiento de datos se hace directamente en renderizar()
        para mantener simplicidad y evitar duplicacion de logica.

        Args:
            estado_visual: Dict con datos actuales de la simulacion

        Este metodo existe para compatibilidad futura y puede ser extendido
        para cachear calculos pesados si se necesita optimizacion.
        """
        # V1: Simple pass - todo se procesa en renderizar()
        # Futuro: Cachear calculos pesados aqui si se necesita
        pass

    def renderizar(self, pantalla: pygame.Surface, estado_visual: Dict[str, Any],
                   offset_x: int = 0) -> None:
        """
        Renderiza el dashboard completo con el nuevo diseño "Dashboard de Agentes".

        REFACTOR V11: Implementa el diseño exacto de la imagen de referencia:
        1. Titulo: "Dashboard de Agentes"
        2. Metricas de Simulacion: Tiempo (HH:MM:SS), WorkOrders (completadas/totales),
           Tareas Completadas, Progreso (porcentaje + barra visual)
        3. Estado de Operarios: Lista detallada con ID, Estado (con color),
           Posicion (x,y), Tareas completadas

        Args:
            pantalla: Superficie Pygame donde dibujar
            estado_visual: Dict con datos actuales (fuente de verdad unica)
            offset_x: Offset horizontal para posicionar panel (default=0)

        Manejo de Errores:
        - Early return si dashboard no visible
        - Early return si fuentes no inicializadas
        - Valores default para todos los accesos a dict (.get())
        """
        # A. VERIFICACIONES PREVIAS
        if not self.visible:
            return

        if not self.font_titulo:
            # Fuentes no inicializadas, no podemos renderizar
            return

        # B. CALCULAR DIMENSIONES DEL PANEL
        panel_height = pantalla.get_height()
        panel_x = offset_x

        # C. DIBUJAR FONDO Y BORDE
        # Rectangulo de fondo
        pygame.draw.rect(pantalla, self.color_fondo,
                        (panel_x, 0, self.panel_width, panel_height))

        # Linea vertical izquierda (borde)
        pygame.draw.line(pantalla, self.color_borde,
                        (panel_x, 0), (panel_x, panel_height), 2)

        # D. INICIALIZAR POSICION VERTICAL
        y_pos = self.y_inicial
        margen_izq = panel_x + self.margen_izq

        # E. SECCION 1: TITULO - "Dashboard de Agentes"
        titulo = self.font_titulo.render("Dashboard de Agentes", True, self.color_texto)
        pantalla.blit(titulo, (margen_izq, y_pos))
        y_pos += 40

        # Linea separadora horizontal
        pygame.draw.line(pantalla, self.color_borde,
                        (margen_izq, y_pos),
                        (panel_x + self.panel_width - self.margen_derecho, y_pos), 1)
        y_pos += 20

        # F. SECCION 2: METRICAS DE SIMULACION
        seccion_titulo = self.font_seccion.render("Metricas de Simulacion", True, self.color_texto)
        pantalla.blit(seccion_titulo, (margen_izq, y_pos))
        y_pos += 30

        # Extraer metricas desde estado_visual con valores default
        metricas_dict = estado_visual.get('metricas', {})
        
        # BUGFIX: Corregir mapeo de clave del tiempo
        tiempo_sim = metricas_dict.get('tiempo', 0.0)  # Era: 'tiempo_simulacion'
        wos_completadas = metricas_dict.get('workorders_completadas', 0)
        total_wos = metricas_dict.get('total_wos', 0)
        tareas_completadas = metricas_dict.get('tareas_completadas', 0)

        # Formatear tiempo en formato HH:MM:SS como en la imagen
        tiempo_formateado = self._formatear_tiempo_hhmmss(tiempo_sim)

        # Calcular progreso como porcentaje
        progreso_porcentaje = self._calcular_progreso(wos_completadas, total_wos)

        # Renderizar metricas en formato exacto de la imagen
        metricas_texto = [
            f"Tiempo: {tiempo_formateado}",
            f"WorkOrders: {wos_completadas}/{total_wos}",
            f"Tareas Completadas: {tareas_completadas}",
            f"Progreso: {progreso_porcentaje:.1f}%"
        ]

        for texto in metricas_texto:
            superficie = self.font_texto.render(texto, True, self.color_texto)
            pantalla.blit(superficie, (margen_izq + 10, y_pos))
            y_pos += 25

        # Renderizar barra de progreso visual
        self._renderizar_barra_progreso(pantalla, margen_izq + 10, y_pos, 200, 15, progreso_porcentaje)
        y_pos += 30

        # G. SECCION 3: ESTADO DE OPERARIOS
        seccion_titulo = self.font_seccion.render("Estado de Operarios", True, self.color_texto)
        pantalla.blit(seccion_titulo, (margen_izq, y_pos))
        y_pos += 30

        # Lista detallada de operarios como en la imagen
        operarios_dict = estado_visual.get('operarios', {})
        operarios_mostrar = list(operarios_dict.items())[:self.max_operarios_mostrar]

        for agent_id, agent_data in operarios_mostrar:
            self._renderizar_operario_detallado(pantalla, margen_izq, y_pos, agent_id, agent_data)
            y_pos += 25

        y_pos += 15  # Espaciado adicional

        # H. SECCION 4: CONTROLES (solo si hay espacio)
        if y_pos < panel_height - 200:
            seccion_titulo = self.font_seccion.render("Controles", True, self.color_texto)
            pantalla.blit(seccion_titulo, (margen_izq, y_pos))
            y_pos += 30

            controles_texto = [
                "ESPACIO - Pausar/Reanudar",
                "+/- - Velocidad",
                "D - Toggle Dashboard",
                "M - Metricas consola",
                "X - Exportar datos",
                "ESC - Salir"
            ]

            for texto in controles_texto:
                superficie = self.font_pequeno.render(texto, True, self.color_texto)
                pantalla.blit(superficie, (margen_izq + 10, y_pos))
                y_pos += 18

    def toggle_visibilidad(self) -> bool:
        """
        Alterna la visibilidad del dashboard.

        Returns:
            bool: Nuevo estado de visibilidad (True=visible, False=oculto)
        """
        self.visible = not self.visible
        return self.visible

    def set_visibilidad(self, visible: bool) -> None:
        """
        Establece la visibilidad del dashboard de forma explicita.

        Args:
            visible: True para mostrar, False para ocultar
        """
        self.visible = visible

    def _formatear_tiempo_hhmmss(self, segundos: float) -> str:
        """
        Formatea tiempo a formato HH:MM:SS como en la imagen de referencia.

        Args:
            segundos: Tiempo en segundos (float)

        Returns:
            str: Tiempo formateado en formato HH:MM:SS

        Examples:
            27.63 -> "00:00:27"
            125.0 -> "00:02:05"
            7325.0 -> "02:02:05"
        """
        horas = int(segundos // 3600)
        minutos = int((segundos % 3600) // 60)
        segs = int(segundos % 60)
        return f"{horas:02d}:{minutos:02d}:{segs:02d}"

    def _calcular_progreso(self, completadas: int, total: int) -> float:
        """
        Calcula porcentaje de progreso de WorkOrders.

        Args:
            completadas: Numero de WorkOrders completadas
            total: Numero total de WorkOrders

        Returns:
            float: Porcentaje de progreso (0.0 a 100.0)
        """
        if total == 0:
            return 0.0
        return (completadas / total) * 100.0

    def _renderizar_barra_progreso(self, surface: pygame.Surface, x: int, y: int, 
                                 width: int, height: int, porcentaje: float) -> None:
        """
        Renderiza barra de progreso visual naranja como en la imagen.

        Args:
            surface: Superficie Pygame donde dibujar
            x, y: Posicion de la barra
            width, height: Dimensiones de la barra
            porcentaje: Porcentaje de progreso (0.0 a 100.0)
        """
        # Fondo gris de la barra
        pygame.draw.rect(surface, (200, 200, 200), (x, y, width, height))
        
        # Progreso naranja (como en la imagen)
        progress_width = int(width * (porcentaje / 100.0))
        pygame.draw.rect(surface, (255, 165, 0), (x, y, progress_width, height))

    def _renderizar_operario_detallado(self, surface: pygame.Surface, x: int, y: int,
                                      agent_id: str, agent_data: Dict[str, Any]) -> None:
        """
        Renderiza operario en formato detallado como en la imagen.

        Formato: "ID: agent_id Estado: status Pos: (x,y) Tareas: N"

        Args:
            surface: Superficie Pygame donde dibujar
            x, y: Posicion inicial
            agent_id: ID del agente
            agent_data: Datos del agente
        """
        # Extraer datos del operario
        estado = agent_data.get('status', 'idle')
        pos_x = agent_data.get('pos_x', 0)
        pos_y = agent_data.get('pos_y', 0)
        
        # BUGFIX: Usar picking_executions en lugar de tareas_completadas
        tareas = agent_data.get('picking_executions', 0)  # Era: 'tareas_completadas'

        # Determinar color segun estado (como en la imagen)
        color_estado = self._obtener_color_estado(estado)

        # Renderizar en formato: "ID: agent_id Estado: status Pos: (x,y) Tareas: N"
        # Ejemplo: "ID: GroundOperator_1 Estado: discharging Pos: (2, 24) Tareas: 0"

        # ID del operario
        id_texto = self.font_texto.render(f"ID: {agent_id}", True, self.color_texto)
        surface.blit(id_texto, (x, y))

        # Estado con color apropiado
        estado_texto = self.font_texto.render(f"Estado: {estado}", True, color_estado)
        surface.blit(estado_texto, (x + 120, y))

        # Posicion
        pos_texto = self.font_texto.render(f"Pos: ({pos_x}, {pos_y})", True, self.color_texto)
        surface.blit(pos_texto, (x + 250, y))

        # Tareas
        tareas_texto = self.font_texto.render(f"Tareas: {tareas}", True, self.color_texto)
        surface.blit(tareas_texto, (x + 350, y))

    def _obtener_color_estado(self, estado: str) -> tuple:
        """
        Retorna color segun estado como en la imagen de referencia.

        Args:
            estado: Estado del agente

        Returns:
            tuple: Color RGB para el estado
        """
        if estado == 'discharging':
            return (255, 165, 0)  # Naranja (como en la imagen)
        elif estado == 'moving':
            return (0, 150, 255)  # Azul/Verde (como en la imagen)
        elif estado == 'idle':
            return (150, 150, 150)  # Gris
        elif estado == 'working':
            return COLOR_AGENTE_TRABAJANDO
        else:
            return self.color_texto

    def _formatear_tiempo(self, segundos: float) -> str:
        """
        Formatea tiempo SimPy a formato legible (helper privado - LEGACY).

        NOTA: Este metodo se mantiene por compatibilidad pero se recomienda
        usar _formatear_tiempo_hhmmss() para el nuevo diseño.

        Args:
            segundos: Tiempo en segundos (float)

        Returns:
            str: Tiempo formateado
            - < 60s: "45.3s"
            - < 3600s: "2m 5s"
            - >= 3600s: "2h 2m"

        Examples:
            45.3 -> "45.3s"
            125.0 -> "2m 5s"
            7325.0 -> "2h 2m"
        """
        if segundos < 60:
            return f"{segundos:.1f}s"
        elif segundos < 3600:
            minutos = int(segundos // 60)
            segs = int(segundos % 60)
            return f"{minutos}m {segs}s"
        else:
            horas = int(segundos // 3600)
            minutos = int((segundos % 3600) // 60)
            return f"{horas}h {minutos}m"

    def _formatear_id_corto(self, agent_id: str) -> str:
        """
        Acorta IDs de agentes para display compacto (helper privado - LEGACY).

        NOTA: Este metodo se mantiene por compatibilidad pero el nuevo diseño
        usa IDs completos en la lista detallada.

        Args:
            agent_id: ID completo del agente

        Returns:
            str: ID corto de 2 digitos con padding de ceros

        Examples:
            "GroundOperator_1" -> "01"
            "Forklift_3" -> "03"
            "Agente_12" -> "12"
        """
        # Intentar extraer numero despues del ultimo underscore
        if '_' in agent_id:
            numero = agent_id.split('_')[-1]
            return numero.zfill(2)
        else:
            # Fallback: ultimos 2 caracteres
            return agent_id[-2:].zfill(2)


# =============================================================================
# NUEVA CLASE: DashboardGUI (pygame_gui)
# =============================================================================

class DashboardGUI:
    """
    Dashboard profesional usando pygame_gui para alcanzar estándar visual "world class".
    
    FASE 2 REFACTORIZACION: Integración con nueva arquitectura de layout
    Esta clase utiliza DashboardLayoutManager y ResponsiveGrid para crear un layout
    completamente responsivo sin coordenadas fijas hardcodeadas.
    
    Características:
    - Layout responsivo usando DashboardLayoutManager
    - Grid adaptativo usando ResponsiveGrid para tabla de operarios
    - UIPanel como contenedor principal
    - UILabel para títulos y métricas
    - UIProgressBar para barra de progreso visual
    - Tabla de operarios con scroll dinámico
    - Sistema de theming JSON para consistencia visual
    - Integración con UIManager de pygame_gui
    
    Responsabilidades:
    - Crear y gestionar componentes pygame_gui con layout responsivo
    - Actualizar datos desde estado_visual
    - Mantener compatibilidad con sistema actual
    - Proporcionar interfaz profesional y moderna
    - Manejar scroll dinámico para operarios
    
    Atributos:
        ui_manager: UIManager de pygame_gui para gestionar componentes
        rect: Rectángulo que define posición y tamaño del dashboard
        layout_manager: DashboardLayoutManager para cálculo de layout
        operators_grid: ResponsiveGrid para tabla de operarios
        main_panel: Panel principal del dashboard
        sections: Dict con paneles de cada sección
        title_label: Etiqueta del título "Dashboard de Agentes"
        metrics_labels: Dict de etiquetas para métricas
        progress_bar: Barra de progreso visual
        operators_scroll: Scroll container para tabla de operarios
        operator_rows: Lista de filas de operarios creadas dinámicamente
        visible: Flag de visibilidad del dashboard
    """
    
    def __init__(self, ui_manager: pygame_gui.UIManager, rect: pygame.Rect):
        """
        Inicializa el dashboard GUI con nueva arquitectura de layout responsivo.
        
        FASE 2 REFACTORIZACION: Integración completa con DashboardLayoutManager
        y ResponsiveGrid para eliminar coordenadas fijas y crear layout adaptativo.
        
        Args:
            ui_manager: UIManager de pygame_gui para gestionar componentes
            rect: Rectángulo que define posición y tamaño del dashboard
        """
        self.ui_manager = ui_manager
        self.rect = rect
        self.visible = True
        
        # FASE 2: Inicializar nueva arquitectura de layout
        self.layout_manager = DashboardLayoutManager(rect)
        
        # Crear componentes del dashboard usando layout responsivo
        self._create_main_panel()
        self._create_header_section()
        self._create_metrics_section()
        self._create_progress_bar()
        self._create_operators_section()
        
        print("[DASHBOARD-GUI] DashboardGUI refactorizado con nueva arquitectura de layout")
    
    def _create_main_panel(self):
        """
        Crear panel principal del dashboard usando layout responsivo.
        
        FASE 2 REFACTORIZACION: Usa rectángulo del layout_manager en lugar de
        coordenadas fijas hardcodeadas.
        """
        self.main_panel = pygame_gui.elements.UIPanel(
            self.rect,
            manager=self.ui_manager,
            starting_height=1
        )
    
    def _create_header_section(self):
        """
        Crear sección de header usando layout responsivo.
        
        FASE 2 REFACTORIZACION: Usa rectángulo calculado por layout_manager
        para posicionamiento dinámico y responsivo.
        """
        header_rect = self.layout_manager.get_section_rect('header')
        
        # Crear panel de header
        self.header_panel = pygame_gui.elements.UIPanel(
            header_rect,
            manager=self.ui_manager,
            container=self.main_panel,
            starting_height=2
        )
        
        # Título principal centrado
        title_rect = pygame.Rect(
            header_rect.width // 4,  # Centrado horizontalmente
            10,  # Margen superior
            header_rect.width // 2,  # Ancho del título
            40   # Altura del título
        )
        
        self.title_label = pygame_gui.elements.UILabel(
            title_rect,
            "Dashboard de Agentes",
            manager=self.ui_manager,
            container=self.header_panel
        )
    
    def _create_metrics_section(self):
        """
        Crear sección de métricas usando layout responsivo.
        
        FASE 2 REFACTORIZACION: Usa rectángulo calculado por layout_manager
        y ResponsiveGrid para organizar métricas de forma adaptativa.
        """
        metrics_rect = self.layout_manager.get_section_rect('metrics')
        
        # Crear panel de métricas
        self.metrics_panel = pygame_gui.elements.UIPanel(
            metrics_rect,
            manager=self.ui_manager,
            container=self.main_panel,
            starting_height=2
        )
        
        # Título de sección
        section_title_rect = pygame.Rect(10, 10, metrics_rect.width - 20, 25)
        self.section_title = pygame_gui.elements.UILabel(
            section_title_rect,
            "Métricas de Simulación",
            manager=self.ui_manager,
            container=self.metrics_panel
        )
        
        # Crear grid responsivo para métricas
        grid_area = pygame.Rect(10, 40, metrics_rect.width - 20, metrics_rect.height - 50)
        self.metrics_grid = ResponsiveGrid(grid_area, columns=2, row_height=20)
        
        # Métricas individuales usando grid
        self.metrics_labels = {}
        
        # Tiempo de simulación
        time_rect = self.metrics_grid.get_cell_rect(0, 0)
        self.metrics_labels['tiempo'] = pygame_gui.elements.UILabel(
            time_rect,
            "Tiempo: 00:00:00",
            manager=self.ui_manager,
            container=self.metrics_panel
        )
        
        # WorkOrders
        workorders_rect = self.metrics_grid.get_cell_rect(1, 0)
        self.metrics_labels['workorders'] = pygame_gui.elements.UILabel(
            workorders_rect,
            "WorkOrders: 0/0",
            manager=self.ui_manager,
            container=self.metrics_panel
        )
        
        # Tareas completadas (solo si hay espacio)
        if self.metrics_grid.get_available_rows() > 1:
            tasks_rect = self.metrics_grid.get_cell_rect(0, 1)
            self.metrics_labels['tareas'] = pygame_gui.elements.UILabel(
                tasks_rect,
                "Tareas: 0",
                manager=self.ui_manager,
                container=self.metrics_panel
            )
            
            # Progreso (solo si hay espacio)
            progress_rect = self.metrics_grid.get_cell_rect(1, 1)
            self.metrics_labels['progreso'] = pygame_gui.elements.UILabel(
                progress_rect,
                "Progreso: 0%",
                manager=self.ui_manager,
                container=self.metrics_panel
            )
        else:
            # Fallback: crear labels sin grid para espacios pequeños
            tasks_rect = pygame.Rect(10, 70, metrics_rect.width - 20, 20)
            self.metrics_labels['tareas'] = pygame_gui.elements.UILabel(
                tasks_rect,
                "Tareas: 0",
                manager=self.ui_manager,
                container=self.metrics_panel
            )
            
            progress_rect = pygame.Rect(10, 95, metrics_rect.width - 20, 20)
            self.metrics_labels['progreso'] = pygame_gui.elements.UILabel(
                progress_rect,
                "Progreso: 0%",
                manager=self.ui_manager,
                container=self.metrics_panel
            )
    
    def _create_progress_bar(self):
        """
        Crear barra de progreso usando layout responsivo.
        
        FASE 2 REFACTORIZACION: Integra la barra de progreso dentro de la
        sección de métricas usando el grid responsivo.
        """
        # Obtener rectángulo de métricas para posicionar la barra
        metrics_rect = self.layout_manager.get_section_rect('metrics')
        
        # Barra de progreso en la fila 2 del grid
        progress_bar_rect = pygame.Rect(
            10,
            metrics_rect.height - 30,  # Parte inferior de métricas
            metrics_rect.width - 20,
            20
        )
        
        self.progress_bar = pygame_gui.elements.UIProgressBar(
            progress_bar_rect,
            manager=self.ui_manager,
            container=self.metrics_panel
        )
    
    def _create_operators_section(self):
        """
        Crear sección de operarios usando layout responsivo y scroll dinámico.
        
        FASE 2 REFACTORIZACION: Usa ResponsiveGrid para tabla de operarios
        y UIScrollingContainer para manejo dinámico de contenido.
        """
        operators_rect = self.layout_manager.get_section_rect('operators')
        
        # Crear panel de operarios
        self.operators_panel = pygame_gui.elements.UIPanel(
            operators_rect,
            manager=self.ui_manager,
            container=self.main_panel,
            starting_height=2
        )
        
        # Título de sección
        section_title_rect = pygame.Rect(10, 10, operators_rect.width - 20, 25)
        self.operators_title = pygame_gui.elements.UILabel(
            section_title_rect,
            "Estado de Operarios",
            manager=self.ui_manager,
            container=self.operators_panel
        )
        
        # Crear scroll container para operarios
        scroll_area = pygame.Rect(
            10,
            40,
            operators_rect.width - 20,
            operators_rect.height - 50
        )
        
        self.operators_scroll = pygame_gui.elements.UIScrollingContainer(
            scroll_area,
            manager=self.ui_manager,
            container=self.operators_panel
        )
        
        # Crear grid responsivo dentro del scroll container
        grid_area = pygame.Rect(0, 0, scroll_area.width - 20, scroll_area.height)
        self.operators_grid = ResponsiveGrid(grid_area, columns=4, row_height=25)
        
        # Lista para almacenar filas de operarios creadas dinámicamente
        self.operator_rows = []
        
        print("[DASHBOARD-GUI] Sección de operarios creada con scroll dinámico")
    
    def update_data(self, estado_visual: Dict[str, Any]) -> None:
        """
        Actualiza los datos del dashboard desde estado_visual usando nueva arquitectura.
        
        FASE 2 REFACTORIZACION: Actualiza métricas y operarios usando los nuevos
        componentes pygame_gui con layout responsivo.
        
        Args:
            estado_visual: Dict con datos actuales de la simulación
        """
        if not self.visible:
            return
        
        # Extraer métricas
        metricas = estado_visual.get('metricas', {})
        operarios = estado_visual.get('operarios', {})
        
        # Actualizar métricas usando nuevos labels
        self._update_metrics(metricas)
        
        # Actualizar operarios usando grid responsivo
        self._update_operators(operarios)
    
    def _update_metrics(self, metricas: Dict[str, Any]) -> None:
        """
        Actualiza las métricas del dashboard usando layout responsivo.
        
        FASE 2 REFACTORIZACION: Usa los nuevos labels creados con ResponsiveGrid
        para actualizar métricas de forma organizada.
        """
        # Actualizar tiempo de simulación
        tiempo = metricas.get('tiempo', 0.0)
        tiempo_formateado = self._format_time_hhmmss(tiempo)
        self.metrics_labels['tiempo'].set_text(f"Tiempo: {tiempo_formateado}")
        
        # Actualizar WorkOrders
        wos_completadas = metricas.get('workorders_completadas', 0)
        total_wos = metricas.get('total_wos', 0)
        self.metrics_labels['workorders'].set_text(f"WorkOrders: {wos_completadas}/{total_wos}")
        
        # Actualizar tareas completadas
        tareas_completadas = metricas.get('tareas_completadas', 0)
        self.metrics_labels['tareas'].set_text(f"Tareas: {tareas_completadas}")
        
        # Actualizar progreso
        if total_wos > 0:
            progreso_porcentaje = (wos_completadas / total_wos) * 100.0
            self.metrics_labels['progreso'].set_text(f"Progreso: {progreso_porcentaje:.1f}%")
            self.progress_bar.set_current_progress(progreso_porcentaje)
        else:
            self.metrics_labels['progreso'].set_text("Progreso: 0.0%")
            self.progress_bar.set_current_progress(0.0)
    
    def _update_operators(self, operarios: Dict[str, Any]) -> None:
        """
        Actualiza la tabla de operarios usando ResponsiveGrid y scroll dinámico.
        
        FASE 2 REFACTORIZACION: Usa ResponsiveGrid para crear filas de operarios
        de forma dinámica y responsiva, con scroll automático.
        """
        # Limpiar filas existentes
        for row in self.operator_rows:
            row.kill()
        self.operator_rows.clear()
        
        # Resetear grid para nueva fila
        self.operators_grid.reset_row()
        
        # Crear headers de tabla
        headers = ["ID", "Estado", "Posición", "Tareas"]
        for i, header in enumerate(headers):
            header_rect = self.operators_grid.get_cell_rect(i, 0)
            header_label = pygame_gui.elements.UILabel(
                header_rect,
                header,
                manager=self.ui_manager,
                container=self.operators_scroll
            )
            self.operator_rows.append(header_label)
        
        # Avanzar a siguiente fila
        self.operators_grid.next_row()
        
        # Crear filas de operarios
        for op_id, op_data in operarios.items():
            if not self.operators_grid.can_fit_rows(1):
                print(f"[DASHBOARD-GUI] Advertencia: No hay espacio para más operarios")
                break
            
            # Crear fila de operario usando grid
            row_elements = []
            
            # ID del operario
            id_rect = self.operators_grid.get_cell_rect(0, self.operators_grid.current_row)
            id_label = pygame_gui.elements.UILabel(
                id_rect,
                str(op_id),
                manager=self.ui_manager,
                container=self.operators_scroll
            )
            row_elements.append(id_label)
            
            # Estado del operario
            estado = op_data.get('status', 'Desconocido')
            estado_rect = self.operators_grid.get_cell_rect(1, self.operators_grid.current_row)
            estado_label = pygame_gui.elements.UILabel(
                estado_rect,
                estado,
                manager=self.ui_manager,
                container=self.operators_scroll
            )
            row_elements.append(estado_label)
            
            # Posición del operario
            pos_x = op_data.get('pos_x', 0)
            pos_y = op_data.get('pos_y', 0)
            posicion_rect = self.operators_grid.get_cell_rect(2, self.operators_grid.current_row)
            posicion_label = pygame_gui.elements.UILabel(
                posicion_rect,
                f"({pos_x},{pos_y})",
                manager=self.ui_manager,
                container=self.operators_scroll
            )
            row_elements.append(posicion_label)
            
            # Tareas completadas
            tareas_completadas = op_data.get('picking_executions', 0)
            tareas_rect = self.operators_grid.get_cell_rect(3, self.operators_grid.current_row)
            tareas_label = pygame_gui.elements.UILabel(
                tareas_rect,
                str(tareas_completadas),
                manager=self.ui_manager,
                container=self.operators_scroll
            )
            row_elements.append(tareas_label)
            
            # Agregar elementos de la fila a la lista
            self.operator_rows.extend(row_elements)
            
            # Avanzar a siguiente fila
            self.operators_grid.next_row()
        
        # Actualizar scroll container para mostrar nuevo contenido
        self.operators_scroll.rebuild()
    
    def _format_time_hhmmss(self, segundos: float) -> str:
        """
        Formatea tiempo a formato HH:MM:SS.
        
        Args:
            segundos: Tiempo en segundos (float)
            
        Returns:
            str: Tiempo formateado en formato HH:MM:SS
        """
        horas = int(segundos // 3600)
        minutos = int((segundos % 3600) // 60)
        segs = int(segundos % 60)
        return f"{horas:02d}:{minutos:02d}:{segs:02d}"
    
    def set_visible(self, visible: bool) -> None:
        """
        Controla la visibilidad del dashboard.
        
        Args:
            visible: True para mostrar, False para ocultar
        """
        self.visible = visible
        if hasattr(self, 'main_panel'):
            self.main_panel.visible = visible
    
    def update_layout(self, new_rect: pygame.Rect) -> None:
        """
        Actualiza el layout del dashboard cuando cambia el tamaño del contenedor.
        
        FASE 2 REFACTORIZACION: Usa DashboardLayoutManager para recalcular
        posiciones y ResponsiveGrid para ajustar tabla de operarios.
        
        Args:
            new_rect: Nuevo rectángulo del contenedor
        """
        self.rect = new_rect
        
        # Actualizar layout manager
        self.layout_manager.update_container_size(new_rect)
        
        # Actualizar grid de operarios
        if hasattr(self, 'operators_grid'):
            operators_rect = self.layout_manager.get_section_rect('operators')
            scroll_area = pygame.Rect(
                10,
                40,
                operators_rect.width - 20,
                operators_rect.height - 50
            )
            self.operators_grid.update_container_size(scroll_area)
        
        print("[DASHBOARD-GUI] Layout actualizado para nuevo tamaño")
    
    def toggle_visibility(self) -> bool:
        """
        Alterna la visibilidad del dashboard.
        
        Returns:
            bool: Nuevo estado de visibilidad
        """
        self.visible = not self.visible
        self.main_panel.visible = self.visible
        return self.visible
    
    def set_visibility(self, visible: bool) -> None:
        """
        Establece la visibilidad del dashboard.
        
        Args:
            visible: True para mostrar, False para ocultar
        """
        self.visible = visible
        self.main_panel.visible = visible


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'DashboardLayoutManager',  # FASE 1: Nueva arquitectura de layout
    'ResponsiveGrid',          # FASE 1: Sistema de grid responsivo
    'DashboardOriginal',       # Dashboard original (Pygame)
    'DashboardGUI'            # Dashboard pygame_gui (FASE 2 REFACTORIZACION COMPLETA)
]

# Mensaje de carga del modulo
print("[DASHBOARD] Modulo cargado: DashboardOriginal + DashboardGUI (FASE 2 REFACTORIZACION COMPLETA)")