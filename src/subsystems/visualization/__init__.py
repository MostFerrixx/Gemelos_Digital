# -*- coding: utf-8 -*-
"""
Visualization Subsystem - Estado visual y renderizado Pygame

FASE 1a: ESQUELETO FUNCIONAL
"""

from .state import (
    estado_visual,
    inicializar_estado,
    inicializar_estado_con_cola,
    limpiar_estado,
    actualizar_metricas_tiempo,
    toggle_pausa,
    toggle_dashboard,
    aumentar_velocidad,
    disminuir_velocidad,
    obtener_velocidad_simulacion
)

from .renderer import (
    RendererOriginal,
    renderizar_agentes,
    renderizar_tareas_pendientes,
    renderizar_dashboard,
    renderizar_diagnostico_layout
)

from .dashboard import DashboardOriginal


__all__ = [
    # State
    'estado_visual',
    'inicializar_estado',
    'inicializar_estado_con_cola',
    'limpiar_estado',
    'actualizar_metricas_tiempo',
    'toggle_pausa',
    'toggle_dashboard',
    'aumentar_velocidad',
    'disminuir_velocidad',
    'obtener_velocidad_simulacion',

    # Renderer
    'RendererOriginal',
    'renderizar_agentes',
    'renderizar_tareas_pendientes',
    'renderizar_dashboard',
    'renderizar_diagnostico_layout',

    # Dashboard
    'DashboardOriginal'
]

print("[OK] Subsistema 'subsystems.visualization' cargado (SKELETON)")
