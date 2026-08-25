"""Testes offline do provedor factual de sessão RC8."""

from datetime import datetime, timedelta

from psychology import (
    TraderPsychologySessionProvider,
    TraderPsychologyState,
)


class FakeClock:
    def __init__(self):
        self.value = datetime(2026, 8, 25, 9, 0, 0)

    def __call__(self):
        return self.value

    def advance(self, **changes):
        self.value += timedelta(**changes)


def provider():
    clock = FakeClock()
    return TraderPsychologySessionProvider(clock=clock), clock


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_snapshot_inicial_e_neutro():
    session, _ = provider()
    state = session.snapshot(None)
    assert isinstance(state, TraderPsychologyState)
    assert state.trades_today == 0
    assert state.consecutive_losses == 0
    assert state.seconds_since_last_exit is None
    assert state.plan_checklist_passed


def teste_abertura_registra_somente_fatos_explicitos():
    session, _ = provider()
    state = session.record_trade_open(
        quantity=2,
        plan_checklist_passed=False,
        chased_price=True,
        skipped_confirmation=True,
    )
    assert session.trade_open
    assert state.trades_today == 1
    assert state.trade_size_multiplier == 2.0
    assert not state.plan_checklist_passed
    assert state.chased_price
    assert state.skipped_confirmation


def teste_fechamento_negativo_registra_loss_em_r():
    session, _ = provider()
    session.record_trade_open(
        quantity=1,
        plan_checklist_passed=True,
    )
    state = session.record_trade_close(result_r=-1.25)
    assert not session.trade_open
    assert state.last_trade_was_loss
    assert state.consecutive_losses == 1
    assert state.daily_loss_r == 1.25
    assert state.session_pnl_r == -1.25


def teste_win_reseta_sequencia_sem_apagar_perda_diaria():
    session, _ = provider()
    session.record_trade_open(quantity=1, plan_checklist_passed=True)
    session.record_trade_close(result_r=-1.0)
    session.record_trade_open(quantity=1, plan_checklist_passed=True)
    state = session.record_trade_close(result_r=2.0)
    assert not state.last_trade_was_loss
    assert state.consecutive_losses == 0
    assert state.daily_loss_r == 1.0
    assert state.session_pnl_r == 1.0


def teste_breakeven_reseta_sequencia_de_losses():
    session, _ = provider()
    session.record_trade_open(quantity=1, plan_checklist_passed=True)
    session.record_trade_close(result_r=-1.0)
    session.record_trade_open(quantity=1, plan_checklist_passed=True)
    state = session.record_trade_close(result_r=0.0)
    assert not state.last_trade_was_loss
    assert state.consecutive_losses == 0
    assert state.session_pnl_r == -1.0


def teste_losses_consecutivos_sao_acumulados():
    session, _ = provider()
    for result_r in (-1.0, -0.5, -1.5):
        session.record_trade_open(
            quantity=1,
            plan_checklist_passed=True,
        )
        state = session.record_trade_close(result_r=result_r)
    assert state.trades_today == 3
    assert state.consecutive_losses == 3
    assert state.daily_loss_r == 3.0
    assert state.session_pnl_r == -3.0


def teste_aumento_de_mao_apos_loss_e_factual():
    session, _ = provider()
    session.record_trade_open(quantity=1, plan_checklist_passed=True)
    session.record_trade_close(result_r=-1.0)
    state = session.record_trade_open(
        quantity=2,
        plan_checklist_passed=True,
    )
    assert state.increased_size_after_loss
    assert state.trade_size_multiplier == 2.0


def teste_mao_igual_apos_loss_nao_marca_aumento():
    session, _ = provider()
    session.record_trade_open(quantity=2, plan_checklist_passed=True)
    session.record_trade_close(result_r=-1.0)
    state = session.record_trade_open(
        quantity=2,
        plan_checklist_passed=True,
    )
    assert not state.increased_size_after_loss


def teste_tempo_desde_ultima_saida_usa_relogio():
    session, clock = provider()
    session.record_trade_open(quantity=1, plan_checklist_passed=True)
    session.record_trade_close(result_r=-1.0)
    clock.advance(seconds=75)
    state = session.snapshot(None)
    assert state.seconds_since_last_exit == 75.0


def teste_pausa_manual_pode_ser_solicitada_e_limpada():
    session, _ = provider()
    assert session.request_manual_pause().manual_pause_requested
    assert not session.clear_manual_pause().manual_pause_requested


def teste_virada_do_dia_reseta_automaticamente():
    session, clock = provider()
    session.record_trade_open(
        quantity=2,
        plan_checklist_passed=False,
        chased_price=True,
    )
    session.record_trade_close(result_r=-2.0)
    session.request_manual_pause()
    clock.advance(days=1)
    state = session.snapshot(None)
    assert state.trades_today == 0
    assert state.consecutive_losses == 0
    assert state.daily_loss_r == 0.0
    assert state.session_pnl_r == 0.0
    assert state.seconds_since_last_exit is None
    assert state.plan_checklist_passed
    assert not state.manual_pause_requested


def teste_reset_manual_limpa_toda_a_sessao():
    session, _ = provider()
    session.record_trade_open(quantity=1, plan_checklist_passed=False)
    session.record_trade_close(result_r=-1.0)
    state = session.reset_session()
    assert state == TraderPsychologyState()


def teste_transicoes_invalidas_sao_rejeitadas():
    session, _ = provider()
    raises(
        RuntimeError,
        lambda: session.record_trade_close(result_r=-1.0),
    )
    session.record_trade_open(quantity=1, plan_checklist_passed=True)
    raises(
        RuntimeError,
        lambda: session.record_trade_open(
            quantity=1,
            plan_checklist_passed=True,
        ),
    )


def teste_entradas_invalidas_e_flags_operacionais_sao_bloqueadas():
    raises(
        ValueError,
        lambda: TraderPsychologySessionProvider(
            baseline_quantity=0,
        ),
    )
    session, _ = provider()
    raises(
        ValueError,
        lambda: session.record_trade_open(
            quantity=0,
            plan_checklist_passed=True,
        ),
    )
    raises(
        TypeError,
        lambda: session.record_trade_open(
            quantity=1,
            plan_checklist_passed=1,
        ),
    )
    state = session.snapshot(None)
    assert state.observational_only
    assert not state.score_influence_allowed
    assert not state.order_execution_allowed


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 TRADER PSYCHOLOGY RC8 APROVADO")


if __name__ == "__main__":
    main()
