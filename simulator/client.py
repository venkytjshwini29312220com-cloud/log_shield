"""
HTTP client to Laptop 2 — host/port from environment, never hard-coded.

Usage:
    python client.py                 # interactive scenario menu
    python client.py --scenario A    # single scenario
    python client.py --scenario ALL  # run A-F sequentially
    python client.py --scenario F --delay 0.3  # fast continuous demo
"""

import argparse
import os
import sys
import time

import requests
from dotenv import load_dotenv

# ------------------------------------------------------------------
# Load configuration from .env (copies the root .env if present)
# ------------------------------------------------------------------
_env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(_env_path, override=False)

SERVER_HOST = os.getenv('LOGSHIELD_SERVER_HOST', '127.0.0.1')
SERVER_PORT  = os.getenv('LOGSHIELD_SERVER_PORT', '8000')
BASE_URL     = f"http://{SERVER_HOST}:{SERVER_PORT}"

# ------------------------------------------------------------------
# Internal HTTP helpers
# ------------------------------------------------------------------

def post_event(payload: dict, verbose: bool = True) -> dict | None:
    """POST a single structured event to /api/events."""
    url = f"{BASE_URL}/api/events"
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        data = r.json()
        if verbose:
            eid  = data.get('event', {}).get('event_id', '?')
            aids = data.get('alert_ids', [])
            iids = data.get('incident_ids', [])
            flags = []
            if aids:  flags.append(f"alerts={','.join(aids)}")
            if iids:  flags.append(f"incidents={','.join(iids)}")
            suffix = f"  [{' | '.join(flags)}]" if flags else ''
            print(f"  ✓ {eid}  {payload.get('action')} [{payload.get('status')}]{suffix}")
        return data
    except requests.RequestException as exc:
        print(f"  ✗ POST failed: {exc}", file=sys.stderr)
        return None


def post_batch(payloads: list[dict], delay: float = 0.4, verbose: bool = True) -> None:
    """POST a list of events with a configurable inter-event delay."""
    for p in payloads:
        post_event(p, verbose=verbose)
        time.sleep(delay)
