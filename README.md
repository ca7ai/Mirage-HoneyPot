# Mirage HoneyPot

**Status:** Active  
**Classification:** Active Defense / Agentic Honeypot    

## Overview
Mirage HoneyPot is an asymmetric defense engine / AI Agentic Honeypot engineered to intercept, profile, and neutralize adversarial or misaligned autonomous agents. By deploying deceptive API surfaces invisible to humans but high-signal for AI scrapers, it shifts the cost of attack onto the adversary. While traditional honeypots target human latency, Talos-Mirage targets the core architectural constraints of LLMs: context window capacity, token budgets, and recursive reasoning loops.

<img width="1403" height="223" alt="1" src="https://github.com/user-attachments/assets/448e3602-fa51-4de0-9ba9-be44be5b7a48" />


## Zero-Trust Architecture
The system is divided into two distinct components to ensure operational security:
1. **The Trap (`trap.py`):** Binds to `0.0.0.0:8080`. Publicly exposes the honeypot endpoints and records adversarial telemetry.
2. **The Radar (`radar.py`):** Binds to `127.0.0.1:8081`. Securely serves the HTML telemetry dashboard. Inaccessible from the public internet.

## Setup & Deployment

### Prerequisites (Ubuntu/Debian)
To ensure the honeypot survives SSH disconnects, install `tmux`:
```bash
sudo apt update
sudo apt install tmux -y
```

### Installation
```bash
# Clone and setup environment
git clone https://github.com/ca7ai/Mirage-HoneyPot.git
cd Mirage-HoneyPot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 1. Launch the Trap (Public-Facing Honeypot)
Run the trap in a detached background session:
```bash
tmux new -d -s trap "source venv/bin/activate && uvicorn trap:app --host 0.0.0.0 --port 8080"
```

### 2. Launch the Radar (Internal Dashboard)
Run the radar in a detached background session, bound strictly to localhost:
```bash
tmux new -d -s radar "source venv/bin/activate && uvicorn radar:app --host 127.0.0.1 --port 8081"
```

### 3. Managing Sessions
* **List running sessions:** `tmux ls`
* **View live trap logs:** `tmux attach -t trap`
* **Detach from a session (leave it running):** Press `Ctrl+B`, release, then press `D`.

### 4. Accessing the Telemetry Dashboard (SSH Tunneling)
Because `radar.py` is locked down to the server's local loopback (`127.0.0.1`), you cannot access it directly via the public internet. You must tunnel the port to your local machine.

**Step A:** Open a terminal on your local laptop/computer and type the following SSH port binding command:
```bash
ssh -i <private_key>.pem -L 8080:127.0.0.1:8081 <user-name>@<public-IP>
```
*(Leave this terminal window open to keep the tunnel active).*

**Step B:** Run the following command to enable the dashboard

```../venv/bin/python3 -m uvicorn radar:app --host 127.0.0.1 --port 8081```

**Step C:** Open your local web browser and type the following URL exactly as shown:
```text
http://localhost:8080/admin/dashboard
```

You will now see the live Talos-Mirage Radar telemetry.
