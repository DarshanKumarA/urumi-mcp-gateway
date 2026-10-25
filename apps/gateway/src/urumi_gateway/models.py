"""Internal registration records, separate observation, and safe public projection."""

import math
import re
from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import urlsplit
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

    def __post_init__(self):
        if (not isinstance(self.id, UUID) or type(self.enabled) is not bool
                or not isinstance(self.slug, str)
                or not re.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*", self.slug)
                or len(self.slug) > 32):
            raise ValueError("INVALID_REGISTRATION")
        if not isinstance(self.display_name, str) or not 1 <= len(self.display_name.strip()) <= 100:
            raise ValueError("INVALID_DISPLAY_NAME")
        try:
            parsed = urlsplit(self.url)
            valid = (not any(c.isspace() for c in self.url)
                     and parsed.scheme in {"http", "https"} and parsed.hostname
                     and not parsed.username and not parsed.password and not parsed.query
                     and not parsed.fragment and parsed.port != 0)
        except (ValueError, TypeError):
            valid = False
        if not valid:
            raise ValueError("INVALID_UPSTREAM_URL")
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


@dataclass(frozen=True)
class Timeouts:
    discovery: float = 5.0
    call: float = 30.0

    def __post_init__(self):
        if any(type(x) not in (float, int) or not math.isfinite(x) or x <= 0 or x > 120
               for x in (self.discovery, self.call)):
            raise ValueError("INVALID_TIMEOUT")
