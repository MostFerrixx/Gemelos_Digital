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

FASE 1: Estructura Base
- Clase principal con configuracion
- Sistema de colores y fuentes
- Renderizado de fondo
- Estructura basica de render

Autor: Claude Code (Dashboard World-Class Implementation)
Fecha: 2025-10-07
Estado: FASE 1 - Estructura Base
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
        
        print("[DASHBOARD-WC] Dashboard World-Class inicializado")
        print(f"[DASHBOARD-WC] Panel: {panel_width}px, Posicion: {panel_position}")
    
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
            'status_discharging': (243, 139, 168), # #F38BA8 (rosa/rojo)
            'status_loading': (137, 180, 250),  # #89B4FA (azul)
            'status_waiting': (203, 166, 247),  # #CBA6F7 (purpura)
            'status_error': (243, 139, 168),    # #F38BA8 (rojo)
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
        
        # Fondo principal con gradiente vertical sutil
        self._draw_gradient_rect(
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
        # Fondo del header con gradiente
        header_rect = pygame.Rect(x, y, self.panel_width, self.section_heights['header'])
        self._draw_gradient_rect(
            surface,
            header_rect,
            self.colors['surface_bg'],
            self.colors['primary_bg'],
            vertical=True
        )
        
        # Titulo principal
        title_text = self.fonts['title'].render(
            "Dashboard de Agentes",
            True,
            self.colors['text_primary']
        )
        title_x = x + 15
        title_y = y + 12
        surface.blit(title_text, (title_x, title_y))
        
        # Subtitulo
        subtitle_text = self.fonts['subtitle'].render(
            "Sistema de Monitoreo en Tiempo Real",
            True,
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
                'icon': '⏰',
                'label': 'Tiempo',
                'value': tiempo_formateado,
                'color': self.colors['accent_blue']
            },
            {
                'icon': '📦',
                'label': 'WorkOrders',
                'value': wos_text,
                'color': self.colors['accent_green']
            },
            {
                'icon': '✅',
                'label': 'Tareas',
                'value': tareas_text,
                'color': self.colors['accent_orange']
            },
            {
                'icon': '📈',
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
        Renderiza lista scrollable de operarios.
        
        Args:
            surface: Superficie pygame donde dibujar
            x: Posicion X del panel
            y: Posicion Y inicial
            height: Altura disponible para la lista
            estado_visual: Datos actuales
            
        Returns:
            Nueva posicion Y
        """
        # TODO: Implementar en FASE 5
        # Por ahora, solo dibujar placeholder
        operators_rect = pygame.Rect(x + 10, y + 5, self.panel_width - 20, height - 10)
        pygame.draw.rect(surface, self.colors['surface_0'], operators_rect, border_radius=10)
        
        placeholder_text = self.fonts['section_header'].render(
            "Operators List - FASE 5",
            True,
            self.colors['text_muted']
        )
        surface.blit(placeholder_text, (x + 20, y + 20))
        
        return y + height
    
    def _render_footer(self, surface: pygame.Surface, x: int, y: int) -> None:
        """
        Renderiza footer con controles de teclado.
        
        Args:
            surface: Superficie pygame donde dibujar
            x: Posicion X del panel
            y: Posicion Y inicial
        """
        # TODO: Implementar en FASE 6
        # Por ahora, solo dibujar placeholder
        footer_rect = pygame.Rect(x, y, self.panel_width, self.section_heights['footer'])
        pygame.draw.rect(surface, self.colors['surface_bg'], footer_rect)
        
        # Linea separadora superior
        pygame.draw.line(
            surface,
            self.colors['border_primary'],
            (x, y),
            (x + self.panel_width, y),
            2
        )
        
        placeholder_text = self.fonts['footer_desc'].render(
            "Footer Controls - FASE 6",
            True,
            self.colors['text_muted']
        )
        surface.blit(placeholder_text, (x + 20, y + 20))
    
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
        # TODO: Implementar en FASE 5 (scroll de operarios)
        pass
    
    def update_data(self, estado_visual: Dict[str, Any]) -> None:
        """
        Actualiza datos internos si necesario (opcional).
        
        Args:
            estado_visual: Dict con datos actuales
        """
        # TODO: Implementar si se necesita cache de datos
        pass

