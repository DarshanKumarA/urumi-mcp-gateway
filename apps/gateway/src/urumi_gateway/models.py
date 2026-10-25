"""Internal registration records, separate observation, and safe public projection."""

import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID, uuid4


@dataclass(frozen=True)
class Credential:
    kind: Literal["bearer", "header"]
    value: str = field(repr=False)
    header_name: str | None = None

    def __post_init__(self):
        if (self.kind not in ("bearer", "header") or not isinstance(self.value, str)
                or not self.value or any(ord(c) < 32 or ord(c) > 126 for c in self.value)):
            raise ValueError("INVALID_CREDENTIAL")
        if self.kind == "bearer":
            if self.header_name is not None or " " in self.value:
                raise ValueError("INVALID_CREDENTIAL")
        elif (not isinstance(self.header_name, str)
              or not re.fullmatch(r"[A-Za-z][A-Za-z0-9-]{0,63}", self.header_name)
              or self.header_name.lower() in {"host", "connection", "content-length", "content-type",
                                              "accept", "origin", "cookie", "transfer-encoding"}
              or self.header_name.lower().startswith(("mcp-", "proxy-", "sec-"))):
            raise ValueError("INVALID_CREDENTIAL_HEADER")

    def headers(self):
        return ({"Authorization": "Bearer " + self.value} if self.kind == "bearer"
                else {self.header_name: self.value})


@dataclass(frozen=True)
class Upstream:
    slug: str
    display_name: str
    url: str = field(repr=False)
    id: UUID = field(default_factory=uuid4)
    enabled: bool = True
    credential: Credential | None = field(default=None, repr=False)
    revision: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc), compare=False)
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc), compare=False)

    def __post_init__(self):
        if (not isinstance(self.id, UUID) or type(self.enabled) is not bool
                or not isinstance(self.slug, str)
                or not re.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*", self.slug)
                or len(self.slug) > 32):
            raise ValueError("INVALID_REGISTRATION")
        if not isinstance(self.display_name, str) or not 1 <= len(self.display_name.strip()) <= 100:
            raise ValueError("INVALID_DISPLAY_NAME")
        if not isinstance(self.url, str):
            raise ValueError("INVALID_UPSTREAM_URL")
        try:
            parsed = urlsplit(self.url)
            valid = (len(self.url) <= 2048 and not any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in self.url)
                     and not any(c in self.url for c in ("?", "#", "\\"))
                     and parsed.scheme in {"http", "https"} and parsed.hostname
                     and parsed.username is None and parsed.password is None and not parsed.query
                     and not parsed.fragment and parsed.port != 0)
        except (ValueError, TypeError):
            valid = False
        if not valid:
            raise ValueError("INVALID_UPSTREAM_URL")
        host = parsed.hostname.lower()
        if ":" in host:
            host = f"[{host}]"
        port = parsed.port
        authority = host + (f":{port}" if port and (parsed.scheme, port) not in {("http", 80), ("https", 443)} else "")
        object.__setattr__(self, "url", urlunsplit((parsed.scheme, authority, parsed.path or "/", "", "")))
        if self.credential is not None and not isinstance(self.credential, Credential):
            raise ValueError("INVALID_CREDENTIAL")

    @property
    def configured_state(self):
        return "enabled" if self.enabled else "disabled"

    def public_info(self):
        # Deliberately not dataclasses.asdict: credentials and connection URL are internal.
        return {"id": str(self.id), "slug": self.slug, "display_name": self.display_name,
                "configured_state": self.configured_state,
                "has_credential": self.credential is not None}


@dataclass(frozen=True)
class Observation:
    health: Literal["unknown", "connected", "unreachable"] = "unknown"
    error_code: str | None = None
    checked_at: datetime | None = None

    def __post_init__(self):
        allowed = {"UPSTREAM_TIMEOUT", "UPSTREAM_UNREACHABLE", "UPSTREAM_INVALID_RESPONSE",
                   "UPSTREAM_REDIRECT", "UPSTREAM_UNSAFE_RESPONSE", "UPSTREAM_UNAVAILABLE",
                   "UPSTREAM_PROTOCOL_ERROR", "UPSTREAM_CHANGED", "UNKNOWN_TOOL"}
        if self.health not in {"unknown", "connected", "unreachable"} or (
            self.error_code is not None and self.error_code not in allowed
        ):
            raise ValueError("INVALID_OBSERVATION")


@dataclass(frozen=True)
class Timeouts:
    discovery: float = 5.0
    call: float = 30.0

    def __post_init__(self):
        if any(type(x) not in (float, int) or not math.isfinite(x) or x <= 0 or x > 120
               for x in (self.discovery, self.call)):
            raise ValueError("INVALID_TIMEOUT")
