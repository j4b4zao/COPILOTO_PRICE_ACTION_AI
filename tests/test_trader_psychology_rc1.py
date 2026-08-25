"""Testes offline do estado Psicologia do Trader RC1."""

from psychology import TraderPsychologyState


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_estado_padrao_e_neutro_e_observacional():
    state = TraderPsychologyState()
    assert state.trades_today == 0
    assert state.consecutive_losses == 0
    assert state.observational_only
    assert not state.score_influence_allowed
    assert not state.order_execution_allowed


def teste_snapshot_aceita_fatos_de_comportamento():
    state = TraderPsychologyState(
        trades_today=4,
        consecutive_losses=2,
        seconds_since_last_exit=45,
        last_trade_was_loss=True,
        trade_size_multiplier=1.5,
        daily_loss_r=2.0,
        session_pnl_r=-2.0,
        plan_checklist_passed=False,
        chased_price=True,
        skipped_confirmation=True,
        increased_size_after_loss=True,
    )
    assert state.has_recent_exit
    assert state.chased_price
    assert state.session_pnl_r == -2.0


def teste_contagens_negativas_sao_rejeitadas():
    raises(
        ValueError,
        lambda: TraderPsychologyState(trades_today=-1),
    )
    raises(
        ValueError,
        lambda: TraderPsychologyState(consecutive_losses=-1),
    )


def teste_booleano_nao_passa_como_contagem():
    raises(
        TypeError,
        lambda: TraderPsychologyState(trades_today=True),
    )


def teste_tempo_desde_saida_deve_ser_valido():
    raises(
        ValueError,
        lambda: TraderPsychologyState(seconds_since_last_exit=-1),
    )
    raises(
        ValueError,
        lambda: TraderPsychologyState(
            seconds_since_last_exit=float("nan")
        ),
    )


def teste_multiplicador_de_tamanho_tem_limite_seguro():
    raises(
        ValueError,
        lambda: TraderPsychologyState(trade_size_multiplier=-0.1),
    )
    raises(
        ValueError,
        lambda: TraderPsychologyState(trade_size_multiplier=10.1),
    )


def teste_metricas_r_devem_ser_finitas():
    raises(
        ValueError,
        lambda: TraderPsychologyState(daily_loss_r=float("inf")),
    )
    raises(
        ValueError,
        lambda: TraderPsychologyState(session_pnl_r=float("nan")),
    )


def teste_sinais_comportamentais_exigem_booleanos():
    raises(
        TypeError,
        lambda: TraderPsychologyState(chased_price=1),
    )
    raises(
        TypeError,
        lambda: TraderPsychologyState(plan_checklist_passed="sim"),
    )


def teste_flags_operacionais_nao_podem_ser_liberadas():
    raises(
        ValueError,
        lambda: TraderPsychologyState(
            score_influence_allowed=True
        ),
    )
    raises(
        ValueError,
        lambda: TraderPsychologyState(
            order_execution_allowed=True
        ),
    )


def teste_exportacao_preserva_apenas_estado_observacional():
    state = TraderPsychologyState(
        trades_today=3,
        manual_pause_requested=True,
    )
    payload = state.to_observational_dict()
    assert payload["trades_today"] == 3
    assert payload["manual_pause_requested"]
    assert payload["observational_only"]
    assert not payload["score_influence_allowed"]
    assert not payload["order_execution_allowed"]


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 TRADER PSYCHOLOGY RC1 APROVADO")


if __name__ == "__main__":
    main()
