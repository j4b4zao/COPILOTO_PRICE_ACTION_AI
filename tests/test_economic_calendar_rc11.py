"""Testes offline do contrato de ensaio observacional RC11."""

from economic_context import (
    EconomicCalendarTrialEvidence,
    EconomicCalendarTrialGate,
    EconomicCalendarTrialPolicy,
)


CRITICAL = (
    "COPOM",
    "IPCA",
    "NON_FARM_PAYROLLS",
    "US_CPI",
    "FOMC",
    "JOBLESS_CLAIMS",
)


def valid_evidence(**changes):
    values = {
        "completed_sessions": 5,
        "coverage_ratio": 0.98,
        "rejection_ratio": 0.01,
        "duplicate_ratio": 0.01,
        "maximum_clock_error_seconds": 30,
        "critical_events_checked": CRITICAL,
        "secrets_exposed": False,
    }
    values.update(changes)
    return EconomicCalendarTrialEvidence(**values)


def teste_politica_e_observacional_e_sem_influencia():
    policy = EconomicCalendarTrialPolicy()
    assert policy.observational_only
    assert not policy.score_influence_allowed
    assert not policy.order_execution_allowed
    assert policy.countries == ("BR", "US")


def teste_politica_rejeita_menos_de_cinco_pregoes():
    try:
        EconomicCalendarTrialPolicy(minimum_sessions=4)
    except ValueError:
        return
    raise AssertionError("Menos de cinco pregões não deveria ser permitido.")


def teste_politica_rejeita_influencia_no_score_ou_ordens():
    for changes in (
        {"score_influence_allowed": True},
        {"order_execution_allowed": True},
        {"observational_only": False},
    ):
        try:
            EconomicCalendarTrialPolicy(**changes)
        except ValueError:
            continue
        raise AssertionError(f"Política insegura aceita: {changes}")


def teste_evidencia_completa_fica_apenas_elegivel_para_revisao_manual():
    decision = EconomicCalendarTrialGate().evaluate(valid_evidence())
    assert decision.eligible_for_manual_review
    assert decision.reasons == ()


def teste_sessoes_insuficientes_bloqueiam_revisao():
    decision = EconomicCalendarTrialGate().evaluate(
        valid_evidence(completed_sessions=4)
    )
    assert not decision.eligible_for_manual_review
    assert "INSUFFICIENT_SESSIONS" in decision.reasons


def teste_segredo_exposto_bloqueia_mesmo_com_metricas_perfeitas():
    decision = EconomicCalendarTrialGate().evaluate(
        valid_evidence(secrets_exposed=True)
    )
    assert not decision.eligible_for_manual_review
    assert decision.reasons[0] == "SECRET_EXPOSURE"


def teste_eventos_criticos_incompletos_bloqueiam():
    decision = EconomicCalendarTrialGate().evaluate(
        valid_evidence(critical_events_checked=("COPOM", "IPCA", "FOMC"))
    )
    assert "CRITICAL_EVENTS_NOT_VERIFIED" in decision.reasons


def teste_todas_as_falhas_de_qualidade_sao_reportadas():
    decision = EconomicCalendarTrialGate().evaluate(
        valid_evidence(
            coverage_ratio=0.80,
            rejection_ratio=0.20,
            duplicate_ratio=0.10,
            maximum_clock_error_seconds=120,
        )
    )
    assert decision.reasons == (
        "INSUFFICIENT_COVERAGE",
        "EXCESSIVE_REJECTIONS",
        "EXCESSIVE_DUPLICATES",
        "CLOCK_MISMATCH",
    )


def main():
    tests = [value for name, value in globals().items() if name.startswith("teste_")]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 ECONOMIC CALENDAR RC11 APROVADO")


if __name__ == "__main__":
    main()
