"""
BookDiagnostics RC44 - Windows Voice Discovery / Selection.

Descobre vozes SAPI instaladas no Windows e resolve um voice_profile abstrato
para uma voz concreta quando possivel. A camada e somente de apresentacao e
nao altera Strategy, Score, Risk, Decision ou Alert.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import platform
import shutil
import subprocess
from typing import Callable


@dataclass(slots=True, frozen=True)
class WindowsVoiceInfo:
    name: str
    culture: str
    gender: str
    age: str
    enabled: bool
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class WindowsVoiceSelection:
    version: str
    requested_profile: str
    requested_language: str
    selected_voice: str | None
    matched: bool
    reason: str
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class WindowsSAPIVoiceDiscovery:
    VERSION = "RC44-WINDOWS-VOICE-DISCOVERY"

    PROFILE_HINTS = {
        "BRITISH_CALM_PRECISE_ASSISTANT": ("en-GB", "male", "female"),
    }

    def __init__(
        self,
        *,
        run_factory: Callable = subprocess.run,
        which: Callable[[str], str | None] = shutil.which,
        platform_name: str | None = None,
    ):
        self._run_factory = run_factory
        self._which = which
        self._platform_name = platform_name

    def available(self) -> bool:
        system = (self._platform_name or platform.system()).strip().lower()
        return system == "windows" and self._powershell_executable() is not None

    def list_voices(self) -> tuple[WindowsVoiceInfo, ...]:
        if not self.available():
            return ()

        executable = self._powershell_executable()
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$items = $s.GetInstalledVoices() | ForEach-Object { "
            "$i=$_.VoiceInfo; [PSCustomObject]@{Name=$i.Name;Culture=$i.Culture.Name;"
            "Gender=$i.Gender.ToString();Age=$i.Age.ToString();Enabled=$_.Enabled} }; "
            "$items | ConvertTo-Json -Compress; $s.Dispose();"
        )
        try:
            result = self._run_factory(
                [executable, "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except Exception:
            return ()

        if int(getattr(result, "returncode", 1) or 0) != 0:
            return ()

        raw = str(getattr(result, "stdout", "") or "").strip()
        if not raw:
            return ()
        try:
            parsed = json.loads(raw)
        except Exception:
            return ()
        if isinstance(parsed, dict):
            parsed = [parsed]

        voices = []
        for item in parsed or []:
            name = str(item.get("Name", "") or "").strip()
            if not name:
                continue
            voices.append(
                WindowsVoiceInfo(
                    name=name,
                    culture=str(item.get("Culture", "") or ""),
                    gender=str(item.get("Gender", "") or ""),
                    age=str(item.get("Age", "") or ""),
                    enabled=bool(item.get("Enabled", False)),
                )
            )
        return tuple(voices)

    def select(self, *, voice_profile: str, language: str) -> WindowsVoiceSelection:
        profile = str(voice_profile or "").strip()
        requested_language = str(language or "").strip()
        if not profile:
            raise ValueError("voice_profile cannot be empty")
        if not requested_language:
            raise ValueError("language cannot be empty")

        voices = tuple(v for v in self.list_voices() if v.enabled)
        if not voices:
            return WindowsVoiceSelection(
                version=self.VERSION,
                requested_profile=profile,
                requested_language=requested_language,
                selected_voice=None,
                matched=False,
                reason="NO_ENABLED_VOICES",
            )

        exact_language = [v for v in voices if v.culture.lower() == requested_language.lower()]
        if exact_language:
            return self._selection(profile, requested_language, exact_language[0], "LANGUAGE_MATCH")

        hints = self.PROFILE_HINTS.get(profile.upper(), ())
        hinted_culture = hints[0] if hints else None
        if hinted_culture:
            culture_matches = [v for v in voices if v.culture.lower() == hinted_culture.lower()]
            if culture_matches:
                return self._selection(profile, requested_language, culture_matches[0], "PROFILE_CULTURE_MATCH")

        return self._selection(profile, requested_language, voices[0], "DEFAULT_ENABLED_VOICE")

    def _selection(self, profile: str, language: str, voice: WindowsVoiceInfo, reason: str):
        return WindowsVoiceSelection(
            version=self.VERSION,
            requested_profile=profile,
            requested_language=language,
            selected_voice=voice.name,
            matched=reason != "DEFAULT_ENABLED_VOICE",
            reason=reason,
        )

    def _powershell_executable(self) -> str | None:
        return self._which("powershell") or self._which("pwsh")
