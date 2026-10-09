from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.orm import SystemStatus, User


def seed_defaults(session: Session) -> None:
    if session.scalar(select(User).where(User.username == "analyst")) is None:
        session.add(
            User(
                user_id="USR-001",
                username="analyst",
                display_name="SOC Analyst",
                role="analyst",
            )
        )

    now = datetime.now(timezone.utc)
    defaults = {
        "api": ("ONLINE", "FastAPI process accepting HTTP"),
        "database": ("ONLINE", "SQLite schema ready"),
        "log_collector": ("ONLINE", "Event ingestion and normalization pipeline active (POST /api/events)"),
        "ai_engine": ("ONLINE", "Hybrid detection active: Rule Engine (6 rules) + Isolation Forest anomaly detector"),
    }
    existing = {row.component: row for row in session.scalars(select(SystemStatus)).all()}
    for component, (status, detail) in defaults.items():
        row = existing.get(component)
        if row is None:
            session.add(SystemStatus(component=component, status=status, detail=detail, updated_at=now))
        else:
            row.status = status
            row.detail = detail
            row.updated_at = now


if __name__ == "__main__":
    from app.database.session import init_db

    init_db()
    print("Database schema created and default seed applied successfully.")
