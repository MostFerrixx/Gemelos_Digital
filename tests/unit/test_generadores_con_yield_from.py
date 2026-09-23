# -*- coding: utf-8 -*-
"""
BK-29: un metodo generador llamado SIN `yield from` no ejecuta nada.

Asi se colo el error de la estacion con turno: `self._esperar_sin_estorbar()`
(un generador SimPy) se llamaba como sentencia suelta y el operario sin lugar
en la fila se quedaba parado en medio del pasillo, trabando a los demas.

Este test lee el codigo del motor con `ast`, junta los metodos que son
generadores y falla si alguno se invoca como sentencia suelta
(`self.metodo()` sin `yield from`, sin asignarlo y sin pasarlo a nadie).
"""
import ast
import os

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODULOS = [
    os.path.join(RAIZ, 'src', 'subsystems', 'simulation', nombre)
    for nombre in ('operators.py', 'warehouse.py', 'dispatcher.py', 'outbound.py', 'inbound.py')
]


def _es_generador(funcion: ast.FunctionDef) -> bool:
    """Tiene yield en SU cuerpo (no en funciones anidadas)."""
    pendientes = list(funcion.body)
    while pendientes:
        nodo = pendientes.pop()
        if isinstance(nodo, (ast.Yield, ast.YieldFrom)):
            return True
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            continue
        pendientes.extend(ast.iter_child_nodes(nodo))
    return False


def _llamadas_sueltas(arbol, generadores):
    for nodo in ast.walk(arbol):
        if (isinstance(nodo, ast.Expr) and isinstance(nodo.value, ast.Call)
                and isinstance(nodo.value.func, ast.Attribute)
                and isinstance(nodo.value.func.value, ast.Name)
                and nodo.value.func.value.id == 'self'
                and nodo.value.func.attr in generadores):
            yield nodo.value.func.attr, nodo.lineno


def test_ningun_generador_del_motor_se_llama_sin_yield_from():
    arboles = {ruta: ast.parse(open(ruta, encoding='utf-8').read())
               for ruta in MODULOS if os.path.exists(ruta)}
    generadores = {f.name for arbol in arboles.values() for f in ast.walk(arbol)
                   if isinstance(f, ast.FunctionDef) and _es_generador(f)}
    assert '_esperar_sin_estorbar' in generadores          # el detector funciona
    errores = ['%s:%d self.%s()' % (os.path.basename(ruta), linea, nombre)
               for ruta, arbol in arboles.items()
               for nombre, linea in _llamadas_sueltas(arbol, generadores)]
    assert not errores, "generadores llamados sin 'yield from': %s" % errores
