import os
import json
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(
    title="Mirage HoneyPot Radar",
    description="Internal telemetry dashboard.",
    version="1.0.0"
)

LOG_FILE = "honeypot_logs.jsonl"

@app.get("/", response_class=HTMLResponse)
@app.get("/admin/dashboard", response_class=HTMLResponse)
async def dashboard_view():
    if os.path.exists("dashboard.html"):
        with open("dashboard.html", "r") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    return HTMLResponse(content="<h1>Dashboard missing</h1>", status_code=404)

@app.get("/api/telemetry")
async def get_telemetry():
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        logs.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    return logs[-50:]

@app.post("/api/telemetry/clear")
async def clear_telemetry():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            f.write("")
    return {"status": "cleared"}
