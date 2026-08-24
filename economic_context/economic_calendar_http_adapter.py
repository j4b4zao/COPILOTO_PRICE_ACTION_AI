"""Adaptador HTTP somente leitura e endurecido para calendário econômico RC10."""

from __future__ import annotations

import ipaddress
import json
from dataclasses import dataclass
from urllib.error import HTTPError
from urllib.parse import urlparse, urlunparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


@dataclass(frozen=True, slots=True)
class EconomicCalendarHttpResponse:
    status: int
    headers: dict
    body: bytes
    final_url: str


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class UrllibEconomicCalendarTransport:
    """Transporte padrão sem redirecionamentos automáticos."""

    def get(self, *, url, headers, timeout, max_bytes):
        request = Request(url=url, headers=dict(headers), method="GET")
        opener = build_opener(_NoRedirect())
        try:
            with opener.open(request, timeout=timeout) as response:
                body = response.read(max_bytes + 1)
                return EconomicCalendarHttpResponse(
                    status=int(response.status),
                    headers=dict(response.headers.items()),
                    body=body,
                    final_url=response.geturl(),
                )
        except HTTPError as exc:
            body = exc.read(max_bytes + 1)
            return EconomicCalendarHttpResponse(
                status=int(exc.code),
                headers=dict(exc.headers.items()),
                body=body,
                final_url=exc.geturl(),
            )


class EconomicCalendarHttpAdapter:
    NAME = "EconomicCalendarHttpAdapter"
    VERSION = "RC10"

    def __init__(
        self,
        url,
        *,
        allowed_hosts,
        payload_path=(),
        headers=None,
        timeout_seconds=5.0,
        max_response_bytes=1_000_000,
        transport=None,
    ):
        self.url = str(url).strip()
        self.allowed_hosts = frozenset(
            str(host).strip().lower()
            for host in allowed_hosts
            if str(host).strip()
        )
        if not self.allowed_hosts:
            raise ValueError("allowed_hosts não pode ser vazio.")
        self.payload_path = self._path(payload_path)
        self.headers = dict(headers or {})
        self.timeout_seconds = float(timeout_seconds)
        self.max_response_bytes = int(max_response_bytes)
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds deve ser positivo.")
        if self.max_response_bytes <= 0:
            raise ValueError("max_response_bytes deve ser positivo.")
        self.transport = transport or UrllibEconomicCalendarTransport()
        if not callable(getattr(self.transport, "get", None)):
            raise TypeError("Transport deve expor get().")
        self._validate_url(self.url)
        self.last_diagnostics = {
            "status": "NOT_RUN",
            "source": self._sanitized_url(self.url),
        }

    def __call__(self, *, now):
        try:
            response = self.transport.get(
                url=self.url,
                headers=self.headers,
                timeout=self.timeout_seconds,
                max_bytes=self.max_response_bytes,
            )
        except Exception as exc:
            self.last_diagnostics = {
                "status": "TRANSPORT_ERROR",
                "source": self._sanitized_url(self.url),
                "error_type": type(exc).__name__,
            }
            raise RuntimeError("Falha segura no transporte do calendário.") from None

        if not isinstance(response, EconomicCalendarHttpResponse):
            raise TypeError("Transport retornou resposta incompatível.")
        self._validate_url(response.final_url)
        if response.status != 200:
            self._diagnose("HTTP_ERROR", response, error=f"HTTP {response.status}")
            raise RuntimeError(f"Calendário respondeu HTTP {response.status}.")
        if len(response.body) > self.max_response_bytes:
            self._diagnose("RESPONSE_TOO_LARGE", response)
            raise ValueError("Resposta do calendário excedeu o limite permitido.")
        content_type = self._header(response.headers, "content-type").lower()
        if "application/json" not in content_type:
            self._diagnose("INVALID_CONTENT_TYPE", response)
            raise ValueError("Calendário não retornou application/json.")
        try:
            payload = json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            self._diagnose("INVALID_JSON", response, error=type(exc).__name__)
            raise ValueError("Resposta JSON inválida.") from None
        events = self._extract(payload)
        if not isinstance(events, list):
            self._diagnose("INVALID_PAYLOAD_SHAPE", response)
            raise TypeError("Payload final do calendário deve ser uma lista.")
        self._diagnose("OK", response, event_count=len(events))
        return events

    def _extract(self, payload):
        current = payload
        for key in self.payload_path:
            if not isinstance(current, dict) or key not in current:
                raise ValueError(f"Caminho de payload ausente: {key}")
            current = current[key]
        return current

    def _validate_url(self, url):
        parsed = urlparse(url)
        if parsed.scheme.lower() != "https":
            raise ValueError("Somente URLs HTTPS são permitidas.")
        if parsed.username or parsed.password:
            raise ValueError("Credenciais embutidas na URL não são permitidas.")
        if parsed.fragment:
            raise ValueError("Fragmentos de URL não são permitidos.")
        host = (parsed.hostname or "").lower()
        if not host or host not in self.allowed_hosts:
            raise ValueError("Host não autorizado para calendário econômico.")
        if parsed.port not in (None, 443):
            raise ValueError("Somente a porta HTTPS padrão é permitida.")
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            return
        if not address.is_global:
            raise ValueError("Endereço IP privado/reservado não é permitido.")

    def _diagnose(self, status, response, **extra):
        self.last_diagnostics = {
            "status": status,
            "source": self._sanitized_url(self.url),
            "final_source": self._sanitized_url(response.final_url),
            "http_status": response.status,
            "response_bytes": len(response.body),
            **extra,
        }

    @staticmethod
    def _sanitized_url(url):
        parsed = urlparse(str(url))
        return urlunparse(
            (parsed.scheme, parsed.netloc, parsed.path, parsed.params, "", "")
        )

    @staticmethod
    def _header(headers, name):
        target = name.casefold()
        for key, value in headers.items():
            if str(key).casefold() == target:
                return str(value)
        return ""

    @staticmethod
    def _path(value):
        if value in (None, ""):
            return ()
        if isinstance(value, str):
            return tuple(part for part in value.split(".") if part)
        return tuple(str(part) for part in value)
