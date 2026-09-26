# -*- coding: utf-8 -*-
"""
Servidor web del Gemelo Digital (FastAPI, puerto 8000).

REFACTOR 2026-07-07: era un monolito de ~1400 lineas con 6 responsabilidades
mezcladas. Ahora este archivo solo arma la app; el resto vive en:
  - web_prototype/app_state.py ......... estado compartido (config_manager,
                                          replay_data, paths)
  - web_prototype/routers/configurator.py  /api/configurator/*, /api/upload-orders
  - web_prototype/routers/replay.py ....... /api/layout|snapshot|state|metrics,
                                            /api/load_replay|upload_replay|
                                            validate-replay|event-markers
  - web_prototype/routers/runners.py ...... /ws/simulation-runner,
                                            /api/simulation-status,
                                            /api/optimization/*, /api/experiment/*
  - web_prototype/routers/system.py ....... /api/system/restart|health
"""
import os
import shutil
import sys

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Add project root to path to import existing modules if needed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from web_prototype.app_state import PROJECT_ROOT
from web_prototype.routers import configurator, master_data, replay, runners, system

app = FastAPI()

# CORS for development convenience
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Anti-cache (desarrollo): evita que el navegador sirva versiones viejas de los estaticos
# (configurador/visor) y haya que forzar recarga (Ctrl+Shift+R). Aplica solo al front
# estatico; las APIs JSON ya son dinamicas y no se cachean igual.
@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path == "/" or path.startswith("/web_configurator") or \
            path.endswith((".js", ".css", ".html", ".htm")):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


def limpiar_uploads(raiz: str) -> list:
    """Borra de uploads/ los archivos que la configuracion vigente NO usa.

    QA H-57: antes se borraba la carpeta entera al arrancar, y config.json
    quedaba apuntando a un archivo de pedidos / mapa / Excel subido que ya no
    existia (el servidor del cliente se reinicia solo: BK-16). Las
    configuraciones guardadas no dependen de uploads/ (BK-36 copia sus archivos).
    Devuelve las rutas relativas borradas."""
    uploads_dir = os.path.join(raiz, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    try:
        with open(os.path.join(raiz, "config.json"), "r", encoding="utf-8") as f:
            vigente = f.read().replace(chr(92) * 2, "/").replace(chr(92), "/")
    except OSError:
        vigente = ""
    borrados = []
    for carpeta, _, archivos in os.walk(uploads_dir):
        for nombre in archivos:
            ruta = os.path.join(carpeta, nombre)
            rel = os.path.relpath(ruta, raiz).replace(chr(92), "/")
            if rel in vigente:
                continue
            try:
                os.remove(ruta)
                borrados.append(rel)
            except OSError:
                pass
    return borrados


@app.on_event("startup")
async def startup_event():
    """Limpia uploads/ sin tocar lo que usa la configuracion vigente."""
    try:
        borrados = limpiar_uploads(PROJECT_ROOT)
        print("[OK] uploads/: %d archivo(s) sin uso borrado(s)." % len(borrados))
    except Exception as e:
        print(f"[WARN] No se pudo limpiar uploads/: {e}")


app.include_router(configurator.router)
app.include_router(master_data.router)
app.include_router(replay.router)
app.include_router(runners.router)
app.include_router(system.router)

# Serve static files (Frontend)
app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static"), html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(
        "web_prototype.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload for development
        reload_dirs=[PROJECT_ROOT]  # Watch project directory for changes
    )
