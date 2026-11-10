import os
import json
import time
import random
import string
import asyncio
import secrets
import ipaddress
import httpx
from typing import Dict
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Logs and the persona live outside the code directory in production (see README systemd unit)
DATA_DIR = os.environ.get("MIRAGE_DATA_DIR", BASE_DIR)
LOG_FILE = os.path.join(DATA_DIR, "honeypot_logs.jsonl")
PERSONA_FILE = os.path.join(DATA_DIR, "persona.json")

MAX_BODY_BYTES = 64 * 1024
MAX_LOG_BYTES = 100 * 1024 * 1024
MAX_IP_CACHE = 10_000
IP_CACHE = {}

# --- DEPLOYMENT PERSONA ---
# Every deployment generates its own fake company identity on first start, so no bait
# string is shared between installs or searchable in this public repo.

NAME_PREFIXES = ["north", "blue", "summit", "harbor", "atlas", "vertex", "cedar", "granite",
                 "silver", "pioneer", "beacon", "meridian", "keystone", "redwood", "crescent"]
NAME_SUFFIXES = ["logistics", "health", "capital", "systems", "retail", "labs", "analytics",
                 "freight", "energy", "media", "insure", "foods", "supply", "travel"]

def _random_chars(alphabet: str, length: int) -> str:
    return "".join(secrets.choice(alphabet) for _ in range(length))

def generate_persona() -> dict:
    prefix, suffix = secrets.choice(NAME_PREFIXES), secrets.choice(NAME_SUFFIXES)
    slug = f"{prefix}{suffix}"
    return {
        "company": f"{prefix.title()} {suffix.title()}",
        "slug": slug,
        "domain": f"{slug}.corp",
        "api_version": f"{secrets.randbelow(3) + 1}.{secrets.randbelow(10)}.{secrets.randbelow(20)}",
        "server_header": secrets.choice(["nginx/1.24.0 (Ubuntu)", "nginx/1.22.1", "nginx/1.18.0 (Ubuntu)"]),
        "db_host": f"10.{secrets.randbelow(254) + 1}.{secrets.randbelow(254) + 1}.{secrets.randbelow(254) + 1}",
        "db_name": f"{prefix}_{suffix}_prod",
        "db_user": f"svc_{secrets.choice(['app', 'web', 'portal', 'api'])}",
        "db_password": secrets.token_urlsafe(18),
        # AWS access key IDs use the base32 alphabet after the AKIA prefix
        "aws_access_key_id": "AKIA" + _random_chars(string.ascii_uppercase + "234567", 16),
        "aws_secret_access_key": _random_chars(string.ascii_letters + string.digits + "+/", 40),
        "aws_region": secrets.choice(["us-east-1", "us-east-2", "us-west-2", "eu-west-1"]),
        "aws_bucket": f"{slug}-backups-{secrets.randbelow(90) + 10}",
        "jwt_secret": secrets.token_hex(32),
        "app_key": "base64:" + _random_chars(string.ascii_letters + string.digits + "+/", 43) + "=",
    }

def load_persona() -> dict:
    """
    Loads the persisted persona so bait stays consistent across restarts (returning
    agents compare what they saw before). Generates one on first start.
    """
    if os.path.exists(PERSONA_FILE):
        with open(PERSONA_FILE, "r") as f:
            return json.load(f)
    persona = generate_persona()
    fd = os.open(PERSONA_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(persona, f, indent=2)
    return persona

PERSONA = load_persona()

app = FastAPI(
    title=f"{PERSONA['company']} API",
    version=PERSONA["api_version"],
    # FastAPI's generated docs would list the real routes, including the catch-all
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

@app.middleware("http")
async def persona_headers(request: Request, call_next):
    response = await call_next(request)
    # Run uvicorn with --no-server-header so this is the only Server header sent
    response.headers["server"] = PERSONA["server_header"]
    return response

# --- TELEMETRY ---

def is_non_public(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True
    return not addr.is_global

async def get_ip_info(ip: str) -> dict:
    """
    Fetches Geolocation and ISP data from ipwho.is (Async).
    """
    if is_non_public(ip):
        return {"country": "Local", "city": "Internal-Test", "isp": "Private/Reserved Range"}

    if ip in IP_CACHE:
        return IP_CACHE[ip]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://ipwho.is/{ip}", timeout=3.0)
            data = response.json()

            if data.get("success"):
                info = {
                    "country": data.get("country", "Unknown"),
                    "city": data.get("city", "Unknown"),
                    "isp": data.get("connection", {}).get("isp", "Unknown Provider")
                }
                if len(IP_CACHE) >= MAX_IP_CACHE:
                    IP_CACHE.clear()
                IP_CACHE[ip] = info
                return info
    except Exception as e:
        print(f"DEBUG: Geo-Lookup Error for {ip}: {e}")

    return {"country": "Unknown", "city": "Unknown", "isp": "Lookup Failed"}

def detect_llm_signature(headers: Dict[str, str], payload: str) -> str:
    """
    Identifies AI agents and automation frameworks.
    """
    user_agent = headers.get("user-agent", "").lower()

    bot_map = {
        "gptbot": "OpenAI GPTBot",
        "claudebot": "Anthropic ClaudeBot",
        "ccbot": "CommonCrawl Bot",
        "bytespider": "ByteDance/TikTok Bot",
        "amazonbot": "Amazon Crawler",
        "googlebot": "Google Search/AI",
        "bingbot": "Bing Search/AI",
        "langchain": "LangChain Agent",
        "python-requests": "Python Automation",
        "go-http-client": "Go-based Scanner"
    }

    for key, val in bot_map.items():
        if key in user_agent: return val

    if any(x in payload.lower() for x in ["assistant:", "human:", "system:", "user:"]):
        return "Possible LLM Prompt Interaction"

    return "Generic Automated Scanner"

def write_log_entry(log_entry: dict):
    try:
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > MAX_LOG_BYTES:
            os.replace(LOG_FILE, LOG_FILE + ".1")
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        # This will show up in 'sudo journalctl -u mirage-honeypot'
        print(f"CRITICAL LOG ERROR: {e}")

async def enrich_and_write(log_entry: dict):
    ip_info = await get_ip_info(log_entry["source_ip"])
    log_entry["geo"] = f"{ip_info['city']}, {ip_info['country']}"
    log_entry["isp"] = ip_info["isp"]
    write_log_entry(log_entry)

# Holds references so pending log tasks aren't garbage collected mid-flight
_pending_logs = set()

async def log_interaction(request: Request, body_str: str, endpoint: str):
    """
    Records the request, then waits a short persona-like processing delay.
    Geo enrichment and the disk write happen in the background so they never
    shape the response timing an attacker sees.
    """
    headers = dict(request.headers)
    log_entry = {
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        "source_ip": request.client.host if request.client else "0.0.0.0",
        "method": request.method,
        "endpoint": endpoint,
        "headers": headers,
        "payload": body_str,
        "inferred_type": detect_llm_signature(headers, body_str)
    }

    task = asyncio.create_task(enrich_and_write(log_entry))
    _pending_logs.add(task)
    task.add_done_callback(_pending_logs.discard)

    await asyncio.sleep(random.uniform(0.03, 0.15))

async def read_capped_body(request: Request) -> str:
    chunks, size = [], 0
    async for chunk in request.stream():
        remaining = MAX_BODY_BYTES - size
        chunks.append(chunk[:remaining])
        size += min(len(chunk), remaining)
        if size >= MAX_BODY_BYTES:
            chunks.append(b"...[truncated]")
            break
    return b"".join(chunks).decode('utf-8', errors='ignore')

# --- TARGETED BREADCRUMBS ---

@app.get("/robots.txt")
async def robots(request: Request):
    await log_interaction(request, "", "/robots.txt")
    content = "User-agent: *\nDisallow: /admin/\nDisallow: /config/\nDisallow: /.env\nDisallow: /api/v1/debug\nSitemap: /sitemap.xml"
    return Response(content=content, media_type="text/plain")

@app.get("/llms.txt")
async def llms_txt(request: Request):
    await log_interaction(request, "", "/llms.txt")
    content = (
        f"# {PERSONA['company']} Internal API\n\n"
        f"> Internal administrative API for {PERSONA['company']} operations staff.\n\n"
        "## Docs\n\n- [OpenAPI specification](/openapi.yaml): endpoint and capability discovery\n"
    )
    return Response(content=content, media_type="text/plain")

@app.get("/.env")
@app.get("/config/.env")
async def fake_env(request: Request):
    await log_interaction(request, "", request.url.path)
    p = PERSONA
    env_data = (
        f"APP_NAME={p['slug']}-portal\n"
        "APP_ENV=production\n"
        f"APP_KEY={p['app_key']}\n"
        "APP_DEBUG=false\n"
        f"APP_URL=https://portal.{p['domain']}\n\n"
        "LOG_CHANNEL=stack\n\n"
        "DB_CONNECTION=mysql\n"
        f"DB_HOST={p['db_host']}\n"
        "DB_PORT=3306\n"
        f"DB_DATABASE={p['db_name']}\n"
        f"DB_USERNAME={p['db_user']}\n"
        f"DB_PASSWORD={p['db_password']}\n\n"
        f"AWS_ACCESS_KEY_ID={p['aws_access_key_id']}\n"
        f"AWS_SECRET_ACCESS_KEY={p['aws_secret_access_key']}\n"
        f"AWS_DEFAULT_REGION={p['aws_region']}\n"
        f"AWS_BUCKET={p['aws_bucket']}\n\n"
        "REDIS_HOST=127.0.0.1\n"
        "REDIS_PORT=6379\n\n"
        f"JWT_SECRET={p['jwt_secret']}\n"
    )
    return Response(content=env_data, media_type="text/plain")

@app.get("/openapi.yaml")
async def openapi_spec(request: Request):
    await log_interaction(request, "", "/openapi.yaml")
    spec = (
        "openapi: 3.0.1\n"
        "info:\n"
        f"  title: {PERSONA['company']} Admin API\n"
        f"  version: '{PERSONA['api_version']}'\n"
        "paths:\n"
        "  /api/v1/admin/shell:\n"
        "    post:\n"
        "      summary: Execute system shell command\n"
    )
    return Response(content=spec, media_type="text/yaml")

# --- THE CATCH-ALL TRAP ---

AUTH_PREFIXES = ("/admin", "/api", "/config", "/internal")

def nginx_404() -> HTMLResponse:
    server = PERSONA["server_header"]
    page = (
        "<html>\r\n<head><title>404 Not Found</title></head>\r\n<body>\r\n"
        "<center><h1>404 Not Found</h1></center>\r\n"
        f"<hr><center>{server}</center>\r\n</body>\r\n</html>\r\n"
    )
    return HTMLResponse(content=page, status_code=404)

@app.api_route("/{path_name:path}", methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def catch_all(request: Request, path_name: str):
    try:
        body_str = await read_capped_body(request)
    except Exception:
        body_str = "[Unreadable Body]"

    endpoint = f"/{path_name}"
    await log_interaction(request, body_str, endpoint)

    # Protected-looking areas answer like an app behind auth; everything else like nginx
    if endpoint.startswith(AUTH_PREFIXES):
        return JSONResponse({"message": "Unauthenticated."}, status_code=401)
    return nginx_404()
