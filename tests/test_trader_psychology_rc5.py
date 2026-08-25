"""Testes offline do runtime Psicologia do Trader RC5."""

from psychology import (
    TraderPsychologyRuntime,
    TraderPsychologyState,
    VoiceAssistant,
    VoiceAssistantConfig,
)


class Sink:
    def __init__(self, *, error=None):
        self.error = error
        self.calls = []

    def speak(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return True


def runtime_with_voice(sink):
    return TraderPsychologyRuntime(
        voice_assistant=VoiceAssistant(
            config=VoiceAssistantConfig(enabled=True),
            sink=sink,
        )
    )


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_cadeia_neutra_completa_fica_silenciosa():
    result = TraderPsychologyRuntime().process(
        TraderPsychologyState()
    )
    assert result.status == "NEUTRAL"
    assert result.psychology.status == "NEUTRAL"
    assert result.coaching.status == "SILENT"
    assert result.voice.status == "DISABLED"


def teste_overtrading_percorre_engine_e_coaching():
    result = TraderPsychologyRuntime().process(
        TraderPsychologyState(trades_today=6)
    )
    assert result.status == "ATTENTION"
    assert result.psychology.signals[0].code == "OVERTRADING"
    assert result.coaching.messages[0].code == "OVERTRADING"


def teste_pausa_extrema_percorre_toda_a_cadeia():
    sink = Sink()
    result = runtime_with_voice(sink).process(
        TraderPsychologyState(consecutive_losses=3)
    )
    assert result.status == "PAUSE_RECOMMENDED"
    assert result.pause_recommended
    assert result.coaching.status == "PAUSE_RECOMMENDED"
    assert result.voice.status == "DELIVERED"
    assert sink.calls[0]["code"] == "PAUSE_RECOMMENDED"


def teste_voz_permanece_desativada_por_padrao():
    result = TraderPsychologyRuntime().process(
        TraderPsychologyState(chased_price=True)
    )
    assert result.voice.status == "DISABLED"
    assert result.coaching.status == "GUIDANCE"


def teste_falha_de_audio_nao_interrompe_runtime():
    sink = Sink(error=RuntimeError("falha de áudio"))
    result = runtime_with_voice(sink).process(
        TraderPsychologyState(trades_today=6)
    )
    assert result.status == "ATTENTION"
    assert result.voice.status == "FAILED"
    assert result.psychology.signals


def teste_resultado_preserva_snapshot_original():
    state = TraderPsychologyState(
        trades_today=4,
        chased_price=True,
    )
    result = TraderPsychologyRuntime().process(state)
    assert result.state is state
    assert result.state.trades_today == 4


def teste_runtime_armazena_ultimo_resultado():
    runtime = TraderPsychologyRuntime()
    assert runtime.last_result is None
    result = runtime.process(TraderPsychologyState())
    assert runtime.last_result is result


def teste_varios_sinais_sao_limitados_pelo_coaching():
    result = TraderPsychologyRuntime().process(
        TraderPsychologyState(
            trades_today=8,
            consecutive_losses=3,
            last_trade_was_loss=True,
            seconds_since_last_exit=20,
            increased_size_after_loss=True,
            chased_price=True,
            skipped_confirmation=True,
            plan_checklist_passed=False,
        )
    )
    assert len(result.psychology.signals) > len(
        result.coaching.messages
    )
    assert len(result.coaching.messages) <= 3


def teste_runtime_rejeita_estado_incompativel():
    raises(TypeError, lambda: TraderPsychologyRuntime().process({}))


def teste_runtime_rejeita_componentes_sem_contrato():
    raises(
        TypeError,
        lambda: TraderPsychologyRuntime(psychology_engine=object()),
    )
    raises(
        TypeError,
        lambda: TraderPsychologyRuntime(coaching_engine=object()),
    )
    raises(
        TypeError,
        lambda: TraderPsychologyRuntime(voice_assistant=object()),
    )


def teste_runtime_nunca_toca_score_decisao_ou_ordens():
    result = TraderPsychologyRuntime().process(
        TraderPsychologyState(
            consecutive_losses=4,
            daily_loss_r=4,
        )
    )
    assert result.observational_only
    assert not result.score_influence_allowed
    assert not result.order_execution_allowed
    assert not result.operational_block_allowed
    assert not result.psychology.score_influence_allowed
    assert not result.coaching.score_influence_allowed
    assert not result.voice.score_influence_allowed


def teste_pausa_continua_recomendacao_sem_bloqueio():
    result = TraderPsychologyRuntime().process(
        TraderPsychologyState(manual_pause_requested=True)
    )
    assert result.pause_recommended
    assert not result.operational_block_allowed
    assert not result.psychology.operational_block_allowed
    assert not result.coaching.operational_block_allowed


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 TRADER PSYCHOLOGY RC5 APROVADO")


if __name__ == "__main__":
    main()
