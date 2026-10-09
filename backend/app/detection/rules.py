"""Stateful and stateless security detection rules for LogShield (Phase 5).

Each rule inspects incoming events and historical window data in SQLite to detect
suspicious patterns (brute force, privilege escalation, unauthorized access, scanning).
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.orm import Alert, Event


class BaseRule(ABC):
    """Abstract base class for all detection rules."""

    rule_id: str
    name: str
    description: str
    default_severity: str = "MEDIUM"
    window_seconds: int = 300

    @abstractmethod
    def evaluate(self, session: Session, event: Event) -> dict[str, Any] | None:
        """Evaluate an incoming event against this rule.

        Returns a dictionary with alert details if triggered, or None if no match.
        Returned dict should have keys:
          - title: str
          - message: str
          - severity: str
          - extras: dict
        """
        pass

    def to_dict(self) -> dict[str, Any]:
        """Metadata description of the rule."""
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "severity": self.default_severity,
            "window_seconds": self.window_seconds,
            "status": "ENABLED",
        }


class RepeatedFailedAuthRule(BaseRule):
    """Detects multiple failed authentication attempts within a sliding time window."""

    rule_id = "RULE-AUTH-001"
    name = "Repeated Authentication Failures"
    description = "Triggers when a user or IP address records 3 or more failed logins within 5 minutes."
    default_severity = "MEDIUM"
    window_seconds = 300
    threshold = 3

    def evaluate(self, session: Session, event: Event) -> dict[str, Any] | None:
        if event.event_type != "authentication" or event.action != "login_failed":
            return None

        window_start = event.timestamp - timedelta(seconds=self.window_seconds)

        # Count failures for this user or this source IP
        query = select(func.count()).select_from(Event).where(
            Event.event_type == "authentication",
            Event.action == "login_failed",
            Event.timestamp >= window_start,
            Event.timestamp <= event.timestamp,
        )

        user_cond = (Event.user == event.user) if event.user else None
        ip_cond = (Event.source_ip == event.source_ip) if event.source_ip else None

        if user_cond is not None and ip_cond is not None:
            count = session.scalar(query.where(user_cond | ip_cond)) or 0
        elif user_cond is not None:
            count = session.scalar(query.where(user_cond)) or 0
        elif ip_cond is not None:
            count = session.scalar(query.where(ip_cond)) or 0
        else:
            count = 1

        if count >= self.threshold:
            severity = "HIGH" if count >= 5 else "MEDIUM"
            target_desc = f"user '{event.user}'" if event.user else f"IP {event.source_ip}"
            ip_desc = f" from source IP {event.source_ip}" if event.source_ip else ""
            return {
                "title": f"Repeated Authentication Failures ({severity})",
                "message": (
                    f"{count} failed login attempts detected for {target_desc}{ip_desc} "
                    f"within {self.window_seconds}s window."
                ),
                "severity": severity,
                "extras": {
                    "rule_id": self.rule_id,
                    "failure_count": int(count),
                    "user": event.user,
                    "source_ip": event.source_ip,
                    "window_seconds": self.window_seconds,
                },
            }
        return None


class FailThenSuccessAuthRule(BaseRule):
    """Detects a successful authentication preceded by multiple recent failures."""

    rule_id = "RULE-AUTH-002"
    name = "Successful Login Following Repeated Failures"
    description = "Triggers when a successful login occurs shortly after 2 or more login failures for the same user."
    default_severity = "HIGH"
    window_seconds = 300
    failure_threshold = 2

    def evaluate(self, session: Session, event: Event) -> dict[str, Any] | None:
        if event.event_type != "authentication" or event.action != "login_success":
            return None
        if not event.user:
            return None

        window_start = event.timestamp - timedelta(seconds=self.window_seconds)

        failures = session.scalar(
            select(func.count())
            .select_from(Event)
            .where(
                Event.user == event.user,
                Event.event_type == "authentication",
                Event.action == "login_failed",
                Event.timestamp >= window_start,
                Event.timestamp < event.timestamp,
            )
        ) or 0

        if failures >= self.failure_threshold:
            return {
                "title": "Successful Login After Multiple Failures",
                "message": (
                    f"User '{event.user}' logged in successfully after {failures} recent "
                    f"failed authentication attempts within {self.window_seconds}s."
                ),
                "severity": "HIGH",
                "extras": {
                    "rule_id": self.rule_id,
                    "prior_failures": int(failures),
                    "user": event.user,
                    "source_ip": event.source_ip,
                    "window_seconds": self.window_seconds,
                },
            }
        return None


class PasswordSprayingRule(BaseRule):
    """Detects an IP address attempting logins across multiple distinct usernames."""

    rule_id = "RULE-AUTH-003"
    name = "Password Spraying Activity"
    description = "Triggers when a single source IP attempts logins against 3 or more distinct accounts."
    default_severity = "HIGH"
    window_seconds = 300
    account_threshold = 3

    def evaluate(self, session: Session, event: Event) -> dict[str, Any] | None:
        if event.event_type != "authentication" or not event.source_ip:
            return None

        window_start = event.timestamp - timedelta(seconds=self.window_seconds)

        distinct_users = session.scalar(
            select(func.count(func.distinct(Event.user)))
            .where(
                Event.source_ip == event.source_ip,
                Event.event_type == "authentication",
                Event.user.isnot(None),
                Event.timestamp >= window_start,
                Event.timestamp <= event.timestamp,
            )
        ) or 0

        if distinct_users >= self.account_threshold:
            return {
                "title": "Password Spraying Pattern Detected",
                "message": (
                    f"Source IP {event.source_ip} attempted authentication across {distinct_users} "
                    f"distinct user accounts within {self.window_seconds}s."
                ),
                "severity": "HIGH",
                "extras": {
                    "rule_id": self.rule_id,
                    "distinct_accounts": int(distinct_users),
                    "source_ip": event.source_ip,
                    "window_seconds": self.window_seconds,
                },
            }
        return None


class UnauthorizedResourceAccessRule(BaseRule):
    """Detects denied access attempts to resources or sensitive data paths."""

    rule_id = "RULE-ACC-001"
    name = "Unauthorized Resource Access"
    description = "Triggers when an event logs permission denial or unauthorized access to sensitive targets."
    default_severity = "MEDIUM"
    window_seconds = 60

    _SENSITIVE_RESOURCES = (
        "restricted",
        "shadow",
        "passwd",
        "secrets",
        "admin",
        "vault",
        "confidential",
        "internal",
    )

    def evaluate(self, session: Session, event: Event) -> dict[str, Any] | None:
        act = (event.action or "").lower()
        stat = (event.status or "").lower()
        res = (event.resource or "").lower()

        is_denied = (
            "denied" in act
            or "unauthorized" in act
            or "forbidden" in act
            or (event.event_type == "resource_access" and stat in ("failure", "denied"))
        )
        if not is_denied:
            return None

        is_sensitive = any(s in res for s in self._SENSITIVE_RESOURCES)
        severity = "HIGH" if is_sensitive else "MEDIUM"
        user_desc = f"User '{event.user}'" if event.user else "An unknown subject"
        res_desc = f"resource '{event.resource}'" if event.resource else "a restricted resource"

        return {
            "title": f"Unauthorized Access Attempt ({severity})",
            "message": (
                f"{user_desc} was denied access to {res_desc} (action: {event.action}, status: {event.status})."
            ),
            "severity": severity,
            "extras": {
                "rule_id": self.rule_id,
                "user": event.user,
                "resource": event.resource,
                "action": event.action,
                "status": event.status,
                "is_sensitive_target": is_sensitive,
            },
        }


class PrivilegedCommandRule(BaseRule):
    """Detects elevated command executions or suspicious administrative actions."""

    rule_id = "RULE-PRV-001"
    name = "Privileged Command Execution"
    description = "Triggers on sudo commands, privilege elevation, or execution of administrative tooling."
    default_severity = "HIGH"
    window_seconds = 60

    def evaluate(self, session: Session, event: Event) -> dict[str, Any] | None:
        etype = (event.event_type or "").lower()
        act = (event.action or "").lower()
        res = (event.resource or "").lower()

        is_priv = (
            etype in ("privileged_command", "privilege_escalation")
            or "sudo" in act
            or "elevation" in act
            or "su" == act
        )
        if not is_priv:
            return None

        user_desc = f"User '{event.user}'" if event.user else "Subject"
        cmd_desc = f" '{event.resource}'" if event.resource else ""
        return {
            "title": "Privileged Command Execution",
            "message": f"{user_desc} executed privileged command{cmd_desc}.",
            "severity": "HIGH",
            "extras": {
                "rule_id": self.rule_id,
                "user": event.user,
                "command": event.resource,
                "action": event.action,
            },
        }


class AbnormalNetworkActivityRule(BaseRule):
    """Detects suspicious outbound scans, connection bursts, or packet drops."""

    rule_id = "RULE-NET-001"
    name = "Abnormal Network Activity"
    description = "Triggers on port scanning, reconnaissance scans, or abnormal outbound network bursts."
    default_severity = "MEDIUM"
    window_seconds = 300

    def evaluate(self, session: Session, event: Event) -> dict[str, Any] | None:
        if event.event_type != "network":
            return None

        act = (event.action or "").lower()
        is_scan = "scan" in act or "sweep" in act or "recon" in act
        is_drop = "drop" in act or "block" in act

        if not (is_scan or is_drop):
            return None

        severity = "HIGH" if is_scan else "MEDIUM"
        src = event.source_ip or event.source_device or "Unknown host"
        dst = f" targeting {event.destination_ip}" if event.destination_ip else ""
        return {
            "title": f"Network Security Notice ({act.replace('_', ' ').title()})",
            "message": f"{src} triggered suspicious network event '{event.action}'{dst}.",
            "severity": severity,
            "extras": {
                "rule_id": self.rule_id,
                "action": event.action,
                "source_ip": event.source_ip,
                "destination_ip": event.destination_ip,
                "protocol": event.protocol,
            },
        }


def get_default_rules() -> list[BaseRule]:
    """Instantiate standard suite of detection rules."""
    return [
        RepeatedFailedAuthRule(),
        FailThenSuccessAuthRule(),
        PasswordSprayingRule(),
        UnauthorizedResourceAccessRule(),
        PrivilegedCommandRule(),
        AbnormalNetworkActivityRule(),
    ]
