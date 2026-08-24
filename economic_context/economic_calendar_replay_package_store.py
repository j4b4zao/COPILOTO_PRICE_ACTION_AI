"""Pacotes íntegros e sanitizados de replay do calendário econômico RC13."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urlunparse


@dataclass(frozen=True, slots=True)
class EconomicCalendarReplayPackage:
    session_id: str
    captured_at: datetime
    provider: str
    payload: tuple[dict, ...]
    checksum_sha256: str
    observational_only: bool = True


class EconomicCalendarReplayPackageStore:
    """Salva/importa JSON local; não possui transporte nem acesso a credenciais."""

    NAME = "EconomicCalendarReplayPackageStore"
    VERSION = "RC13"
    SCHEMA_VERSION = 1
    PROVIDER = "TRADING_ECONOMICS"
    MAX_EVENTS = 10_000
    SENSITIVE_KEYS = frozenset(
        {
            "api_key",
            "apikey",
            "api_token",
            "token",
            "authorization",
            "password",
            "secret",
            "c",
        }
    )

    def save(
        self,
        path,
        *,
        session_id,
        captured_at,
        payload,
        forbidden_secret_values=(),
        overwrite=False,
    ):
        destination = self._path(path)
        if destination.exists() and not overwrite:
            raise FileExistsError("Pacote de replay já existe.")

        session_id = str(session_id).strip()
        if not session_id:
            raise ValueError("session_id é obrigatório.")
        self._aware(captured_at)

        rows = tuple(payload)
        if len(rows) > self.MAX_EVENTS:
            raise ValueError("Payload excede o limite de eventos.")
        secrets = tuple(
            str(value) for value in forbidden_secret_values if str(value)
        )
        sanitized = self._sanitize(list(rows), secrets)
        if not isinstance(sanitized, list) or not all(
            isinstance(row, dict) for row in sanitized
        ):
            raise TypeError("Payload do replay deve ser lista de objetos.")

        body = {
            "schema_version": self.SCHEMA_VERSION,
            "session_id": session_id,
            "captured_at": captured_at.isoformat(),
            "provider": self.PROVIDER,
            "payload": sanitized,
            "observational_only": True,
            "score_influence_allowed": False,
            "order_execution_allowed": False,
        }
        envelope = dict(body)
        envelope["checksum_sha256"] = self._checksum(body)

        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + ".tmp")
        temporary.write_text(
            json.dumps(envelope, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(destination)
        return self.load(destination)

    def load(self, path):
        source = self._path(path)
        try:
            envelope = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Pacote de replay ilegível ou inválido.") from exc
        self._validate_envelope(envelope)

        checksum = envelope["checksum_sha256"]
        body = {key: value for key, value in envelope.items() if key != "checksum_sha256"}
        expected = self._checksum(body)
        if not hmac.compare_digest(str(checksum), expected):
            raise ValueError("Checksum do pacote de replay inválido.")

        try:
            captured_at = datetime.fromisoformat(envelope["captured_at"])
        except (TypeError, ValueError) as exc:
            raise ValueError("captured_at inválido.") from exc
        self._aware(captured_at)

        return EconomicCalendarReplayPackage(
            session_id=envelope["session_id"],
            captured_at=captured_at,
            provider=envelope["provider"],
            payload=tuple(dict(row) for row in envelope["payload"]),
            checksum_sha256=checksum,
        )

    def replay_into(
        self,
        runner,
        path,
        *,
        expected_event_count,
        maximum_clock_error_seconds,
    ):
        if not callable(getattr(runner, "add_session", None)):
            raise TypeError("Runner de replay incompatível.")
        package = self.load(path)
        return runner.add_session(
            session_id=package.session_id,
            payload=package.payload,
            expected_event_count=expected_event_count,
            maximum_clock_error_seconds=maximum_clock_error_seconds,
        )

    @classmethod
    def _sanitize(cls, value, secrets):
        if isinstance(value, dict):
            clean = {}
            for key, item in value.items():
                text_key = str(key)
                normalized = text_key.strip().casefold().replace("-", "_")
                if normalized in cls.SENSITIVE_KEYS:
                    raise ValueError(f"Campo sensível proibido: {text_key}")
                clean[text_key] = cls._sanitize(item, secrets)
            return clean
        if isinstance(value, (list, tuple)):
            return [cls._sanitize(item, secrets) for item in value]
        if isinstance(value, str):
            if any(secret in value for secret in secrets):
                raise ValueError("Valor secreto detectado no pacote.")
            parsed = urlparse(value)
            if parsed.scheme.lower() in {"http", "https"} and parsed.netloc:
                return urlunparse(
                    (parsed.scheme, parsed.netloc, parsed.path, parsed.params, "", "")
                )
            return value
        if value is None or isinstance(value, (bool, int, float)):
            return value
        raise TypeError(f"Tipo não serializável no replay: {type(value).__name__}")

    @classmethod
    def _validate_envelope(cls, envelope):
        if not isinstance(envelope, dict):
            raise TypeError("Envelope do replay deve ser objeto.")
        required = {
            "schema_version",
            "session_id",
            "captured_at",
            "provider",
            "payload",
            "observational_only",
            "score_influence_allowed",
            "order_execution_allowed",
            "checksum_sha256",
        }
        if set(envelope) != required:
            raise ValueError("Esquema do pacote de replay incompatível.")
        if envelope["schema_version"] != cls.SCHEMA_VERSION:
            raise ValueError("schema_version não suportada.")
        if str(envelope["provider"]).strip().upper() != cls.PROVIDER:
            raise ValueError("Provider do replay incompatível.")
        if not str(envelope["session_id"]).strip():
            raise ValueError("session_id vazio.")
        if not isinstance(envelope["payload"], list):
            raise TypeError("payload deve ser lista.")
        if len(envelope["payload"]) > cls.MAX_EVENTS:
            raise ValueError("Payload excede o limite de eventos.")
        if not all(isinstance(row, dict) for row in envelope["payload"]):
            raise TypeError("Cada evento do payload deve ser objeto.")
        if envelope["observational_only"] is not True:
            raise ValueError("Pacote deve permanecer observacional.")
        if envelope["score_influence_allowed"] is not False:
            raise ValueError("Pacote não pode influenciar o score.")
        if envelope["order_execution_allowed"] is not False:
            raise ValueError("Pacote não pode executar ordens.")
        if not isinstance(envelope["checksum_sha256"], str) or len(
            envelope["checksum_sha256"]
        ) != 64:
            raise ValueError("checksum_sha256 inválido.")

    @staticmethod
    def _checksum(body):
        canonical = json.dumps(
            body,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    @staticmethod
    def _aware(value):
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise ValueError("captured_at deve possuir fuso horário.")

    @staticmethod
    def _path(value):
        path = Path(value)
        if not path.name.endswith(".calendar-replay.json"):
            raise ValueError("Pacote deve usar extensão .calendar-replay.json.")
        return path
