# -*- coding: utf-8 -*-
"""
Analytics module for Digital Twin Warehouse Simulator V10.0.2+
Extracted analytics and reporting functionality from SimulationEngine.

Phase 2: Enhanced architecture with SimulationContext and ExportResult patterns.
"""

# Phase 1 - Original exporter (legacy compatibility)
from .exporter import AnalyticsExporter as AnalyticsExporterV1

# Phase 2 - Enhanced exporter with robust architecture
from .exporter_v2 import AnalyticsExporter
from .context import SimulationContext, ExportResult

# Default export is V2 for new code, V1 available for compatibility
__all__ = [
    'AnalyticsExporter',     # V2 - Default
    'AnalyticsExporterV1',   # V1 - Legacy compatibility
    'SimulationContext',
    'ExportResult'
]