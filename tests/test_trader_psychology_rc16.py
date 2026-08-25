"""Testes offline do cooldown de voz psicológica RC16."""

from psychology import (
    CoachingEngine,
    TraderPsychologyEngine,
    TraderPsychologyState,
    VoiceAssistant,
    VoiceAssistantConfig,
)


class Clock:
    def __init__(self, value=100.0):
        self.value = value
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.value

    def advance(self, seconds):
        self.value += seconds


class Sink:
    def __init__(self, *, accepted=True, error=None):
        self.accepted = accepted
        self.error = error
        self.calls = []

    def speak(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.accepted


def coaching(**changes):
    result = TraderPsychologyEngine().analyze(
        TraderPsychologyState(**changes)
    )
    return CoachingEngine().build(result)


def assistant(*, cooldown=60.0, sink=None, clock=None, maximum=128):
    return VoiceAssistant(
        config=VoiceAssistantConfig(
            enabled=True,
            cooldown_seconds=cooldown,
            maximum_remembered_messages=maximum,
        ),
        sink=sink or Sink(),
        clock=clock or Clock(),
    )


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_primeira_mensagem_e_entregue():
    sink = Sink()
    voice = assistant(sink=sink)
    result = voice.dispatch(coaching(chased_price=True))
    assert result.status == "DELIVERED"
    assert result.attempted_count == 1
    assert result.suppressed_count == 0
    assert len(sink.calls) == 1


def teste_repeticao_imediata_e_suprimida():
    sink = Sink()
    voice = assistant(sink=sink)
    item = coaching(chased_price=True)
    voice.dispatch(item)
    result = voice.dispatch(item)
    assert result.status == "COOLDOWN"
    assert result.attempted_count == 0
    assert result.delivered_count == 0
    assert result.failed_count == 0
    assert result.suppressed_count == 1
    assert result.deliveries[0].status == "COOLDOWN_SUPPRESSED"
    assert len(sink.calls) == 1


def teste_mensagem_volta_apos_cooldown():
    sink = Sink()
    clock = Clock()
    voice = assistant(sink=sink, clock=clock)
    item = coaching(chased_price=True)
    voice.dispatch(item)
    clock.advance(60.0)
    result = voice.dispatch(item)
    assert result.status == "DELIVERED"
    assert len(sink.calls) == 2


def teste_antes_do_limite_continua_suprimida():
    sink = Sink()
    clock = Clock()
    voice = assistant(sink=sink, clock=clock)
    item = coaching(chased_price=True)
    voice.dispatch(item)
    clock.advance(59.999)
    assert voice.dispatch(item).status == "COOLDOWN"


def teste_cooldown_zero_nao_suprime():
    sink = Sink()
    clock = Clock()
    voice = assistant(sink=sink, clock=clock, cooldown=0.0)
    item = coaching(chased_price=True)
    voice.dispatch(item)
    voice.dispatch(item)
    assert len(sink.calls) == 2


def teste_codigos_diferentes_possuem_cooldowns_independentes():
    sink = Sink()
    voice = assistant(sink=sink)
    voice.dispatch(coaching(chased_price=True))
    result = voice.dispatch(coaching(plan_checklist_passed=False))
    assert result.status == "DELIVERED"
    assert [call["code"] for call in sink.calls] == [
        "FOMO",
        "OUTSIDE_PLAN",
    ]


def teste_falha_de_audio_pode_ser_tentada_novamente():
    sink = Sink(error=RuntimeError("falha"))
    voice = assistant(sink=sink)
    item = coaching(chased_price=True)
    first = voice.dispatch(item)
    second = voice.dispatch(item)
    assert first.status == "FAILED"
    assert second.status == "FAILED"
    assert len(sink.calls) == 2


def teste_rejeicao_pode_ser_tentada_novamente():
    sink = Sink(accepted=False)
    voice = assistant(sink=sink)
    item = coaching(chased_price=True)
    voice.dispatch(item)
    voice.dispatch(item)
    assert len(sink.calls) == 2


def teste_clear_cooldown_libera_nova_entrega():
    sink = Sink()
    voice = assistant(sink=sink)
    item = coaching(chased_price=True)
    voice.dispatch(item)
    assert voice.dispatch(item).status == "COOLDOWN"
    voice.clear_cooldown()
    assert voice.dispatch(item).status == "DELIVERED"
    assert len(sink.calls) == 2


def teste_memoria_de_deduplicacao_e_limitada():
    sink = Sink()
    voice = assistant(sink=sink, maximum=1)
    voice.dispatch(coaching(chased_price=True))
    voice.dispatch(coaching(plan_checklist_passed=False))
    result = voice.dispatch(coaching(chased_price=True))
    assert result.status == "DELIVERED"
    assert len(voice._delivered_at) == 1


def teste_misto_entregue_e_suprimido_e_parcial():
    sink = Sink()
    voice = assistant(sink=sink)
    voice.dispatch(coaching(plan_checklist_passed=False))
    result = voice.dispatch(coaching(
        plan_checklist_passed=False,
        chased_price=True,
    ))
    assert result.status == "PARTIAL"
    assert result.attempted_count == 1
    assert result.delivered_count == 1
    assert result.suppressed_count == 1


def teste_desativado_nao_consulta_clock():
    clock = Clock()
    sink = Sink()
    voice = VoiceAssistant(
        config=VoiceAssistantConfig(enabled=False),
        sink=sink,
        clock=clock,
    )
    result = voice.dispatch(coaching(chased_price=True))
    assert result.status == "DISABLED"
    assert clock.calls == 0
    assert sink.calls == []


def teste_estado_neutro_nao_consulta_clock():
    clock = Clock()
    voice = assistant(clock=clock)
    result = voice.dispatch(coaching())
    assert result.status == "SILENT"
    assert clock.calls == 0


def teste_configuracao_de_cooldown_invalida_e_rejeitada():
    for value in (-1, float("inf"), True, "60"):
        raises(
            (TypeError, ValueError),
            lambda value=value: VoiceAssistantConfig(
                cooldown_seconds=value,
            ),
        )
    raises(
        ValueError,
        lambda: VoiceAssistantConfig(maximum_remembered_messages=0),
    )
    raises(
        TypeError,
        lambda: VoiceAssistantConfig(maximum_remembered_messages=True),
    )


def teste_clock_invalido_e_rejeitado():
    raises(
        TypeError,
        lambda: VoiceAssistant(clock=object()),
    )
    voice = assistant(clock=lambda: "agora")
    raises(TypeError, lambda: voice.dispatch(coaching(chased_price=True)))


def teste_isolamento_operacional_permanece_fechado():
    voice = assistant()
    item = coaching(chased_price=True)
    voice.dispatch(item)
    result = voice.dispatch(item)
    assert result.observational_only
    assert not result.score_influence_allowed
    assert not result.order_execution_allowed
    assert not result.operational_block_allowed
    assert not hasattr(voice, "send_order")
    assert not hasattr(voice, "block_trading")


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 TRADER PSYCHOLOGY RC16 APROVADO")


if __name__ == "__main__":
    main()
