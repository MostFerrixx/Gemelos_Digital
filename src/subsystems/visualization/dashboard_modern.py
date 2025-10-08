#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard Moderno - Diseño visual moderno y profesional para el simulador.

Este módulo implementa un dashboard con:
- Diseño moderno con colores profesionales
- Tipografía mejorada y jerarquía visual clara
- Elementos gráficos modernos (iconos, cards, sombras)
- Layout profesional con espaciado y bordes redondeados
- Efectos visuales sutiles y transiciones suaves
"""

import pygame
import pygame_gui
import json
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class ModernColorScheme:
    """Esquema de colores moderno para el dashboard."""
    primary_bg: str = "#1E1E2E"
    surface_bg: str = "#313244"
    accent_blue: str = "#89B4FA"
    accent_teal: str = "#94E2D5"
    accent_green: str = "#A6E3A1"
    accent_orange: str = "#FAB387"
    accent_red: str = "#F38BA8"
    accent_purple: str = "#CBA6F7"
    text_primary: str = "#CDD6F4"
    text_secondary: str = "#BAC2DE"
    text_muted: str = "#A6ADC8"
    border_primary: str = "#45475A"
    border_secondary: str = "#585B70"

class ModernDashboard:
    """
    Dashboard moderno con diseño visual profesional.
    
    Características:
    - Diseño moderno con colores profesionales
    - Tipografía mejorada y jerarquía visual clara
    - Elementos gráficos modernos (iconos, cards, sombras)
    - Layout profesional con espaciado y bordes redondeados
    - Efectos visuales sutiles y transiciones suaves
    """
    
    def __init__(self, ui_manager: pygame_gui.UIManager, rect: pygame.Rect):
        """
        Inicializa el dashboard moderno.
        
        Args:
            ui_manager: UIManager de pygame_gui
            rect: Rectángulo que define posición y tamaño del dashboard
        """
        self.ui_manager = ui_manager
        self.rect = rect
        self.colors = ModernColorScheme()
        
        # Cargar tema moderno
        self._load_modern_theme()
        
        # Componentes del dashboard
        self.main_panel = None
        self.title_label = None
        self.ticker_panel = None
        self.ticker_labels = {}
        self.metrics_cards = {}
        self.operators_cards = {}
        self.progress_bar = None
        
        # Estado
        self.visible = True
        self.last_update_time = 0
        
        # Inicializar componentes
        self._create_modern_layout()
        
        print("[MODERN-DASHBOARD] Dashboard moderno inicializado con diseño profesional")
    
    def _load_modern_theme(self):
        """Carga el tema moderno desde el archivo JSON."""
        try:
            theme_path = os.path.join("data", "themes", "dashboard_theme_modern.json")
            if os.path.exists(theme_path):
                with open(theme_path, 'r', encoding='utf-8') as f:
                    self.modern_theme = json.load(f)
                print("[MODERN-DASHBOARD] Tema moderno cargado exitosamente")
            else:
                print("[MODERN-DASHBOARD] Advertencia: Archivo de tema moderno no encontrado")
                self.modern_theme = {}
        except Exception as e:
            print(f"[MODERN-DASHBOARD] Error cargando tema moderno: {e}")
            self.modern_theme = {}
    
    def _create_modern_layout(self):
        """Crea el layout moderno del dashboard."""
        # Panel principal con diseño moderno
        # CRITICO: Posicionar el panel en las coordenadas absolutas del rect del dashboard
        # para que aparezca en el panel derecho y no en (0, 0)
        self.main_panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(self.rect.x, self.rect.y, self.rect.width, self.rect.height),
            manager=self.ui_manager,
            container=None,
            object_id="modern_main_panel"
        )
        
        # Sistema de layout vertical con margenes y separaciones consistentes
        margin_x = 20
        y = 15
        gap = 12

        # Título principal con estilo más elegante y profesional
        title_rect = pygame.Rect(margin_x, y, self.rect.width - 2*margin_x, 36)
        self.title_label = pygame_gui.elements.UILabel(
            relative_rect=title_rect,
            text="SIMULACION EN TIEMPO REAL",
            manager=self.ui_manager,
            container=self.main_panel,
            object_id="modern_title"
        )
        y += title_rect.height + gap

        # Subtítulo con información del estado
        subtitle_rect = pygame.Rect(margin_x, y, self.rect.width - 2*margin_x, 22)
        self.subtitle_label = pygame_gui.elements.UILabel(
            relative_rect=subtitle_rect,
            text="Sistema de Monitoreo Avanzado",
            manager=self.ui_manager,
            container=self.main_panel,
            object_id="modern_subtitle"
        )
        y += subtitle_rect.height + gap

        # Ticker Row
        y = self._create_ticker_row_at(y, margin_x)

        # Sección de métricas con cards modernas
        y = self._create_metrics_section_at(y, margin_x)
        
        # Sección de operarios con cards modernas
        y = self._create_operators_section_at(y, margin_x)
        
        # Barra de progreso moderna
        self._create_progress_section_at(y, margin_x)
        
        print("[MODERN-DASHBOARD] Layout moderno creado exitosamente")

    def _create_ticker_row_at(self, y: int, margin_x: int) -> int:
        """Fila superior de KPIs compactos estilo 'ticker'. Devuelve el nuevo y."""
        panel_rect = pygame.Rect(margin_x, y, self.rect.width - 2*margin_x, 30)
        self.ticker_panel = pygame_gui.elements.UIPanel(
            relative_rect=panel_rect,
            manager=self.ui_manager,
            container=self.main_panel,
            object_id="modern_ticker_panel"
        )

        # Cuatro slots: Tiempo, WIP, Utilizacion, Throughput
        slot_width = (panel_rect.width - 36) // 4
        labels = [
            ("tiempo", "Tiempo"),
            ("wip", "WIP"),
            ("utilizacion", "Utilizacion"),
            ("throughput", "Throughput/min")
        ]

        for idx, (key, title) in enumerate(labels):
            x = 5 + idx * (slot_width + 10)
            title_label = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(x, 2, slot_width, 14),
                text=title,
                manager=self.ui_manager,
                container=self.ticker_panel,
                object_id="modern_metric_label"
            )
            value_label = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(x, 16, slot_width, 16),
                text="-",
                manager=self.ui_manager,
                container=self.ticker_panel,
                object_id="modern_metric_value"
            )
            self.ticker_labels[key] = value_label
        return y + panel_rect.height + 12
    
    def _create_metrics_section_at(self, y: int, margin_x: int) -> int:
        """Crea la sección de métricas con cards modernas. Devuelve nuevo y."""
        # Header de métricas
        metrics_header_rect = pygame.Rect(margin_x, y, self.rect.width - 2*margin_x, 26)
        metrics_header = pygame_gui.elements.UILabel(
            relative_rect=metrics_header_rect,
            text="Metricas de Simulacion",
            manager=self.ui_manager,
            container=self.main_panel,
            object_id="modern_metrics_header"
        )
        y += metrics_header_rect.height + 8
        # Cards de métricas
        card_width = (self.rect.width - 2*margin_x - 20) // 2
        card_height = 70
        card_spacing = 20
        
        # Card 1: Tiempo
        time_card_rect = pygame.Rect(margin_x, y, card_width, card_height)
        self.metrics_cards['time'] = pygame_gui.elements.UIPanel(
            relative_rect=time_card_rect,
            manager=self.ui_manager,
            container=self.main_panel,
            object_id="modern_metric_card"
        )
        
        time_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, 10, card_width - 20, 25),
            text="Tiempo",
            manager=self.ui_manager,
            container=self.metrics_cards['time'],
            object_id="modern_metric_label"
        )
        
        self.time_value_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, 35, card_width - 20, 30),
            text="00:00:00",
            manager=self.ui_manager,
            container=self.metrics_cards['time'],
            object_id="modern_metric_value"
        )
        
        # Card 2: WorkOrders
        wo_card_rect = pygame.Rect(margin_x + card_width + 20, y, card_width, card_height)
        self.metrics_cards['workorders'] = pygame_gui.elements.UIPanel(
            relative_rect=wo_card_rect,
            manager=self.ui_manager,
            container=self.main_panel,
            object_id="modern_metric_card"
        )
        
        wo_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, 10, card_width - 20, 25),
            text="WorkOrders",
            manager=self.ui_manager,
            container=self.metrics_cards['workorders'],
            object_id="modern_metric_label"
        )
        
        self.wo_value_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, 35, card_width - 20, 30),
            text="0/0",
            manager=self.ui_manager,
            container=self.metrics_cards['workorders'],
            object_id="modern_metric_value"
        )
        
        # Card 3: Tareas (segunda fila)
        y += card_height + 12
        tasks_card_rect = pygame.Rect(margin_x, y, card_width, card_height)
        self.metrics_cards['tasks'] = pygame_gui.elements.UIPanel(
            relative_rect=tasks_card_rect,
            manager=self.ui_manager,
            container=self.main_panel,
            object_id="modern_metric_card"
        )
        
        tasks_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, 10, card_width - 20, 25),
            text="Tareas",
            manager=self.ui_manager,
            container=self.metrics_cards['tasks'],
            object_id="modern_metric_label"
        )
        
        self.tasks_value_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, 35, card_width - 20, 30),
            text="0",
            manager=self.ui_manager,
            container=self.metrics_cards['tasks'],
            object_id="modern_metric_value"
        )
        
        # Card 4: Progreso
        progress_card_rect = pygame.Rect(margin_x + card_width + 20, y, card_width, card_height)
        self.metrics_cards['progress'] = pygame_gui.elements.UIPanel(
            relative_rect=progress_card_rect,
            manager=self.ui_manager,
            container=self.main_panel,
            object_id="modern_metric_card"
        )
        return y + card_height + 16
        
        progress_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, 10, card_width - 20, 25),
            text="Progreso",
            manager=self.ui_manager,
            container=self.metrics_cards['progress'],
            object_id="modern_metric_label"
        )
        
        self.progress_value_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, 35, card_width - 20, 30),
            text="0%",
            manager=self.ui_manager,
            container=self.metrics_cards['progress'],
            object_id="modern_metric_value"
        )
    
    def _create_operators_section_at(self, y: int, margin_x: int) -> int:
        """Crea la sección de operarios con cards modernas. Devuelve nuevo y."""
        # Header de operarios
        operators_header_rect = pygame.Rect(margin_x, y, self.rect.width - 2*margin_x, 26)
        operators_header = pygame_gui.elements.UILabel(
            relative_rect=operators_header_rect,
            text="Estado de Operarios",
            manager=self.ui_manager,
            container=self.main_panel,
            object_id="modern_operators_header"
        )
        y += operators_header_rect.height + 8
        # Container para operarios con scroll
        operators_container_rect = pygame.Rect(margin_x, y, self.rect.width - 2*margin_x, 180)
        self.operators_container = pygame_gui.elements.UIScrollingContainer(
            relative_rect=operators_container_rect,
            manager=self.ui_manager,
            container=self.main_panel,
            object_id="modern_operators_container"
        )
        y += operators_container_rect.height + 12
        # Lista de operarios (se creará dinámicamente)
        self.operator_cards = []
        return y
    
    def _create_progress_section_at(self, y: int, margin_x: int) -> None:
        """Crea la sección de progreso con barra moderna."""
        # Header de progreso
        progress_header_rect = pygame.Rect(margin_x, y, self.rect.width - 2*margin_x, 24)
        progress_header = pygame_gui.elements.UILabel(
            relative_rect=progress_header_rect,
            text="Progreso General",
            manager=self.ui_manager,
            container=self.main_panel,
            object_id="modern_progress_header"
        )
        y += progress_header_rect.height + 8
        # Barra de progreso moderna
        progress_bar_rect = pygame.Rect(margin_x, y, self.rect.width - 2*margin_x, 18)
        self.progress_bar = pygame_gui.elements.UIProgressBar(
            relative_rect=progress_bar_rect,
            manager=self.ui_manager,
            container=self.main_panel,
            object_id="modern_progress_bar"
        )
        y += progress_bar_rect.height + 6
        # Label de porcentaje
        progress_percent_rect = pygame.Rect(margin_x, y, self.rect.width - 2*margin_x, 20)
        self.progress_percent_label = pygame_gui.elements.UILabel(
            relative_rect=progress_percent_rect,
            text="0% Completado",
            manager=self.ui_manager,
            container=self.main_panel,
            object_id="modern_progress_percent"
        )
    
    def update_data(self, estado_visual: Dict[str, Any]) -> None:
        """
        Actualiza los datos del dashboard moderno.
        
        Args:
            estado_visual: Dict con datos actuales de la simulación
        """
        if not self.visible:
            return
        
        # Actualizar métricas
        self._update_metrics(estado_visual.get('metricas', {}))
        
        # Actualizar operarios
        self._update_operators(estado_visual.get('operarios', {}))
        
        # Actualizar progreso
        self._update_progress(estado_visual.get('metricas', {}))
    
    def _update_metrics(self, metricas: Dict[str, Any]) -> None:
        """Actualiza las métricas con estilo moderno."""
        # Tiempo
        tiempo = metricas.get('tiempo', 0.0)
        tiempo_formateado = self._format_time_hhmmss(tiempo)
        time_value_label = getattr(self, 'time_value_label', None)
        if time_value_label is not None:
            time_value_label.set_text(tiempo_formateado)
        if self.ticker_labels.get("tiempo"):
            self.ticker_labels["tiempo"].set_text(tiempo_formateado)
        
        # WorkOrders
        wos_completadas = metricas.get('workorders_completadas', 0)
        total_wos = metricas.get('total_wos', 0)
        wo_value_label = getattr(self, 'wo_value_label', None)
        if wo_value_label is not None:
            wo_value_label.set_text(f"{wos_completadas}/{total_wos}")
        
        # Tareas
        tareas_completadas = metricas.get('tareas_completadas', 0)
        tasks_value_label = getattr(self, 'tasks_value_label', None)
        if tasks_value_label is not None:
            tasks_value_label.set_text(str(tareas_completadas))
        
        # Progreso
        progress_value_label = getattr(self, 'progress_value_label', None)
        if total_wos > 0:
            progreso_porcentaje = (wos_completadas / total_wos) * 100.0
            if progress_value_label is not None:
                progress_value_label.set_text(f"{progreso_porcentaje:.1f}%")
        else:
            if progress_value_label is not None:
                progress_value_label.set_text("0.0%")

        # WIP (work in progress): total de WOs - completadas
        wip = max(total_wos - wos_completadas, 0)
        if self.ticker_labels.get("wip"):
            self.ticker_labels["wip"].set_text(str(wip))

        # Utilizacion: si viene en metricas la usamos, si no, placeholder "-"
        utilizacion = metricas.get('utilizacion_promedio')
        if self.ticker_labels.get("utilizacion"):
            self.ticker_labels["utilizacion"].set_text(
                f"{utilizacion:.0f}%" if isinstance(utilizacion, (int, float)) else "-"
            )

        # Throughput: si existe (wo completadas por minuto)
        throughput = metricas.get('throughput_min')
        if self.ticker_labels.get("throughput"):
            self.ticker_labels["throughput"].set_text(
                f"{throughput:.1f}" if isinstance(throughput, (int, float)) else "-"
            )
    
    def _update_operators(self, operarios: Dict[str, Any]) -> None:
        """Actualiza los operarios con cards modernas."""
        # Limpiar operarios existentes
        for card in self.operator_cards:
            card.kill()
        self.operator_cards.clear()
        
        # Crear cards para cada operario
        y_offset = 10
        card_height = 50
        
        for i, (operator_id, operator_data) in enumerate(operarios.items()):
            if i >= 6:  # Limitar a 6 operarios visibles
                break
            
            # Card del operario
            operator_card_rect = pygame.Rect(10, y_offset, self.operators_container.rect.width - 30, card_height)
            operator_card = pygame_gui.elements.UIPanel(
                relative_rect=operator_card_rect,
                manager=self.ui_manager,
                container=self.operators_container,
                object_id="modern_operator_card"
            )
            
            # Estado del operario con icono
            estado = operator_data.get('estado', 'unknown')
            estado_info = self._get_operator_state_info(estado)
            
            # Label del operario
            operator_label_rect = pygame.Rect(10, 5, operator_card_rect.width - 20, 20)
            operator_label = pygame_gui.elements.UILabel(
                relative_rect=operator_label_rect,
                text=f"{estado_info['icon']} {operator_id}",
                manager=self.ui_manager,
                container=operator_card,
                object_id="modern_operator_label"
            )
            
            # Label del estado
            status_label_rect = pygame.Rect(10, 25, operator_card_rect.width - 20, 20)
            status_label = pygame_gui.elements.UILabel(
                relative_rect=status_label_rect,
                text=f"Estado: {estado} | Pos: {operator_data.get('posicion', (0, 0))}",
                manager=self.ui_manager,
                container=operator_card,
                object_id="modern_operator_status"
            )
            
            self.operator_cards.append(operator_card)
            y_offset += card_height + 10
        
        # Ajustar altura del container
        self.operators_container.set_scrollable_area_dimensions(
            (self.operators_container.rect.width - 20, y_offset + 10)
        )
    
    def _update_progress(self, metricas: Dict[str, Any]) -> None:
        """Actualiza la barra de progreso moderna."""
        wos_completadas = metricas.get('workorders_completadas', 0)
        total_wos = metricas.get('total_wos', 0)
        
        if total_wos > 0:
            progreso_porcentaje = (wos_completadas / total_wos) * 100.0
            if self.progress_bar:
                self.progress_bar.set_current_progress(progreso_porcentaje / 100.0)
            if self.progress_percent_label:
                self.progress_percent_label.set_text(f"{progreso_porcentaje:.1f}% Completado")
        else:
            if self.progress_bar:
                self.progress_bar.set_current_progress(0.0)
            if self.progress_percent_label:
                self.progress_percent_label.set_text("0% Completado")
    
    def _get_operator_state_info(self, estado: str) -> Dict[str, str]:
        """Obtiene información del estado del operario con iconos modernos."""
        state_info = {
            'idle': {'icon': '⏸️', 'color': self.colors.text_secondary},
            'moving': {'icon': '🚚', 'color': self.colors.accent_green},
            'working': {'icon': '⚡', 'color': self.colors.accent_orange},
            'discharging': {'icon': '📦', 'color': self.colors.accent_red},
            'loading': {'icon': '📥', 'color': self.colors.accent_blue},
            'waiting': {'icon': '⏳', 'color': self.colors.accent_purple},
            'error': {'icon': '❌', 'color': self.colors.accent_red},
            'unknown': {'icon': '❓', 'color': self.colors.text_primary}
        }
        
        return state_info.get(estado, state_info['unknown'])
    
    def _format_time_hhmmss(self, segundos: float) -> str:
        """Formatea tiempo a formato HH:MM:SS."""
        horas = int(segundos // 3600)
        minutos = int((segundos % 3600) // 60)
        segs = int(segundos % 60)
        return f"{horas:02d}:{minutos:02d}:{segs:02d}"
    
    def set_visible(self, visible: bool) -> None:
        """Establece la visibilidad del dashboard."""
        self.visible = visible
        if self.main_panel:
            self.main_panel.show() if visible else self.main_panel.hide()
    
    def kill(self) -> None:
        """Limpia todos los componentes del dashboard."""
        if self.main_panel:
            self.main_panel.kill()
        self.main_panel = None
        self.metrics_cards.clear()
        self.operator_cards.clear()
        print("[MODERN-DASHBOARD] Dashboard moderno limpiado")
