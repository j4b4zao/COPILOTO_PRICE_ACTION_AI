"""Testes controlados da normalização de payloads econômicos RC4."""

from datetime import datetime, timedelta, timezone

from economic_context import EconomicCalendarPayloadNormalizer


NORMALIZER = EconomicCalendarPayloadNormalizer()


def row(**changes):
    base = {
        "title": "Payroll",
        "scheduled_at": "2026-08-24T13:30:00-03:00",
        "impact": "HIGH",
        "currency": "USD",
        "country": "US",
    }
    base.update(changes)
    return base


def teste_normaliza_payload_canonico():
    result = NORMALIZER.normalize([row()], source="api_teste")
    event = result.events[0]
    assert result.valid and result.usable
    assert event.title == "Payroll"
    assert event.source == "API_TESTE"
    assert event.scheduled_at.utcoffset() == timedelta(hours=-3)


def teste_aceita_aliases_em_portugues():
    result = NORMALIZER.normalize([{
        "evento": "Copom", "data": "2026-08-24T14:00:00-03:00",
        "impacto": "alto", "moeda": "BRL", "pais": "BR",
    }])
    assert result.events[0].title == "Copom"
    assert result.events[0].impact == "HIGH"


def teste_aplica_fuso_padrao_em_datetime_ingenuo():
    result = NORMALIZER.normalize(
        [row(scheduled_at="2026-08-24T13:30:00")], default_timezone="America/Sao_Paulo"
    )
    assert result.events[0].scheduled_at.utcoffset() == timedelta(hours=-3)


def teste_preserva_instante_com_offset_explicito():
    result = NORMALIZER.normalize(
        [row(scheduled_at="2026-08-24T16:30:00Z")], default_timezone="America/Sao_Paulo"
    )
    assert result.events[0].scheduled_at.utcoffset() == timedelta(0)


def teste_impactos_numericos_e_textuais():
    result = NORMALIZER.normalize([
        row(title="Baixo", impact=1), row(title="Médio", impact="médio"), row(title="Alto", impact=3)
    ])
    assert [event.impact for event in result.events] == ["LOW", "MEDIUM", "HIGH"]


def teste_rejeita_linha_malformada_sem_perder_validas():
    result = NORMALIZER.normalize([row(), row(title="")])
    assert len(result.events) == 1
    assert result.rejected_count == 1
    assert result.valid is False
    assert result.usable is True


def teste_deduplica_mesmo_instante_em_fusos_diferentes():
    result = NORMALIZER.normalize([
        row(scheduled_at="2026-08-24T13:30:00-03:00"),
        row(scheduled_at="2026-08-24T16:30:00Z"),
    ])
    assert len(result.events) == 1
    assert result.duplicate_count == 1


def teste_deduplicacao_preserva_maior_impacto():
    result = NORMALIZER.normalize([row(impact="LOW"), row(impact="HIGH")])
    assert result.events[0].impact == "HIGH"
    assert result.duplicate_count == 1


def teste_nao_deduplica_eventos_em_horarios_diferentes():
    result = NORMALIZER.normalize([
        row(scheduled_at="2026-08-24T13:30:00-03:00"),
        row(scheduled_at="2026-08-24T14:30:00-03:00"),
    ])
    assert len(result.events) == 2


def teste_ordena_eventos_cronologicamente():
    result = NORMALIZER.normalize([
        row(title="Segundo", scheduled_at="2026-08-24T14:30:00-03:00"),
        row(title="Primeiro", scheduled_at="2026-08-24T13:30:00-03:00"),
    ])
    assert [event.title for event in result.events] == ["Primeiro", "Segundo"]


def teste_fuso_invalido_falha_antes_da_normalizacao():
    try:
        NORMALIZER.normalize([row()], default_timezone="Fuso/Inexistente")
    except ValueError:
        return
    raise AssertionError("Fuso inválido deveria ser rejeitado.")


def teste_snapshot_expoe_diagnostico_da_normalizacao():
    result = NORMALIZER.normalize([row(), "inválido"])
    snapshot = result.snapshot()
    assert snapshot["received_count"] == 2
    assert snapshot["event_count"] == 1
    assert snapshot["rejected_count"] == 1
    assert snapshot["errors"][0].startswith("ROW_1:")


def main():
    tests = [value for name, value in globals().items() if name.startswith("teste_")]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 ECONOMIC CALENDAR RC4 APROVADO")


if __name__ == "__main__":
    main()
