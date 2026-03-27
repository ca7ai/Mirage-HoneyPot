
# 🍯 Mirage-HoneyPot
## Asymmetric Defense Engine & AI Agentic Trap

Mirage-HoneyPot is an asymmetric defense engine engineered to intercept, profile, and neutralize adversarial or misaligned autonomous agents. By deploying deceptive API surfaces invisible to humans but high-signal for AI scrapers, it shifts the cost of attack onto the adversary.

While traditional honeypots target human latency, Mirage-HoneyPot targets the core architectural constraints of LLMs: context window capacity, token budgets, and recursive reasoning loops.

## 🏗️ Zero-Trust Architecture

The system is divided into two distinct components to ensure operational security and process isolation:

    The Trap (trap.py): The public-facing sensor. Binds to 0.0.0.0:80. It exposes deceptive endpoints and records high-fidelity adversarial telemetry.

    The Radar (radar.py): The internal analytics engine. Binds to 127.0.0.1:8081. Securely serves the HTML telemetry dashboard and is inaccessible from the public internet.

## 🚀 Setup & Deployment
### 1.  Installation
```
# Clone and setup environment
git clone https://github.com/ca7ai/Mirage-HoneyPot.git
cd Mirage-HoneyPot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Persistent Service Deployment (systemd)

To ensure the HoneyPot survives reboots and SSH disconnects, deploy both components as system services.

#### Deploy the Trap:
```sudo vi /etc/systemd/system/mirage-honeypot.service```
```
[Unit]
Description=Mirage HoneyPot Trap (Port 80)
After=network.target

[Service]
User=root
WorkingDirectory=/home/ubuntu/Mirage-HoneyPot
ExecStart=/home/ubuntu/Mirage-HoneyPot/venv/bin/python3 -m uvicorn trap:app --host 0.0.0.0 --port 80
Restart=always

[Install]
WantedBy=multi-user.target
```

#### Deploy the Radar:

```sudo vi /etc/systemd/system/mirage-radar.service```

```
[Unit]
Description=Mirage Radar Dashboard (Port 8081)
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/Mirage-HoneyPot
ExecStart=/home/ubuntu/Mirage-HoneyPot/venv/bin/python3 -m uvicorn radar:app --host 127.0.0.1 --port 8081
Restart=always

[Install]
WantedBy=multi-user.target
```

#### Enable & Start Services:
```
sudo systemctl daemon-reload
sudo systemctl enable mirage-honeypot mirage-radar
sudo systemctl start mirage-honeypot mirage-radar
```

### 📊 Accessing the Telemetry Radar

Because radar.py is locked to the local loopback (127.0.0.1), it is invisible to the public internet. Access requires a secure SSH tunnel.

#### Step A: Establish the Secure Tunnel

Run this on your local machine (Laptop):

```
ssh -i <your-key>.pem -L 8081:127.0.0.1:8081 ubuntu@<EC2-Public-IP>
```

#### Step B: View the Dashboard

Open your local browser and navigate to:

```
http://localhost:8081/admin/dashboard
```

### ⚖️ Legal & Ethical Use

This data is provided "as-is" for defensive security research. All telemetry originates from unsolicited traffic targeting unadvertised, non-production infrastructure. Usage of captured IoCs should comply with local and international regulations.

###  License

This project is licensed under the MIT License.
