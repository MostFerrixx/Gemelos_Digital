# -*- coding: utf-8 -*-
"""
Visualization Dashboard - Dashboard lateral de metricas en Pygame

FASE 1a: ESQUELETO FUNCIONAL MINIMO
Este modulo contiene implementaciones stub que permiten importacion y ejecucion
sin errores, pero sin funcionalidad completa aun.

Estado: SKELETON - Pendiente de implementacion completa
"""

import pygame


# =============================================================================
# CLASE DASHBOARD ORIGINAL
# =============================================================================

class DashboardOriginal:
    """
    Dashboard lateral que muestra metricas de simulacion en tiempo real.

    SKELETON: Implementacion minima
    """

    def __init__(self):
        """
        Inicializa el dashboard.

        SKELETON: Configuracion basica
        """
        self.visible = True
        self.font = None

        # Intentar inicializar font (puede fallar si pygame no esta init)
        try:
            self.font = pygame.font.Font(None, 20)
        except:
            pass

        print("[DASHBOARD] DashboardOriginal inicializado (SKELETON)")

    def actualizar_datos(self, env, almacen):
        """
        Actualiza los datos internos del dashboard desde el estado de simulacion.

        Args:
            env: Entorno SimPy
            almacen: Instancia de AlmacenMejorado

        SKELETON: Stub - no hace nada
        """
        # TODO: Implementar actualizacion de datos
        pass

    def renderizar(self, pantalla, almacen):
        """
        Renderiza el dashboard en la pantalla.

        Args:
            pantalla: pygame.Surface principal
            almacen: Instancia de AlmacenMejorado

        SKELETON: Stub - no renderiza nada
        """
        # TODO: Implementar renderizado completo
        pass


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'DashboardOriginal'
]


print("[OK] Modulo 'subsystems.visualization.dashboard' cargado (SKELETON - Funcional minimo)")
