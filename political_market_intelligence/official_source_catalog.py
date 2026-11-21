"""PMI-RC2-A3: offline-only metadata catalog for candidate official sources.

Registration does not authenticate a website or authorize data collection.
No transport, file I/O, credentials, or trading integrations are provided.
"""

from dataclasses import dataclass
from enum import Enum
import ipaddress
import re
from urllib.parse import urlsplit

from .event_model import EventCategory
from .source_registry import SourceStatus


class OfficialSourceKind(str, Enum):
    AGENDA = "AGENDA"
    SPEECH = "SPEECH"
    COMMUNICATION = "COMMUNICATION"
    ECONOMIC_RELEASE = "ECONOMIC_RELEASE"


def _required(value: str, name: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(f"{name} requires a nonempty, trimmed string")
    return value


def _candidate_https_url(value: str) -> str:
    _required(value, "candidate_url")
    if any(ord(char) < 33 or ord(char) == 127 for char in value):
        raise ValueError("candidate_url contains whitespace or controls")
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise ValueError("invalid candidate_url") from exc
    if (parsed.scheme != "https" or not parsed.netloc or not hostname
            or parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment or port is not None):
        raise ValueError("candidate_url requires HTTPS host without credentials, port, query or fragment")
    if not re.fullmatch(r"[A-Za-z0-9.-]+", hostname) or "." not in hostname:
        raise ValueError("candidate_url requires a DNS hostname")
    if hostname.lower() == "localhost" or hostname.lower().endswith(".localhost"):
        raise ValueError("local hosts are prohibited")
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        raise ValueError("IP addresses are prohibited")
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class OfficialSource:
    source_id: str
    institution: str
    country_code: str
    kind: OfficialSourceKind
    candidate_url: str
    capabilities: frozenset[EventCategory]
    status: SourceStatus = SourceStatus.UNVERIFIED
    collection_enabled: bool = False

    def __post_init__(self) -> None:
        _required(self.source_id, "source_id")
        _required(self.institution, "institution")
        if not re.fullmatch(r"[A-Z]{2}", _required(self.country_code, "country_code")):
            raise ValueError("country_code requires two uppercase letters")
        if not isinstance(self.kind, OfficialSourceKind):
            raise ValueError("kind requires OfficialSourceKind")
        _candidate_https_url(self.candidate_url)
        if type(self.capabilities) not in (frozenset, set, tuple, list):
            raise ValueError("capabilities requires a collection")
        capabilities = frozenset(self.capabilities)
        if not capabilities or any(not isinstance(item, EventCategory) for item in capabilities):
            raise ValueError("capabilities requires EventCategory values")
        object.__setattr__(self, "capabilities", capabilities)
        if self.status is not SourceStatus.UNVERIFIED:
            raise ValueError("A3 catalog entries must remain UNVERIFIED")
        if self.collection_enabled is not False:
            raise ValueError("A3 does not authorize collection")


class OfficialSourceCatalog:
    """Immutable, deterministic registry of candidate metadata only."""

    def __init__(self, sources: tuple[OfficialSource, ...] = ()) -> None:
        if type(sources) not in (tuple, list):
            raise TypeError("sources requires a tuple or list")
        indexed: dict[str, OfficialSource] = {}
        for source in sources:
            if type(source) is not OfficialSource:
                raise TypeError("catalog accepts OfficialSource values")
            if source.source_id in indexed:
                raise ValueError(f"duplicate source_id: {source.source_id}")
            indexed[source.source_id] = source
        self._sources = tuple(indexed[key] for key in sorted(indexed))
        self._by_id = indexed

    def all(self) -> tuple[OfficialSource, ...]:
        return self._sources

    def get(self, source_id: str) -> OfficialSource:
        return self._by_id[source_id]
