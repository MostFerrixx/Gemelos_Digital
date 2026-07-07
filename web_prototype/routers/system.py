# -*- coding: utf-8 -*-
"""Endpoints de SISTEMA (restart por touch + health check).
REFACTOR 2026-07-07: extraido verbatim del monolito server.py."""
import os
import time

from fastapi import APIRouter, HTTPException

from web_prototype.app_state import replay_data

router = APIRouter()

# El restart funciona tocando el archivo del server (uvicorn reload lo ve).
# Tras el refactor, __file__ seria este router: apuntar explicitamente a
# server.py para conservar el comportamiento historico.
SERVER_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py")


@router.post("/api/system/restart")
def restart_server():
    """
    Trigger server restart by touching the server file.
    Requires reload=True in uvicorn.run() to work.
    """
    try:
        # Touch server.py to trigger Uvicorn reload
        server_file = SERVER_FILE
        os.utime(server_file, None)
        
        return {
            "success": True,
            "message": "Server restart triggered. Reloading...",
            "estimated_time": 3  # seconds
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger restart: {str(e)}")


@router.get("/api/system/health")
def health_check():
    """
    Health check endpoint to verify server is responsive.
    Used by frontend to detect when server has restarted.
    """
    return {
        "status": "ok",
        "timestamp": time.time(),
        "uptime": time.time() - replay_data.events[0].get('timestamp', 0) if replay_data.events else 0
    }

