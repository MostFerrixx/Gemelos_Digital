"""
Utilidades del Sistema de Simulacion de Almacen V10.0.1+

Este paquete contiene funciones de utilidad extraidas de SimulationEngine
para reducir el acoplamiento y mejorar la modularidad del sistema.
"""

# Importaciones de conveniencia
from .diagnostic_tools import diagnosticar_route_calculator, ejecutar_diagnosticos_completos

__all__ = ['diagnosticar_route_calculator', 'ejecutar_diagnosticos_completos']