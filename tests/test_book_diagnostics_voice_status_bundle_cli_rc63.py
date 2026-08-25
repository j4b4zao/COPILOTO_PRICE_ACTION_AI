from app import voice_status_bundle_cli


def test_parser_has_no_speak_or_text_options():
    help_text = voice_status_bundle_cli.build_parser().format_help()
    assert "--speak" not in help_text
    assert "--text" not in help_text


def test_parser_has_json_option():
    help_text = voice_status_bundle_cli.build_parser().format_help()
    assert "--json" in help_text


def test_parser_defaults_are_readonly_safe():
    args = voice_status_bundle_cli.build_parser().parse_args([])
    assert args.enabled is False
    assert args.backend == "NULL_TTS"
    assert args.language == "pt-BR"
    assert args.as_json is False


def test_parser_normalizes_configuration_in_run_contract():
    args = voice_status_bundle_cli.build_parser().parse_args([
        "--backend", "windows_sapi",
        "--language", "pt-BR",
        "--profile", "BRITISH_CALM_PRECISE_ASSISTANT",
        "--rate", "1.1",
    ])
    assert args.backend == "windows_sapi"
    assert args.rate == 1.1


def test_module_has_run_and_main_entrypoints():
    assert callable(voice_status_bundle_cli.run)
    assert callable(voice_status_bundle_cli.main)


def test_module_does_not_expose_audio_test_entrypoint():
    assert not hasattr(voice_status_bundle_cli, "test_audio")
    assert not hasattr(voice_status_bundle_cli, "speak")


def test_source_uses_status_bundle_only_for_presentation():
    import inspect
    source = inspect.getsource(voice_status_bundle_cli)
    assert "status_bundle()" in source
    assert "test_audio(" not in source
    assert ".speak(" not in source


def test_text_mode_contains_three_sections():
    import inspect
    source = inspect.getsource(voice_status_bundle_cli)
    assert "VOICE STATUS BUNDLE" in source
    assert "HEALTH REPORT" in source
    assert "DASHBOARD PROJECTION" in source
    assert "DASHBOARD WIDGET" in source


def test_json_mode_serializes_bundle_payload():
    import inspect
    source = inspect.getsource(voice_status_bundle_cli)
    assert "bundle.to_dict()" in source
    assert "json.dumps" in source


def test_exit_policy_marks_degraded_as_nonzero():
    import inspect
    source = inspect.getsource(voice_status_bundle_cli)
    assert '"DEGRADED"' not in source.split("return 0 if bundle.status in", 1)[1].split("else 2", 1)[0]
