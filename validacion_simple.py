#!/usr/bin/env python3
"""
Script Simple de Validación: Ejecución de Plan (Filtro por Prioridad)
"""

import re

def validar_estrategia():
    print("=" * 80)
    print("VALIDACIÓN SIMPLE: EJECUCIÓN DE PLAN (FILTRO POR PRIORIDAD)")
    print("=" * 80)
    
    # Leer archivo
    try:
        with open('test_output.log', 'r', encoding='latin-1') as f:
            contenido = f.read()
    except Exception as e:
        print(f"Error leyendo archivo: {e}")
        return
    
    # Buscar patrones
    patrones = {
        'estrategia_seleccionada': r'\[DISPATCHER\] Estrategia \'Ejecucion de Plan \(Filtro por Prioridad\)\' selecciono (\d+) candidatos',
        'cost_calc': r'\[COST-CALC\] (.+?) -> (.+?): priority=(\d+), penalty=(\d+), distance=(\d+), total=(\d+)',
        'route_calculator': r'\[ROUTE-CALCULATOR\] Ordenados (\d+) WorkOrders por pick_sequence',
        'warnings': r'\[DISPATCHER WARN\] Estrategia desconocida \'Ejecucion de Plan \(Filtro por Prioridad\)\', usando FIFO',
        'optimizacion_global': r'\[DISPATCHER\] Optimización Global: usando tour construido por proximidad',
        'assignment_cost': r'\[DISPATCHER DEBUG\] Buscando mejor primera WO entre (\d+) candidatos'
    }
    
    resultados = {}
    
    for nombre, patron in patrones.items():
        matches = re.findall(patron, contenido)
        resultados[nombre] = len(matches)
        print(f"{nombre}: {len(matches)} ocurrencias")
    
    # Mostrar evidencia
    print(f"\n📋 EVIDENCIA DETALLADA:")
    
    # Selecciones de estrategia
    selecciones = re.findall(patrones['estrategia_seleccionada'], contenido)
    print(f"\n🎯 SELECCIONES DE ESTRATEGIA:")
    for i, candidatos in enumerate(selecciones[:10]):
        print(f"   {i+1}. {candidatos} candidatos")
    
    # Ordenamientos por pick_sequence
    route_calcs = re.findall(patrones['route_calculator'], contenido)
    print(f"\n🔄 ORDENAMIENTOS POR PICK_SEQUENCE:")
    for i, workorders in enumerate(route_calcs[:10]):
        print(f"   {i+1}. {workorders} WorkOrders")
    
    # Cálculos de costo
    cost_calcs = re.findall(patrones['cost_calc'], contenido)
    print(f"\n💰 CÁLCULOS DE COSTO:")
    for i, match in enumerate(cost_calcs[:10]):
        operador, area, priority, penalty, distance, total = match
        print(f"   {i+1}. {operador} -> {area} (priority={priority}, distance={distance})")
    
    # Warnings
    warnings = re.findall(patrones['warnings'], contenido)
    print(f"\n⚠️  WARNINGS:")
    print(f"   Total warnings: {len(warnings)}")
    
    # AssignmentCostCalculator
    assignment_costs = re.findall(patrones['assignment_cost'], contenido)
    print(f"\n🔍 ASSIGNMENTCOSTCALCULATOR:")
    print(f"   Total usos: {len(assignment_costs)}")
    
    # Validación final
    print(f"\n🏁 VALIDACIÓN FINAL:")
    
    if resultados['estrategia_seleccionada'] > 0:
        print(f"   ✅ La estrategia se ejecutó {resultados['estrategia_seleccionada']} veces")
    else:
        print(f"   ❌ La estrategia NO se ejecutó")
    
    if resultados['assignment_cost'] == 0:
        print(f"   ✅ NO usa AssignmentCostCalculator para primera WO")
    else:
        print(f"   ❌ USA AssignmentCostCalculator para primera WO ({resultados['assignment_cost']} veces)")
    
    if resultados['route_calculator'] > 0:
        print(f"   ✅ Ordena por pick_sequence ({resultados['route_calculator']} veces)")
    else:
        print(f"   ❌ NO ordena por pick_sequence")
    
    if resultados['cost_calc'] > 0:
        print(f"   ✅ Filtra por área de trabajo ({resultados['cost_calc']} cálculos)")
    else:
        print(f"   ❌ NO filtra por área de trabajo")
    
    if resultados['optimizacion_global'] == 0:
        print(f"   ✅ NO usa Optimización Global")
    else:
        print(f"   ❌ USA Optimización Global ({resultados['optimizacion_global']} veces)")
    
    # Conclusión
    comportamiento_correcto = (
        resultados['estrategia_seleccionada'] > 0 and
        resultados['assignment_cost'] == 0 and
        resultados['route_calculator'] > 0 and
        resultados['cost_calc'] > 0 and
        resultados['optimizacion_global'] == 0
    )
    
    print(f"\n🎯 CONCLUSIÓN:")
    if comportamiento_correcto:
        print(f"   ✅ COMPORTAMIENTO CORRECTO: La estrategia funciona exactamente como se describió")
    else:
        print(f"   ❌ COMPORTAMIENTO INCORRECTO: La estrategia NO funciona como se describió")

if __name__ == "__main__":
    validar_estrategia()
