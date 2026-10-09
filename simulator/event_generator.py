"""
Synthetic log factory for LogShield — deterministic multi-stage attack scenarios.

Each scenario returns a list of event dicts ready to POST to /api/events.
Timestamps are always ISO-8601 UTC, spread across a realistic time window.
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ts(offset_seconds: float = 0) -> str:
    return (_now() + timedelta(seconds=offset_seconds)).isoformat()


def _ip(subnet: str = "10.0.0") -> str:
    return f"{subnet}.{random.randint(2, 250)}"


def _uid() -> str:
    return str(uuid.uuid4())


# ------------------------------------------------------------------
# Scenario A — Normal Baseline Traffic (no alerts expected)
# ------------------------------------------------------------------
def scenario_a_normal(user: str = "analyst_user", count: int = 8) -> list[dict]:
    """Routine SOC analyst and operator activity — benign baseline."""
    actions = [
        ("resource_access", "file_open",        "success", "/reports/monthly.pdf"),
        ("resource_access", "api_query",         "success", "analytics-api"),
        ("authentication",  "login_success",     "success", "vpn-gateway"),
        ("resource_access", "dashboard_view",    "success", "soc-dashboard"),
        ("network",         "dns_lookup",        "success", "internal-dns"),
        ("resource_access", "export_csv",        "success", "log-archive"),
        ("authentication",  "logout",            "success", "vpn-gateway"),
        ("system",          "service_heartbeat", "success", "monitoring-agent"),
    ]
    events = []
    for i, (etype, action, status, resource) in enumerate(actions[:count]):
        events.append({
            "timestamp":   _ts(i * 15),
            "source_ip":   _ip(),
            "user":        user,
            "event_type":  etype,
            "action":      action,
            "status":      status,
            "resource":    resource,
            "protocol":    "https",
        })
    return events


# ------------------------------------------------------------------
# Scenario B — Brute Force Authentication (threshold alert)
# ------------------------------------------------------------------
def scenario_b_brute_force(attacker_ip: str = "203.0.113.99", target: str = "admin") -> list[dict]:
    """Rapid successive login failures from a single external IP — triggers rule engine alert."""
    events = []
    for i in range(12):
        events.append({
            "timestamp":  _ts(i * 5),
            "source_ip":  attacker_ip,
            "user":       target,
            "event_type": "authentication",
            "action":     "login_failed",
            "status":     "failure",
            "resource":   "bastion-host",
            "protocol":   "ssh",
            "metadata":   {"attempt": i + 1, "reason": "bad_password"},
        })
    return events


# ------------------------------------------------------------------
# Scenario C — Credential Stuffing (rotating IPs, single user)
# ------------------------------------------------------------------
def scenario_c_credential_stuffing(target_user: str = "jsmith") -> list[dict]:
    """Distributed auth failures across multiple source IPs against one account."""
    ips = ["198.51.100.{0}".format(i) for i in range(5, 15)]
    events = []
    for i, ip in enumerate(ips):
        events.append({
            "timestamp":  _ts(i * 8),
            "source_ip":  ip,
            "user":       target_user,
            "event_type": "authentication",
            "action":     "login_failed",
            "status":     "failure",
            "resource":   "web-portal",
            "protocol":   "https",
            "metadata":   {"tool": "credential_stuffer", "user_agent": "python-requests/2.31"},
        })
    return events


# ------------------------------------------------------------------
# Scenario D — Privilege Escalation Chain
# ------------------------------------------------------------------
def scenario_d_privilege_escalation(
    attacker_ip: str = "10.0.0.41",
    user: str = "jdoe",
) -> list[dict]:
    """Login → privilege check → sudo attempt → root exec chain — multi-rule match."""
    return [
        {
            "timestamp":  _ts(0),
            "source_ip":  attacker_ip,
            "user":       user,
            "event_type": "authentication",
            "action":     "login_success",
            "status":     "success",
            "resource":   "jump-server",
            "protocol":   "ssh",
        },
        {
            "timestamp":  _ts(5),
            "source_ip":  attacker_ip,
            "user":       user,
            "event_type": "privilege_escalation",
            "action":     "sudo_attempt",
            "status":     "success",
            "resource":   "/etc/sudoers",
            "protocol":   "local",
        },
        {
            "timestamp":  _ts(12),
            "source_ip":  attacker_ip,
            "user":       "root",
            "event_type": "privilege_escalation",
            "action":     "root_exec",
            "status":     "success",
            "resource":   "/bin/bash",
            "protocol":   "local",
            "metadata":   {"command": "id && cat /etc/shadow", "elevated": True},
        },
        {
            "timestamp":  _ts(20),
            "source_ip":  attacker_ip,
            "user":       "root",
            "event_type": "resource_access",
            "action":     "file_read",
            "status":     "success",
            "resource":   "/etc/shadow",
            "protocol":   "local",
            "metadata":   {"bytes_read": 2048},
        },
    ]


# ------------------------------------------------------------------
# Scenario E — Lateral Movement (port scan + SMB pivot)
# ------------------------------------------------------------------
def scenario_e_lateral_movement(
    attacker_ip: str = "10.0.0.88",
    user: str = "svc_account",
) -> list[dict]:
    """Internal recon port scan followed by SMB lateral movement."""
    events = [
        {
            "timestamp":  _ts(0),
            "source_ip":  attacker_ip,
            "user":       user,
            "event_type": "network",
            "action":     "port_scan",
            "status":     "success",
            "resource":   "10.0.0.0/24",
            "protocol":   "tcp",
            "metadata":   {"ports_scanned": 65535, "open_ports": [22, 445, 3389]},
        },
        {
            "timestamp":  _ts(10),
            "source_ip":  attacker_ip,
            "user":       user,
            "event_type": "network",
            "action":     "smb_connect",
            "status":     "success",
            "resource":   "10.0.0.50",
            "protocol":   "smb",
            "metadata":   {"share": r"\\10.0.0.50\C$"},
        },
        {
            "timestamp":  _ts(20),
            "source_ip":  attacker_ip,
            "user":       user,
            "event_type": "resource_access",
            "action":     "file_copy",
            "status":     "success",
            "resource":   r"\\10.0.0.50\C$\Windows\Temp\payload.exe",
            "protocol":   "smb",
            "metadata":   {"bytes_transferred": 524288},
        },
        {
            "timestamp":  _ts(30),
            "source_ip":  "10.0.0.50",
            "user":       user,
            "event_type": "network",
            "action":     "c2_beacon",
            "status":     "failure",
            "resource":   "203.0.113.50:4444",
            "protocol":   "tcp",
            "metadata":   {"connection_refused": True},
        },
    ]
    return events


# ------------------------------------------------------------------
# Scenario F — Full Kill-Chain: Multi-stage Credential Compromise
# ------------------------------------------------------------------
def scenario_f_kill_chain(
    attacker_ip: str = "198.51.100.7",
    internal_ip: str = "10.0.0.42",
    victim: str = "alice",
    admin_user: str = "admin",
) -> list[dict]:
    """
    Complete correlated multi-stage incident:
    Recon → Brute force → VPN breach → Lateral move → Data exfil.
    This is the primary hackathon demo scenario — should produce a CRITICAL incident.
    """
    return [
        # Stage 1: Recon
        {
            "timestamp":  _ts(-120),
            "source_ip":  attacker_ip,
            "user":       "anonymous",
            "event_type": "network",
            "action":     "port_scan",
            "status":     "success",
            "resource":   "10.0.0.0/24",
            "protocol":   "tcp",
            "metadata":   {"stage": "recon", "open_ports": [22, 80, 443, 3389, 8000]},
        },
        # Stage 2: Brute force (3 failures)
        {
            "timestamp":  _ts(-90),
            "source_ip":  attacker_ip,
            "user":       victim,
            "event_type": "authentication",
            "action":     "login_failed",
            "status":     "failure",
            "resource":   "vpn-gateway",
            "protocol":   "https",
            "metadata":   {"stage": "initial_access", "attempt": 1},
        },
        {
            "timestamp":  _ts(-85),
            "source_ip":  attacker_ip,
            "user":       victim,
            "event_type": "authentication",
            "action":     "login_failed",
            "status":     "failure",
            "resource":   "vpn-gateway",
            "protocol":   "https",
            "metadata":   {"stage": "initial_access", "attempt": 2},
        },
        {
            "timestamp":  _ts(-80),
            "source_ip":  attacker_ip,
            "user":       victim,
            "event_type": "authentication",
            "action":     "login_failed",
            "status":     "failure",
            "resource":   "vpn-gateway",
            "protocol":   "https",
            "metadata":   {"stage": "initial_access", "attempt": 3},
        },
        # Stage 3: Successful compromise
        {
            "timestamp":  _ts(-70),
            "source_ip":  attacker_ip,
            "user":       victim,
            "event_type": "authentication",
            "action":     "login_success",
            "status":     "success",
            "resource":   "vpn-gateway",
            "protocol":   "https",
            "metadata":   {"stage": "initial_access", "mfa_bypassed": True},
        },
        # Stage 4: Privilege escalation
        {
            "timestamp":  _ts(-55),
            "source_ip":  attacker_ip,
            "user":       victim,
            "event_type": "privilege_escalation",
            "action":     "sudo_attempt",
            "status":     "success",
            "resource":   "/usr/bin/python3",
            "protocol":   "local",
            "metadata":   {"stage": "privilege_escalation"},
        },
        # Stage 5: Internal lateral movement
        {
            "timestamp":  _ts(-40),
            "source_ip":  attacker_ip,
            "user":       victim,
            "event_type": "network",
            "action":     "smb_connect",
            "status":     "success",
            "resource":   internal_ip,
            "protocol":   "smb",
            "metadata":   {"stage": "lateral_movement", "share": r"\\10.0.0.42\ADMIN$"},
        },
        # Stage 6: Data exfiltration
        {
            "timestamp":  _ts(-20),
            "source_ip":  internal_ip,
            "user":       victim,
            "event_type": "resource_access",
            "action":     "file_download",
            "status":     "success",
            "resource":   "s3://confidential-hr-data/employees.csv",
            "protocol":   "https",
            "metadata":   {
                "stage": "exfiltration",
                "bytes_transferred": 10485760,
                "destination": attacker_ip,
            },
        },
        # Stage 7: C2 beaconing
        {
            "timestamp":  _ts(-5),
            "source_ip":  internal_ip,
            "user":       victim,
            "event_type": "network",
            "action":     "c2_beacon",
            "status":     "success",
            "resource":   f"{attacker_ip}:4444",
            "protocol":   "tcp",
            "metadata":   {"stage": "c2", "interval_seconds": 60, "encrypted": True},
        },
    ]


# ------------------------------------------------------------------
# Registry
# ------------------------------------------------------------------
SCENARIOS: dict[str, tuple[str, callable]] = {
    "A": ("Normal Baseline Traffic (benign, no alerts expected)", scenario_a_normal),
    "B": ("Brute Force Authentication (rapid login failures)",     scenario_b_brute_force),
    "C": ("Credential Stuffing (distributed IPs, one victim)",     scenario_c_credential_stuffing),
    "D": ("Privilege Escalation Chain (sudo → root)",              scenario_d_privilege_escalation),
    "E": ("Lateral Movement (port scan → SMB pivot → C2 fail)",    scenario_e_lateral_movement),
    "F": ("Full Kill-Chain — Credential Compromise Demo (CRITICAL)", scenario_f_kill_chain),
}
