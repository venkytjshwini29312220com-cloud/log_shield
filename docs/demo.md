# Hackathon demonstration (target)

Target length: **2–3 minutes**. Full polish is Phase 15. This is the story the architecture must support.

## Preconditions

1. All three laptops on the same LAN.
2. Laptop 2 engine `ONLINE`.
3. Laptop 3 dashboard open.
4. Laptop 1 simulator ready; Scenario F labeled **Credential Compromise Scenario**.

## Script

1. Show System Status: System / AI Engine / Log Collector **ONLINE**.
2. Trigger Scenario F from Laptop 1.
3. Laptop 3 Live Events: events stream in real time.
4. Severity / current risk moves LOW → MEDIUM → HIGH, then after correlation **CRITICAL**.
5. Incident **INC-1042** (or next sequential ID) appears — **one** incident, not six.
6. Open investigation: auto timeline, **Risk Score: 94/100** (or computed equivalent), “Why was this detected?”, recommended response.

## What judges should hear

> LogShield does not simply detect suspicious logs. It connects individual events, understands their relationship, reconstructs potential security incidents, and gives security analysts an explainable risk assessment.
