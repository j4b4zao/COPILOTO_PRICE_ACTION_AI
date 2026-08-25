"""Testes offline do VoiceAssistant RC4."""

from psychology import (
    CoachingEngine,
    TraderPsychologyEngine,
    TraderPsychologyState,
    VoiceAssistant,
    VoiceAssistantConfig,
)


class Sink:
    def __init__(self, *, error=None, accepted=True):
        self.error = error
        self.accepted = accepted
        self.calls = []

    def speak(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.accepted


def coaching(**changes):
    psychology = TraderPsychologyEngine().analyze(
        TraderPsychologyState(**changes)
    )
    return CoachingEngine().build(psychology)


def enabled(sink, **changes):
    return VoiceAssistant(
        config=VoiceAssistantConfig(enabled=True, **changes),
        sink=sink,
    )


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_voz_fica_desativada_por_padrao():
    sink = Sink()
    result = VoiceAssistant(sink=sink).dispatch(
        coaching(trades_today=6)
    )
    assert result.status == "DISABLED"
    assert sink.calls == []


def teste_estado_neutro_permanece_silencioso():
    sink = Sink()
    result = enabled(sink).dispatch(coaching())
    assert result.status == "SILENT"
    assert result.attempted_count == 0
    assert sink.calls == []


def teste_mensagem_de_coaching_e_entregue_quando_habilitada():
    sink = Sink()
    result = enabled(sink).dispatch(coaching(trades_today=6))
    assert result.status == "DELIVERED"
    assert result.delivered_count == 1
    assert sink.calls[0]["code"] == "OVERTRADING"


def teste_pausa_recebe_prioridade_urgente():
    sink = Sink()
    enabled(sink).dispatch(coaching(consecutive_losses=3))
    assert sink.calls[0]["code"] == "PAUSE_RECOMMENDED"
    assert sink.calls[0]["priority"] == "URGENT"


def teste_sinal_grave_recebe_prioridade_caution():
    sink = Sink()
    enabled(sink).dispatch(
        coaching(plan_checklist_passed=False)
    )
    assert sink.calls[0]["code"] == "OUTSIDE_PLAN"
    assert sink.calls[0]["priority"] == "CAUTION"


def teste_fomo_isolado_recebe_prioridade_normal():
    sink = Sink()
    enabled(sink).dispatch(coaching(chased_price=True))
    assert sink.calls[0]["code"] == "FOMO"
    assert sink.calls[0]["priority"] == "NORMAL"


def teste_limite_de_mensagens_por_dispatch_e_respeitado():
    sink = Sink()
    assistant = enabled(
        sink,
        maximum_messages_per_dispatch=1,
    )
    result = assistant.dispatch(coaching(
        consecutive_losses=3,
        plan_checklist_passed=False,
        chased_price=True,
    ))
    assert result.attempted_count == 1
    assert len(sink.calls) == 1


def teste_falha_do_sink_nao_propaga_excecao():
    sink = Sink(error=RuntimeError("falha de áudio"))
    result = enabled(sink).dispatch(coaching(trades_today=6))
    assert result.status == "FAILED"
    assert result.failed_count == 1


def teste_rejeicao_do_sink_e_registrada_sem_bloqueio():
    sink = Sink(accepted=False)
    result = enabled(sink).dispatch(coaching(chased_price=True))
    assert result.status == "FAILED"
    assert result.deliveries[0].status == "REJECTED"
    assert not result.operational_block_allowed


def teste_guidance_pode_ser_silenciado_mantendo_pausa():
    sink = Sink()
    assistant = enabled(sink, speak_guidance=False)
    result = assistant.dispatch(coaching(chased_price=True))
    assert result.status == "SILENT"
    result = assistant.dispatch(coaching(consecutive_losses=3))
    assert result.status == "DELIVERED"
    assert sink.calls[-1]["code"] == "PAUSE_RECOMMENDED"


def teste_pausa_pode_ser_silenciada_sem_bloquear_guidance():
    sink = Sink()
    assistant = enabled(
        sink,
        speak_pause_recommendation=False,
    )
    result = assistant.dispatch(coaching(consecutive_losses=3))
    assert "PAUSE_RECOMMENDED" not in [
        call["code"] for call in sink.calls
    ]
    assert result.status == "DELIVERED"


def teste_resultado_de_voz_nao_toca_score_ou_ordens():
    result = enabled(Sink()).dispatch(
        coaching(consecutive_losses=3)
    )
    assert result.observational_only
    assert not result.score_influence_allowed
    assert not result.order_execution_allowed
    assert not result.operational_block_allowed


def teste_configuracao_invalida_e_rejeitada():
    raises(
        ValueError,
        lambda: VoiceAssistantConfig(
            maximum_messages_per_dispatch=0
        ),
    )
    raises(
        TypeError,
        lambda: VoiceAssistantConfig(enabled=1),
    )


def teste_assistente_rejeita_coaching_incompativel():
    raises(
        TypeError,
        lambda: VoiceAssistant().dispatch({}),
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
    print("🏆 TRADER PSYCHOLOGY RC4 APROVADO")


if __name__ == "__main__":
    main()
