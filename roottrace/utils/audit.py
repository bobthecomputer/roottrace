from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from roottrace.utils.files import timestamped_stem

_EMAIL_RE = re.compile(r"\b([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
_PHONE_RE = re.compile(r"\+?\d[\d\s().-]{6,}\d")


def _redact(value: str) -> str:
    def mask_email(match: re.Match[str]) -> str:
        local, domain = match.groups()
        return f"{local[0]}***@{domain}"

    def mask_phone(match: re.Match[str]) -> str:
        digits = re.sub(r"\D", "", match.group())
        if len(digits) <= 4:
            return "***"
        return f"+***{digits[-4:]}"

    partially = _EMAIL_RE.sub(mask_email, value)
    return _PHONE_RE.sub(mask_phone, partially)


def redact_details(details: dict[str, Any]) -> dict[str, Any]:
    """Recursively redact potentially sensitive strings."""

    redacted: dict[str, Any] = {}
    for key, value in details.items():
        if isinstance(value, str):
            redacted[key] = _redact(value)
        elif isinstance(value, dict):
            redacted[key] = redact_details(value)
        elif isinstance(value, list):
            redacted[key] = [
                redact_details(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            redacted[key] = value
    return redacted


@dataclass(slots=True)
class AuditEvent:
    level: str
    event: str
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level,
            "event": self.event,
            "details": redact_details(self.details),
        }
        return payload


class AuditTrail:
    """Collect audit events and persist them to JSONL."""

    def __init__(self, log_dir: Path) -> None:
        log_dir.mkdir(parents=True, exist_ok=True)
        stem = timestamped_stem("ingest")
        self.path = log_dir / f"{stem}.jsonl"
        self._events: list[AuditEvent] = []

    def record(self, level: str, event: str, **details: Any) -> AuditEvent:
        audit_event = AuditEvent(level=level, event=event, details=details)
        self._events.append(audit_event)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(audit_event.to_dict(), ensure_ascii=False) + "\n")
        return audit_event

    @property
    def events(self) -> list[AuditEvent]:
        return list(self._events)


__all__ = ["AuditTrail", "AuditEvent", "redact_details"]
