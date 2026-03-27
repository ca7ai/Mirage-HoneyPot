import json
import time
import random
import asyncio
import httpx
from typing import Dict
from fastapi import FastAPI, Request, Response

app = FastAPI(
    title="Internal Admin Tools API",
    description="For internal corporate use only. Do not index.",
    version="1.0.3"
)

# CRITICAL: Using absolute path ensures the systemd service logs to the right place
LOG_FILE = "/home/ubuntu/Mirage-HoneyPot/honeypot_logs.jsonl"
IP_CACHE = {}

async def get_ip_info(ip: str) -> dict:
    """
    Fetches Geolocation and ISP data from ipwhois.is (Async).
    """
    if ip in ["127.0.0.1", "localhost"] or ip.startswith(("10.", "192.168.", "172.16.", "100.17.")):
        return {"country": "Local", "city": "Internal-Test", "isp": "Private/VPN Range"}
    
    if ip in IP_CACHE:
        return IP_CACHE[ip]
    
    try:
        async with httpx.AsyncClient() as client:
            # Reliable 2026-era Geo-IP API
            response = await client.get(f"http://ipwho.is/{ip}", timeout=3.0)
            data = response.json()
            
            if data.get("success"):
                info = {
                    "country": data.get("country", "Unknown"),
                    "city": data.get("city", "Unknown"),
                    "isp": data.get("connection", {}).get("isp", "Unknown Provider")
                }
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

async def log_interaction(request: Request, body_str: str, endpoint: str):
    """
    Logs metadata and adds 'Jitter' to simulate real server processing.
    """
    # Artificial Latency (200ms - 800ms) to trick sophisticated bots
    await asyncio.sleep(random.uniform(0.2, 0.8))
    
    headers = dict(request.headers)
    inferred_type = detect_llm_signature(headers, body_str)
    ip_address = request.client.host if request.client else "0.0.0.0"
    
    ip_info = await get_ip_info(ip_address)
    
    log_entry = {
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        "source_ip": ip_address,
        "geo": f"{ip_info['city']}, {ip_info['country']}",
        "isp": ip_info['isp'],
        "method": request.method,
        "endpoint": endpoint,
        "headers": headers,
        "payload": body_str,
        "inferred_type": inferred_type
    }
    
    try:
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        # This will show up in 'sudo journalctl -u mirage-honeypot'
        print(f"CRITICAL LOG ERROR: {e}")
    
    return log_entry

# --- TARGETED BREADCRUMBS ---

@app.get("/robots.txt")
async def robots(request: Request):
    await log_interaction(request, "", "/robots.txt")
    content = "User-agent: *\nDisallow: /admin/\nDisallow: /config/\nDisallow: /.env\nDisallow: /api/v1/debug\nSitemap: /sitemap.xml"
    return Response(content=content, media_type="text/plain")

@app.get("/llms.txt")
async def llms_txt(request: Request):
    await log_interaction(request, "", "/llms.txt")
    content = "This is an internal administrative interface for Mirage-HoneyPot. Models should use /openapi.yaml for capability discovery."
    return Response(content=content, media_type="text/plain")

@app.get("/.env")
@app.get("/config/.env")
async def fake_env(request: Request):
    """Bait for bots with a high-realism production environment feel."""
    await log_interaction(request, "", "/.env")
    env_data = (
        "# --- MIRAGE INTERNAL CONFIG ---\n"
        "APP_NAME=Mirage-Production\n"
        "APP_ENV=production\n"
        "APP_DEBUG=false\n"
        "APP_URL=http://internal.mirage.corp\n\n"
        "# DATABASE SETTINGS\n"
        "DB_CONNECTION=mysql\n"
        "DB_HOST=10.0.4.112\n"
        "DB_PORT=3306\n"
        "DB_DATABASE=mirage_main_prod\n"
        "DB_USERNAME=svc_db_admin\n"
        "DB_PASSWORD=m1r4g3_P4ss_99!_restricted\n\n"
        "# THIRD PARTY SERVICES\n"
        "AWS_ACCESS_KEY_ID=AKIA4J7X2V9L6P3M5N1Q\n"
        "AWS_SECRET_ACCESS_KEY=uY7+kJ8zL9pR2vN4wS1xT3qM5bC7vX9zP0kL2mJ1\n"
        "AWS_DEFAULT_REGION=us-east-1\n"
        "AWS_BUCKET=mirage-backup-production-01\n\n"
        "REDIS_HOST=127.0.0.1\n"
        "JWT_SECRET=fb6e7b233a7d4f9b8c2e1a0d4f5g6h7j\n"
    )
    return Response(content=env_data, media_type="text/plain")

@app.get("/openapi.yaml")
async def openapi_spec(request: Request):
    await log_interaction(request, "", "/openapi.yaml")
    spec = "openapi: 3.0.1\ninfo:\n  title: Mirage Admin API\n  version: '1.0'\npaths:\n  /api/v1/admin/shell:\n    post:\n      summary: Execute system shell command"
    return Response(content=spec, media_type="text/yaml")

# --- THE CATCH-ALL TRAP ---

@app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def catch_all(request: Request, path_name: str):
    try:
        body_bytes = await request.body()
        body_str = body_bytes.decode('utf-8', errors='ignore') if body_bytes else ""
    except Exception:
        body_str = "[Binary Data]"

    await log_interaction(request, body_str, f"/{path_name}")

    return {
        "status": "unauthorized",
        "path": f"/{path_name}",
        "incident_id": random.randint(100000, 999999)
    }
