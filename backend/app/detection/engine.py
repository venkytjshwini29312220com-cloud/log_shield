"""Rule evaluation engine for LogShield (Phase 5).

Evaluates ingested events against registered detection rules, assigns
sequential alert IDs (ALT-0001), and persists alerts to SQLite.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.detection.rules import BaseRule, get_default_rules
from app.models.orm import Alert, Event


def generate_next_alert_ids(session: Session, count: int = 1) -> list[str]:
    """Generate sequential, collision-free alert identifiers (e.g. ALT-0001)."""
    stmt = select(Alert.alert_id).where(Alert.alert_id.like("ALT-%"))
    existing_ids = session.scalars(stmt).all()

    max_num = 0
    for aid in existing_ids:
        suffix = aid[4:]
        if suffix.isdigit():
            max_num = max(max_num, int(suffix))

    allocated: list[str] = []
    current = max_num
    for _ in range(count):
        current += 1
        candidate = f"ALT-{current:04d}"
        while session.get(Alert, candidate) is not None:
            current += 1
            candidate = f"ALT-{current:04d}"
        allocated.append(candidate)
    return allocated


class RuleEngine:
    """Manages rules and evaluates events against them."""

    def __init__(self, rules: list[BaseRule] | None = None) -> None:
        self.rules: list[BaseRule] = rules if rules is not None else get_default_rules()

    def evaluate_event(self, session: Session, event: Event) -> list[Alert]:
        """Evaluate an individual event against all active rules."""
        triggered: list[dict[str, Any]] = []

        for rule in self.rules:
            result = rule.evaluate(session, event)
            if result:
                triggered.append(result)

        if not triggered:
            return []

        alert_ids = generate_next_alert_ids(session, count=len(triggered))
        now = datetime.now(timezone.utc)
        created_alerts: list[Alert] = []

        for aid, data in zip(alert_ids, triggered):
            alert = Alert(
                alert_id=aid,
                created_at=now,
                source="rule",
                severity=data["severity"],
                title=data["title"],
                message=data["message"],
                event_id=event.event_id,
                incident_id=None,
                extras=data.get("extras", {}),
            )
            session.add(alert)
            session.flush()
            created_alerts.append(alert)

        return created_alerts

    def evaluate_batch(self, session: Session, events: list[Event]) -> list[Alert]:
        """Sequentially evaluate a batch of newly stored events."""
        all_alerts: list[Alert] = []
        for event in events:
            alerts = self.evaluate_event(session, event)
            all_alerts.extend(alerts)
        return all_alerts

    def list_rules(self) -> list[dict[str, Any]]:
        """Return metadata list of all configured detection rules."""
        return [rule.to_dict() for rule in self.rules]


# Global singleton instance with default rules
default_rule_engine = RuleEngine()
