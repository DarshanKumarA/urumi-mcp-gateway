"""Non-sensitive deployment configuration and mounted credential loading."""

from dataclasses import dataclass, field
import os
import re
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass(frozen=True)
class Config:
    connection_origin: str = "http://urumi-wordpress.urumi.svc.cluster.local"
    canonical_origin: str = "http://store.urumi.test:8080"
    secret_directory: Path = Path("/run/secrets/woocommerce-rest")
    deadline_seconds: float = 8.0
    currency: str = "INR"
    store_timezone: str = "Asia/Kolkata"
    allowed_hosts: tuple[str, ...] = ("127.0.0.1", "127.0.0.1:8000", "localhost", "localhost:8000")

    @classmethod
    def from_environment(cls):
        """Only non-secret settings; credentials remain mounted files."""
        names = ("connection_origin", "canonical_origin", "secret_directory", "deadline_seconds",
                 "currency", "store_timezone")
        values = {name: os.environ["WOO_" + name.upper()] for name in names
                  if "WOO_" + name.upper() in os.environ}
        try:
            if "secret_directory" in values:
                if not values["secret_directory"]:
                    raise ValueError()
                values["secret_directory"] = Path(values["secret_directory"])
            if "deadline_seconds" in values:
                values["deadline_seconds"] = float(values["deadline_seconds"])
            if "WOO_MCP_ALLOWED_HOSTS" in os.environ:
                values["allowed_hosts"] = tuple(os.environ["WOO_MCP_ALLOWED_HOSTS"].split(","))
            return cls(**values)
        except (ValueError, TypeError):
            # Never interpolate rejected environment contents into startup errors.
            raise ValueError("Invalid Woo MCP runtime configuration.") from None

    def __post_init__(self):
        if not self.allowed_hosts or len(set(self.allowed_hosts)) != len(self.allowed_hosts):
            raise ValueError("Expected unique explicit MCP Host values.")
        for host in self.allowed_hosts:
            # DNS/IPv4 only; no wildcards, Origin URLs, paths, spaces or credentials.
            if not re.fullmatch(r"[a-z0-9]+(?:[.-][a-z0-9]+)*(?::[0-9]{1,5})?", host):
                raise ValueError("Expected an explicit MCP hostname and optional port.")
            if ":" in host and not 1 <= int(host.rsplit(":", 1)[1]) <= 65535:
                raise ValueError("Invalid MCP Host port.")
        try:
            ZoneInfo(self.store_timezone)
        except (ZoneInfoNotFoundError, ValueError, TypeError):
            raise ValueError("Invalid store timezone configuration.") from None
        for origin in (self.connection_origin, self.canonical_origin):
            u = urlsplit(origin)
            if (u.scheme != "http" or not u.hostname or u.username or u.password
                    or u.path or u.query or u.fragment):
                raise ValueError("Expected a plain HTTP origin without path or credentials.")
            if u.port == 0 or any(c.isspace() or ord(c) < 32 for c in origin):
                raise ValueError("Invalid HTTP origin.")
        if not 0 < self.deadline_seconds <= 8:
            raise ValueError("REST deadline must be positive and at most eight seconds.")
        if (len(self.currency) != 3 or not self.currency.isascii()
                or not self.currency.isalpha() or not self.currency.isupper()):
            raise ValueError("Expected a three-letter currency code.")

    @property
    def host(self):
        return urlsplit(self.canonical_origin).netloc


@dataclass(frozen=True, repr=False)
class Credentials:
    consumer_key: str = field(repr=False)
    consumer_secret: str = field(repr=False)

    @classmethod
    def from_directory(cls, directory: Path):
        try:
            values = []
            for name in ("consumer-key", "consumer-secret"):
                with (directory / name).open("rb") as stream:
                    raw = stream.read(1025)
                text = raw.decode("utf-8")
                if (not text or len(raw) > 1024 or text != text.strip()
                        or any(c in text for c in "\x00\r\n")):
                    raise ValueError()
                values.append(text)
            return cls(*values)
        except (OSError, UnicodeError, ValueError):
            raise ValueError("Required credential files are missing or invalid.") from None
