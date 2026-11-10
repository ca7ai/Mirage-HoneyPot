import os
import json
from collections import deque
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from starlette.middleware.trustedhost import TrustedHostMiddleware

app = FastAPI(
    title="Mirage HoneyPot Radar",
    description="Internal telemetry dashboard.",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# Rejects DNS-rebinding pages that resolve their own hostname to 127.0.0.1
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1"])

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Must match MIRAGE_DATA_DIR used by trap.py
DATA_DIR = os.environ.get("MIRAGE_DATA_DIR", BASE_DIR)
LOG_FILE = os.path.join(DATA_DIR, "honeypot_logs.jsonl")
DASHBOARD_PATH = os.path.join(BASE_DIR, "dashboard.html")
DASHBOARD_JS_PATH = os.path.join(BASE_DIR, "dashboard.js")

# Telemetry is attacker-controlled; the CSP blocks inline script if anything slips through
CSP = (
    "default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; connect-src 'self'; "
    "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
)

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = CSP
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response

@app.get("/", response_class=HTMLResponse)
@app.get("/admin/dashboard", response_class=HTMLResponse)
async def dashboard_view():
    """
    Serves the static HTML dashboard file.
    """
    if os.path.exists(DASHBOARD_PATH):
        with open(DASHBOARD_PATH, "r") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    return HTMLResponse(content="<h1>Dashboard missing</h1>", status_code=404)

@app.get("/dashboard.js")
async def dashboard_script():
    with open(DASHBOARD_JS_PATH, "r") as f:
        return Response(content=f.read(), media_type="application/javascript")

@app.get("/api/telemetry")
async def get_telemetry():
    """
    Returns the last 50 log entries, newest first.
    """
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            tail = deque(f, maxlen=50)
        for line in tail:
            line = line.strip()
            if line:
                try:
                    logs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    return logs[::-1]

if __name__ == "__main__":
    import uvicorn
    # Loopback only: reach it through an SSH tunnel (see README)
    uvicorn.run(app, host="127.0.0.1", port=8081)
