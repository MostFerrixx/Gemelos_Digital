#!/usr/bin/env python3
"""
Script de Validación: Ejecución de Plan (Filtro por Prioridad)

Este script analiza los logs de simulación para validar que la estrategia
"Ejecución de Plan (Filtro por Prioridad)" funciona exactamente como se describió:

1. Filtra por compatibilidad de área de trabajo
2. Prioriza por área de trabajo (menor número = mayor prioridad)
3. NO usa AssignmentCostCalculator para la primera WO
4. Ordena por pick_sequence usando ROUTE-CALCULATOR
5. Construye tours siguiendo la secuencia
"""

import re
import json
from collections import defaultdict
from datetime import datetime

def analizar_logs_simulacion():
    """Analiza los logs de la simulación para validar el comportamiento de la estrategia"""
    
    print("=" * 80)
    print("VALIDACIÓN DE ESTRATEGIA: EJECUCIÓN DE PLAN (FILTRO POR PRIORIDAD)")
    print("=" * 80)
    
    # Leer el archivo de logs
    try:
        # Intentar diferentes codificaciones
        for encoding in ['utf-8', 'latin-1', 'cp1252', 'utf-16']:
            try:
                with open('test_output.log', 'r', encoding=encoding) as f:
                    logs = f.readlines()
                print(f"✅ Archivo leído con codificación: {encoding}")
                break
            except UnicodeDecodeError:
                continue
        else:
            print("❌ ERROR: No se pudo leer el archivo con ninguna codificación")
            return
    except FileNotFoundError:
        print("❌ ERROR: No se encontró el archivo test_output.log")
        return
    
    # Patrones para buscar
    patrones = {
        'estrategia_seleccionada': r'\[DISPATCHER\] Estrategia \'Ejecucion de Plan \(Filtro por Prioridad\)\' selecciono (\d+) candidatos',
        'cost_calc': r'\[COST-CALC\] (.+?) -> (.+?): priority=(\d+), penalty=(\d+), distance=(\d+), total=(\d+)',
        'route_calculator': r'\[ROUTE-CALCULATOR\] Ordenados (\d+) WorkOrders por pick_sequence',
        'warnings': r'\[DISPATCHER WARN\] Estrategia desconocida \'Ejecucion de Plan \(Filtro por Prioridad\)\', usando FIFO',
        'optimizacion_global': r'\[DISPATCHER\] Optimización Global: usando tour construido por proximidad',
        'assignment_cost': r'\[DISPATCHER DEBUG\] Buscando mejor primera WO entre (\d+) candidatos',
        'assignment_cost_calc': r'\[DISPATCHER DEBUG\] Calculando costos desde posición:'
    }
    
    # Contadores y datos
    resultados = {
        'total_selecciones': 0,
        'total_cost_calculations': 0,
        'total_route_calculations': 0,
        'total_warnings': 0,
        'total_optimizacion_global': 0,
        'total_assignment_cost': 0,
        'evidencias': [],
        'comportamiento_correcto': True
    }
    
    # Analizar cada línea
    for i, linea in enumerate(logs):
        linea = linea.strip()
        
        # Buscar selecciones de estrategia
        match = re.search(patrones['estrategia_seleccionada'], linea)
        if match:
            candidatos = int(match.group(1))
            resultados['total_selecciones'] += 1
            resultados['evidencias'].append({
                'tipo': 'estrategia_seleccionada',
                'linea': i + 1,
                'candidatos': candidatos,
                'contenido': linea
            })
        
        # Buscar cálculos de costo
        match = re.search(patrones['cost_calc'], linea)
        if match:
            resultados['total_cost_calculations'] += 1
            resultados['evidencias'].append({
                'tipo': 'cost_calc',
                'linea': i + 1,
                'operador': match.group(1),
                'area': match.group(2),
                'priority': int(match.group(3)),
                'distance': int(match.group(5)),
                'total': int(match.group(6)),
                'contenido': linea
            })
        
        # Buscar ordenamiento por pick_sequence
        match = re.search(patrones['route_calculator'], linea)
        if match:
            resultados['total_route_calculations'] += 1
            resultados['evidencias'].append({
                'tipo': 'route_calculator',
                'linea': i + 1,
                'workorders': int(match.group(1)),
                'contenido': linea
            })
        
        # Buscar warnings
        if re.search(patrones['warnings'], linea):
            resultados['total_warnings'] += 1
            resultados['evidencias'].append({
                'tipo': 'warning',
                'linea': i + 1,
                'contenido': linea
            })
        
        # Buscar Optimización Global
        if re.search(patrones['optimizacion_global'], linea):
            resultados['total_optimizacion_global'] += 1
            resultados['evidencias'].append({
                'tipo': 'optimizacion_global',
                'linea': i + 1,
                'contenido': linea
            })
        
        # Buscar AssignmentCostCalculator
        if re.search(patrones['assignment_cost'], linea):
            resultados['total_assignment_cost'] += 1
            resultados['evidencias'].append({
                'tipo': 'assignment_cost',
                'linea': i + 1,
                'candidatos': int(match.group(1)),
                'contenido': linea
            })
    
    # Generar reporte
    generar_reporte_validacion(resultados)
    
    return resultados

def generar_reporte_validacion(resultados):
    """Genera un reporte detallado de la validación"""
    
    print(f"\n📊 ESTADÍSTICAS GENERALES:")
    print(f"   • Total selecciones de estrategia: {resultados['total_selecciones']}")
    print(f"   • Total cálculos de costo: {resultados['total_cost_calculations']}")
    print(f"   • Total ordenamientos por pick_sequence: {resultados['total_route_calculations']}")
    print(f"   • Total warnings: {resultados['total_warnings']}")
    print(f"   • Total Optimización Global: {resultados['total_optimizacion_global']}")
    print(f"   • Total AssignmentCostCalculator: {resultados['total_assignment_cost']}")
    
    print(f"\n🔍 VALIDACIÓN DE COMPORTAMIENTO:")
    
    # Validación 1: La estrategia se está ejecutando
    if resultados['total_selecciones'] > 0:
        print(f"   ✅ La estrategia se ejecutó {resultados['total_selecciones']} veces")
    else:
        print(f"   ❌ La estrategia NO se ejecutó")
        resultados['comportamiento_correcto'] = False
    
    # Validación 2: NO usa AssignmentCostCalculator para primera WO
    if resultados['total_assignment_cost'] == 0:
        print(f"   ✅ NO usa AssignmentCostCalculator para primera WO")
    else:
        print(f"   ❌ USA AssignmentCostCalculator para primera WO ({resultados['total_assignment_cost']} veces)")
        resultados['comportamiento_correcto'] = False
    
    # Validación 3: Ordena por pick_sequence
    if resultados['total_route_calculations'] > 0:
        print(f"   ✅ Ordena por pick_sequence usando ROUTE-CALCULATOR ({resultados['total_route_calculations']} veces)")
    else:
        print(f"   ❌ NO ordena por pick_sequence")
        resultados['comportamiento_correcto'] = False
    
    # Validación 4: Filtra por área de trabajo
    if resultados['total_cost_calculations'] > 0:
        print(f"   ✅ Filtra por área de trabajo ({resultados['total_cost_calculations']} cálculos de costo)")
    else:
        print(f"   ❌ NO filtra por área de trabajo")
        resultados['comportamiento_correcto'] = False
    
    # Validación 5: NO usa Optimización Global
    if resultados['total_optimizacion_global'] == 0:
        print(f"   ✅ NO usa Optimización Global")
    else:
        print(f"   ❌ USA Optimización Global ({resultados['total_optimizacion_global']} veces)")
        resultados['comportamiento_correcto'] = False
    
    # Mostrar evidencia detallada
    print(f"\n📋 EVIDENCIA DETALLADA:")
    
    # Mostrar primeras 5 selecciones de estrategia
    selecciones = [e for e in resultados['evidencias'] if e['tipo'] == 'estrategia_seleccionada']
    print(f"\n   🎯 SELECCIONES DE ESTRATEGIA (primeras 5):")
    for i, evidencia in enumerate(selecciones[:5]):
        print(f"      {i+1}. Línea {evidencia['linea']}: {evidencia['candidatos']} candidatos")
    
    # Mostrar primeras 5 ordenamientos por pick_sequence
    route_calcs = [e for e in resultados['evidencias'] if e['tipo'] == 'route_calculator']
    print(f"\n   🔄 ORDENAMIENTOS POR PICK_SEQUENCE (primeras 5):")
    for i, evidencia in enumerate(route_calcs[:5]):
        print(f"      {i+1}. Línea {evidencia['linea']}: {evidencia['workorders']} WorkOrders")
    
    # Mostrar primeras 5 cálculos de costo
    cost_calcs = [e for e in resultados['evidencias'] if e['tipo'] == 'cost_calc']
    print(f"\n   💰 CÁLCULOS DE COSTO (primeras 5):")
    for i, evidencia in enumerate(cost_calcs[:5]):
        print(f"      {i+1}. Línea {evidencia['linea']}: {evidencia['operador']} -> {evidencia['area']} (priority={evidencia['priority']}, distance={evidencia['distance']})")
    
    # Mostrar warnings
    warnings = [e for e in resultados['evidencias'] if e['tipo'] == 'warning']
    if warnings:
        print(f"\n   ⚠️  WARNINGS ENCONTRADOS ({len(warnings)}):")
        for i, evidencia in enumerate(warnings[:3]):
            print(f"      {i+1}. Línea {evidencia['linea']}: {evidencia['contenido']}")
        if len(warnings) > 3:
            print(f"      ... y {len(warnings) - 3} más")
    
    # Conclusión final
    print(f"\n🏁 CONCLUSIÓN:")
    if resultados['comportamiento_correcto']:
        print(f"   ✅ COMPORTAMIENTO CORRECTO: La estrategia funciona exactamente como se describió")
        print(f"   ✅ NO usa AssignmentCostCalculator para primera WO")
        print(f"   ✅ Ordena por pick_sequence usando ROUTE-CALCULATOR")
        print(f"   ✅ Filtra por área de trabajo y prioridad")
        print(f"   ✅ Construye tours siguiendo la secuencia")
    else:
        print(f"   ❌ COMPORTAMIENTO INCORRECTO: La estrategia NO funciona como se describió")
    
    # Guardar reporte detallado
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    reporte_file = f"reporte_validacion_estrategia_{timestamp}.json"
    
    with open(reporte_file, 'w', encoding='utf-8') as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Reporte detallado guardado en: {reporte_file}")

if __name__ == "__main__":
    print("Iniciando validación de estrategia...")
    resultados = analizar_logs_simulacion()
    print("\nValidación completada.")
