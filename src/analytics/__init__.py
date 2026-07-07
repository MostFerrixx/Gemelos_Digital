# -*- coding: utf-8 -*-
"""
Analytics module for Digital Twin Warehouse Simulator V10.0.2+
Extracted analytics and reporting functionality from SimulationEngine.

PODA 2026-07-07: eliminado el exporter V1 (0 usos reales del alias
AnalyticsExporterV1; el unico "import" era este __init__). Queda solo el V2.
"""

from .exporter_v2 import AnalyticsExporter
from .context import SimulationContext, ExportResult

__all__ = [
    'AnalyticsExporter',
    'SimulationContext',
    'ExportResult'
]
