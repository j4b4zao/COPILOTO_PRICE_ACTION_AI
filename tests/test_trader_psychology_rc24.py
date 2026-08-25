"""Testes offline da projeção psicológica de dashboard RC24."""

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone

from core.system_initializer import SystemInitializer
from psychology import (
    PsychologyVoiceReadiness,
    TraderPsychologyDashboardMessage,
    TraderPsychologyDashboardProjection,
    TraderPsychologyDashboardProjector,
    TraderPsychologyRuntime,
    TraderPsychologySessionJournal,
    TraderPsychologySessionReviewer,
    TraderPsychologySessionSummarizer,
    TraderPsychologySessionSummary,
    TraderPsychologyState,
    VoiceAssistantConfig,
)


NOW = datetime(2026, 8, 25, 15, 0, tzinfo=timezone.utc)


def summary(**changes):
    payload = dict(
        status="AVAILABLE",
        total_cycles=5,
        neutral_cycles=0,
        attention_cycles=5,
        pause_recommended_cycles=0,
        linked_evidence_cycles=0,
        unique_evidence_trade_ids=(),
        signal_counts=(("FOMO", 3),),
        dominant_signal_code="FOMO",
        voice_delivered_cycles=0,
        voice_suppressed_cycles=0,
        voice_failed_cycles=0,
        first_sequence=1,
        last_sequence=5,
        started_at=NOW,
        updated_at=NOW,
    )
    payload.update(changes)
    return TraderPsychologySessionSummary(**payload)


def empty_summary():
    return summary(
        status="EMPTY",
        total_cycles=0,
        neutral_cycles=0,
        attention_cycles=0,
        signal_counts=(),
        dominant_signal_code=None,
        first_sequence=None,
        last_sequence=None,
        started_at=None,
        updated_at=None,
    )


def readiness(enabled=False):
    return PsychologyVoiceReadiness().inspect(
        config=VoiceAssistantConfig(enabled=enabled),
        sink=None,
    )


def project(source=None, voice=None):
    source = source or summary()
    review = TraderPsychologySessionReviewer().build(
        source
    )
    return TraderPsychologyDashboardProjector().project(
        summary=source,
        review=review,
        voice_readiness=voice or readiness(),
    )


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_sessao_vazia_produz_dashboard_empty():
    result = project(empty_summary())
    assert result.status == "EMPTY"
    assert result.total_cycles == 0
    assert result.latest_sequence is None
    assert result.review_messages == ()
    assert "Aguardando" in result.headline


def teste_sessao_neutra_produz_estado_neutral():
    source = summary(
        total_cycles=3,
        neutral_cycles=3,
        attention_cycles=0,
        signal_counts=(),
        dominant_signal_code=None,
    )
    result = project(source)
    assert result.status == "NEUTRAL"
    assert result.neutral_cycles == 3
    assert "Nenhum padrão" in result.headline


def teste_atencao_produz_estado_observacional():
    result = project()
    assert result.status == "ATTENTION_OBSERVED"
    assert result.attention_cycles == 5
    assert "revisão" in result.headline


def teste_pausa_observada_tem_precedencia_visual():
    result = project(summary(
        pause_recommended_cycles=2,
    ))
    assert result.status == "PAUSE_OBSERVED"
    assert result.pause_recommended_cycles == 2
    assert "recomendações de pausa" in result.headline
    assert not result.operational_block_allowed


def teste_sinal_dominante_e_contagem_sao_projetados():
    result = project(summary(
        signal_counts=(
            ("OVERTRADING", 4),
            ("FOMO", 2),
        ),
        dominant_signal_code="OVERTRADING",
    ))
    assert result.dominant_signal_code == "OVERTRADING"
    assert result.dominant_signal_count == 4


def teste_sem_sinal_dominante_tem_contagem_zero():
    result = project(summary(
        signal_counts=(),
        dominant_signal_code=None,
        attention_cycles=0,
        neutral_cycles=5,
    ))
    assert result.dominant_signal_code is None
    assert result.dominant_signal_count == 0


def teste_cobertura_de_evidencia_e_projetada():
    result = project(summary(
        linked_evidence_cycles=3,
        unique_evidence_trade_ids=(
            "trade-1",
            "trade-2",
        ),
    ))
    assert result.linked_evidence_cycles == 3
    assert result.evidence_trade_count == 2


def teste_metricas_de_voz_sao_projetadas():
    result = project(summary(
        voice_delivered_cycles=4,
        voice_suppressed_cycles=2,
        voice_failed_cycles=1,
    ))
    assert result.voice_delivered_cycles == 4
    assert result.voice_suppressed_cycles == 2
    assert result.voice_failed_cycles == 1


def teste_prontidao_de_voz_e_projetada():
    result = project()
    assert result.voice_readiness_status == "DISABLED"
    assert not result.voice_ready


def teste_mensagens_de_revisao_sao_copiadas():
    result = project(summary(
        pause_recommended_cycles=1,
        linked_evidence_cycles=2,
    ))
    assert result.review_messages
    assert isinstance(
        result.review_messages[0],
        TraderPsychologyDashboardMessage,
    )
    codes = {
        message.code for message in result.review_messages
    }
    assert "DOMINANT_PATTERN" in codes
    assert "PAUSE_REVIEW" in codes
    assert "EVIDENCE_COVERAGE" in codes


def teste_sequencia_e_atualizacao_sao_projetadas():
    result = project()
    assert result.latest_sequence == 5
    assert result.updated_at == NOW


def teste_review_de_outra_sessao_e_rejeitado():
    source = summary()
    wrong = TraderPsychologySessionReviewer().build(
        replace(source, total_cycles=4)
    )
    raises(
        ValueError,
        lambda: TraderPsychologyDashboardProjector().project(
            summary=source,
            review=wrong,
            voice_readiness=readiness(),
        ),
    )


def teste_contratos_invalidos_sao_rejeitados():
    projector = TraderPsychologyDashboardProjector()
    source = summary()
    review = TraderPsychologySessionReviewer().build(source)
    voice = readiness()
    raises(
        TypeError,
        lambda: projector.project(
            summary=object(),
            review=review,
            voice_readiness=voice,
        ),
    )
    raises(
        TypeError,
        lambda: projector.project(
            summary=source,
            review=object(),
            voice_readiness=voice,
        ),
    )
    raises(
        TypeError,
        lambda: projector.project(
            summary=source,
            review=review,
            voice_readiness=object(),
        ),
    )


def teste_system_initializer_antes_de_inicializar_expoe_empty():
    result = SystemInitializer().psychology_dashboard_projection()
    assert result.status == "EMPTY"
    assert result.voice_readiness_status == "DISABLED"


def teste_system_initializer_projeta_diario_atual():
    system = SystemInitializer()
    system.psychology_session_journal = (
        TraderPsychologySessionJournal(
            clock=lambda: NOW,
        )
    )
    system.psychology_session_journal.record(
        TraderPsychologyRuntime().process(
            TraderPsychologyState(chased_price=True)
        )
    )
    result = system.psychology_dashboard_projection()
    assert result.status == "ATTENTION_OBSERVED"
    assert result.dominant_signal_code == "FOMO"
    assert result.latest_sequence == 1


def teste_projecao_e_mensagens_sao_imutaveis():
    result = project()
    assert isinstance(result, TraderPsychologyDashboardProjection)
    raises(
        FrozenInstanceError,
        lambda: setattr(result, "status", "ALTERADO"),
    )
    raises(
        FrozenInstanceError,
        lambda: setattr(
            result.review_messages[0],
            "text",
            "ALTERADO",
        ),
    )


def teste_dashboard_nao_expoe_estado_operacional():
    result = project()
    for name in (
        "score",
        "strategy",
        "risk",
        "decision",
        "alert",
        "direction",
        "send_order",
    ):
        assert not hasattr(result, name)


def teste_flags_operacionais_permanecem_fechadas():
    result = project(summary(pause_recommended_cycles=2))
    assert result.observational_only
    assert not result.score_influence_allowed
    assert not result.order_execution_allowed
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
    print("🏆 TRADER PSYCHOLOGY RC24 APROVADO")


if __name__ == "__main__":
    main()
