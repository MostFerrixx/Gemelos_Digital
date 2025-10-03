# -*- coding: utf-8 -*-
"""
Global Settings and Constants
Configuration module for the Digital Twin Warehouse Simulator
"""

# ============================================================================
# DISPLAY RESOLUTIONS
# ============================================================================

SUPPORTED_RESOLUTIONS = {
    "Pequena (800x800)": (800, 800),
    "Mediana (1200x1200)": (1200, 1200),
    "Grande (1600x1600)": (1600, 1600),
    "Extra Grande (1920x1920)": (1920, 1920),
}

# Logical dimensions for TMX map (fixed size)
LOGICAL_WIDTH = 1920
LOGICAL_HEIGHT = 1920

# ============================================================================
# WAREHOUSE EQUIPMENT CAPACITIES
# ============================================================================

# Capacity for ground operators (pallet jacks) in volume units
CAPACIDAD_TRASPALETA = 150

# Capacity for forklifts in volume units
CAPACIDAD_MONTACARGAS = 1000

# ============================================================================
# SIMULATION CONSTANTS
# ============================================================================

# Default panel width for UI dashboard
PANEL_WIDTH = 400

# Default tile size for TMX maps
DEFAULT_TILE_WIDTH = 32
DEFAULT_TILE_HEIGHT = 32

# ============================================================================
# TIMING CONSTANTS
# ============================================================================

# Update interval for metrics in simulation time units
INTERVALO_ACTUALIZACION_METRICAS = 5.0

# Default discharge time per task
TIEMPO_DESCARGA_POR_TAREA = 5

# ============================================================================
# AGENT CONFIGURATION
# ============================================================================

# Default number of ground operators
NUM_OPERARIOS_TERRESTRES_DEFAULT = 2

# Default number of forklifts
NUM_MONTACARGAS_DEFAULT = 1

# ============================================================================
# PATHFINDING CONSTANTS
# ============================================================================

# Movement cost for standard grid cell
COSTO_MOVIMIENTO_NORMAL = 1.0

# Movement cost penalty for diagonal movement
COSTO_MOVIMIENTO_DIAGONAL = 1.414  # sqrt(2)

# ============================================================================
# WORK ORDER CONFIGURATION
# ============================================================================

# Default total number of work orders
TOTAL_ORDENES_DEFAULT = 300

# Default cart capacity
CAPACIDAD_CARRO_DEFAULT = 150

# ============================================================================
# FILE PATHS
# ============================================================================

# Default TMX layout file
DEFAULT_LAYOUT_FILE = "layouts/WH1.tmx"

# Default warehouse logic file
DEFAULT_SEQUENCE_FILE = "layouts/Warehouse_Logic.xlsx"

# ============================================================================
# CONFIGURATION EXPORT
# ============================================================================

__all__ = [
    'SUPPORTED_RESOLUTIONS',
    'LOGICAL_WIDTH',
    'LOGICAL_HEIGHT',
    'CAPACIDAD_TRASPALETA',
    'CAPACIDAD_MONTACARGAS',
    'PANEL_WIDTH',
    'DEFAULT_TILE_WIDTH',
    'DEFAULT_TILE_HEIGHT',
    'INTERVALO_ACTUALIZACION_METRICAS',
    'TIEMPO_DESCARGA_POR_TAREA',
    'NUM_OPERARIOS_TERRESTRES_DEFAULT',
    'NUM_MONTACARGAS_DEFAULT',
    'COSTO_MOVIMIENTO_NORMAL',
    'COSTO_MOVIMIENTO_DIAGONAL',
    'TOTAL_ORDENES_DEFAULT',
    'CAPACIDAD_CARRO_DEFAULT',
    'DEFAULT_LAYOUT_FILE',
    'DEFAULT_SEQUENCE_FILE',
]
