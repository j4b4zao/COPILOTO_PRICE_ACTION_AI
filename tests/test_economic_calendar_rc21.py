"""Testes offline das proteções operacionais RC21."""

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
GITIGNORE = ROOT / ".gitignore"
RUNBOOK = (
    ROOT
    / "docs"
    / "providers"
    / "TRADING_ECONOMICS_WINDOWS_RUNBOOK.md"
)


def gitignore():
    return GITIGNORE.read_text(encoding="utf-8")


def runbook():
    return RUNBOOK.read_text(encoding="utf-8")


def teste_env_local_permanece_ignorado():
    text = gitignore()
    assert ".env\\n" in text
    assert ".env.*" in text


def teste_arquivos_de_credencial_sao_ignorados():
    text = gitignore()
    for pattern in (
        "*.pem",
        "*.key",
        "*.p12",
        "*.pfx",
        "credentials.json",
        "secrets.json",
    ):
        assert pattern in text


def teste_pacotes_de_replay_sao_ignorados():
    assert "*.calendar-replay.json" in gitignore()


def teste_runbook_comeca_por_preflight():
    text = runbook()
    preflight = text.index("Executar somente o pré-voo")
    execute = text.index("Executar uma captura controlada")
    assert preflight < execute


def teste_runbook_exige_duas_flags_para_captura():
    text = runbook()
    assert "--capture-enabled --execute" in text


def teste_runbook_nao_coloca_chave_em_argumento():
    text = runbook()
    command_lines = [
        line
        for line in text.splitlines()
        if "python -m app.economic_calendar_capture_cli" in line
    ]
    assert command_lines
    assert all("api-key" not in line.casefold() for line in command_lines)
    assert all("COPILOTO_TE_API_KEY" not in line for line in command_lines)


def teste_runbook_usa_entrada_oculta():
    text = runbook()
    assert 'Read-Host "Trading Economics API key" -AsSecureString' in text
    assert "SecureStringToBSTR" in text
    assert "ZeroFreeBSTR" in text


def teste_runbook_remove_variaveis_ao_final():
    text = runbook()
    assert "Remove-Item Env:COPILOTO_TE_API_KEY" in text
    assert "Remove-Item Env:COPILOTO_TE_ENABLED" in text


def teste_runbook_documenta_rotacao_em_incidente():
    text = runbook().casefold()
    assert "revogar/rotacionar" in text
    assert "não reutilizar a chave exposta" in text


def teste_runbook_preserva_limites_operacionais():
    text = runbook()
    assert "não altera o `ScoreEngine`" in text
    assert "não envia nem executa ordens" in text
    assert "permanece observacional" in text


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 ECONOMIC CALENDAR RC21 APROVADO")


if __name__ == "__main__":
    main()
