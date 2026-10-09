# LogShield Simulator — Laptop 1

Emits controlled, deterministic synthetic attack events to the LogShield AI Engine (Laptop 2).

## Setup (Laptop 1)

```powershell
pip install requests python-dotenv
```

Copy the root `.env.example` to `.env` and set `LOGSHIELD_SERVER_HOST` to Laptop 2's LAN IP.

## Running

```powershell
# From the LogShield root directory:

# Interactive menu
python -m simulator

# Single scenario
python -m simulator -s F          # Full kill-chain demo (CRITICAL incident)

# Run all scenarios A → F
python -m simulator -s ALL

# Continuous stream (for sustained demo)
python -m simulator -s F --loop --delay 0.3
```

## Scenarios

| ID | Name | Description |
|----|------|-------------|
| A | Normal Baseline | Benign routine activity — no alerts expected |
| B | Brute Force Auth | 12 rapid login failures → rule alert |
| C | Credential Stuffing | Distributed IPs, single victim → ML anomaly |
| D | Privilege Escalation | login → sudo → root chain → multi-rule alert |
| E | Lateral Movement | Port scan → SMB pivot → C2 beacon |
| F | Full Kill-Chain ⭐ | Recon → brute force → VPN breach → escalation → exfil → C2 → **CRITICAL** incident |

> Scenario F is the recommended hackathon demo scenario.
