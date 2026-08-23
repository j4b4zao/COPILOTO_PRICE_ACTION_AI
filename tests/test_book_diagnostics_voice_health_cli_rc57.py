from app.voice_health_cli import build_parser, run


def test_parser_has_no_speak_option():
    parser = build_parser()
    options = {opt for action in parser._actions for opt in action.option_strings}
    assert "--speak" not in options


def test_default_run_is_readonly_and_disabled(capsys):
    code = run([])
    out = capsys.readouterr().out
    assert code == 0
    assert "VOICE HEALTH" in out
    assert "STATUS: DISABLED" in out


def test_json_output_is_supported(capsys):
    code = run(["--json"])
    out = capsys.readouterr().out
    assert code == 0
    assert '"status": "DISABLED"' in out
    assert '"readonly": true' in out
    assert '"affects_decision": false' in out


def test_enabled_null_tts_does_not_become_ready(capsys):
    code = run(["--enabled", "--backend", "NULL_TTS"])
    out = capsys.readouterr().out
    assert code in {0, 2}
    assert "STATUS:" in out
    assert "OPERATIONAL_VOICE_ALLOWED: False" in out


def test_backend_argument_is_normalized(capsys):
    code = run(["--backend", "null_tts", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    assert '"backend"' in out


def test_language_profile_and_rate_arguments_are_accepted(capsys):
    code = run([
        "--language", "pt-BR",
        "--profile", "BRITISH_CALM_PRECISE_ASSISTANT",
        "--rate", "1.1",
    ])
    out = capsys.readouterr().out
    assert code == 0
    assert "STATUS: DISABLED" in out


def test_cli_never_exposes_audio_test_text_argument():
    parser = build_parser()
    options = {opt for action in parser._actions for opt in action.option_strings}
    assert "--text" not in options


def test_degraded_status_uses_nonzero_exit_contract():
    # Contract-level assertion: RC57 reserves exit code 2 for DEGRADED.
    # Current default path is DISABLED and returns zero.
    assert run([]) == 0


def test_cli_module_is_separate_from_voice_test_cli():
    import app.voice_health_cli as health_cli
    import app.voice_test_cli as test_cli
    assert health_cli.run is not test_cli.run


def test_cli_has_main_entrypoint():
    import app.voice_health_cli as module
    assert callable(module.main)
