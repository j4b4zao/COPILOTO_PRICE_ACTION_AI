"""
BookDiagnostics RC43 - Windows SAPI TTS Backend.

Primeiro backend TTS real opcional do projeto. Usa PowerShell + System.Speech
presentes no Windows, sem dependencia Python externa. O backend somente produz
audio quando selecionado explicitamente via VoiceConfig.backend="WINDOWS_SAPI".
NULL_TTS continua sendo o padrao do sistema.

Esta camada permanece exclusivamente de apresentacao e nunca altera Strategy,
Score, Risk, Decision ou Alert.
"""

from __future__ import annotations

import base64
import platform
import shutil
import subprocess
from threading import Lock
from typing import Callable

from analysis.replay.book_diagnostics_tts_backend import TTSResult, _payload, _validate_command


class WindowsSAPITTSBackend:
    name = "WINDOWS_SAPI"
    VERSION = "RC35-TTS-BACKEND-CONTRACT"

    def __init__(
        self,
        *,
        popen_factory: Callable = subprocess.Popen,
        which: Callable[[str], str | None] = shutil.which,
        platform_name: str | None = None,
    ):
        self._popen_factory = popen_factory
        self._which = which
        self._platform_name = platform_name
        self._active_process = None
        self._active_event_id: str | None = None
        self._lock = Lock()

    def healthcheck(self) -> bool:
        system = (self._platform_name or platform.system()).strip().lower()
        if system != "windows":
            return False
        return self._powershell_executable() is not None

    def speak(self, command) -> TTSResult:
        payload = _payload(command)
        _validate_command(payload)

        event_id = str(payload["event_id"])
        if not self.healthcheck():
            return self._result(
                event_id=event_id,
                accepted=False,
                completed=False,
                interrupted=False,
                error="WINDOWS_SAPI unavailable on this host",
            )

        encoded_text = base64.b64encode(str(payload["text"]).encode("utf-8")).decode("ascii")
        rate = self._sapi_rate(float(payload["speech_rate"]))
        script = self._powershell_script(encoded_text=encoded_text, rate=rate)
        executable = self._powershell_executable()

        try:
            process = self._popen_factory(
                [
                    executable,
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    script,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
        except Exception as exc:
            return self._result(
                event_id=event_id,
                accepted=False,
                completed=False,
                interrupted=False,
                error=f"WINDOWS_SAPI start failed: {exc}",
            )

        with self._lock:
            self._active_process = process
            self._active_event_id = event_id

        try:
            _, stderr = process.communicate()
            return_code = int(getattr(process, "returncode", 0) or 0)
            if return_code != 0:
                message = str(stderr or "").strip() or f"PowerShell exited with code {return_code}"
                return self._result(
                    event_id=event_id,
                    accepted=True,
                    completed=False,
                    interrupted=False,
                    error=message,
                )

            return self._result(
                event_id=event_id,
                accepted=True,
                completed=True,
                interrupted=False,
                error="",
            )
        finally:
            with self._lock:
                if self._active_event_id == event_id:
                    self._active_process = None
                    self._active_event_id = None

    def stop(self, event_id: str | None = None) -> bool:
        with self._lock:
            process = self._active_process
            active_event_id = self._active_event_id

        if process is None:
            return False
        if event_id is not None and str(event_id) != str(active_event_id):
            return False

        try:
            process.terminate()
            return True
        except Exception:
            return False

    def _powershell_executable(self) -> str | None:
        return self._which("powershell") or self._which("pwsh")

    @staticmethod
    def _sapi_rate(speech_rate: float) -> int:
        """Converte RC40 0.5..2.0 para a escala SAPI -10..10."""
        rate = float(speech_rate)
        normalized = (rate - 1.0) / 0.5
        return max(-10, min(10, round(normalized * 4)))

    @staticmethod
    def _powershell_script(*, encoded_text: str, rate: int) -> str:
        return (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.Rate = {int(rate)}; "
            f"$b = [Convert]::FromBase64String('{encoded_text}'); "
            "$t = [Text.Encoding]::UTF8.GetString($b); "
            "$s.Speak($t); $s.Dispose();"
        )

    def _result(
        self,
        *,
        event_id: str,
        accepted: bool,
        completed: bool,
        interrupted: bool,
        error: str,
    ) -> TTSResult:
        return TTSResult(
            version=self.VERSION,
            backend=self.name,
            event_id=event_id,
            accepted=accepted,
            completed=completed,
            interrupted=interrupted,
            error=str(error or ""),
        )
