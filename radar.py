import os
import json
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(
    title="Mirage HoneyPot Radar",
    description="Internal telemetry dashboard.",
    version="1.0.0"
)

# CRITICAL: This must match the ABSOLUTE path in trap.py
LOG_FILE = "/home/ubuntu/Mirage-HoneyPot/honeypot_logs.jsonl"
DASHBOARD_PATH = "/home/ubuntu/Mirage-HoneyPot/dashboard.html"

@app.get("/", response_class=HTMLResponse)
@app.get("/admin/dashboard", response_class=HTMLResponse)
async def dashboard_view():
    """
    Serves the static HTML dashboard file using an absolute path.
    """
    if os.path.exists(DASHBOARD_PATH):
        with open(DASHBOARD_PATH, "r") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    return HTMLResponse(content=f"<h1>Dashboard ({DASHBOARD_PATH}) missing</h1>", status_code=404)

@app.get("/api/telemetry")
async def get_telemetry():
    """
    Reads the JSONL log file and returns the last 50 entries.
    """
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        logs.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    
    # Reverse to show newest first for the dashboard
    return logs[::-1][:50]

@app.post("/api/telemetry/clear")
async def clear_telemetry():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            f.write("")
    return {"status": "cleared"}

if __name__ == "__main__":
    import uvicorn
    # Change host to 0.0.0.0 if you want to access it via public IP:8081 
    # OR stay 127.0.0.1 for SSH Tunneling (more secure for SOC managers)
    uvicorn.run(app, host="0.0.0.0", port=8081)
