# -*- coding: utf-8 -*-
"""
MEJ-1: smoke del gate de regresion via pytest (marker "gate").

Excluido del run default (pytest.ini: addopts -m "not gate").
Correrlo: python -m pytest -m gate
"""
import os
import subprocess
import sys

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GATE = os.path.join(PROJECT_ROOT, "scripts", "regression_gate.py")


@pytest.mark.gate
def test_gate_byte_identico():
    proc = subprocess.run([sys.executable, GATE], cwd=PROJECT_ROOT,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          timeout=660)
    salida = proc.stdout.decode("utf-8", errors="replace")
    assert proc.returncode == 0, "Gate FAIL:\n" + salida
    assert "[OK] GATE PASS" in salida
