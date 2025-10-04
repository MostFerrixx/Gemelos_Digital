# -*- coding: utf-8 -*-
"""
Utils Helpers - Funciones helper para exportacion y metricas

FASE 1a: ESQUELETO FUNCIONAL MINIMO
Este modulo contiene implementaciones stub que permiten importacion y ejecucion
sin errores, pero sin funcionalidad completa aun.

Estado: SKELETON - Pendiente de implementacion completa
"""

import json
from datetime import datetime


# =============================================================================
# FUNCIONES DE EXPORTACION
# =============================================================================

def exportar_metricas(almacen):
    """
    Exporta las metricas del almacen a un archivo JSON.

    Args:
        almacen: Instancia de AlmacenMejorado

    Returns:
        str: Path del archivo JSON generado, o None si fallo

    SKELETON: Implementacion minima - genera archivo vacio
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"metricas_{timestamp}.json"

        # Datos minimos de exportacion
        data = {
            "timestamp": timestamp,
            "status": "SKELETON - Exportacion minima",
            "tareas_completadas": getattr(almacen, 'tareas_completadas_count', 0) if almacen else 0
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=True)

        print(f"[HELPERS] Metricas exportadas a: {filename} (SKELETON)")
        return filename

    except Exception as e:
        print(f"[HELPERS ERROR] Error exportando metricas: {e}")
        return None


# =============================================================================
# FUNCIONES DE CONSOLA
# =============================================================================

def mostrar_metricas_consola(almacen):
    """
    Muestra las metricas del almacen en la consola (pretty print).

    Args:
        almacen: Instancia de AlmacenMejorado

    SKELETON: Implementacion minima - muestra datos basicos
    """
    print("=" * 60)
    print("METRICAS DE SIMULACION (SKELETON)")
    print("=" * 60)

    if almacen is None:
        print("Almacen no disponible")
        return

    # Mostrar metricas basicas disponibles
    try:
        print(f"Tareas completadas: {getattr(almacen, 'tareas_completadas_count', 'N/A')}")
        print(f"Total ordenes: {getattr(almacen, 'total_ordenes', 'N/A')}")

        if hasattr(almacen, 'env') and almacen.env:
            print(f"Tiempo simulacion: {almacen.env.now:.2f}s")

    except Exception as e:
        print(f"Error accediendo a metricas: {e}")

    print("=" * 60)
    print("[NOTA] Implementacion completa pendiente")
    print("=" * 60)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'exportar_metricas',
    'mostrar_metricas_consola'
]


print("[OK] Modulo 'subsystems.utils.helpers' cargado (SKELETON - Funcional minimo)")
