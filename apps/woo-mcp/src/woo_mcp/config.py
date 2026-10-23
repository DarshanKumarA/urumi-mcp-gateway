"""Non-sensitive deployment configuration and mounted credential loading."""

from dataclasses import dataclass, field
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

    def __post_init__(self):
        try:
            ZoneInfo(self.store_timezone)
        except (ZoneInfoNotFoundError, ValueError, TypeError):
            raise ValueError("Invalid store timezone configuration.") from None
        for origin in (self.connection_origin, self.canonical_origin):
            u = urlsplit(origin)
            if (u.scheme != "http" or not u.hostname or u.username or u.password
                    or u.path or u.query or u.fragment):
                raise ValueError("Expected a plain HTTP origin without path or credentials.")
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
