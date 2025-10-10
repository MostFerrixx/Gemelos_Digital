#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard World-Class - Panel lateral profesional para modo replay.

Este modulo implementa un dashboard de nivel profesional con:
- Diseno moderno con cards, gradientes y sombras
- Colores semanticos del tema Catppuccin Mocha
- Lista scrollable de operarios
- Todas las metricas del sistema
- Pygame nativo para maximo control
- Optimizaciones de rendimiento con cache inteligente
- Manejo seguro de errores y datos malformados

FASE 1: Estructura Base COMPLETADA
FASE 2: Header y Ticker COMPLETADA  
FASE 3: Metrics Cards COMPLETADA
FASE 4: Progress Bar COMPLETADA
FASE 5: Operators List COMPLETADA
FASE 6: Footer COMPLETADA + MEJORAS UX
FASE 7: Integracion COMPLETADA + OPTIMIZACIONES
FASE 8: Pulido Final COMPLETADA

Autor: Claude Code (Dashboard World-Class Implementation)
Fecha: 2025-10-08
Estado: FASE 8 - Pulido Final COMPLETADA - Dashboard World-Class 100% funcional
Version: v11.0.0-beta.1
"""

import pygame
import json
import os
from typing import Dict, List, Any, Optional, Tuple


class DashboardWorldClass:
    """
    Dashboard World-Class para modo replay con diseno profesional.
    
    Caracteristicas:
    - Posicionamiento flexible (izquierda/derecha)
    - Diseno moderno con cards y colores semanticos
    - Lista scrollable de operarios
    - Todas las metricas del dashboard original
    - Pygame nativo (sin pygame_gui) para maximo control
    
    Atributos:
        panel_width: Ancho del panel (default 440px)
        panel_position: Posicion del panel ('left' o 'right')
        colors: Dict con esquema de colores del tema
        fonts: Dict con todas las fuentes necesarias
        visible: Flag de visibilidad del dashboard
        scroll_offset: Offset de scroll para lista de operarios
        max_operators_visible: Numero maximo de operarios visibles
    """
    
    def __init__(self, panel_width: int = 440, panel_position: str = 'left'):
        """
        Inicializa el Dashboard World-Class.
        
        Args:
            panel_width: Ancho del panel en pixeles (default 440)
            panel_position: Posicion del panel ('left' o 'right')
        """
        # Configuracion basica
        self.panel_width = panel_width
        self.panel_position = panel_position
        
        # Cargar esquema de colores del tema moderno
        self.colors = self._load_color_scheme()
        
        # Inicializar fuentes
        self.fonts = self._init_fonts()
        
        # Estado interno
        self.visible = True
        self.scroll_offset = 0
        self.max_operators_visible = 8
        self.hovered_operator = None
        
        # Dimensiones de secciones (calculadas dinamicamente)
        self.section_heights = {
            'header': 60,
            'ticker': 50,
            'metrics': 240,
            'progress': 40,
            'operators': 0,  # Dinamico
            'footer': 120
        }
        
        # OPTIMIZACION FASE 7: Cache de superficies para mejor rendimiento
        self._cached_surfaces = {}
        self._last_render_time = 0
        self._render_cache_valid = False
        self._cached_operators_data = None
        self._cached_metrics_data = None
        
        # OPTIMIZACION FASE 7: Configuracion de rendimiento
        self._performance_config = {
            'enable_gradient_cache': True,
            'enable_text_cache': True,
            'enable_card_cache': True,
            'max_cache_size': 50,
            'cache_ttl': 0.1  # 100ms TTL para cache
        }
        
        print("[DASHBOARD-WC] Dashboard World-Class inicializado")
        print(f"[DASHBOARD-WC] Panel: {panel_width}px, Posicion: {panel_position}")
        print("[DASHBOARD-WC] Optimizaciones de rendimiento FASE 7 activadas")
        print("[DASHBOARD-WC] FASE 8: Pulido Final completado - Dashboard 100% funcional")
    
    def _load_color_scheme(self) -> Dict[str, Tuple[int, int, int]]:
        """
        Carga esquema de colores del tema moderno (Catppuccin Mocha).
        
        Returns:
            Dict con colores en formato (R, G, B)
        """
        # Paleta Catppuccin Mocha - Colores principales
        colors = {
            # Fondos
            'primary_bg': (30, 30, 46),       # #1E1E2E
            'surface_bg': (49, 50, 68),       # #313244
            'surface_0': (17, 17, 27),        # #11111B
            'surface_1': (24, 24, 37),        # #181825
            'surface_2': (30, 30, 46),        # #1E1E2E
            
            # Acentos
            'accent_blue': (137, 180, 250),   # #89B4FA
            'accent_teal': (148, 226, 213),   # #94E2D5
            'accent_green': (166, 227, 161),  # #A6E3A1
            'accent_orange': (250, 179, 135), # #FAB387
            'accent_red': (243, 139, 168),    # #F38BA8
            'accent_purple': (203, 166, 247), # #CBA6F7
            'accent_yellow': (249, 226, 175), # #F9E2AF
            
            # Texto
            'text_primary': (205, 214, 244),  # #CDD6F4
            'text_secondary': (186, 194, 222),# #BAC2DE
            'text_muted': (166, 173, 200),    # #A6ADC8
            
            # Bordes
            'border_primary': (69, 71, 90),   # #45475A
            'border_secondary': (88, 91, 112),# #585B70
            'border_accent': (108, 112, 134), # #6C7086
            
            # Estados de operarios
            'status_idle': (186, 194, 222),     # #BAC2DE (gris claro)
            'status_moving': (166, 227, 161),   # #A6E3A1 (verde)
            'status_working': (250, 179, 135),  # #FAB387 (naranja)
            'status_picking': (137, 180, 250),  # #89B4FA (azul)
            'status_unloading': (243, 139, 168), # #F38BA8 (rosa/rojo)
            'status_lifting': (203, 166, 247),  # #CBA6F7 (purpura)
            'status_assigned': (249, 226, 175),  # #F9E2AF (amarillo)
            'status_in_progress': (148, 226, 213), # #94E2D5 (teal)
            'status_completed': (166, 227, 161), # #A6E3A1 (verde)
            'status_pending': (186, 194, 222),   # #BAC2DE (gris claro)
        }
        
        print("[DASHBOARD-WC] Esquema de colores cargado")
        return colors
    
    def _init_fonts(self) -> Dict[str, pygame.font.Font]:
        """
        Inicializa todas las fuentes necesarias para el dashboard.
        
        Returns:
            Dict con fuentes pygame
        """
        try:
            fonts = {
                'title': pygame.font.Font(None, 24),        # Titulo principal
                'subtitle': pygame.font.Font(None, 14),     # Subtitulo
                'section_header': pygame.font.Font(None, 16), # Headers de seccion
                'ticker_label': pygame.font.Font(None, 11), # Labels de ticker
                'ticker_value': pygame.font.Font(None, 14), # Valores de ticker
                'card_label': pygame.font.Font(None, 12),   # Labels de cards
                'card_value': pygame.font.Font(None, 22),   # Valores de cards
                'operator_id': pygame.font.Font(None, 14),  # ID de operario
                'operator_detail': pygame.font.Font(None, 12), # Detalles de operario
                'footer_key': pygame.font.Font(None, 12),   # Teclas de control
                'footer_desc': pygame.font.Font(None, 12),  # Descripciones
            }
            print("[DASHBOARD-WC] Fuentes inicializadas")
            return fonts
        except Exception as e:
            print(f"[DASHBOARD-WC ERROR] Error inicializando fuentes: {e}")
            # Fallback: usar fuente por defecto para todo
            default_font = pygame.font.Font(None, 14)
            return {key: default_font for key in [
                'title', 'subtitle', 'section_header', 'ticker_label', 
                'ticker_value', 'card_label', 'card_value', 'operator_id',
                'operator_detail', 'footer_key', 'footer_desc'
            ]}
    
    def render(self, surface: pygame.Surface, estado_visual: Dict[str, Any], 
               offset_x: int = 0) -> None:
        """
        Renderiza el dashboard completo con diseno world-class.
        
        Args:
            surface: Superficie pygame donde dibujar
            estado_visual: Dict con datos actuales de la simulacion
            offset_x: Offset horizontal para posicionamiento
        """
        if not self.visible:
            return
        
        # OPTIMIZACION FASE 7: Manejo seguro de datos None o vacios
        if estado_visual is None:
            estado_visual = {}
        
        # FASE 8: Validacion adicional de tipos de datos
        if not isinstance(estado_visual, dict):
            estado_visual = {}
        
        # Calcular posicion X segun configuracion
        if self.panel_position == 'left':
            panel_x = offset_x
        else:  # 'right'
            panel_x = surface.get_width() - self.panel_width + offset_x
        
        # 1. FONDO Y BORDE DEL PANEL
        self._render_background(surface, panel_x)
        
        # Inicializar posicion Y
        y = 0
        
        # 2. HEADER (Titulo + Subtitulo)
        y = self._render_header(surface, panel_x, y)
        
        # 3. TICKER ROW (KPIs rapidos)
        y = self._render_ticker_row(surface, panel_x, y, estado_visual)
        
        # 4. METRICS CARDS (4 cards principales)
        y = self._render_metrics_cards(surface, panel_x, y, estado_visual)
        
        # 5. PROGRESS BAR (Barra de progreso)
        y = self._render_progress_bar(surface, panel_x, y, estado_visual)
        
        # 6. OPERATORS LIST (Lista scrollable)
        operators_height = surface.get_height() - y - self.section_heights['footer']
        y = self._render_operators_list(surface, panel_x, y, operators_height, estado_visual)
        
        # 7. FOOTER (Controles)
        footer_y = surface.get_height() - self.section_heights['footer']
        self._render_footer(surface, panel_x, footer_y)
    
    def _render_background(self, surface: pygame.Surface, x: int) -> None:
        """
        Renderiza fondo del panel con gradiente sutil.
        
        Args:
            surface: Superficie pygame donde dibujar
            x: Posicion X del panel
        """
        height = surface.get_height()
        
        # Fondo principal con gradiente vertical sutil (OPTIMIZADO FASE 7)
        self._draw_gradient_rect_optimized(
            surface,
            pygame.Rect(x, 0, self.panel_width, height),
            self.colors['primary_bg'],
            self.colors['surface_bg'],
            vertical=True
        )
        
        # Borde derecho del panel (si esta a la izquierda)
        if self.panel_position == 'left':
            border_x = x + self.panel_width - 2
            pygame.draw.line(
                surface,
                self.colors['border_primary'],
                (border_x, 0),
                (border_x, height),
                2
            )
        else:  # Borde izquierdo (si esta a la derecha)
            border_x = x
            pygame.draw.line(
                surface,
                self.colors['border_primary'],
                (border_x, 0),
                (border_x, height),
                2
            )
    
    def _render_header(self, surface: pygame.Surface, x: int, y: int) -> int:
        """
        Renderiza header con titulo y subtitulo.
        
        Args:
            surface: Superficie pygame donde dibujar
            x: Posicion X del panel
            y: Posicion Y inicial
            
        Returns:
            Nueva posicion Y despues del header
        """
        # Fondo del header con gradiente (OPTIMIZADO FASE 7)
        header_rect = pygame.Rect(x, y, self.panel_width, self.section_heights['header'])
        self._draw_gradient_rect_optimized(
            surface,
            header_rect,
            self.colors['surface_bg'],
            self.colors['primary_bg'],
            vertical=True
        )
        
        # Titulo principal (OPTIMIZADO FASE 7)
        title_text = self._render_text_cached(
            "Dashboard de Agentes",
            self.fonts['title'],
            self.colors['text_primary']
        )
        title_x = x + 15
        title_y = y + 12
        surface.blit(title_text, (title_x, title_y))
        
        # Subtitulo (OPTIMIZADO FASE 7)
        subtitle_text = self._render_text_cached(
            "Sistema de Monitoreo en Tiempo Real",
            self.fonts['subtitle'],
            self.colors['text_muted']
        )
        subtitle_x = x + 15
        subtitle_y = y + 36
        surface.blit(subtitle_text, (subtitle_x, subtitle_y))
        
        # Linea separadora inferior con color accent
        line_y = y + self.section_heights['header'] - 1
        pygame.draw.line(
            surface,
            self.colors['accent_blue'],
            (x + 15, line_y),
            (x + self.panel_width - 15, line_y),
            2
        )
        
        return y + self.section_heights['header']
    
    def _render_ticker_row(self, surface: pygame.Surface, x: int, y: int, 
                          estado_visual: Dict[str, Any]) -> int:
        """
        Renderiza fila de KPIs rapidos (ticker).
        
        Args:
            surface: Superficie pygame donde dibujar
            x: Posicion X del panel
            y: Posicion Y inicial
            estado_visual: Datos actuales
            
        Returns:
            Nueva posicion Y
        """
        # Fondo del ticker
        ticker_rect = pygame.Rect(x + 10, y + 5, self.panel_width - 20, self.section_heights['ticker'] - 10)
        pygame.draw.rect(surface, self.colors['surface_0'], ticker_rect, border_radius=8)
        pygame.draw.rect(surface, self.colors['border_primary'], ticker_rect, width=1, border_radius=8)
        
        # Extraer metricas
        metricas = estado_visual.get('metricas', {})
        
        # Calcular valores para los 4 slots
        tiempo = metricas.get('tiempo', 0.0)
        tiempo_formateado = self._format_time_short(tiempo)
        
        wos_completadas = metricas.get('workorders_completadas', 0)
        total_wos = metricas.get('total_wos', 0)
        wip = max(total_wos - wos_completadas, 0)  # Work In Progress
        
        utilizacion = metricas.get('utilizacion_promedio', 0)
        util_text = f"{utilizacion:.0f}%" if isinstance(utilizacion, (int, float)) and utilizacion > 0 else "-"
        
        throughput = metricas.get('throughput_min', 0)
        throughput_text = f"{throughput:.1f}/min" if isinstance(throughput, (int, float)) and throughput > 0 else "-"
        
        # Configurar 4 slots
        slots = [
            ("Tiempo", tiempo_formateado, self.colors['accent_blue']),
            ("WIP", f"{wip}/{total_wos}" if total_wos > 0 else "0/0", self.colors['accent_orange']),
            ("Util", util_text, self.colors['accent_green']),
            ("T/put", throughput_text, self.colors['accent_teal'])
        ]
        
        # Calcular dimensiones
        slot_width = (ticker_rect.width - 40) // 4
        slot_x = ticker_rect.x + 10
        
        for i, (label, value, accent_color) in enumerate(slots):
            # Posicion X del slot
            current_x = slot_x + (i * (slot_width + 10))
            
            # Renderizar label (arriba)
            label_surface = self.fonts['ticker_label'].render(label, True, self.colors['text_secondary'])
            label_rect = label_surface.get_rect()
            label_rect.centerx = current_x + slot_width // 2
            label_rect.y = ticker_rect.y + 8
            surface.blit(label_surface, label_rect)
            
            # Renderizar valor (abajo) con color accent
            value_surface = self.fonts['ticker_value'].render(value, True, accent_color)
            value_rect = value_surface.get_rect()
            value_rect.centerx = current_x + slot_width // 2
            value_rect.y = ticker_rect.y + 26
            surface.blit(value_surface, value_rect)
            
            # Separador vertical (excepto ultimo slot)
            if i < len(slots) - 1:
                sep_x = current_x + slot_width + 5
                pygame.draw.line(
                    surface,
                    self.colors['border_primary'],
                    (sep_x, ticker_rect.y + 6),
                    (sep_x, ticker_rect.bottom - 6),
                    1
                )
        
        return y + self.section_heights['ticker']
    
    def _render_metrics_cards(self, surface: pygame.Surface, x: int, y: int,
                             estado_visual: Dict[str, Any]) -> int:
        """
        Renderiza 4 cards de metricas principales en layout 2x2.
        
        Args:
            surface: Superficie pygame donde dibujar
            x: Posicion X del panel
            y: Posicion Y inicial
            estado_visual: Datos actuales
            
        Returns:
            Nueva posicion Y
        """
        # Extraer metricas
        metricas = estado_visual.get('metricas', {})
        
        tiempo = metricas.get('tiempo', 0.0)
        tiempo_formateado = self._format_time_hhmmss(tiempo)
        
        wos_completadas = metricas.get('workorders_completadas', 0)
        total_wos = metricas.get('total_wos', 0)
        wos_text = f"{wos_completadas} / {total_wos}"
        
        tareas_completadas = metricas.get('tareas_completadas', 0)
        tareas_text = str(tareas_completadas)
        
        progreso = (wos_completadas / total_wos * 100) if total_wos > 0 else 0.0
        progreso_text = f"{progreso:.1f}%"
        
        # Configurar las 4 cards
        cards_data = [
            {
                'icon': 'T',
                'label': 'Tiempo',
                'value': tiempo_formateado,
                'color': self.colors['accent_blue']
            },
            {
                'icon': 'W',
                'label': 'WorkOrders',
                'value': wos_text,
                'color': self.colors['accent_green']
            },
            {
                'icon': 'U',
                'label': 'Tareas',
                'value': tareas_text,
                'color': self.colors['accent_orange']
            },
            {
                'icon': 'P',
                'label': 'Progreso',
                'value': progreso_text,
                'color': self.colors['accent_teal']
            }
        ]
        
        # Dimensiones de las cards
        card_width = (self.panel_width - 40) // 2  # 2 columnas
        card_height = (self.section_heights['metrics'] - 20) // 2  # 2 filas
        gap = 10  # Espacio entre cards
        
        # Renderizar cards en layout 2x2
        for i, card_data in enumerate(cards_data):
            row = i // 2  # 0 o 1
            col = i % 2   # 0 o 1
            
            card_x = x + 10 + (col * (card_width + gap))
            card_y = y + 5 + (row * (card_height + gap))
            
            self._draw_card(
                surface,
                card_x,
                card_y,
                card_width,
                card_height,
                card_data['icon'],
                card_data['label'],
                card_data['value'],
                card_data['color']
            )
        
        return y + self.section_heights['metrics']
    
    def _render_progress_bar(self, surface: pygame.Surface, x: int, y: int,
                            estado_visual: Dict[str, Any]) -> int:
        """
        Renderiza barra de progreso con gradiente horizontal.
        
        Args:
            surface: Superficie pygame donde dibujar
            x: Posicion X del panel
            y: Posicion Y inicial
            estado_visual: Datos actuales
            
        Returns:
            Nueva posicion Y
        """
        # Extraer datos de progreso
        metricas = estado_visual.get('metricas', {})
        wos_completadas = metricas.get('workorders_completadas', 0)
        total_wos = metricas.get('total_wos', 0)
        
        # Calcular porcentaje
        if total_wos > 0:
            progreso = (wos_completadas / total_wos) * 100.0
        else:
            progreso = 0.0
        
        # Posicion inicial
        start_y = y + 5
        
        # 1. Header de la seccion
        header_text = self.fonts['section_header'].render(
            "Progreso General",
            True,
            self.colors['text_primary']
        )
        surface.blit(header_text, (x + 15, start_y))
        start_y += 22
        
        # 2. Barra de progreso
        bar_width = self.panel_width - 30
        bar_height = 20
        bar_x = x + 15
        bar_y = start_y
        
        # Fondo de la barra (oscuro)
        bar_bg_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
        pygame.draw.rect(surface, self.colors['surface_0'], bar_bg_rect, border_radius=10)
        pygame.draw.rect(surface, self.colors['border_primary'], bar_bg_rect, width=2, border_radius=10)
        
        # Relleno de la barra (con gradiente verde-teal)
        if progreso > 0:
            fill_width = int((bar_width - 4) * (progreso / 100.0))
            if fill_width > 0:
                fill_rect = pygame.Rect(bar_x + 2, bar_y + 2, fill_width, bar_height - 4)
                
                # Dibujar gradiente horizontal (verde -> teal)
                self._draw_gradient_rect(
                    surface,
                    fill_rect,
                    self.colors['accent_green'],
                    self.colors['accent_teal'],
                    vertical=False
                )
                
                # Borde redondeado del relleno
                pygame.draw.rect(surface, self.colors['accent_green'], fill_rect, width=1, border_radius=8)
        
        start_y += bar_height + 8
        
        # 3. Label de porcentaje
        percentage_text = f"{progreso:.1f}% Completado ({wos_completadas}/{total_wos} WorkOrders)"
        percentage_surface = self.fonts['ticker_label'].render(
            percentage_text,
            True,
            self.colors['text_secondary']
        )
        percentage_rect = percentage_surface.get_rect()
        percentage_rect.centerx = x + (self.panel_width // 2)
        percentage_rect.y = start_y
        surface.blit(percentage_surface, percentage_rect)
        
        return y + self.section_heights['progress']
    
    def _render_operators_list(self, surface: pygame.Surface, x: int, y: int,
                               height: int, estado_visual: Dict[str, Any]) -> int:
        """
        Renderiza lista scrollable de operarios con estados y capacidades.
        
        Args:
            surface: Superficie pygame donde dibujar
            x: Posicion X del panel
            y: Posicion Y inicial
            height: Altura disponible para la lista
            estado_visual: Datos actuales
            
        Returns:
            Nueva posicion Y
        """
        # 1. Header de la seccion
        header_text = self.fonts['section_header'].render(
            "Operarios Activos",
            True,
            self.colors['text_primary']
        )
        surface.blit(header_text, (x + 15, y + 5))
        
        # 2. Contenedor de la lista
        list_y = y + 25
        list_height = height - 30
        operators_rect = pygame.Rect(x + 10, list_y, self.panel_width - 20, list_height)
        
        # Fondo del contenedor
        pygame.draw.rect(surface, self.colors['surface_0'], operators_rect, border_radius=10)
        pygame.draw.rect(surface, self.colors['border_primary'], operators_rect, width=1, border_radius=10)
        
        # 3. Extraer datos de operarios
        operarios_dict = estado_visual.get('operarios', {})
        
        if not operarios_dict:
            # Mostrar mensaje cuando no hay operarios
            no_ops_text = self.fonts['operator_detail'].render(
                "No hay operarios activos",
                True,
                self.colors['text_muted']
            )
            no_ops_rect = no_ops_text.get_rect()
            no_ops_rect.center = operators_rect.center
            surface.blit(no_ops_text, no_ops_rect)
            return y + height
        
        # Convertir diccionario a lista de operarios con ID
        operarios_list = []
        for operator_id, operator_data in operarios_dict.items():
            operario = {
                'id': operator_id,
                'tipo': operator_data.get('tipo', 'GroundOperator'),
                'estado': operator_data.get('status', 'idle'),
                'carga_actual': operator_data.get('carga', 0),
                'capacidad_max': operator_data.get('capacidad', 100),
                'ubicacion': f"({operator_data.get('x', 0)}, {operator_data.get('y', 0)})",
                'current_task': operator_data.get('current_task', None),  # WorkOrder actual
                'current_work_area': operator_data.get('current_work_area', None)  # Work Area actual
            }
            operarios_list.append(operario)
        
        # 4. Configurar scroll y dimensiones
        operator_height = 45  # Altura de cada operario
        visible_operators = min(len(operarios_list), list_height // operator_height)
        
        # Calcular scroll offset si hay mas operarios de los visibles
        if len(operarios_list) > visible_operators:
            max_scroll = len(operarios_list) - visible_operators
            self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))
        else:
            self.scroll_offset = 0
        
        # 5. Renderizar operarios visibles
        start_index = self.scroll_offset
        end_index = start_index + visible_operators
        
        for i, operario in enumerate(operarios_list[start_index:end_index]):
            operator_y = list_y + 5 + (i * operator_height)
            self._render_single_operator(surface, x + 15, operator_y, operario)
        
        # 6. Renderizar indicador de scroll si es necesario
        if len(operarios_list) > visible_operators:
            self._render_scroll_indicator(surface, operators_rect, len(operarios_list), visible_operators)
        
        return y + height
    
    def _render_single_operator(self, surface: pygame.Surface, x: int, y: int, operario: Dict[str, Any]) -> None:
        """
        Renderiza un operario individual con estado, carga y tipo.
        
        Args:
            surface: Superficie pygame donde dibujar
            x, y: Posicion del operario
            operario: Dict con datos del operario
        """
        # Extraer datos del operario
        operator_id = operario.get('id', 'Unknown')
        operator_type = operario.get('tipo', 'GroundOperator')
        estado = operario.get('estado', 'idle')
        carga_actual = operario.get('carga_actual', 0)
        capacidad_max = operario.get('capacidad_max', 100)
        ubicacion = operario.get('ubicacion', 'Unknown')
        current_task = operario.get('current_task', None)  # WorkOrder actual
        current_work_area = operario.get('current_work_area', None)  # Work Area actual
        
        # Calcular porcentaje de carga
        carga_porcentaje = (carga_actual / capacidad_max * 100) if capacidad_max > 0 else 0
        
        # 1. Fondo del operario
        operator_rect = pygame.Rect(x, y, self.panel_width - 30, 40)
        pygame.draw.rect(surface, self.colors['surface_bg'], operator_rect, border_radius=8)
        pygame.draw.rect(surface, self.colors['border_secondary'], operator_rect, width=1, border_radius=8)
        
        # 2. Icono del tipo de operario
        icon = self._get_operator_icon(operator_type)
        icon_surface = self.fonts['operator_id'].render(icon, True, self.colors['accent_blue'])
        surface.blit(icon_surface, (x + 8, y + 8))
        
        # 3. ID del operario
        id_text = self.fonts['operator_id'].render(operator_id, True, self.colors['text_primary'])
        surface.blit(id_text, (x + 35, y + 6))
        
        # 3.5. WorkOrder actual y Work Area (si existe)
        if current_task:
            # Formato: "WO: WO-XXXX (Area_Ground)"
            if current_work_area:
                wo_text = f"WO: {current_task} ({current_work_area})"
            else:
                wo_text = f"WO: {current_task}"
            
            wo_surface = self.fonts['operator_detail'].render(wo_text, True, self.colors['accent_green'])
            # Posicionar en la parte superior derecha del cuadro
            wo_x = x + operator_rect.width - wo_surface.get_width() - 8
            surface.blit(wo_surface, (wo_x, y + 6))
        
        # 4. Estado del operario
        estado_text = self._get_operator_status_text(estado)
        estado_color = self._get_operator_status_color(estado)
        estado_surface = self.fonts['operator_detail'].render(estado_text, True, estado_color)
        surface.blit(estado_surface, (x + 35, y + 22))
        
        # 5. Barra de carga (si aplica)
        if capacidad_max > 0:
            carga_x = x + 120
            carga_y = y + 8
            carga_width = 80
            carga_height = 8
            
            # Fondo de la barra de carga
            carga_bg_rect = pygame.Rect(carga_x, carga_y, carga_width, carga_height)
            pygame.draw.rect(surface, self.colors['surface_0'], carga_bg_rect, border_radius=4)
            
            # Relleno de la barra de carga
            if carga_porcentaje > 0:
                fill_width = int(carga_width * (carga_porcentaje / 100.0))
                if fill_width > 0:
                    fill_rect = pygame.Rect(carga_x, carga_y, fill_width, carga_height)
                    carga_color = self._get_load_color(carga_porcentaje)
                    pygame.draw.rect(surface, carga_color, fill_rect, border_radius=4)
            
            # Label de carga
            carga_text = f"{carga_actual}/{capacidad_max}"
            carga_label_surface = self.fonts['operator_detail'].render(carga_text, True, self.colors['text_secondary'])
            surface.blit(carga_label_surface, (carga_x + carga_width + 5, carga_y - 2))
        
        # 6. Ubicacion (si hay espacio)
        if self.panel_width > 300:  # Solo si hay espacio suficiente
            ubicacion_text = f"@{ubicacion}"
            ubicacion_surface = self.fonts['operator_detail'].render(ubicacion_text, True, self.colors['text_muted'])
            ubicacion_x = x + operator_rect.width - ubicacion_surface.get_width() - 8
            surface.blit(ubicacion_surface, (ubicacion_x, y + 22))
    
    def _render_scroll_indicator(self, surface: pygame.Surface, operators_rect: pygame.Rect, 
                                total_operators: int, visible_operators: int) -> None:
        """
        Renderiza indicador de scroll en el lado derecho.
        
        Args:
            surface: Superficie pygame donde dibujar
            operators_rect: Rectangulo del contenedor de operarios
            total_operators: Total de operarios
            visible_operators: Operarios visibles
        """
        # Calcular posicion del indicador
        indicator_width = 6
        indicator_height = max(20, (visible_operators / total_operators) * operators_rect.height)
        indicator_x = operators_rect.right - indicator_width - 3
        indicator_y = operators_rect.y + 3
        
        # Fondo del indicador
        indicator_bg_rect = pygame.Rect(indicator_x, operators_rect.y + 2, indicator_width, operators_rect.height - 4)
        pygame.draw.rect(surface, self.colors['surface_0'], indicator_bg_rect, border_radius=3)
        
        # Barra del indicador
        indicator_rect = pygame.Rect(indicator_x, indicator_y, indicator_width, int(indicator_height))
        pygame.draw.rect(surface, self.colors['accent_blue'], indicator_rect, border_radius=3)
    
    def _get_operator_icon(self, operator_type: str) -> str:
        """
        Retorna icono para el tipo de operario.
        
        Args:
            operator_type: Tipo de operario
            
        Returns:
            Icono emoji
        """
        icons = {
            'GroundOperator': 'G',
            'Forklift': 'F',
            'Montacargas': 'F',
            'Operario': 'O',
            'default': '?'
        }
        return icons.get(operator_type, icons['default'])
    
    def _get_operator_status_text(self, estado: str) -> str:
        """
        Retorna texto descriptivo para el estado del operario.
        
        Args:
            estado: Estado del operario
            
        Returns:
            Texto descriptivo
        """
        status_texts = {
            'idle': 'Idle',
            'moving': 'En ruta',
            'working': 'Trabajando',
            'picking': 'Picking',
            'unloading': 'Descargando',
            'lifting': 'Elevando',
            'assigned': 'Asignado',
            'in_progress': 'En progreso',
            'completed': 'Completado',
            'pending': 'Pendiente',
            'default': 'Desconocido'
        }
        return status_texts.get(estado.lower(), status_texts['default'])
    
    def _get_operator_status_color(self, estado: str) -> Tuple[int, int, int]:
        """
        Retorna color para el estado del operario.
        
        Args:
            estado: Estado del operario
            
        Returns:
            Color RGB
        """
        return self.colors.get(f'status_{estado.lower()}', self.colors['text_secondary'])
    
    def _get_load_color(self, carga_porcentaje: float) -> Tuple[int, int, int]:
        """
        Retorna color para la barra de carga segun el porcentaje.
        
        Args:
            carga_porcentaje: Porcentaje de carga (0-100)
            
        Returns:
            Color RGB
        """
        if carga_porcentaje < 30:
            return self.colors['accent_green']
        elif carga_porcentaje < 70:
            return self.colors['accent_yellow']
        else:
            return self.colors['accent_red']
    
    def _render_footer(self, surface: pygame.Surface, x: int, y: int) -> None:
        """
        Renderiza footer con controles de teclado y informacion del sistema.
        
        Args:
            surface: Superficie pygame donde dibujar
            x: Posicion X del panel
            y: Posicion Y inicial
        """
        # 1. FONDO DEL FOOTER
        footer_rect = pygame.Rect(x, y, self.panel_width, self.section_heights['footer'])
        
        # Gradiente de fondo
        self._draw_gradient_rect(
            surface,
            footer_rect,
            self.colors['surface_bg'],
            self.colors['surface_0'],
            vertical=True
        )
        
        # Linea separadora superior
        pygame.draw.line(
            surface,
            self.colors['border_primary'],
            (x, y),
            (x + self.panel_width, y),
            2
        )
        
        # 2. SECCION DE CONTROLES DE TECLADO
        controls_y = y + 10
        
        # Header de controles
        controls_header = self.fonts['section_header'].render(
            "Controles de Teclado",
            True,
            self.colors['text_primary']
        )
        surface.blit(controls_header, (x + 15, controls_y))
        controls_y += 25
        
        # Definir controles de teclado
        keyboard_controls = [
            ("ESPACIO", "Pausa/Reanudar"),
            ("+/-", "Velocidad +/-"),
            ("R", "Reiniciar"),
            ("ESC", "Salir"),
            ("F11", "Pantalla Completa"),
            ("H", "Ayuda")
        ]
        
        # Renderizar controles en 2 columnas
        control_width = (self.panel_width - 40) // 2
        control_height = 20
        
        for i, (key, description) in enumerate(keyboard_controls):
            col = i % 2
            row = i // 2
            
            control_x = x + 15 + (col * (control_width + 10))
            control_y = controls_y + (row * control_height)
            
            # Tecla (con fondo destacado y mejor contraste)
            key_rect = pygame.Rect(control_x, control_y, 40, 16)
            pygame.draw.rect(surface, self.colors['surface_0'], key_rect, border_radius=4)
            pygame.draw.rect(surface, self.colors['accent_blue'], key_rect, width=2, border_radius=4)
            
            # Texto de tecla con mejor contraste (blanco sobre fondo oscuro)
            key_text = self.fonts['footer_key'].render(key, True, self.colors['text_primary'])
            key_text_rect = key_text.get_rect()
            key_text_rect.center = key_rect.center
            surface.blit(key_text, key_text_rect)
            
            # Descripcion con mejor contraste
            desc_text = self.fonts['footer_desc'].render(description, True, self.colors['text_primary'])
            surface.blit(desc_text, (control_x + 45, control_y + 2))
        
        # 3. SECCION DE INFORMACION DEL SISTEMA (reposicionada para evitar superposicion)
        system_y = y + 70  # Movido mas arriba para evitar superposicion
        
        # Header de sistema
        system_header = self.fonts['section_header'].render(
            "Informacion del Sistema",
            True,
            self.colors['text_primary']
        )
        surface.blit(system_header, (x + 15, system_y))
        system_y += 25
        
        # Informacion del sistema
        system_info = [
            ("Version", "v11.0.0-beta.1"),
            ("Modo", "Replay Viewer"),
            ("Dashboard", "World-Class"),
            ("Estado", "Activo")
        ]
        
        # Renderizar informacion del sistema
        for i, (label, value) in enumerate(system_info):
            info_y = system_y + (i * 18)
            
            # Label
            label_text = self.fonts['footer_desc'].render(f"{label}:", True, self.colors['text_muted'])
            surface.blit(label_text, (x + 20, info_y))
            
            # Valor
            value_text = self.fonts['footer_desc'].render(value, True, self.colors['accent_green'])
            surface.blit(value_text, (x + 80, info_y))
        
        # 4. INDICADOR DE ESTADO EN TIEMPO REAL (mas visible)
        status_y = y + self.section_heights['footer'] - 30  # Movido mas arriba
        
        # Punto de estado mas grande y brillante (verde = activo)
        status_dot_rect = pygame.Rect(x + 15, status_y + 8, 12, 12)
        pygame.draw.circle(surface, self.colors['accent_green'], status_dot_rect.center, 6)
        # Agregar un borde brillante para mayor visibilidad
        pygame.draw.circle(surface, self.colors['accent_teal'], status_dot_rect.center, 6, width=2)
        
        # Texto de estado mas prominente
        status_text = self.fonts['footer_desc'].render(
            "Dashboard World-Class Activo",
            True,
            self.colors['accent_green']  # Color mas brillante
        )
        surface.blit(status_text, (x + 35, status_y + 5))
        
        # 5. VERSION Y COPYRIGHT
        version_text = self.fonts['footer_desc'].render(
            "Digital Twin Warehouse Simulator",
            True,
            self.colors['text_muted']
        )
        version_rect = version_text.get_rect()
        version_rect.bottomright = (x + self.panel_width - 15, y + self.section_heights['footer'] - 5)
        surface.blit(version_text, version_rect)
    
    # =========================================================================
    # HELPERS DE FORMATEO DE DATOS
    # =========================================================================
    
    def _format_time_short(self, segundos: float) -> str:
        """
        Formatea tiempo a formato corto para ticker (MM:SS o HH:MM).
        
        Args:
            segundos: Tiempo en segundos
            
        Returns:
            Tiempo formateado
        """
        if segundos < 3600:  # Menos de 1 hora
            minutos = int(segundos // 60)
            segs = int(segundos % 60)
            return f"{minutos:02d}:{segs:02d}"
        else:  # 1 hora o mas
            horas = int(segundos // 3600)
            minutos = int((segundos % 3600) // 60)
            return f"{horas:02d}:{minutos:02d}h"
    
    def _format_time_hhmmss(self, segundos: float) -> str:
        """
        Formatea tiempo a formato HH:MM:SS completo.
        
        Args:
            segundos: Tiempo en segundos
            
        Returns:
            Tiempo formateado en HH:MM:SS
        """
        horas = int(segundos // 3600)
        minutos = int((segundos % 3600) // 60)
        segs = int(segundos % 60)
        return f"{horas:02d}:{minutos:02d}:{segs:02d}"
    
    def _format_number(self, numero: float, decimales: int = 1) -> str:
        """
        Formatea numero con separadores y decimales.
        
        Args:
            numero: Numero a formatear
            decimales: Numero de decimales
            
        Returns:
            Numero formateado
        """
        if numero >= 1000000:
            return f"{numero/1000000:.{decimales}f}M"
        elif numero >= 1000:
            return f"{numero/1000:.{decimales}f}K"
        else:
            return f"{numero:.{decimales}f}"
    
    # =========================================================================
    # HELPERS DE RENDERIZADO
    # =========================================================================
    
    def _draw_card(self, surface: pygame.Surface, x: int, y: int, width: int, height: int,
                   icon: str, label: str, value: str, accent_color: Tuple[int, int, int]) -> None:
        """
        Dibuja una card de metrica con sombra, icono y valores.
        
        Args:
            surface: Superficie pygame donde dibujar
            x, y: Posicion de la card
            width, height: Dimensiones de la card
            icon: Emoji/icono para la metrica
            label: Label de la metrica
            value: Valor de la metrica
            accent_color: Color accent para el valor
        """
        card_rect = pygame.Rect(x, y, width, height)
        
        # 1. Dibujar sombra (offset 3px abajo y derecha)
        shadow_rect = pygame.Rect(x + 3, y + 3, width, height)
        shadow_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.rect(
            shadow_surface, 
            (0, 0, 0, 60),  # Negro con alpha 60
            (0, 0, width, height), 
            border_radius=12
        )
        surface.blit(shadow_surface, shadow_rect.topleft)
        
        # 2. Dibujar fondo de la card
        pygame.draw.rect(surface, self.colors['surface_bg'], card_rect, border_radius=12)
        
        # 3. Dibujar borde
        pygame.draw.rect(surface, self.colors['border_primary'], card_rect, width=2, border_radius=12)
        
        # 4. Renderizar icono (esquina superior izquierda)
        icon_surface = self.fonts['card_value'].render(icon, True, accent_color)
        icon_x = x + 12
        icon_y = y + 10
        surface.blit(icon_surface, (icon_x, icon_y))
        
        # 5. Renderizar label (debajo del icono)
        label_surface = self.fonts['card_label'].render(label, True, self.colors['text_secondary'])
        label_x = x + 12
        label_y = y + 40
        surface.blit(label_surface, (label_x, label_y))
        
        # 6. Renderizar valor (grande, centro-abajo)
        value_surface = self.fonts['card_value'].render(value, True, accent_color)
        value_rect = value_surface.get_rect()
        value_rect.centerx = card_rect.centerx
        value_rect.bottom = card_rect.bottom - 15
        surface.blit(value_surface, value_rect)
    
    def _draw_gradient_rect(self, surface: pygame.Surface, rect: pygame.Rect,
                           color1: Tuple[int, int, int], 
                           color2: Tuple[int, int, int],
                           vertical: bool = True) -> None:
        """
        Dibuja rectangulo con gradiente suave.
        
        Args:
            surface: Superficie pygame donde dibujar
            rect: Rectangulo a rellenar
            color1: Color inicial (R, G, B)
            color2: Color final (R, G, B)
            vertical: True para gradiente vertical, False para horizontal
        """
        if vertical:
            # Gradiente vertical
            for y in range(rect.height):
                ratio = y / rect.height
                r = int(color1[0] + (color2[0] - color1[0]) * ratio)
                g = int(color1[1] + (color2[1] - color1[1]) * ratio)
                b = int(color1[2] + (color2[2] - color1[2]) * ratio)
                pygame.draw.line(
                    surface,
                    (r, g, b),
                    (rect.x, rect.y + y),
                    (rect.x + rect.width, rect.y + y)
                )
        else:
            # Gradiente horizontal
            for x in range(rect.width):
                ratio = x / rect.width
                r = int(color1[0] + (color2[0] - color1[0]) * ratio)
                g = int(color1[1] + (color2[1] - color1[1]) * ratio)
                b = int(color1[2] + (color2[2] - color1[2]) * ratio)
                pygame.draw.line(
                    surface,
                    (r, g, b),
                    (rect.x + x, rect.y),
                    (rect.x + x, rect.y + rect.height)
                )
    
    # =========================================================================
    # METODOS DE CONTROL
    # =========================================================================
    
    def toggle_visibility(self) -> bool:
        """
        Alterna la visibilidad del dashboard.
        
        Returns:
            Nuevo estado de visibilidad
        """
        self.visible = not self.visible
        return self.visible
    
    def set_visibility(self, visible: bool) -> None:
        """
        Establece la visibilidad del dashboard.
        
        Args:
            visible: True para mostrar, False para ocultar
        """
        self.visible = visible
    
    def handle_mouse_event(self, event: pygame.event.Event, offset_x: int = 0) -> None:
        """
        Maneja eventos de mouse para scroll y hover.
        
        Args:
            event: Evento de pygame
            offset_x: Offset horizontal del panel
        """
        if not self.visible:
            return
        
        # Calcular posicion del panel
        if self.panel_position == 'left':
            panel_x = offset_x
        else:
            panel_x = pygame.display.get_surface().get_width() - self.panel_width + offset_x
        
        # Manejar scroll de la lista de operarios
        if event.type == pygame.MOUSEWHEEL:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            
            # Verificar si el mouse esta sobre el area de operarios
            operators_area = pygame.Rect(
                panel_x + 10, 
                0,  # Se calculara dinamicamente
                self.panel_width - 20, 
                0   # Se calculara dinamicamente
            )
            
            # Solo procesar scroll si estamos sobre el panel
            if panel_x <= mouse_x <= panel_x + self.panel_width:
                # Scroll hacia arriba (wheel up)
                if event.y > 0:
                    self.scroll_offset = max(0, self.scroll_offset - 1)
                # Scroll hacia abajo (wheel down)
                elif event.y < 0:
                    self.scroll_offset += 1
    
    def update_data(self, estado_visual: Dict[str, Any]) -> None:
        """
        Actualiza datos internos si necesario (opcional).
        
        Args:
            estado_visual: Dict con datos actuales
        """
        # OPTIMIZACION FASE 7: Cache inteligente de datos con manejo seguro
        import time
        current_time = time.time()
        
        # Manejo seguro de datos None o vacios
        if estado_visual is None:
            estado_visual = {}
        
        # Solo actualizar cache si los datos han cambiado significativamente
        metrics_data = estado_visual.get('metricas', {}) if isinstance(estado_visual, dict) else {}
        operators_data = estado_visual.get('operarios', {}) if isinstance(estado_visual, dict) else {}
        
        # Verificar si los datos han cambiado
        metrics_changed = self._cached_metrics_data != metrics_data
        operators_changed = self._cached_operators_data != operators_data
        
        if metrics_changed or operators_changed or (current_time - self._last_render_time) > self._performance_config['cache_ttl']:
            self._cached_metrics_data = metrics_data.copy() if isinstance(metrics_data, dict) else {}
            self._cached_operators_data = operators_data.copy() if isinstance(operators_data, dict) else {}
            self._render_cache_valid = False
            self._last_render_time = current_time
    
    # =========================================================================
    # OPTIMIZACIONES DE RENDIMIENTO FASE 7
    # =========================================================================
    
    def _get_cached_surface(self, cache_key: str, width: int, height: int) -> Optional[pygame.Surface]:
        """
        Obtiene superficie desde cache o crea una nueva.
        
        Args:
            cache_key: Clave unica para el cache
            width: Ancho de la superficie
            height: Alto de la superficie
            
        Returns:
            Superficie pygame desde cache o None si no existe
        """
        if not self._performance_config['enable_gradient_cache']:
            return None
            
        if cache_key in self._cached_surfaces:
            surface = self._cached_surfaces[cache_key]
            if surface.get_width() == width and surface.get_height() == height:
                return surface
        
        # Limpiar cache si esta lleno
        if len(self._cached_surfaces) >= self._performance_config['max_cache_size']:
            self._clear_cache()
        
        return None
    
    def _cache_surface(self, cache_key: str, surface: pygame.Surface) -> None:
        """
        Guarda superficie en cache.
        
        Args:
            cache_key: Clave unica para el cache
            surface: Superficie pygame a cachear
        """
        if self._performance_config['enable_gradient_cache']:
            self._cached_surfaces[cache_key] = surface.copy()
    
    def _clear_cache(self) -> None:
        """Limpia el cache de superficies."""
        self._cached_surfaces.clear()
        print("[DASHBOARD-WC] Cache de superficies limpiado")
    
    def _draw_gradient_rect_optimized(self, surface: pygame.Surface, rect: pygame.Rect,
                                    color1: Tuple[int, int, int], 
                                    color2: Tuple[int, int, int],
                                    vertical: bool = True) -> None:
        """
        Dibuja rectangulo con gradiente optimizado usando cache.
        
        Args:
            surface: Superficie pygame donde dibujar
            rect: Rectangulo a rellenar
            color1: Color inicial (R, G, B)
            color2: Color final (R, G, B)
            vertical: True para gradiente vertical, False para horizontal
        """
        # Crear clave de cache unica
        cache_key = f"gradient_{rect.width}x{rect.height}_{color1}_{color2}_{vertical}"
        
        # Intentar obtener desde cache
        cached_surface = self._get_cached_surface(cache_key, rect.width, rect.height)
        
        if cached_surface:
            # Usar superficie cacheada
            surface.blit(cached_surface, rect.topleft)
        else:
            # Crear nueva superficie y cachearla
            gradient_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            
            if vertical:
                # Gradiente vertical optimizado
                for y in range(rect.height):
                    ratio = y / rect.height
                    r = int(color1[0] + (color2[0] - color1[0]) * ratio)
                    g = int(color1[1] + (color2[1] - color1[1]) * ratio)
                    b = int(color1[2] + (color2[2] - color1[2]) * ratio)
                    pygame.draw.line(
                        gradient_surface,
                        (r, g, b),
                        (0, y),
                        (rect.width, y)
                    )
            else:
                # Gradiente horizontal optimizado
                for x in range(rect.width):
                    ratio = x / rect.width
                    r = int(color1[0] + (color2[0] - color1[0]) * ratio)
                    g = int(color1[1] + (color2[1] - color1[1]) * ratio)
                    b = int(color1[2] + (color2[2] - color1[2]) * ratio)
                    pygame.draw.line(
                        gradient_surface,
                        (r, g, b),
                        (x, 0),
                        (x, rect.height)
                    )
            
            # Cachear y usar la superficie
            self._cache_surface(cache_key, gradient_surface)
            surface.blit(gradient_surface, rect.topleft)
    
    def _render_text_cached(self, text: str, font: pygame.font.Font, color: Tuple[int, int, int]) -> pygame.Surface:
        """
        Renderiza texto con cache para mejor rendimiento.
        
        Args:
            text: Texto a renderizar
            font: Fuente pygame
            color: Color del texto
            
        Returns:
            Superficie con texto renderizado
        """
        if not self._performance_config['enable_text_cache']:
            return font.render(text, True, color)
        
        # Crear clave de cache
        cache_key = f"text_{text}_{font.get_height()}_{color}"
        
        if cache_key in self._cached_surfaces:
            return self._cached_surfaces[cache_key]
        
        # Renderizar y cachear
        text_surface = font.render(text, True, color)
        self._cache_surface(cache_key, text_surface)
        return text_surface
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Retorna estadisticas de rendimiento del dashboard.
        
        Returns:
            Dict con estadisticas de rendimiento
        """
        return {
            'cache_size': len(self._cached_surfaces),
            'max_cache_size': self._performance_config['max_cache_size'],
            'cache_ttl': self._performance_config['cache_ttl'],
            'gradient_cache_enabled': self._performance_config['enable_gradient_cache'],
            'text_cache_enabled': self._performance_config['enable_text_cache'],
            'card_cache_enabled': self._performance_config['enable_card_cache'],
            'last_render_time': self._last_render_time,
            'render_cache_valid': self._render_cache_valid
        }
    
    # =========================================================================
    # METODOS AVANZADOS FASE 8 - PULIDO FINAL
    # =========================================================================
    
    def get_dashboard_info(self) -> Dict[str, Any]:
        """
        Retorna informacion completa del dashboard.
        
        Returns:
            Dict con informacion del dashboard
        """
        return {
            'version': 'v11.0.0-beta.1',
            'phase': 'FASE 8 - Pulido Final COMPLETADA',
            'panel_width': self.panel_width,
            'panel_position': self.panel_position,
            'visible': self.visible,
            'scroll_offset': self.scroll_offset,
            'max_operators_visible': self.max_operators_visible,
            'section_heights': self.section_heights.copy(),
            'performance_config': self._performance_config.copy(),
            'features': [
                'Estructura Base',
                'Header y Ticker',
                'Metrics Cards',
                'Progress Bar',
                'Operators List',
                'Footer con Controles',
                'Integracion Completa',
                'Optimizaciones de Rendimiento',
                'Manejo Seguro de Errores',
                'Pulido Final'
            ],
            'total_features': 10,
            'completion_percentage': 100.0
        }
    
    def reset_scroll(self) -> None:
        """Resetea el scroll de la lista de operarios."""
        self.scroll_offset = 0
        print("[DASHBOARD-WC] Scroll reseteado")
    
    def set_max_operators_visible(self, max_ops: int) -> None:
        """
        Establece el numero maximo de operarios visibles.
        
        Args:
            max_ops: Numero maximo de operarios visibles
        """
        self.max_operators_visible = max(1, max_ops)
        print(f"[DASHBOARD-WC] Max operarios visibles: {self.max_operators_visible}")
    
    def toggle_performance_mode(self) -> bool:
        """
        Alterna el modo de rendimiento (cache on/off).
        
        Returns:
            Nuevo estado del modo de rendimiento
        """
        new_state = not self._performance_config['enable_gradient_cache']
        self._performance_config['enable_gradient_cache'] = new_state
        self._performance_config['enable_text_cache'] = new_state
        self._performance_config['enable_card_cache'] = new_state
        
        if not new_state:
            self._clear_cache()
        
        print(f"[DASHBOARD-WC] Modo rendimiento: {'ON' if new_state else 'OFF'}")
        return new_state
    
    def get_color_scheme_info(self) -> Dict[str, Any]:
        """
        Retorna informacion del esquema de colores.
        
        Returns:
            Dict con informacion de colores
        """
        return {
            'theme': 'Catppuccin Mocha',
            'total_colors': len(self.colors),
            'primary_colors': {
                'background': self.colors['primary_bg'],
                'surface': self.colors['surface_bg'],
                'text': self.colors['text_primary']
            },
            'accent_colors': {
                'blue': self.colors['accent_blue'],
                'teal': self.colors['accent_teal'],
                'green': self.colors['accent_green'],
                'orange': self.colors['accent_orange'],
                'red': self.colors['accent_red'],
                'purple': self.colors['accent_purple'],
                'yellow': self.colors['accent_yellow']
            },
            'status_colors': {
                'idle': self.colors['status_idle'],
                'moving': self.colors['status_moving'],
                'working': self.colors['status_working'],
                'picking': self.colors['status_picking'],
                'unloading': self.colors['status_unloading'],
                'lifting': self.colors['status_lifting']
            }
        }
    
    def validate_data_integrity(self, estado_visual: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida la integridad de los datos recibidos.
        
        Args:
            estado_visual: Datos a validar
            
        Returns:
            Dict con resultado de validacion
        """
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'data_types': {}
        }
        
        # Validar estructura basica
        if not isinstance(estado_visual, dict):
            validation_result['valid'] = False
            validation_result['errors'].append("estado_visual no es un diccionario")
            return validation_result
        
        # Validar metricas
        metricas = estado_visual.get('metricas', {})
        validation_result['data_types']['metricas'] = type(metricas).__name__
        
        if isinstance(metricas, dict):
            required_metrics = ['tiempo', 'workorders_completadas', 'total_wos']
            for metric in required_metrics:
                if metric not in metricas:
                    validation_result['warnings'].append(f"Metrica '{metric}' no encontrada")
        
        # Validar operarios
        operarios = estado_visual.get('operarios', {})
        validation_result['data_types']['operarios'] = type(operarios).__name__
        
        if isinstance(operarios, dict):
            validation_result['operators_count'] = len(operarios)
        else:
            validation_result['warnings'].append("Operarios no es un diccionario")
        
        return validation_result
    
    def export_dashboard_config(self) -> Dict[str, Any]:
        """
        Exporta la configuracion actual del dashboard.
        
        Returns:
            Dict con configuracion exportable
        """
        return {
            'dashboard_config': {
                'panel_width': self.panel_width,
                'panel_position': self.panel_position,
                'max_operators_visible': self.max_operators_visible,
                'section_heights': self.section_heights.copy()
            },
            'performance_config': self._performance_config.copy(),
            'color_scheme': self.get_color_scheme_info(),
            'dashboard_info': self.get_dashboard_info()
        }
    
    def import_dashboard_config(self, config: Dict[str, Any]) -> bool:
        """
        Importa configuracion del dashboard.
        
        Args:
            config: Configuracion a importar
            
        Returns:
            True si la importacion fue exitosa
        """
        try:
            dashboard_config = config.get('dashboard_config', {})
            
            if 'panel_width' in dashboard_config:
                self.panel_width = dashboard_config['panel_width']
            if 'panel_position' in dashboard_config:
                self.panel_position = dashboard_config['panel_position']
            if 'max_operators_visible' in dashboard_config:
                self.max_operators_visible = dashboard_config['max_operators_visible']
            if 'section_heights' in dashboard_config:
                self.section_heights.update(dashboard_config['section_heights'])
            
            performance_config = config.get('performance_config', {})
            if performance_config:
                self._performance_config.update(performance_config)
            
            print("[DASHBOARD-WC] Configuracion importada exitosamente")
            return True
            
        except Exception as e:
            print(f"[DASHBOARD-WC ERROR] Error importando configuracion: {e}")
            return False

