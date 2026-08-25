"""Testes offline da prontidão da voz psicológica RC19."""

from dataclasses import FrozenInstanceError

from core.system_initializer import SystemInitializer
from psychology import (
    PsychologyVoiceReadiness,
    PsychologyVoiceReadinessSnapshot,
    VoiceAssistantConfig,
    WindowsSAPIPsychologyVoiceSink,
)


class Sink:
    NAME = "TEST_SINK"

    def __init__(self, *, healthy=True, error=None):
        self.healthy = healthy
        self.error = error
        self.health_calls = 0
        self.speak_calls = 0

    def speak(self, **kwargs):
        self.speak_calls += 1
        return True

    def healthcheck(self):
        self.health_calls += 1
        if self.error:
            raise self.error
        return self.healthy


class SinkWithoutHealth:
    name = "NO_HEALTH"

    def __init__(self):
        self.speak_calls = 0

    def speak(self, **kwargs):
        self.speak_calls += 1
        return True


class Backend:
    name = "WINDOWS_SAPI"

    def __init__(self, healthy=True):
        self.healthy = healthy

    def healthcheck(self):
        return self.healthy

    def speak(self, command):
        raise AssertionError("readiness não deve falar")

    def stop(self, event_id=None):
        return False


def config(enabled):
    return VoiceAssistantConfig(enabled=enabled)


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def inspect(enabled=True, sink=None):
    return PsychologyVoiceReadiness().inspect(
        config=config(enabled),
        sink=sink,
    )


def teste_desativada_sem_sink():
    result = inspect(enabled=False)
    assert result.status == "DISABLED"
    assert not result.enabled
    assert not result.configured
    assert result.available is None
    assert not result.ready


def teste_desativada_nao_executa_healthcheck():
    sink = Sink()
    result = inspect(enabled=False, sink=sink)
    assert result.status == "DISABLED"
    assert result.configured
    assert sink.health_calls == 0
    assert sink.speak_calls == 0


def teste_habilitada_sem_sink_fica_nao_configurada():
    result = inspect(enabled=True)
    assert result.status == "NOT_CONFIGURED"
    assert result.enabled
    assert not result.configured
    assert result.available is False


def teste_sink_sem_healthcheck_fica_nao_verificado():
    sink = SinkWithoutHealth()
    result = inspect(sink=sink)
    assert result.status == "UNVERIFIED"
    assert result.configured
    assert not result.healthcheck_supported
    assert result.available is None
    assert not result.ready
    assert sink.speak_calls == 0


def teste_backend_saudavel_fica_pronto():
    sink = Sink(healthy=True)
    result = inspect(sink=sink)
    assert result.status == "READY"
    assert result.ready
    assert result.available is True
    assert sink.health_calls == 1
    assert sink.speak_calls == 0


def teste_backend_indisponivel_e_reportado():
    sink = Sink(healthy=False)
    result = inspect(sink=sink)
    assert result.status == "UNAVAILABLE"
    assert not result.ready
    assert result.available is False
    assert sink.health_calls == 1


def teste_erro_de_healthcheck_e_isolado():
    sink = Sink(error=RuntimeError("falha"))
    result = inspect(sink=sink)
    assert result.status == "ERROR"
    assert not result.ready
    assert result.available is False
    assert "RuntimeError" in result.reason
    assert sink.speak_calls == 0


def teste_nome_do_sink_e_exposto():
    result = inspect(sink=Sink())
    assert result.sink_name == "TEST_SINK"


def teste_nome_do_backend_e_exposto():
    sink = WindowsSAPIPsychologyVoiceSink(
        backend=Backend(healthy=True),
    )
    result = inspect(sink=sink)
    assert result.status == "READY"
    assert result.sink_name == "WindowsSAPIPsychologyVoiceSink"
    assert result.backend_name == "WINDOWS_SAPI"


def teste_system_initializer_expoe_status_desativado():
    system = SystemInitializer()
    result = system.psychology_voice_readiness()
    assert result.status == "DISABLED"
    assert not result.ready


def teste_system_initializer_expoe_status_pronto():
    sink = Sink()
    system = SystemInitializer(
        psychology_voice_config=config(True),
        psychology_voice_sink=sink,
    )
    result = system.psychology_voice_readiness()
    assert result.status == "READY"
    assert result.ready
    assert sink.speak_calls == 0


def teste_inspecoes_repetidas_nao_produzem_audio():
    sink = Sink()
    service = PsychologyVoiceReadiness()
    for _ in range(3):
        service.inspect(config=config(True), sink=sink)
    assert sink.health_calls == 3
    assert sink.speak_calls == 0


def teste_snapshot_e_imutavel():
    result = inspect(sink=Sink())
    assert isinstance(result, PsychologyVoiceReadinessSnapshot)
    raises(
        FrozenInstanceError,
        lambda: setattr(result, "status", "ALTERADO"),
    )


def teste_configuracao_incompativel_e_rejeitada():
    raises(
        TypeError,
        lambda: PsychologyVoiceReadiness().inspect(
            config={},
            sink=Sink(),
        ),
    )


def teste_flags_de_isolamento_permanecem_fechadas():
    result = inspect(sink=Sink())
    assert result.observational_only
    assert not result.score_influence_allowed
    assert not result.order_execution_allowed
    assert not result.operational_block_allowed


def teste_servico_nao_expoe_audio_ordens_ou_bloqueio():
    service = PsychologyVoiceReadiness()
    assert not hasattr(service, "speak")
    assert not hasattr(service, "send_order")
    assert not hasattr(service, "block_trading")


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 TRADER PSYCHOLOGY RC19 APROVADO")


if __name__ == "__main__":
    main()
