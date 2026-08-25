"""Testes offline do CoachingEngine RC3."""

from psychology import (
    CoachingEngine,
    CoachingPolicy,
    TraderPsychologyEngine,
    TraderPsychologyResult,
    TraderPsychologySignal,
    TraderPsychologyState,
)


def coaching(**changes):
    psychology = TraderPsychologyEngine().analyze(
        TraderPsychologyState(**changes)
    )
    return CoachingEngine().build(psychology)


def codes(result):
    return [message.code for message in result.messages]


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_estado_neutro_permanece_silencioso():
    result = coaching()
    assert result.status == "SILENT"
    assert result.messages == ()
    assert not result.pause_recommended


def teste_overtrading_gera_mensagem_curta():
    result = coaching(trades_today=6)
    assert result.status == "GUIDANCE"
    assert codes(result) == ["OVERTRADING"]
    assert "qualidade" in result.messages[0].text.casefold()


def teste_revenge_trading_gera_orientacao_sem_julgamento():
    result = coaching(
        last_trade_was_loss=True,
        seconds_since_last_exit=100,
        increased_size_after_loss=True,
    )
    assert result.status == "PAUSE_RECOMMENDED"
    assert codes(result)[0] == "PAUSE_RECOMMENDED"
    assert "REVENGE_TRADING" in codes(result)


def teste_sequencia_de_stops_prioriza_pausa():
    result = coaching(consecutive_losses=3)
    assert result.pause_recommended
    assert codes(result)[0] == "PAUSE_RECOMMENDED"
    assert "STOP_SEQUENCE" in codes(result)


def teste_fomo_orienta_esperar_confirmacao():
    result = coaching(chased_price=True)
    message = result.messages[0].text.casefold()
    assert "espere confirmação" in message
    assert "compre" not in message
    assert "venda" not in message


def teste_pressa_orienta_aguardar_nova_informacao():
    result = coaching(
        last_trade_was_loss=True,
        seconds_since_last_exit=30,
    )
    assert "RUSHED_REENTRY" in codes(result)
    text = next(
        item.text
        for item in result.messages
        if item.code == "RUSHED_REENTRY"
    )
    assert "nova informação" in text


def teste_excesso_de_confianca_preserva_padrao_de_risco():
    result = coaching(
        trade_size_multiplier=1.5,
        session_pnl_r=2.0,
    )
    assert "OVERCONFIDENCE" in codes(result)
    assert "disciplina" in result.messages[0].text.casefold()


def teste_fora_do_plano_pede_revisao_do_checklist():
    result = coaching(plan_checklist_passed=False)
    assert "OUTSIDE_PLAN" in codes(result)
    assert "checklist" in result.messages[0].text.casefold()


def teste_limite_de_mensagens_e_respeitado():
    psychology = TraderPsychologyEngine().analyze(
        TraderPsychologyState(
            trades_today=8,
            consecutive_losses=3,
            last_trade_was_loss=True,
            seconds_since_last_exit=20,
            chased_price=True,
            skipped_confirmation=True,
            increased_size_after_loss=True,
            plan_checklist_passed=False,
        )
    )
    result = CoachingEngine(
        policy=CoachingPolicy(maximum_messages=2)
    ).build(psychology)
    assert len(result.messages) == 2
    assert result.messages[0].code == "PAUSE_RECOMMENDED"


def teste_mensagens_repetidas_sao_deduplicadas():
    result = TraderPsychologyResult(
        status="ATTENTION",
        severity="HIGH",
        signals=(
            TraderPsychologySignal("FOMO", "MEDIUM", ("a",)),
            TraderPsychologySignal("FOMO", "MEDIUM", ("b",)),
        ),
        pause_recommended=False,
        pause_reason_codes=(),
    )
    coaching_result = CoachingEngine().build(result)
    assert codes(coaching_result) == ["FOMO"]


def teste_comandos_operacionais_sao_rejeitados():
    engine = CoachingEngine()
    engine.MESSAGE_BY_SIGNAL = dict(engine.MESSAGE_BY_SIGNAL)
    engine.MESSAGE_BY_SIGNAL["FOMO"] = "Compre agora."
    result = TraderPsychologyResult(
        status="ATTENTION",
        severity="MEDIUM",
        signals=(
            TraderPsychologySignal("FOMO", "MEDIUM", ("teste",)),
        ),
        pause_recommended=False,
        pause_reason_codes=(),
    )
    raises(ValueError, lambda: engine.build(result))


def teste_resultado_nao_toca_score_ordens_ou_bloqueio():
    result = coaching(
        consecutive_losses=4,
        daily_loss_r=4,
    )
    assert result.observational_only
    assert not result.score_influence_allowed
    assert not result.order_execution_allowed
    assert not result.operational_block_allowed


def teste_politica_invalida_e_rejeitada():
    raises(
        ValueError,
        lambda: CoachingPolicy(maximum_messages=0),
    )
    raises(
        ValueError,
        lambda: CoachingPolicy(maximum_message_characters=50),
    )


def teste_engine_rejeita_resultado_incompativel():
    raises(TypeError, lambda: CoachingEngine().build({}))


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 TRADER PSYCHOLOGY RC3 APROVADO")


if __name__ == "__main__":
    main()
