"""REST routers: events, incidents, alerts, statistics, health."""

from app.api import alerts, events, health, incidents, statistics

__all__ = ["alerts", "events", "health", "incidents", "statistics"]
