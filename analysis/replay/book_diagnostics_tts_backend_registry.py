"""
BookDiagnostics RC41/RC43 - TTS Backend Registry / Factory.

Resolve nomes declarativos do RC40 para instancias de backend TTS sem espalhar
condicionais pelo sistema. NULL_TTS continua sendo o backend padrao seguro;
WINDOWS_SAPI fica disponivel apenas para selecao explicita.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable

from analysis.replay.book_diagnostics_tts_backend import NullTTSBackend
from analysis.replay.book_diagnostics_windows_sapi_backend import WindowsSAPITTSBackend


@dataclass(slots=True, frozen=True)
class TTSBackendRegistrySnapshot:
    version: str
    registered_backends: tuple[str, ...]
    default_backend: str
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsTTSBackendRegistry:
    VERSION = "RC41-TTS-BACKEND-REGISTRY"
    DEFAULT_BACKEND = "NULL_TTS"

    def __init__(self):
        self._factories: dict[str, Callable[[], object]] = {}
        self.register(self.DEFAULT_BACKEND, NullTTSBackend, replace=False)
        self.register("WINDOWS_SAPI", WindowsSAPITTSBackend, replace=False)

    def register(self, name: str, factory: Callable[[], object], *, replace: bool = False):
        key = self._normalize_name(name)
        if not callable(factory):
            raise TypeError("backend factory must be callable")
        if key in self._factories and not replace:
            raise ValueError(f"backend already registered: {key}")
        self._factories[key] = factory
        return self.snapshot()

    def unregister(self, name: str):
        key = self._normalize_name(name)
        if key == self.DEFAULT_BACKEND:
            raise PermissionError("NULL_TTS cannot be unregistered")
        if key not in self._factories:
            return False
        del self._factories[key]
        return True

    def create(self, name: str | None = None):
        key = self._normalize_name(name or self.DEFAULT_BACKEND)
        factory = self._factories.get(key)
        if factory is None:
            raise LookupError(f"unknown TTS backend: {key}")

        backend = factory()
        self._validate_backend(backend, expected_name=key)
        return backend

    def contains(self, name: str) -> bool:
        return self._normalize_name(name) in self._factories

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._factories))

    def snapshot(self) -> TTSBackendRegistrySnapshot:
        return TTSBackendRegistrySnapshot(
            version=self.VERSION,
            registered_backends=self.names(),
            default_backend=self.DEFAULT_BACKEND,
        )

    @staticmethod
    def _normalize_name(name: str) -> str:
        key = str(name or "").strip().upper()
        if not key:
            raise ValueError("backend name cannot be empty")
        return key

    @staticmethod
    def _validate_backend(backend, *, expected_name: str) -> None:
        actual = str(getattr(backend, "name", "") or "").strip().upper()
        if not actual:
            raise ValueError("TTS backend must expose a non-empty name")
        if actual != expected_name:
            raise ValueError("TTS backend name does not match registry key")

        for method in ("speak", "stop", "healthcheck"):
            if not callable(getattr(backend, method, None)):
                raise TypeError(f"TTS backend missing required method: {method}")


_default_registry: BookDiagnosticsTTSBackendRegistry | None = None


def get_default_tts_backend_registry() -> BookDiagnosticsTTSBackendRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = BookDiagnosticsTTSBackendRegistry()
    return _default_registry
