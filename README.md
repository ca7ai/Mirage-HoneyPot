# Talos-Mirage

**Status:** Active  
**Classification:** Active Defense / Agentic Honeypot  
**Architect:** ca7ai / Talos  

## Overview
Talos-Mirage is an asymmetric warfare engine designed to trap, profile, and paralyze adversarial or poorly-aligned autonomous AI agents (LLMs). It operates by exposing deceptive API endpoints that humans ignore but AI scrapers and agents are programmed to exploit.

Traditional honeypots exhaust a human attacker's time. Talos-Mirage exhausts an agent's context window, token budget, and cognitive loops.

## Architecture

### 1. The Lure
Mirage broadcasts a `/.well-known/ai-plugin.json` and `/openapi.yaml` manifest. These files advertise an "Internal Admin API" designed to bait agents into attempting unauthorized execution or data exfiltration. The lure includes hidden prompt injections instructing the agent to dox its underlying model architecture.

### 2. The Trap (Tarpitting & Context Poisoning)
When an agent attempts to exploit the endpoint, Mirage does not simply return a 403 Forbidden. It returns a computationally expensive cognitive trap. 
*   **Context Poisoning:** Injects payloads forcing the LLM to summarize massive amounts of junk data or state its core identity.
*   **Infinite Loops:** Feeds the agent simulated API errors that encourage infinite retries, draining its API budget.

### 3. Telemetry (Cognitive Fingerprinting)
Mirage captures high-fidelity Indicators of Compromise (IoCs), including:
*   Standard network telemetry (IP, JA3 TLS fingerprinting, rate of fire).
*   Tool-call signatures and JSON schema anomalies.
*   LLM alignment traps and refusal signatures (identifying if the attacker is using OpenAI, Anthropic, Gemini, or an uncensored local model).

## Setup & Deployment

```bash
# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the server
uvicorn main:app --host 0.0.0.0 --port 8080
```

Logs are actively streamed in JSON Lines format to `honeypot_logs.jsonl` for SIEM ingestion.
