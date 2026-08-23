import json

from analysis.replay.book_diagnostics_windows_voice_discovery import WindowsSAPIVoiceDiscovery
from analysis.replay.book_diagnostics_windows_sapi_backend import WindowsSAPITTSBackend


class RunResult:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def _which(name):
    return "powershell.exe" if name == "powershell" else None


def _run_with(voices):
    payload = json.dumps(voices)

    def runner(*args, **kwargs):
        return RunResult(stdout=payload, returncode=0)

    return runner


def test_discovery_unavailable_outside_windows():
    discovery = WindowsSAPIVoiceDiscovery(platform_name="Linux", which=_which)
    assert discovery.available() is False
    assert discovery.list_voices() == ()


def test_discovery_reads_installed_voices():
    discovery = WindowsSAPIVoiceDiscovery(
        platform_name="Windows",
        which=_which,
        run_factory=_run_with([
            {"Name": "Microsoft Maria", "Culture": "pt-BR", "Gender": "Female", "Age": "Adult", "Enabled": True},
            {"Name": "Microsoft George", "Culture": "en-GB", "Gender": "Male", "Age": "Adult", "Enabled": True},
        ]),
    )
    voices = discovery.list_voices()
    assert len(voices) == 2
    assert voices[0].readonly is True
    assert voices[0].affects_decision is False


def test_exact_language_has_priority():
    discovery = WindowsSAPIVoiceDiscovery(
        platform_name="Windows",
        which=_which,
        run_factory=_run_with([
            {"Name": "PT Voice", "Culture": "pt-BR", "Gender": "Female", "Age": "Adult", "Enabled": True},
            {"Name": "UK Voice", "Culture": "en-GB", "Gender": "Male", "Age": "Adult", "Enabled": True},
        ]),
    )
    selected = discovery.select(voice_profile="BRITISH_CALM_PRECISE_ASSISTANT", language="pt-BR")
    assert selected.selected_voice == "PT Voice"
    assert selected.reason == "LANGUAGE_MATCH"


def test_profile_culture_used_when_language_missing():
    discovery = WindowsSAPIVoiceDiscovery(
        platform_name="Windows",
        which=_which,
        run_factory=_run_with([
            {"Name": "UK Voice", "Culture": "en-GB", "Gender": "Male", "Age": "Adult", "Enabled": True},
            {"Name": "US Voice", "Culture": "en-US", "Gender": "Female", "Age": "Adult", "Enabled": True},
        ]),
    )
    selected = discovery.select(voice_profile="BRITISH_CALM_PRECISE_ASSISTANT", language="pt-BR")
    assert selected.selected_voice == "UK Voice"
    assert selected.reason == "PROFILE_CULTURE_MATCH"


def test_fallback_uses_first_enabled_voice():
    discovery = WindowsSAPIVoiceDiscovery(
        platform_name="Windows",
        which=_which,
        run_factory=_run_with([
            {"Name": "First", "Culture": "en-US", "Gender": "Female", "Age": "Adult", "Enabled": True},
        ]),
    )
    selected = discovery.select(voice_profile="CUSTOM", language="pt-BR")
    assert selected.selected_voice == "First"
    assert selected.matched is False
    assert selected.reason == "DEFAULT_ENABLED_VOICE"


def test_disabled_voices_are_ignored():
    discovery = WindowsSAPIVoiceDiscovery(
        platform_name="Windows",
        which=_which,
        run_factory=_run_with([
            {"Name": "Disabled", "Culture": "pt-BR", "Gender": "Female", "Age": "Adult", "Enabled": False},
        ]),
    )
    selected = discovery.select(voice_profile="CUSTOM", language="pt-BR")
    assert selected.selected_voice is None
    assert selected.reason == "NO_ENABLED_VOICES"


def test_invalid_json_returns_empty_list():
    discovery = WindowsSAPIVoiceDiscovery(
        platform_name="Windows",
        which=_which,
        run_factory=lambda *a, **k: RunResult(stdout="not-json", returncode=0),
    )
    assert discovery.list_voices() == ()


def test_failed_discovery_process_returns_empty_list():
    discovery = WindowsSAPIVoiceDiscovery(
        platform_name="Windows",
        which=_which,
        run_factory=lambda *a, **k: RunResult(stdout="", stderr="boom", returncode=1),
    )
    assert discovery.list_voices() == ()


class FakeSelection:
    selected_voice = "Chosen Voice"


class FakeDiscovery:
    def list_voices(self):
        return ("voice",)

    def select(self, *, voice_profile, language):
        assert voice_profile == "BRITISH_CALM_PRECISE_ASSISTANT"
        assert language == "pt-BR"
        return FakeSelection()


class FakeProcess:
    def __init__(self):
        self.returncode = 0

    def communicate(self):
        return "", ""

    def terminate(self):
        return None


def _command():
    return {
        "version": "RC33-VOICE-OUTPUT-ADAPTER",
        "command": "SPEAK",
        "event_id": "voice-rc44",
        "text": "Mensagem de teste.",
        "priority": "NORMAL",
        "interrupt": False,
        "voice_profile": "BRITISH_CALM_PRECISE_ASSISTANT",
        "language": "pt-BR",
        "speech_rate": 1.0,
        "estimated_duration_seconds": 2.0,
        "source_version": "RC31-VOICE-EVENT-CONTRACT",
        "readonly": True,
        "affects_decision": False,
    }


def test_backend_exposes_available_voices():
    backend = WindowsSAPITTSBackend(
        platform_name="Windows",
        which=_which,
        voice_discovery=FakeDiscovery(),
    )
    assert backend.available_voices() == ("voice",)


def test_backend_select_voice_delegates_to_discovery():
    backend = WindowsSAPITTSBackend(
        platform_name="Windows",
        which=_which,
        voice_discovery=FakeDiscovery(),
    )
    selected = backend.select_voice(
        voice_profile="BRITISH_CALM_PRECISE_ASSISTANT",
        language="pt-BR",
    )
    assert selected.selected_voice == "Chosen Voice"


def test_backend_script_selects_discovered_voice():
    captured = {}

    def popen(args, **kwargs):
        captured["args"] = args
        return FakeProcess()

    backend = WindowsSAPITTSBackend(
        platform_name="Windows",
        which=_which,
        voice_discovery=FakeDiscovery(),
        popen_factory=popen,
    )
    result = backend.speak(_command())
    assert result.completed is True
    script = captured["args"][-1]
    assert "SelectVoice" in script
    assert "Chosen Voice" not in script


def test_selection_is_readonly_and_never_affects_decision():
    discovery = WindowsSAPIVoiceDiscovery(
        platform_name="Windows",
        which=_which,
        run_factory=_run_with([
            {"Name": "PT Voice", "Culture": "pt-BR", "Gender": "Female", "Age": "Adult", "Enabled": True},
        ]),
    )
    selected = discovery.select(voice_profile="CUSTOM", language="pt-BR")
    assert selected.readonly is True
    assert selected.affects_decision is False
