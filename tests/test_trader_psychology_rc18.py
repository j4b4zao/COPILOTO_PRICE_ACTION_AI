"""Testes offline do sink TTS psicológico RC18."""

from analysis.replay.book_diagnostics_tts_backend import TTSResult
from core.system_initializer import SystemInitializer
from psychology import (
    PsychologyTTSBackendSink,
    TraderPsychologyState,
    VoiceAssistantConfig,
    WindowsSAPIPsychologyVoiceSink,
)


class Backend:
    name = "FAKE_TTS"

    def __init__(
        self,
        *,
        healthy=True,
        accepted=True,
        completed=True,
        error="",
    ):
        self.healthy = healthy
        self.accepted = accepted
        self.completed = completed
        self.error = error
        self.commands = []
        self.stop_calls = []

    def healthcheck(self):
        return self.healthy

    def speak(self, command):
        self.commands.append(command)
        return TTSResult(
            version="RC35-TTS-BACKEND-CONTRACT",
            backend=self.name,
            event_id=command.event_id,
            accepted=self.accepted,
            completed=self.completed,
            interrupted=False,
            error=self.error,
        )

    def stop(self, event_id=None):
        self.stop_calls.append(event_id)
        return True


class InvalidBackend:
    pass


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def sink(backend=None, **changes):
    return PsychologyTTSBackendSink(
        backend=backend or Backend(),
        **changes,
    )


def teste_texto_e_convertido_em_comando_readonly():
    backend = Backend()
    target = sink(backend)
    assert target.speak(
        text="  Aguarde   confirmação. ",
        priority="NORMAL",
        code="FOMO",
    )
    command = backend.commands[0]
    assert command.text == "Aguarde confirmação."
    assert command.readonly
    assert not command.affects_decision
    assert command.command == "SPEAK"


def teste_prioridade_urgente_habilita_interrupcao():
    backend = Backend()
    target = sink(backend)
    target.speak(
        text="Pausa recomendada.",
        priority="URGENT",
        code="PAUSE_RECOMMENDED",
    )
    assert backend.commands[0].interrupt


def teste_prioridade_normal_nao_habilita_interrupcao():
    backend = Backend()
    target = sink(backend)
    target.speak(
        text="Espere o plano.",
        priority="CAUTION",
        code="OUTSIDE_PLAN",
    )
    assert not backend.commands[0].interrupt


def teste_ids_de_evento_sao_unicos_e_sequenciais():
    backend = Backend()
    target = sink(backend)
    for _ in range(2):
        target.speak(
            text="Evite perseguir o preço.",
            priority="NORMAL",
            code="FOMO",
        )
    ids = [command.event_id for command in backend.commands]
    assert ids == [
        "psychology-00000001-fomo",
        "psychology-00000002-fomo",
    ]


def teste_backend_indisponivel_rejeita_sem_sintetizar():
    backend = Backend(healthy=False)
    target = sink(backend)
    accepted = target.speak(
        text="Mensagem.",
        priority="NORMAL",
        code="FOMO",
    )
    assert not accepted
    assert backend.commands == []
    assert target.last_command is None


def teste_resultado_incompleto_e_rejeitado():
    backend = Backend(completed=False)
    target = sink(backend)
    assert not target.speak(
        text="Mensagem.",
        priority="NORMAL",
        code="FOMO",
    )
    assert target.last_result.accepted
    assert not target.last_result.completed


def teste_resultado_com_erro_e_rejeitado():
    backend = Backend(error="falha de voz")
    target = sink(backend)
    assert not target.speak(
        text="Mensagem.",
        priority="NORMAL",
        code="FOMO",
    )


def teste_healthcheck_delega_ao_backend():
    backend = Backend(healthy=True)
    assert sink(backend).healthcheck()
    backend.healthy = False
    assert not sink(backend).healthcheck()


def teste_stop_usa_ultimo_evento():
    backend = Backend()
    target = sink(backend)
    target.speak(
        text="Mensagem.",
        priority="NORMAL",
        code="FOMO",
    )
    assert target.stop()
    assert backend.stop_calls == [
        "psychology-00000001-fomo",
    ]


def teste_configuracao_de_voz_e_preservada():
    backend = Backend()
    target = sink(
        backend,
        language="pt-BR",
        voice_profile="Voz Teste",
        speech_rate=1.25,
    )
    target.speak(
        text="Mensagem.",
        priority="NORMAL",
        code="FOMO",
    )
    command = backend.commands[0]
    assert command.language == "pt-BR"
    assert command.voice_profile == "Voz Teste"
    assert command.speech_rate == 1.25


def teste_entradas_invalidas_sao_rejeitadas():
    target = sink()
    raises(
        ValueError,
        lambda: target.speak(
            text="",
            priority="NORMAL",
            code="FOMO",
        ),
    )
    raises(
        ValueError,
        lambda: target.speak(
            text="Mensagem",
            priority="ALTA",
            code="FOMO",
        ),
    )
    raises(
        ValueError,
        lambda: target.speak(
            text="Mensagem",
            priority="NORMAL",
            code="",
        ),
    )


def teste_backend_e_configuracao_invalidos_sao_rejeitados():
    raises(
        TypeError,
        lambda: PsychologyTTSBackendSink(
            backend=InvalidBackend(),
        ),
    )
    raises(
        ValueError,
        lambda: sink(language=""),
    )
    raises(
        ValueError,
        lambda: sink(voice_profile=""),
    )
    raises(
        ValueError,
        lambda: sink(speech_rate=2.1),
    )


def teste_atalho_windows_aceita_backend_injetado():
    backend = Backend()
    target = WindowsSAPIPsychologyVoiceSink(
        backend=backend,
    )
    assert target.backend is backend
    assert target.NAME == "WindowsSAPIPsychologyVoiceSink"


def teste_system_initializer_aceita_sink_tts_real():
    backend = Backend()
    target = WindowsSAPIPsychologyVoiceSink(
        backend=backend,
    )
    system = SystemInitializer(
        psychology_voice_config=VoiceAssistantConfig(
            enabled=True,
        ),
        psychology_voice_sink=target,
    )
    result = system.psychology_runtime.process(
        TraderPsychologyState(chased_price=True)
    )
    assert result.voice.status == "DELIVERED"
    assert backend.commands[0].priority == "NORMAL"


def teste_falha_tts_nao_bloqueia_runtime():
    backend = Backend(healthy=False)
    target = WindowsSAPIPsychologyVoiceSink(
        backend=backend,
    )
    system = SystemInitializer(
        psychology_voice_config=VoiceAssistantConfig(
            enabled=True,
        ),
        psychology_voice_sink=target,
    )
    result = system.psychology_runtime.process(
        TraderPsychologyState(consecutive_losses=3)
    )
    assert result.voice.status == "FAILED"
    assert result.pause_recommended
    assert not result.operational_block_allowed
    assert not result.order_execution_allowed


def teste_sink_nao_expoe_ordens_ou_decisao():
    target = sink()
    assert not hasattr(target, "send_order")
    assert not hasattr(target, "block_trading")
    assert not hasattr(target, "change_score")


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 TRADER PSYCHOLOGY RC18 APROVADO")


if __name__ == "__main__":
    main()
