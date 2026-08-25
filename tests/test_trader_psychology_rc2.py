"""Testes offline do TraderPsychologyEngine RC2."""

from psychology import (
    TraderPsychologyEngine,
    TraderPsychologyPolicy,
    TraderPsychologyState,
)


def analyze(**changes):
    return TraderPsychologyEngine().analyze(
        TraderPsychologyState(**changes)
    )


def codes(result):
    return {signal.code for signal in result.signals}


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_estado_neutro_nao_gera_alerta():
    result = analyze()
    assert result.status == "NEUTRAL"
    assert result.severity == "NONE"
    assert result.signals == ()
    assert not result.pause_recommended


def teste_detecta_overtrading_no_limite():
    result = analyze(trades_today=6)
    assert "OVERTRADING" in codes(result)
    assert result.severity == "HIGH"
    assert not result.pause_recommended


def teste_detecta_revenge_trading():
    result = analyze(
        last_trade_was_loss=True,
        seconds_since_last_exit=120,
        skipped_confirmation=True,
    )
    assert "REVENGE_TRADING" in codes(result)
    assert "FOMO" in codes(result)


def teste_revenge_com_aumento_de_mao_e_extremo():
    result = analyze(
        last_trade_was_loss=True,
        seconds_since_last_exit=90,
        increased_size_after_loss=True,
    )
    assert result.pause_recommended
    assert "EXTREME_REVENGE_PATTERN" in result.pause_reason_codes
    assert result.severity == "EXTREME"


def teste_detecta_sequencia_de_stops_e_recomenda_pausa():
    result = analyze(consecutive_losses=3)
    assert "STOP_SEQUENCE" in codes(result)
    assert result.pause_recommended
    assert "STOP_SEQUENCE" in result.pause_reason_codes


def teste_detecta_fomo_por_perseguir_preco():
    result = analyze(chased_price=True)
    signal = next(
        item for item in result.signals if item.code == "FOMO"
    )
    assert signal.severity == "MEDIUM"
    assert "chased_price" in signal.evidence
    assert not result.pause_recommended


def teste_detecta_pressa_apos_loss():
    result = analyze(
        last_trade_was_loss=True,
        seconds_since_last_exit=30,
    )
    assert "RUSHED_REENTRY" in codes(result)
    assert result.severity == "HIGH"
    assert not result.pause_recommended


def teste_detecta_excesso_de_confianca():
    result = analyze(
        trade_size_multiplier=1.5,
        session_pnl_r=2.0,
    )
    assert "OVERCONFIDENCE" in codes(result)
    assert not result.pause_recommended


def teste_detecta_entrada_fora_do_plano():
    result = analyze(plan_checklist_passed=False)
    assert "OUTSIDE_PLAN" in codes(result)
    assert result.severity == "HIGH"


def teste_perda_diaria_extrema_recomenda_pausa():
    result = analyze(daily_loss_r=3.0)
    assert result.pause_recommended
    assert "EXTREME_DAILY_LOSS" in result.pause_reason_codes
    assert result.severity == "EXTREME"


def teste_pausa_manual_e_respeitada_sem_bloqueio():
    result = analyze(manual_pause_requested=True)
    assert result.pause_recommended
    assert "MANUAL_PAUSE" in result.pause_reason_codes
    assert not result.operational_block_allowed
    assert not result.order_execution_allowed


def teste_resultado_nunca_altera_score_ou_ordens():
    result = analyze(
        trades_today=10,
        consecutive_losses=4,
        chased_price=True,
        plan_checklist_passed=False,
    )
    assert result.observational_only
    assert not result.score_influence_allowed
    assert not result.order_execution_allowed
    assert not result.operational_block_allowed


def teste_politica_invalida_e_rejeitada():
    raises(
        ValueError,
        lambda: TraderPsychologyPolicy(
            maximum_trades_per_session=0
        ),
    )
    raises(
        ValueError,
        lambda: TraderPsychologyPolicy(
            rushed_reentry_seconds=200,
            revenge_window_seconds=100,
        ),
    )


def teste_engine_rejeita_estado_incompativel():
    raises(
        TypeError,
        lambda: TraderPsychologyEngine().analyze({}),
    )


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 TRADER PSYCHOLOGY RC2 APROVADO")


if __name__ == "__main__":
    main()
