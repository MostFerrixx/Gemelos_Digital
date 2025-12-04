import subprocess
import sys
import os

# Define paths
SERVER_SCRIPT = os.path.join("web_prototype", "server.py")
LOG_FILE = os.path.join("logs", "server.log")
ERROR_FILE = os.path.join("logs", "server_errors.log")

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Open log files
with open(LOG_FILE, "w") as out, open(ERROR_FILE, "w") as err:
    # Launch server process without window
    # CREATE_NO_WINDOW = 0x08000000
    # Use python.exe explicitly to avoid pythonw issues with subprocess
    python_exe = sys.executable.replace("pythonw.exe", "python.exe")
    out.write(f"Launching {python_exe} with {SERVER_SCRIPT}\n")
    out.flush()
    
    subprocess.Popen(
        [python_exe, SERVER_SCRIPT],
        stdout=out,
        stderr=err,
        creationflags=0x08000000
    )
