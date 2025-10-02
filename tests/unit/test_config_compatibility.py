# -*- coding: utf-8 -*-
"""
Test de compatibilidad del config.json generado por fix/configurator-tool
con el código de simulación de main V10.0.5
"""

import json
import os
import sys

def test_config_loading():
    """Prueba de carga y validación del config.json"""

    print("="*70)
    print("TEST DE COMPATIBILIDAD CONFIG.JSON")
    print("Rama Main V10.0.5 vs. Config desde fix/configurator-tool")
    print("="*70)
    print()

    config_path = "config.json"

    # 1. Verificar que existe el archivo
    if not os.path.exists(config_path):
        print(f"[X] ERROR: No se encontro {config_path}")
        return False

    print(f"[OK] Archivo encontrado: {config_path}")

    # 2. Intentar cargar el JSON
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"[OK] JSON cargado exitosamente")
    except json.JSONDecodeError as e:
        print(f"[X] ERROR: JSON invalido - {e}")
        return False
    except Exception as e:
        print(f"[X] ERROR al leer archivo - {e}")
        return False

    # 3. Validar campos esperados por la simulación
    print("\n" + "="*70)
    print("VALIDANDO ESTRUCTURA DEL CONFIG")
    print("="*70)

    campos_requeridos = [
        'total_ordenes',
        'distribucion_tipos',
        'capacidad_carro',
        'dispatch_strategy',
        'layout_file',
        'sequence_file',
        'num_operarios',
        'assignment_rules',
        'outbound_staging_distribution'
    ]

    print("\nCampos requeridos:")
    for campo in campos_requeridos:
        if campo in config:
            print(f"  [OK] {campo}: {type(config[campo]).__name__}")
        else:
            print(f"  [X] {campo}: FALTANTE")

    # 4. Verificar campo NUEVO: agent_types
    print("\nNuevo campo (fix/configurator-tool):")
    if 'agent_types' in config:
        print(f"  [OK] agent_types: {type(config['agent_types']).__name__} con {len(config['agent_types'])} elementos")

        # Analizar estructura de agent_types
        print("\nEstructura de agent_types:")
        for idx, agent in enumerate(config['agent_types']):
            print(f"    [{idx}] {agent.get('type', '?')}: "
                  f"capacity={agent.get('capacity', '?')}, "
                  f"discharge_time={agent.get('discharge_time', '?')}")

            if 'work_area_priorities' in agent:
                was = agent['work_area_priorities']
                print(f"         work_area_priorities: {dict(list(was.items())[:3])}" +
                      (f"... (+{len(was)-3} more)" if len(was) > 3 else ""))
    else:
        print(f"  [WARN] agent_types: NO ENCONTRADO (campo nuevo, podría causar problemas)")

    # 5. Validar work_area_priorities - ¿Son strings o ints?
    print("\nValidando tipos de Work Area priorities:")
    if 'agent_types' in config and config['agent_types']:
        primer_agente = config['agent_types'][0]
        if 'work_area_priorities' in primer_agente:
            wa_priorities = primer_agente['work_area_priorities']
            if wa_priorities:
                primer_wa = list(wa_priorities.keys())[0]
                tipo_wa = type(primer_wa).__name__
                print(f"  Tipo de claves en work_area_priorities: {tipo_wa}")

                if tipo_wa == 'str':
                    print(f"  [OK] Work Areas son STRINGS (ej: '{primer_wa}')")
                    print(f"       Esto es CORRECTO para el nuevo configurator")
                elif tipo_wa == 'int':
                    print(f"  [WARN] Work Areas son INT (ej: {primer_wa})")
                    print(f"         La rama main podría esperar strings")

    # 6. Verificar archivos referenciados
    print("\nVerificando archivos referenciados:")
    archivos_ref = {
        'layout_file': config.get('layout_file', ''),
        'sequence_file': config.get('sequence_file', '')
    }

    for nombre, ruta in archivos_ref.items():
        if os.path.exists(ruta):
            print(f"  [OK] {nombre}: {ruta}")
        else:
            print(f"  [WARN] {nombre}: {ruta} (NO ENCONTRADO)")

    # 7. Resumen final
    print("\n" + "="*70)
    print("RESUMEN FINAL")
    print("="*70)

    # Verificar compatibilidad básica
    todos_campos_presentes = all(campo in config for campo in campos_requeridos)
    tiene_agent_types = 'agent_types' in config

    if todos_campos_presentes and tiene_agent_types:
        print("[OK] COMPATIBILIDAD PROBABLE")
        print("   - Todos los campos requeridos estan presentes")
        print("   - Incluye el nuevo campo 'agent_types'")
        print("   - Estructura parece correcta")
        print()
        print("[WARN] ADVERTENCIAS:")
        print("   - Necesita prueba en simulacion real para confirmar 100%")
        print("   - Work Area priorities usan STRINGS (verificar compatibilidad en main)")
        return True
    elif todos_campos_presentes:
        print("[WARN] COMPATIBILIDAD PARCIAL")
        print("   - Campos basicos presentes")
        print("   - Falta 'agent_types' (campo nuevo)")
        return True
    else:
        print("[X] INCOMPATIBLE")
        print("   - Faltan campos requeridos")
        return False

if __name__ == "__main__":
    exito = test_config_loading()
    sys.exit(0 if exito else 1)
