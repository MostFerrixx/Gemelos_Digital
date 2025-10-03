# -*- coding: utf-8 -*-
"""
Color Palette for Digital Twin Warehouse Simulator
RGB color definitions for rendering and visualization
"""

# ============================================================================
# BACKGROUND COLORS
# ============================================================================

# Main background color (light gray)
COLOR_FONDO = (245, 245, 245)

# Dark background for simulation area
COLOR_FONDO_OSCURO = (25, 25, 25)

# ============================================================================
# AGENT COLORS
# ============================================================================

# Ground operator color (orange)
COLOR_AGENTE_TERRESTRE = (255, 100, 0)

# Forklift color (blue)
COLOR_AGENTE_MONTACARGAS = (0, 150, 255)

# Agent idle state color (gray)
COLOR_AGENTE_IDLE = (128, 128, 128)

# Agent working state color (green)
COLOR_AGENTE_TRABAJANDO = (0, 200, 0)

# Agent moving state color (yellow)
COLOR_AGENTE_MOVIENDO = (255, 255, 0)

# ============================================================================
# WORK ORDER / TASK COLORS
# ============================================================================

# Pending task color (yellow)
COLOR_TAREA_PENDIENTE = (255, 255, 0)

# Assigned task color (orange)
COLOR_TAREA_ASIGNADA = (255, 165, 0)

# In progress task color (light blue)
COLOR_TAREA_EN_PROGRESO = (100, 200, 255)

# Completed task color (green)
COLOR_TAREA_COMPLETADA = (0, 255, 0)

# ============================================================================
# MAP / LAYOUT COLORS
# ============================================================================

# Walkable area color (light gray)
COLOR_AREA_CAMINABLE = (200, 200, 200)

# Obstacle/rack color (dark gray)
COLOR_OBSTACULO = (50, 50, 50)

# Picking point color (cyan)
COLOR_PUNTO_PICKING = (0, 255, 255)

# Depot/staging area color (purple)
COLOR_DEPOT = (200, 0, 255)

# Work area boundary color (white)
COLOR_AREA_TRABAJO = (255, 255, 255)

# ============================================================================
# UI / DASHBOARD COLORS
# ============================================================================

# Dashboard background color (white)
COLOR_DASHBOARD_BG = (255, 255, 255)

# Dashboard text color (black)
COLOR_DASHBOARD_TEXTO = (0, 0, 0)

# Dashboard border color (dark gray)
COLOR_DASHBOARD_BORDE = (50, 50, 50)

# Dashboard highlight color (light blue)
COLOR_DASHBOARD_HIGHLIGHT = (200, 220, 255)

# ============================================================================
# STATUS INDICATOR COLORS
# ============================================================================

# Success/active indicator (green)
COLOR_EXITO = (0, 255, 0)

# Warning indicator (yellow)
COLOR_ADVERTENCIA = (255, 255, 0)

# Error indicator (red)
COLOR_ERROR = (255, 0, 0)

# Info indicator (blue)
COLOR_INFO = (0, 100, 255)

# ============================================================================
# TEXT COLORS
# ============================================================================

# Primary text color (black)
COLOR_TEXTO = (0, 0, 0)

# Secondary text color (dark gray)
COLOR_TEXTO_SECUNDARIO = (100, 100, 100)

# Light text color for dark backgrounds (white)
COLOR_TEXTO_CLARO = (255, 255, 255)

# ============================================================================
# GRID / PATH COLORS
# ============================================================================

# Grid line color (light gray)
COLOR_GRID = (180, 180, 180)

# Path color (light green)
COLOR_CAMINO = (150, 255, 150)

# Blocked path color (red)
COLOR_CAMINO_BLOQUEADO = (255, 100, 100)

# ============================================================================
# SPECIAL PURPOSE COLORS
# ============================================================================

# Transparent color (for alpha blending)
COLOR_TRANSPARENTE = (0, 0, 0, 0)

# Highlight color for selection (bright yellow)
COLOR_SELECCION = (255, 255, 100)

# Debug overlay color (semi-transparent red)
COLOR_DEBUG = (255, 0, 0, 128)

# ============================================================================
# CONFIGURATION EXPORT
# ============================================================================

__all__ = [
    'COLOR_FONDO',
    'COLOR_FONDO_OSCURO',
    'COLOR_AGENTE_TERRESTRE',
    'COLOR_AGENTE_MONTACARGAS',
    'COLOR_AGENTE_IDLE',
    'COLOR_AGENTE_TRABAJANDO',
    'COLOR_AGENTE_MOVIENDO',
    'COLOR_TAREA_PENDIENTE',
    'COLOR_TAREA_ASIGNADA',
    'COLOR_TAREA_EN_PROGRESO',
    'COLOR_TAREA_COMPLETADA',
    'COLOR_AREA_CAMINABLE',
    'COLOR_OBSTACULO',
    'COLOR_PUNTO_PICKING',
    'COLOR_DEPOT',
    'COLOR_AREA_TRABAJO',
    'COLOR_DASHBOARD_BG',
    'COLOR_DASHBOARD_TEXTO',
    'COLOR_DASHBOARD_BORDE',
    'COLOR_DASHBOARD_HIGHLIGHT',
    'COLOR_EXITO',
    'COLOR_ADVERTENCIA',
    'COLOR_ERROR',
    'COLOR_INFO',
    'COLOR_TEXTO',
    'COLOR_TEXTO_SECUNDARIO',
    'COLOR_TEXTO_CLARO',
    'COLOR_GRID',
    'COLOR_CAMINO',
    'COLOR_CAMINO_BLOQUEADO',
    'COLOR_TRANSPARENTE',
    'COLOR_SELECCION',
    'COLOR_DEBUG',
]
