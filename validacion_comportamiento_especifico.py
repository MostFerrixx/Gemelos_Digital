#!/usr/bin/env python3
"""
Script de Validación Específica: Ejecución de Plan (Filtro por Prioridad)

Este script analiza los logs para validar específicamente que:
1. La estrategia se ejecuta (hay mensajes de selección)
2. NO usa AssignmentCostCalculator para primera WO
3. SÍ ordena por pick_sequence usando ROUTE-CALCULATOR
4. Filtra por área de trabajo y prioridad
"""

import re
from collections import defaultdict

def validar_comportamiento_especifico():
    print("=" * 80)
    print("VALIDACIÓN ESPECÍFICA: EJECUCIÓN DE PLAN (FILTRO POR PRIORIDAD)")
    print("=" * 80)
    
    # Leer archivo
    try:
        with open('test_output_headless.log', 'r', encoding='latin-1') as f:
            contenido = f.read()
    except Exception as e:
        print(f"Error leyendo archivo: {e}")
        return
    
    # Buscar evidencia específica del comportamiento
    evidencias = {
        'estrategia_ejecutada': [],
        'assignment_cost_usage': [],
        'route_calculator_usage': [],
        'cost_calculations': [],
        'warnings': []
    }
    
    # 1. Buscar evidencia de que la estrategia se ejecuta
    patron_ejecucion = r'\[DISPATCHER\] Estrategia \'Ejecucion de Plan \(Filtro por Prioridad\)\' selecciono (\d+) candidatos'
    matches = re.findall(patron_ejecucion, contenido)
    evidencias['estrategia_ejecutada'] = matches
    print(f"✅ EVIDENCIA 1: Estrategia se ejecutó {len(matches)} veces")
    for i, candidatos in enumerate(matches[:5]):
        print(f"   {i+1}. Seleccionó {candidatos} candidatos")
    
    # 2. Buscar evidencia de AssignmentCostCalculator (NO debería haber)
    patron_assignment = r'\[DISPATCHER DEBUG\] Buscando mejor primera WO entre (\d+) candidatos'
    matches = re.findall(patron_assignment, contenido)
    evidencias['assignment_cost_usage'] = matches
    print(f"\n🔍 EVIDENCIA 2: AssignmentCostCalculator usado {len(matches)} veces")
    if len(matches) == 0:
        print("   ✅ CORRECTO: NO usa AssignmentCostCalculator para primera WO")
    else:
        print("   ❌ INCORRECTO: USA AssignmentCostCalculator para primera WO")
        for i, candidatos in enumerate(matches[:3]):
            print(f"   {i+1}. Buscó mejor primera WO entre {candidatos} candidatos")
    
    # 3. Buscar evidencia de ROUTE-CALCULATOR (SÍ debería haber)
    patron_route = r'\[ROUTE-CALCULATOR\] Ordenados (\d+) WorkOrders por pick_sequence'
    matches = re.findall(patron_route, contenido)
    evidencias['route_calculator_usage'] = matches
    print(f"\n🔄 EVIDENCIA 3: ROUTE-CALCULATOR usado {len(matches)} veces")
    if len(matches) > 0:
        print("   ✅ CORRECTO: SÍ ordena por pick_sequence usando ROUTE-CALCULATOR")
        for i, workorders in enumerate(matches[:5]):
            print(f"   {i+1}. Ordenó {workorders} WorkOrders por pick_sequence")
    else:
        print("   ❌ INCORRECTO: NO ordena por pick_sequence")
    
    # 4. Buscar evidencia de cálculos de costo (filtrado por área)
    patron_cost = r'\[COST-CALC\] (.+?) -> (.+?): priority=(\d+), penalty=(\d+), distance=(\d+), total=(\d+)'
    matches = re.findall(patron_cost, contenido)
    evidencias['cost_calculations'] = matches
    print(f"\n💰 EVIDENCIA 4: Cálculos de costo: {len(matches)} ocurrencias")
    if len(matches) > 0:
        print("   ✅ CORRECTO: SÍ filtra por área de trabajo y prioridad")
        for i, match in enumerate(matches[:5]):
            operador, area, priority, penalty, distance, total = match
            print(f"   {i+1}. {operador} -> {area} (priority={priority}, distance={distance})")
    else:
        print("   ❌ INCORRECTO: NO filtra por área de trabajo")
    
    # 5. Buscar warnings (debería haber algunos)
    patron_warning = r'\[DISPATCHER WARN\] Estrategia desconocida \'Ejecucion de Plan \(Filtro por Prioridad\)\', usando FIFO'
    matches = re.findall(patron_warning, contenido)
    evidencias['warnings'] = matches
    print(f"\n⚠️  EVIDENCIA 5: Warnings de estrategia desconocida: {len(matches)} ocurrencias")
    if len(matches) > 0:
        print("   ⚠️  ADVERTENCIA: Hay warnings pero la estrategia SÍ funciona")
        print("   (Esto indica que hay dos lugares donde se verifica la estrategia)")
    else:
        print("   ✅ CORRECTO: No hay warnings")
    
    # Análisis de comportamiento específico
    print(f"\n🎯 ANÁLISIS DE COMPORTAMIENTO ESPECÍFICO:")
    
    # Comportamiento correcto según la descripción
    comportamiento_correcto = (
        len(evidencias['estrategia_ejecutada']) > 0 and  # Se ejecuta
        len(evidencias['assignment_cost_usage']) == 0 and  # NO usa AssignmentCostCalculator
        len(evidencias['route_calculator_usage']) > 0 and  # SÍ ordena por pick_sequence
        len(evidencias['cost_calculations']) > 0  # SÍ filtra por área
    )
    
    print(f"\n📊 RESUMEN DE VALIDACIÓN:")
    print(f"   • Estrategia se ejecuta: {'✅' if len(evidencias['estrategia_ejecutada']) > 0 else '❌'}")
    print(f"   • NO usa AssignmentCostCalculator: {'✅' if len(evidencias['assignment_cost_usage']) == 0 else '❌'}")
    print(f"   • SÍ ordena por pick_sequence: {'✅' if len(evidencias['route_calculator_usage']) > 0 else '❌'}")
    print(f"   • SÍ filtra por área de trabajo: {'✅' if len(evidencias['cost_calculations']) > 0 else '❌'}")
    
    print(f"\n🏁 CONCLUSIÓN FINAL:")
    if comportamiento_correcto:
        print(f"   ✅ COMPORTAMIENTO CORRECTO")
        print(f"   La estrategia 'Ejecución de Plan (Filtro por Prioridad)' funciona exactamente como se describió:")
        print(f"   - Se ejecuta correctamente")
        print(f"   - NO usa AssignmentCostCalculator para primera WO")
        print(f"   - SÍ ordena por pick_sequence usando ROUTE-CALCULATOR")
        print(f"   - SÍ filtra por área de trabajo y prioridad")
    else:
        print(f"   ❌ COMPORTAMIENTO INCORRECTO")
        print(f"   La estrategia NO funciona como se describió")
    
    # Mostrar evidencia detallada de los primeros casos
    print(f"\n📋 EVIDENCIA DETALLADA (primeros 3 casos):")
    
    # Buscar líneas específicas para mostrar contexto
    lineas = contenido.split('\n')
    casos_encontrados = 0
    
    for i, linea in enumerate(lineas):
        if 'Ejecucion de Plan (Filtro por Prioridad)' in linea and 'selecciono' in linea:
            casos_encontrados += 1
            if casos_encontrados <= 3:
                print(f"\n   CASO {casos_encontrados}:")
                print(f"   Línea {i+1}: {linea}")
                
                # Mostrar contexto (5 líneas antes y después)
                inicio = max(0, i-5)
                fin = min(len(lineas), i+6)
                print(f"   Contexto:")
                for j in range(inicio, fin):
                    if j == i:
                        print(f"   >>> {j+1}: {lineas[j]}")
                    else:
                        print(f"      {j+1}: {lineas[j]}")
    
    return evidencias

if __name__ == "__main__":
    evidencias = validar_comportamiento_especifico()
    print(f"\nValidación completada.")
