"""Testes offline da revisão psicológica de sessão RC23."""

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone

from core.system_initializer import SystemInitializer
from psychology import (
    TraderPsychologyReviewMessage,
    TraderPsychologySessionReview,
    TraderPsychologySessionReviewer,
    TraderPsychologySessionSummary,
)


NOW = datetime(2026, 8, 25, tzinfo=timezone.utc)


def summary(**changes):
    payload = dict(
        status="AVAILABLE",
        total_cycles=5,
        neutral_cycles=0,
        attention_cycles=5,
        pause_recommended_cycles=0,
        linked_evidence_cycles=0,
        unique_evidence_trade_ids=(),
        signal_counts=(("FOMO", 2),),
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


def build(**changes):
    return TraderPsychologySessionReviewer().build(
        summary(**changes)
    )


def text(result):
    return " ".join(message.text for message in result.messages)


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_resumo_vazio_produz_revisao_vazia():
    result = TraderPsychologySessionReviewer().build(
        empty_summary()
    )
    assert result.status == "EMPTY"
    assert result.messages == ()
    assert result.source_total_cycles == 0


def teste_fomo_gera_reflexao_de_confirmacao():
    result = build(dominant_signal_code="FOMO")
    assert result.messages[0].code == "DOMINANT_PATTERN"
    assert "confirmação objetiva" in result.messages[0].text


def teste_fora_do_plano_gera_reflexao_de_checklist():
    result = build(dominant_signal_code="OUTSIDE_PLAN")
    assert "checklist" in result.messages[0].text


def teste_overtrading_gera_reflexao_de_criterios():
    result = build(dominant_signal_code="OVERTRADING")
    assert "critérios mínimos" in result.messages[0].text


def teste_revenge_gera_reflexao_sobre_fatos_novos():
    result = build(dominant_signal_code="REVENGE_TRADING")
    assert "quais fatos mudaram" in result.messages[0].text


def teste_stop_sequence_evitar_julgamento_do_resultado():
    result = build(dominant_signal_code="STOP_SEQUENCE")
    assert "sem julgar" in result.messages[0].text


def teste_reentrada_apressada_foca_informacao_nova():
    result = build(dominant_signal_code="RUSHED_REENTRY")
    assert "informação nova" in result.messages[0].text


def teste_excesso_de_confianca_foca_padrao_do_plano():
    result = build(dominant_signal_code="OVERCONFIDENCE")
    assert "padrão do plano" in result.messages[0].text


def teste_sem_sinal_recorrente_revisa_processo():
    result = build(
        dominant_signal_code=None,
        signal_counts=(),
    )
    assert result.messages[0].code == "NO_RECURRING_SIGNAL"
    assert "processo" in result.messages[0].text


def teste_pausas_geram_revisao_factual():
    result = build(pause_recommended_cycles=2)
    message = next(
        item for item in result.messages
        if item.code == "PAUSE_REVIEW"
    )
    assert "2 ciclo(s)" in message.text
    assert "fatos" in message.text
    assert not result.pause_recommended


def teste_evidencias_geram_cobertura_numerica():
    result = build(
        total_cycles=5,
        linked_evidence_cycles=3,
    )
    message = next(
        item for item in result.messages
        if item.code == "EVIDENCE_COVERAGE"
    )
    assert "3 de 5" in message.text


def teste_falha_de_voz_e_tratada_como_dado_tecnico():
    result = build(voice_failed_cycles=2)
    message = next(
        item for item in result.messages
        if item.code == "VOICE_TECHNICAL"
    )
    assert "dado é técnico" in message.text
    assert "não altera a análise" in message.text


def teste_limite_de_mensagens_e_respeitado():
    reviewer = TraderPsychologySessionReviewer(
        maximum_messages=2
    )
    result = reviewer.build(summary(
        pause_recommended_cycles=2,
        linked_evidence_cycles=3,
        voice_failed_cycles=1,
    ))
    assert len(result.messages) == 2


def teste_configuracao_invalida_e_rejeitada():
    for value in (0, 7):
        raises(
            ValueError,
            lambda value=value: TraderPsychologySessionReviewer(
                maximum_messages=value
            ),
        )
    raises(
        TypeError,
        lambda: TraderPsychologySessionReviewer(
            maximum_messages=True
        ),
    )


def teste_summary_incompativel_e_rejeitado():
    raises(
        TypeError,
        lambda: TraderPsychologySessionReviewer().build(
            object()
        ),
    )


def teste_mensagens_nao_contem_comandos_operacionais():
    result = build(
        pause_recommended_cycles=2,
        linked_evidence_cycles=3,
        voice_failed_cycles=1,
    )
    lowered = text(result).casefold()
    for forbidden in (
        "compre agora",
        "venda agora",
        "entre comprado",
        "entre vendido",
    ):
        assert forbidden not in lowered


def teste_resultado_e_mensagens_sao_imutaveis():
    result = build()
    assert isinstance(result, TraderPsychologySessionReview)
    assert isinstance(result.messages[0], TraderPsychologyReviewMessage)
    raises(
        FrozenInstanceError,
        lambda: setattr(result, "status", "ALTERADO"),
    )
    raises(
        FrozenInstanceError,
        lambda: setattr(result.messages[0], "text", "ALTERADO"),
    )


def teste_system_initializer_antes_de_inicializar_retorna_empty():
    result = SystemInitializer().psychology_session_review()
    assert result.status == "EMPTY"
    assert result.messages == ()


def teste_flags_operacionais_permanecem_fechadas():
    result = build(pause_recommended_cycles=2)
    assert result.observational_only
    assert not result.pause_recommended
    assert not result.score_influence_allowed
    assert not result.order_execution_allowed
    assert not result.operational_block_allowed


def teste_reviewer_nao_expoe_execucao_ou_bloqueio():
    reviewer = TraderPsychologySessionReviewer()
    assert not hasattr(reviewer, "send_order")
    assert not hasattr(reviewer, "block_trading")
    assert not hasattr(reviewer, "change_score")


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 TRADER PSYCHOLOGY RC23 APROVADO")


if __name__ == "__main__":
    main()
