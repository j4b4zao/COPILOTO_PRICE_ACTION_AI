"""Testes offline do teste controlado de áudio RC20."""

from dataclasses import FrozenInstanceError

from core.system_initializer import SystemInitializer
from psychology import (
    PsychologyVoiceControlledTest,
    PsychologyVoiceControlledTestResult,
    VoiceAssistantConfig,
)


class Sink:
    NAME = "TEST_SINK"

    def __init__(
        self,
        *,
        healthy=True,
        accepted=True,
        error=None,
    ):
        self.healthy = healthy
        self.accepted = accepted
        self.error = error
        self.health_calls = 0
        self.calls = []

    def healthcheck(self):
        self.health_calls += 1
        return self.healthy

    def speak(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.accepted


def config(enabled=True):
    return VoiceAssistantConfig(enabled=enabled)


def confirmed():
    return PsychologyVoiceControlledTest.CONFIRMATION


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_sem_confirmacao_nao_produz_audio():
    sink = Sink()
    result = PsychologyVoiceControlledTest().run(
        config=config(),
        sink=sink,
    )
    assert result.status == "CONFIRMATION_REQUIRED"
    assert not result.attempted
    assert sink.calls == []


def teste_confirmacao_incorreta_nao_produz_audio():
    sink = Sink()
    result = PsychologyVoiceControlledTest().run(
        config=config(),
        sink=sink,
        confirmation="sim",
    )
    assert result.status == "CONFIRMATION_REQUIRED"
    assert not result.confirmation_accepted
    assert sink.calls == []


def teste_confirmacao_exata_entrega_frase_fixa():
    sink = Sink()
    test = PsychologyVoiceControlledTest()
    result = test.run(
        config=config(),
        sink=sink,
        confirmation=confirmed(),
    )
    assert result.status == "DELIVERED"
    assert result.attempted
    assert result.delivered
    assert sink.calls[0]["text"] == test.TEST_TEXT
    assert sink.calls[0]["code"] == test.TEST_CODE
    assert sink.calls[0]["priority"] == "NORMAL"


def teste_texto_de_teste_e_neutro_e_constante():
    test = PsychologyVoiceControlledTest()
    assert test.TEST_TEXT == (
        "Teste de voz do acompanhamento psicológico. "
        "Áudio funcionando."
    )
    assert "compre" not in test.TEST_TEXT.casefold()
    assert "venda" not in test.TEST_TEXT.casefold()


def teste_voz_desativada_nao_tenta_audio():
    sink = Sink()
    result = PsychologyVoiceControlledTest().run(
        config=config(False),
        sink=sink,
        confirmation=confirmed(),
    )
    assert result.status == "NOT_READY"
    assert result.readiness_status == "DISABLED"
    assert not result.attempted
    assert sink.calls == []


def teste_backend_indisponivel_nao_tenta_audio():
    sink = Sink(healthy=False)
    result = PsychologyVoiceControlledTest().run(
        config=config(),
        sink=sink,
        confirmation=confirmed(),
    )
    assert result.status == "NOT_READY"
    assert result.readiness_status == "UNAVAILABLE"
    assert not result.attempted
    assert sink.calls == []


def teste_sink_rejeita_audio_de_forma_controlada():
    sink = Sink(accepted=False)
    result = PsychologyVoiceControlledTest().run(
        config=config(),
        sink=sink,
        confirmation=confirmed(),
    )
    assert result.status == "REJECTED"
    assert result.attempted
    assert not result.delivered
    assert len(sink.calls) == 1


def teste_falha_do_sink_e_isolada():
    sink = Sink(error=RuntimeError("falha de áudio"))
    result = PsychologyVoiceControlledTest().run(
        config=config(),
        sink=sink,
        confirmation=confirmed(),
    )
    assert result.status == "FAILED"
    assert result.attempted
    assert not result.delivered
    assert "RuntimeError" in result.error


def teste_healthcheck_ocorre_antes_do_audio():
    trace = []

    class OrderedSink:
        def healthcheck(self):
            trace.append("health")
            return True

        def speak(self, **kwargs):
            trace.append("speak")
            return True

    PsychologyVoiceControlledTest().run(
        config=config(),
        sink=OrderedSink(),
        confirmation=confirmed(),
    )
    assert trace == ["health", "speak"]


def teste_resultado_e_armazenado_como_ultimo():
    sink = Sink()
    test = PsychologyVoiceControlledTest()
    result = test.run(
        config=config(),
        sink=sink,
        confirmation=confirmed(),
    )
    assert test.last_result is result


def teste_resultado_e_imutavel():
    result = PsychologyVoiceControlledTest().run(
        config=config(),
        sink=Sink(),
        confirmation=confirmed(),
    )
    assert isinstance(result, PsychologyVoiceControlledTestResult)
    raises(
        FrozenInstanceError,
        lambda: setattr(result, "status", "ALTERADO"),
    )


def teste_configuracao_incompativel_e_rejeitada():
    raises(
        TypeError,
        lambda: PsychologyVoiceControlledTest().run(
            config={},
            sink=Sink(),
            confirmation=confirmed(),
        ),
    )


def teste_nao_aceita_texto_livre():
    raises(
        TypeError,
        lambda: PsychologyVoiceControlledTest().run(
            config=config(),
            sink=Sink(),
            confirmation=confirmed(),
            text="texto arbitrário",
        ),
    )


def teste_system_initializer_expoe_teste_controlado():
    sink = Sink()
    system = SystemInitializer(
        psychology_voice_config=config(),
        psychology_voice_sink=sink,
    )
    result = system.test_psychology_voice(confirmed())
    assert result.status == "DELIVERED"
    assert len(sink.calls) == 1


def teste_system_initializer_sem_confirmacao_permanece_silencioso():
    sink = Sink()
    system = SystemInitializer(
        psychology_voice_config=config(),
        psychology_voice_sink=sink,
    )
    result = system.test_psychology_voice()
    assert result.status == "CONFIRMATION_REQUIRED"
    assert sink.calls == []


def teste_flags_operacionais_permanecem_fechadas():
    result = PsychologyVoiceControlledTest().run(
        config=config(),
        sink=Sink(),
        confirmation=confirmed(),
    )
    assert result.observational_only
    assert not result.score_influence_allowed
    assert not result.order_execution_allowed
    assert not result.operational_block_allowed


def teste_servico_nao_expoe_ordens_ou_decisao():
    test = PsychologyVoiceControlledTest()
    assert not hasattr(test, "send_order")
    assert not hasattr(test, "block_trading")
    assert not hasattr(test, "change_score")


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 TRADER PSYCHOLOGY RC20 APROVADO")


if __name__ == "__main__":
    main()
