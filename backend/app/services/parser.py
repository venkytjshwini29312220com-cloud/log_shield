"""Log parser and normalization engine for LogShield (Phase 4).

Converts raw strings (Syslog, CEF, Key-Value, JSON, Web logs) or dictionary payloads
into the canonical normalized event schema.
"""

from datetime import datetime, timezone
import json
import re
from typing import Any

# Aliases mapped to canonical fields
_FIELD_ALIASES: dict[str, list[str]] = {
    "source_ip": ["src_ip", "src", "source", "client_ip", "ip", "clientip", "s_ip"],
    "destination_ip": ["dst_ip", "dst", "dest", "target_ip", "destination", "d_ip", "server_ip"],
    "user": ["username", "suser", "duser", "usr", "account", "login_user", "identity"],
    "event_type": ["type", "category", "cat", "event_class"],
    "action": ["act", "operation", "event", "activity", "action_name"],
    "status": ["result", "outcome", "disposition"],
    "resource": ["res", "target", "uri", "path", "service", "endpoint", "url", "file_path"],
    "protocol": ["proto", "protocol_name", "scheme"],
    "source_device": ["device", "hostname", "host", "shost", "dhost", "host_name", "computer_name"],
    "timestamp": ["time", "datetime", "date", "@timestamp", "event_time", "log_time"],
    "event_id": ["id", "uuid", "evt_id"],
}

# Reverse lookup for known alias keys
_ALL_ALIAS_KEYS = {alias for aliases in _FIELD_ALIASES.values() for alias in aliases}
_CANONICAL_FIELDS = {
    "event_id",
    "timestamp",
    "source_ip",
    "destination_ip",
    "user",
    "event_type",
    "action",
    "status",
    "resource",
    "protocol",
    "source_device",
    "metadata",
    "raw",
}

# Sensitive keys to redact in metadata
_SENSITIVE_KEY_PATTERNS = re.compile(
    r"(password|passwd|secret|api[_\-]?key|token|auth[_\-]?token|bearer|private[_\-]?key)",
    re.IGNORECASE,
)

# Common CEF pattern
_CEF_PATTERN = re.compile(
    r"^CEF:\s*(?P<cef_version>\d+)\|(?P<vendor>[^|]*)\|(?P<product>[^|]*)\|"
    r"(?P<version>[^|]*)\|(?P<signature_id>[^|]*)\|(?P<name>[^|]*)\|"
    r"(?P<severity>[^|]*)\|(.*)$"
)

# Common Syslog patterns
_SYSLOG_RFC3164_PATTERN = re.compile(
    r"^(?:<(?P<pri>\d{1,3})>)?(?P<timestamp>[A-Z][a-z]{2}\s+\d+\s+\d{2}:\d{2}:\d{2})\s+"
    r"(?P<host>[^\s:]+)\s+(?P<tag>[^\[:\s]+)(?:\[(?P<pid>\d+)\])?:\s*(?P<message>.*)$"
)

_SYSLOG_RFC5424_PATTERN = re.compile(
    r"^(?:<(?P<pri>\d{1,3})>)?\d+\s+(?P<timestamp>\S+)\s+(?P<host>\S+)\s+"
    r"(?P<app_name>\S+)\s+(?P<procid>\S+)\s+(?P<msgid>\S+)\s+(?:-\s+)?(?P<message>.*)$"
)

# Application specific message patterns
_SSH_FAILED_PATTERN = re.compile(
    r"Failed password for (?:invalid user )?(?P<user>\S+) from (?P<src>\S+) port (?P<port>\d+)(?:\s+(?P<proto>\S+))?",
    re.IGNORECASE,
)
_SSH_ACCEPTED_PATTERN = re.compile(
    r"Accepted password for (?P<user>\S+) from (?P<src>\S+) port (?P<port>\d+)(?:\s+(?P<proto>\S+))?",
    re.IGNORECASE,
)
_SUDO_PATTERN = re.compile(
    r"sudo:\s*(?P<user>\S+)\s*:\s*TTY=(?P<tty>\S*)\s*;\s*PWD=(?P<pwd>\S*)\s*;\s*USER=(?P<target_user>\S*)\s*;\s*COMMAND=(?P<command>.*)",
    re.IGNORECASE,
)
_ACCESS_DENIED_PATTERN = re.compile(
    r"(?:access denied|permission denied|unauthorized)(?:\s+for\s+(?:user\s+)?(?P<user>\S+))?(?:\s+(?:to|for)\s+(?:resource\s+)?(?P<resource>\S+))?",
    re.IGNORECASE,
)

# Key-Value / logfmt pattern: key=value or key="quoted value"
_KEY_VALUE_PATTERN = re.compile(r'([a-zA-Z0-9_\.\-]+)=(?:"([^"]*)"|(\S+))')

# Combined/Common Web Log pattern
_COMMON_LOG_PATTERN = re.compile(
    r'^(?P<client_ip>\S+)\s+\S+\s+(?P<user>\S+)\s+\[(?P<time>[^\]]+)\]\s+"(?P<method>\S+)\s+(?P<resource>\S+)\s+(?P<protocol>[^"]+)"\s+(?P<status_code>\d+)\s+(?P<bytes>\S+)'
)


def parse_timestamp(value: Any) -> datetime:
    """Robustly parse timestamp values into a UTC timezone-aware datetime."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    if isinstance(value, (int, float)):
        # Epoch seconds or milliseconds
        if value > 1e11:  # Milliseconds
            return datetime.fromtimestamp(value / 1000.0, tz=timezone.utc)
        return datetime.fromtimestamp(value, tz=timezone.utc)

    if isinstance(value, str):
        cleaned = value.strip()
        # ISO-8601 with Z or offset
        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(cleaned)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            pass

        # Syslog format: "Oct  8 17:00:00" or "Oct 08 17:00:00"
        for fmt in (
            "%b %d %H:%M:%S",
            "%b  %d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%d/%b/%Y:%H:%M:%S %z",
            "%d/%b/%Y:%H:%M:%S",
        ):
            try:
                dt = datetime.strptime(cleaned, fmt)
                if dt.year == 1900:
                    dt = dt.replace(year=datetime.now(timezone.utc).year)
                if dt.tzinfo is None:
                    return dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except ValueError:
                continue

    return datetime.now(timezone.utc)


def redact_sensitive_values(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively sanitize metadata dictionary to redact sensitive credentials."""
    sanitized: dict[str, Any] = {}
    for k, v in data.items():
        if _SENSITIVE_KEY_PATTERNS.search(str(k)):
            sanitized[k] = "[REDACTED]"
        elif isinstance(v, dict):
            sanitized[k] = redact_sensitive_values(v)
        elif isinstance(v, list):
            sanitized[k] = [
                redact_sensitive_values(item) if isinstance(item, dict) else item
                for item in v
            ]
        else:
            sanitized[k] = v
    return sanitized


def _parse_cef(text: str) -> dict[str, Any] | None:
    match = _CEF_PATTERN.match(text.strip())
    if not match:
        return None

    vendor = match.group("vendor")
    product = match.group("product")
    name = match.group("name")
    extension_str = match.group(8)

    ext_data: dict[str, Any] = {}
    for m in _KEY_VALUE_PATTERN.finditer(extension_str):
        k, v1, v2 = m.groups()
        val = v1 if v1 is not None else v2
        ext_data[k] = val

    action = ext_data.get("act") or name or "unknown"
    event_type = ext_data.get("cat") or "security"
    if "login" in action.lower() or "auth" in action.lower():
        event_type = "authentication"

    parsed = {
        "event_type": event_type,
        "action": action,
        "source_ip": ext_data.get("src"),
        "destination_ip": ext_data.get("dst"),
        "user": ext_data.get("suser") or ext_data.get("duser") or ext_data.get("usr"),
        "resource": ext_data.get("resource") or ext_data.get("request"),
        "protocol": ext_data.get("proto"),
        "source_device": ext_data.get("shost") or ext_data.get("dhost") or product or vendor,
        "status": "failure" if "fail" in action.lower() or "denied" in action.lower() else "success",
        "metadata": {
            "cef_vendor": vendor,
            "cef_product": product,
            "cef_severity": match.group("severity"),
            "cef_name": name,
            **{k: v for k, v in ext_data.items() if k not in ("src", "dst", "suser", "duser", "usr", "act", "proto", "cat")},
        },
        "raw": {"raw_log": text, "format": "cef"},
    }
    return parsed


def _parse_syslog(text: str) -> dict[str, Any] | None:
    cleaned = text.strip()
    match = _SYSLOG_RFC3164_PATTERN.match(cleaned) or _SYSLOG_RFC5424_PATTERN.match(cleaned)
    if not match:
        return None

    groups = match.groupdict()
    timestamp_str = groups.get("timestamp")
    host = groups.get("host")
    app_tag = groups.get("tag") or groups.get("app_name") or "syslog"
    message = groups.get("message", "")

    parsed: dict[str, Any] = {
        "timestamp": parse_timestamp(timestamp_str),
        "source_device": host,
        "event_type": "system",
        "action": "syslog_event",
        "status": None,
        "metadata": {"tag": app_tag, "syslog_pri": groups.get("pri")},
        "raw": {"raw_log": text, "format": "syslog"},
    }

    # Inspect message content for specialized security semantics
    ssh_fail = _SSH_FAILED_PATTERN.search(message)
    if ssh_fail:
        parsed["event_type"] = "authentication"
        parsed["action"] = "login_failed"
        parsed["status"] = "failure"
        parsed["user"] = ssh_fail.group("user")
        parsed["source_ip"] = ssh_fail.group("src")
        parsed["protocol"] = (ssh_fail.group("proto") or "ssh").lower()
        parsed["metadata"]["port"] = ssh_fail.group("port")
        return parsed

    ssh_ok = _SSH_ACCEPTED_PATTERN.search(message)
    if ssh_ok:
        parsed["event_type"] = "authentication"
        parsed["action"] = "login_success"
        parsed["status"] = "success"
        parsed["user"] = ssh_ok.group("user")
        parsed["source_ip"] = ssh_ok.group("src")
        parsed["protocol"] = (ssh_ok.group("proto") or "ssh").lower()
        parsed["metadata"]["port"] = ssh_ok.group("port")
        return parsed

    sudo_match = _SUDO_PATTERN.search(message)
    if sudo_match:
        parsed["event_type"] = "privileged_command"
        parsed["action"] = "sudo_execution"
        parsed["user"] = sudo_match.group("user")
        parsed["resource"] = sudo_match.group("command")
        parsed["metadata"]["target_user"] = sudo_match.group("target_user")
        parsed["metadata"]["pwd"] = sudo_match.group("pwd")
        return parsed

    denied_match = _ACCESS_DENIED_PATTERN.search(message)
    if denied_match:
        parsed["event_type"] = "resource_access"
        parsed["action"] = "access_denied"
        parsed["status"] = "failure"
        if denied_match.group("user"):
            parsed["user"] = denied_match.group("user")
        if denied_match.group("resource"):
            parsed["resource"] = denied_match.group("resource")
        return parsed

    parsed["metadata"]["message"] = message
    return parsed


def _parse_web_log(text: str) -> dict[str, Any] | None:
    match = _COMMON_LOG_PATTERN.match(text.strip())
    if not match:
        return None
    groups = match.groupdict()
    status_code = int(groups["status_code"])
    user = groups["user"] if groups["user"] != "-" else None
    return {
        "timestamp": parse_timestamp(groups["time"]),
        "source_ip": groups["client_ip"],
        "user": user,
        "event_type": "network" if status_code < 400 else "resource_access",
        "action": "http_request",
        "status": "success" if status_code < 400 else "failure",
        "resource": groups["resource"],
        "protocol": groups["protocol"].split("/")[0].lower() if "/" in groups["protocol"] else "http",
        "metadata": {
            "method": groups["method"],
            "status_code": status_code,
            "bytes_sent": groups["bytes"],
        },
        "raw": {"raw_log": text, "format": "clf"},
    }


def _parse_key_value_string(text: str) -> dict[str, Any] | None:
    pairs: dict[str, Any] = {}
    for m in _KEY_VALUE_PATTERN.finditer(text):
        k, v1, v2 = m.groups()
        pairs[k] = v1 if v1 is not None else v2
    if len(pairs) >= 2:
        return pairs
    return None


class LogParser:
    """Main parsing and normalization service."""

    @classmethod
    def normalize_dict(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Normalize a dictionary payload with alias resolution and metadata extraction."""
        normalized: dict[str, Any] = {}
        consumed_keys: set[str] = set()

        # 1. Resolve canonical fields and their aliases
        for field, aliases in _FIELD_ALIASES.items():
            val = data.get(field)
            if val is not None:
                normalized[field] = val
                consumed_keys.add(field)
            else:
                for alias in aliases:
                    if alias in data and data[alias] is not None:
                        normalized[field] = data[alias]
                        consumed_keys.add(alias)
                        break

        # 2. Timestamp normalization
        raw_ts = normalized.get("timestamp")
        normalized["timestamp"] = parse_timestamp(raw_ts)

        # 3. String cleanup
        for str_field in ("event_id", "source_ip", "destination_ip", "user", "event_type", "action", "status", "resource", "protocol", "source_device"):
            v = normalized.get(str_field)
            if isinstance(v, str):
                normalized[str_field] = v.strip()
            elif v is not None:
                normalized[str_field] = str(v)

        # Lowercase types/protocols
        if normalized.get("protocol"):
            normalized["protocol"] = normalized["protocol"].lower()
        if normalized.get("status"):
            normalized["status"] = normalized["status"].lower()

        # 4. Infer event_type / action if missing or partial
        if not normalized.get("event_type"):
            act = (normalized.get("action") or "").lower()
            if "login" in act or "auth" in act:
                normalized["event_type"] = "authentication"
            elif "access" in act or "file" in act or "read" in act or "write" in act:
                normalized["event_type"] = "resource_access"
            elif "connect" in act or "traffic" in act or "packet" in act:
                normalized["event_type"] = "network"

        # 5. Extract unmapped keys into metadata
        existing_meta = data.get("metadata") or data.get("metadata_json") or {}
        if not isinstance(existing_meta, dict):
            existing_meta = {"original_metadata": existing_meta}
        extra_meta: dict[str, Any] = dict(existing_meta)

        for k, v in data.items():
            if k in _CANONICAL_FIELDS or k in _ALL_ALIAS_KEYS or k in consumed_keys:
                continue
            extra_meta[k] = v

        # Redact secrets in metadata
        normalized["metadata"] = redact_sensitive_values(extra_meta)

        # 6. Preserve raw information
        raw_info = data.get("raw")
        if isinstance(raw_info, str):
            normalized["raw"] = {"raw_message": raw_info}
        elif isinstance(raw_info, dict):
            normalized["raw"] = raw_info
        else:
            normalized["raw"] = None

        return normalized

    @classmethod
    def parse_string(cls, text: str) -> dict[str, Any]:
        """Parse an unstructured or structured string log entry."""
        cleaned = text.strip()
        if not cleaned:
            raise ValueError("Log string cannot be empty")

        # Try JSON string
        if (cleaned.startswith("{") and cleaned.endswith("}")) or (cleaned.startswith("[") and cleaned.endswith("]")):
            try:
                decoded = json.loads(cleaned)
                if isinstance(decoded, dict):
                    res = cls.normalize_dict(decoded)
                    if not res.get("raw"):
                        res["raw"] = {"raw_log": cleaned, "format": "json"}
                    return res
            except Exception:
                pass

        # Try CEF
        cef_res = _parse_cef(cleaned)
        if cef_res:
            return cls.normalize_dict(cef_res)

        # Try Syslog
        syslog_res = _parse_syslog(cleaned)
        if syslog_res:
            return cls.normalize_dict(syslog_res)

        # Try Common/Combined Web Log
        web_res = _parse_web_log(cleaned)
        if web_res:
            return cls.normalize_dict(web_res)

        # Try Key-Value
        kv_res = _parse_key_value_string(cleaned)
        if kv_res:
            res = cls.normalize_dict(kv_res)
            res["raw"] = {"raw_log": cleaned, "format": "logfmt"}
            return res

        # Generic line fallback
        return cls.normalize_dict({
            "event_type": "system",
            "action": "log_entry",
            "metadata": {"raw_line": cleaned},
            "raw": {"raw_log": cleaned, "format": "raw_text"},
        })

    @classmethod
    def parse(cls, input_data: Any) -> dict[str, Any]:
        """Universal parser entrypoint. Accepts dict, str, or Pydantic models."""
        if hasattr(input_data, "model_dump"):
            dumped = input_data.model_dump(exclude_unset=True)
            if hasattr(input_data, "__pydantic_extra__") and input_data.__pydantic_extra__:
                dumped.update(input_data.__pydantic_extra__)
            return cls.normalize_dict(dumped)
        if isinstance(input_data, dict):
            return cls.normalize_dict(input_data)
        if isinstance(input_data, str):
            return cls.parse_string(input_data)
        raise ValueError(f"Unsupported event payload type: {type(input_data).__name__}")
