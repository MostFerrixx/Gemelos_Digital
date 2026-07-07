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
from web_prototype.routers import configurator, replay, runners, system

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


@app.on_event("startup")
async def startup_event():
    """Clean up uploads directory on startup"""
    uploads_dir = os.path.join(PROJECT_ROOT, "uploads")
    if os.path.exists(uploads_dir):
        print(f"Cleaning up uploads directory: {uploads_dir}")
        try:
            shutil.rmtree(uploads_dir)
            os.makedirs(uploads_dir, exist_ok=True)
            print("Uploads directory cleaned.")
        except Exception as e:
            print(f"Error cleaning uploads directory: {e}")


app.include_router(configurator.router)
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
