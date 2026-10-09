# LogShield event simulator (Laptop 1)

Produces **synthetic** system/network/security events and POSTs them to Laptop 2.

**Phase 1:** layout only. Generators and HTTP client come with later phases.

## Safety

- Predefined scenarios only
- No targeting of real hosts
- No command execution
- No exploit payloads

## Scenarios (planned)

| ID | File | Description |
|----|------|-------------|
| A | `scenarios/normal.py` | Baseline activity |
| B | `scenarios/failed_auth.py` | Repeated login failures |
| C | `scenarios/fail_then_success.py` | Failures then success |
| D | `scenarios/resource_access.py` | Suspicious resource access |
| E | `scenarios/network.py` | Abnormal network behavior |
| F | `scenarios/credential_compromise.py` | Correlated multi-stage demo |

Target URL: `http://$LOGSHIELD_SERVER_HOST:$LOGSHIELD_SERVER_PORT/api/events`
