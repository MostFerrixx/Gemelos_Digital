# `_legacy/communication_raiz/` — carpeta `communication/` huerfana de la raiz

**Qué es:** la carpeta `communication/` que vivia en la **raiz** del proyecto (distinta de
`src/communication/`, que se archivo con las GUI de escritorio en `_legacy/gui_escritorio/communication/`).

**Por qué se archivo (2026-05-31):**
- Estaba **untracked y gitignored** (no formaba parte del control de versiones).
- Contenia un unico archivo, `test_dashboard_communicator.py`, que importa por ruta
  relativa modulos inexistentes en esta carpeta (`.dashboard_communicator`, `.ipc_protocols`,
  `.lifecycle_manager`) y un `simulation_data_provider` que no existe en el codigo. Esta **roto**.
- **Ningun modulo vivo lo importa** (verificado por grep en todo el codigo, excluyendo _legacy/tests).

Es un residuo muerto. Se conserva aqui solo como referencia historica. Reversible: `git mv`/`mv` inverso.
