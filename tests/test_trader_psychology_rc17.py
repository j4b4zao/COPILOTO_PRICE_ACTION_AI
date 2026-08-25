"""Testes offline da configuração de voz psicológica RC17."""

from core.system_initializer import SystemInitializer
from psychology import (
    NullPsychologyVoiceSink,
    TraderPsychologyRuntime,
    TraderPsychologyState,
    VoiceAssistant,
    VoiceAssistantConfig,
)


class Sink:
    def __init__(self, *, accepted=True):
        self.accepted = accepted
        self.calls = []

    def speak(self, *, text, priority, code):
        self.calls.append((text, priority, code))
        return self.accepted


class InvalidSink:
    pass


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def enabled_config(**changes):
    return VoiceAssistantConfig(enabled=True, **changes)


def teste_voz_psicologica_fica_desativada_por_padrao():
    system = SystemInitializer()
    assert not system.psychology_voice_config.enabled
    assert system.psychology_voice_sink is None
    assert system.psychology_voice.last_result.status == "DISABLED"


def teste_runtime_psicologico_e_criado_explicitamente():
    system = SystemInitializer()
    assert isinstance(system.psychology_runtime, TraderPsychologyRuntime)
    assert system.psychology_runtime.voice_assistant is system.psychology_voice


def teste_assistente_psicologico_e_independente_da_voz_do_book():
    system = SystemInitializer(voice_enabled=True)
    assert system.voice_enabled
    assert not system.psychology_voice_config.enabled
    assert system.psychology_voice.last_result.status == "DISABLED"


def teste_habilitacao_psicologica_exige_sink_explicito():
    raises(
        ValueError,
        lambda: SystemInitializer(
            psychology_voice_config=enabled_config(),
        ),
    )


def teste_sink_incompativel_e_rejeitado():
    raises(
        TypeError,
        lambda: SystemInitializer(
            psychology_voice_sink=InvalidSink(),
        ),
    )


def teste_configuracao_incompativel_e_rejeitada():
    raises(
        TypeError,
        lambda: SystemInitializer(
            psychology_voice_config={"enabled": False},
        ),
    )


def teste_sink_pode_ser_preparado_com_voz_desativada():
    sink = Sink()
    system = SystemInitializer(psychology_voice_sink=sink)
    result = system.psychology_runtime.process(
        TraderPsychologyState(chased_price=True)
    )
    assert result.voice.status == "DISABLED"
    assert sink.calls == []


def teste_voz_habilitada_entrega_coaching():
    sink = Sink()
    system = SystemInitializer(
        psychology_voice_config=enabled_config(),
        psychology_voice_sink=sink,
    )
    result = system.psychology_runtime.process(
        TraderPsychologyState(chased_price=True)
    )
    assert result.voice.status == "DELIVERED"
    assert sink.calls[0][2] == "FOMO"


def teste_configuracao_de_cooldown_e_preservada():
    sink = Sink()
    config = enabled_config(
        cooldown_seconds=90.0,
        maximum_remembered_messages=25,
    )
    system = SystemInitializer(
        psychology_voice_config=config,
        psychology_voice_sink=sink,
    )
    assert system.psychology_voice.config is config
    assert system.psychology_voice.config.cooldown_seconds == 90.0
    assert (
        system.psychology_voice.config.maximum_remembered_messages
        == 25
    )


def teste_runtime_reutiliza_cooldown_entre_ciclos():
    sink = Sink()
    system = SystemInitializer(
        psychology_voice_config=enabled_config(
            cooldown_seconds=60.0,
        ),
        psychology_voice_sink=sink,
    )
    state = TraderPsychologyState(chased_price=True)
    first = system.psychology_runtime.process(state)
    second = system.psychology_runtime.process(state)
    assert first.voice.status == "DELIVERED"
    assert second.voice.status == "COOLDOWN"
    assert len(sink.calls) == 1


def teste_rejeicao_do_sink_permanece_observacional():
    sink = Sink(accepted=False)
    system = SystemInitializer(
        psychology_voice_config=enabled_config(),
        psychology_voice_sink=sink,
    )
    result = system.psychology_runtime.process(
        TraderPsychologyState(chased_price=True)
    )
    assert result.voice.status == "FAILED"
    assert not result.voice.operational_block_allowed
    assert not result.order_execution_allowed


def teste_sink_nulo_existe_somente_no_modo_desativado():
    system = SystemInitializer()
    assert isinstance(
        system.psychology_voice.sink,
        NullPsychologyVoiceSink,
    )
    assert not system.psychology_voice.config.enabled


def teste_objetos_de_voz_sao_expostos_para_monitoramento():
    sink = Sink()
    system = SystemInitializer(
        psychology_voice_config=enabled_config(),
        psychology_voice_sink=sink,
    )
    assert isinstance(system.psychology_voice, VoiceAssistant)
    assert system.psychology_voice_sink is sink
    assert system.psychology_voice_config.enabled


def teste_configuracao_nao_libera_capacidades_operacionais():
    sink = Sink()
    system = SystemInitializer(
        psychology_voice_config=enabled_config(),
        psychology_voice_sink=sink,
    )
    assert not hasattr(system.psychology_voice, "send_order")
    assert not hasattr(system.psychology_voice, "block_trading")
    assert not hasattr(system.psychology_runtime, "send_order")


def teste_pausa_continua_recomendacao_com_voz_habilitada():
    sink = Sink()
    system = SystemInitializer(
        psychology_voice_config=enabled_config(),
        psychology_voice_sink=sink,
    )
    result = system.psychology_runtime.process(
        TraderPsychologyState(consecutive_losses=3)
    )
    assert result.pause_recommended
    assert result.voice.status == "DELIVERED"
    assert sink.calls[0][1] == "URGENT"
    assert not result.operational_block_allowed


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 TRADER PSYCHOLOGY RC17 APROVADO")


if __name__ == "__main__":
    main()
