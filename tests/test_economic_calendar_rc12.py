"""Testes totalmente offline do replay observacional RC12."""

from economic_context import EconomicCalendarReplayTrialRunner


def row(event, *, country="United States", date="2026-08-25T12:30:00Z", importance=3):
    return {
        "CalendarId": event,
        "Date": date,
        "Country": country,
        "Event": event,
        "Importance": importance,
        "Currency": "BRL" if country == "Brazil" else "USD",
    }


def add_five_valid_sessions(runner):
    runner.add_session(
        session_id="D1",
        payload=[
            row("Copom Interest Rate Decision", country="Brazil"),
            row("IPCA Inflation", country="Brazil", date="2026-08-25T13:00:00Z"),
        ],
        expected_event_count=2,
        maximum_clock_error_seconds=10,
    )
    runner.add_session(
        session_id="D2",
        payload=[row("Non Farm Payrolls")],
        expected_event_count=1,
        maximum_clock_error_seconds=15,
    )
    runner.add_session(
        session_id="D3",
        payload=[row("US CPI Inflation")],
        expected_event_count=1,
        maximum_clock_error_seconds=20,
    )
    runner.add_session(
        session_id="D4",
        payload=[row("FOMC Rate Decision")],
        expected_event_count=1,
        maximum_clock_error_seconds=25,
    )
    runner.add_session(
        session_id="D5",
        payload=[row("Initial Jobless Claims")],
        expected_event_count=1,
        maximum_clock_error_seconds=30,
    )


def teste_runner_nao_expoe_capacidades_operacionais():
    report = EconomicCalendarReplayTrialRunner().report()
    assert report.observational_only
    assert not report.score_influence_allowed
    assert not report.order_execution_allowed


def teste_adiciona_sessao_e_mapeia_payload_pascal_case():
    runner = EconomicCalendarReplayTrialRunner()
    session = runner.add_session(
        session_id="D1",
        payload=[row("IPCA Inflation", country="Brazil")],
        expected_event_count=1,
        maximum_clock_error_seconds=10,
    )
    assert session.received_count == 1
    assert session.mapped_count == 1
    assert session.event_count == 1
    assert session.observational_only


def teste_rejeita_session_id_duplicado():
    runner = EconomicCalendarReplayTrialRunner()
    kwargs = {
        "session_id": "D1",
        "payload": [row("IPCA Inflation", country="Brazil")],
        "expected_event_count": 1,
        "maximum_clock_error_seconds": 10,
    }
    runner.add_session(**kwargs)
    try:
        runner.add_session(**kwargs)
    except ValueError:
        return
    raise AssertionError("Sessão duplicada deveria ser rejeitada.")


def teste_cobertura_e_calculada_contra_contagem_esperada():
    runner = EconomicCalendarReplayTrialRunner()
    runner.add_session(
        session_id="D1",
        payload=[row("IPCA Inflation", country="Brazil")],
        expected_event_count=2,
        maximum_clock_error_seconds=10,
    )
    assert runner.report().evidence.coverage_ratio == 0.5


def teste_pais_fora_do_escopo_reduz_cobertura_sem_virar_rejeicao():
    runner = EconomicCalendarReplayTrialRunner()
    session = runner.add_session(
        session_id="D1",
        payload=[row("ECB Rate Decision", country="Germany")],
        expected_event_count=1,
        maximum_clock_error_seconds=10,
    )
    assert session.event_count == 0
    assert session.rejected_count == 0
    assert runner.report().evidence.coverage_ratio == 0.0


def teste_linha_invalida_entra_na_taxa_de_rejeicao():
    runner = EconomicCalendarReplayTrialRunner()
    session = runner.add_session(
        session_id="D1",
        payload=[row("Payroll"), {"Country": "Brazil"}],
        expected_event_count=1,
        maximum_clock_error_seconds=10,
    )
    assert session.rejected_count == 1
    assert runner.report().evidence.rejection_ratio == 0.5


def teste_segredo_em_diagnostico_bloqueia_revisao():
    runner = EconomicCalendarReplayTrialRunner()
    runner.add_session(
        session_id="D1",
        payload=[row("Payroll")],
        expected_event_count=1,
        maximum_clock_error_seconds=10,
        diagnostic_text="source=https://provider.test?key=segredo123",
        forbidden_secret_values=("segredo123",),
    )
    report = runner.report()
    assert report.evidence.secrets_exposed
    assert "SECRET_EXPOSURE" in report.reasons


def teste_detecta_duplicacao_pelo_contrato_normalizado():
    runner = EconomicCalendarReplayTrialRunner()
    event = row("Payroll")
    session = runner.add_session(
        session_id="D1",
        payload=[event, dict(event)],
        expected_event_count=1,
        maximum_clock_error_seconds=10,
    )
    assert session.duplicate_count == 1
    assert runner.report().evidence.duplicate_ratio == 0.5


def teste_cinco_sessoes_e_eventos_criticos_liberam_apenas_revisao_manual():
    runner = EconomicCalendarReplayTrialRunner()
    add_five_valid_sessions(runner)
    report = runner.report()
    assert report.eligible_for_manual_review
    assert report.reasons == ()
    assert report.evidence.completed_sessions == 5
    assert set(report.evidence.critical_events_checked) == {
        "COPOM",
        "IPCA",
        "NON_FARM_PAYROLLS",
        "US_CPI",
        "FOMC",
        "JOBLESS_CLAIMS",
    }
    assert not report.score_influence_allowed
    assert not report.order_execution_allowed


def teste_clear_remove_toda_evidencia():
    runner = EconomicCalendarReplayTrialRunner()
    add_five_valid_sessions(runner)
    runner.clear()
    report = runner.report()
    assert report.evidence.completed_sessions == 0
    assert not report.eligible_for_manual_review
    assert "INSUFFICIENT_SESSIONS" in report.reasons


def main():
    tests = [value for name, value in globals().items() if name.startswith("teste_")]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 ECONOMIC CALENDAR RC12 APROVADO")


if __name__ == "__main__":
    main()
