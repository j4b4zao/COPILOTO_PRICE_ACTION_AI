"""Run the PMI-RC2-A15 synthetic audit offline. Prints observations as JSON."""

from collections import Counter
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from hashlib import sha256

from political_market_intelligence.event_model import EventCategory
from political_market_intelligence.official_document_normalizer import DocumentObservation, DocumentState
from political_market_intelligence.official_event_extractor import OfficialEventExtractor
from political_market_intelligence.official_ingestion_service import OfficialIngestionService
from political_market_intelligence.official_source_catalog import OfficialSource, OfficialSourceCatalog, OfficialSourceKind


M = "O Copom elevou a taxa Selic para 13,50% ao ano."
I = "O IBGE divulgou o PIB de 1,2%."
F = "O Tesouro Nacional publicou o resultado fiscal com superávit de R$ 4 bilhões."
E = "O Governo Federal anunciou a suspensão do IOF."
X = "O MDIC publicou os dados da balança comercial."
R = "A CVM revogou a Instrução nº 724/2025."
CATEGORIES = dict(zip("MIFEXR", (
    "MONETARY_POLICY", "ECONOMIC_INDICATOR", "FISCAL_COMMUNICATION",
    "ECONOMIC_MEASURE", "FOREIGN_TRADE", "REGULATORY_CHANGE",
)))

# Expectations describe what these synthetic documents actually assert.
# An illustrative claim, third-party claim or conditional clause is not an
# assertion of an event by the issuing document. Historical facts are eligible.
TEXT = (
    ("nonstandard_heading", "=== Exercício de mesa ===\n" + M, ""),
    ("nonstandard_heading", "[Dados de ensaio]\n" + I, ""),
    ("nonstandard_heading", "Boletim de resultados:\n" + F, "F"),
    ("nonstandard_heading", "2. Resumo executivo\n" + R, "R"),
    ("prior_hypothesis", "Para fins exclusivamente ilustrativos, adotou-se a premissa abaixo.\n\n" + E, ""),
    ("prior_hypothesis", "Suponha o cenário alternativo apresentado a seguir.\n\n" + X, ""),
    ("prior_hypothesis", "Hipótese contrafactual.\n\n" + R, ""),
    ("later_retraction", I + "\n\nCorreção: o dado acima nunca foi divulgado.", ""),
    ("later_retraction", M + " A nota desmente integralmente a frase anterior.", ""),
    ("later_retraction", X + "\nErrata: a publicação referida acima não ocorreu.", ""),
    ("later_retraction", I + "\nCorreção: a coluna foi renomeada. O valor permanece válido.", "I"),
    ("draft", "VERSÃO DE TRABALHO — NÃO PUBLICAR\n" + F, ""),
    ("draft", "Texto sob revisão para o boletim de amanhã.\n\n" + E, ""),
    ("draft", "Minuta para aprovação na próxima reunião.\n" + R, ""),
    ("future_projection", "Estimativa ainda não realizada para o próximo trimestre:\n" + I, ""),
    ("future_projection", "Esperamos que o MDIC publique os dados da balança comercial.", ""),
    ("future_projection", M + " A frase anterior descreve uma decisão prevista para amanhã.", ""),
    ("indirect_negation", "Não procede a alegação a seguir:\n" + X, ""),
    ("indirect_negation", "É falso que o Governo Federal tenha suspendido o IOF.", ""),
    ("indirect_negation", F + " O Tesouro nega que essa divulgação tenha ocorrido.", ""),
    ("double_negation", "O IBGE confirmou que não é falso que divulgou o PIB de 1,2%.", "I"),
    ("double_negation", "Não se pode negar que o Copom elevou a Selic para 13,50% ao ano.", "M"),
    ("double_negation", "Não é verdade que a CVM não tenha revogado a Instrução nº 724/2025.", "R"),
    ("conditional", "Caso a autorização seja concedida:\n" + E, ""),
    ("conditional", "Se o rito houver sido concluído, o MDIC terá publicado os dados da balança comercial.", ""),
    ("conditional", "Se o cenário se confirmar, vale a descrição abaixo.\n\n" + M, ""),
    ("sections", "## Simulação fiscal\n" + F + "\n\n## Fatos documentados\n" + E + "\n" + R, "ER"),
    ("sections", "# Notas da reunião\n" + M + "\n\n## Hipótese alternativa\n" + I + "\n\n## Resultados efetivos\n" + X, "MX"),
    ("sections", "## Cenário simulado\n" + X + "\n\n## Resultados oficiais\n" + I + "\n\n## Minuta futura\n" + R, "I"),
    ("sections", "## Hipótese descartada\n" + R + "\n\n## Deliberação registrada\n" + M, "M"),
    ("punctuation", "• " + I, "I"),
    ("punctuation", M.rstrip(".") + "…", "M"),
    ("punctuation", F.rstrip(".") + ": dado divulgado no boletim.", "F"),
    ("punctuation", E.rstrip(".") + "!", "E"),
    ("punctuation", "O IBGE divulgou o PIB de 1,2%.\u00a0" + X, "IX"),
    ("linebreak", R.replace("revogou", "revo-\ngou"), "R"),
    ("linebreak", X.replace("dados da", "dados\r\n\t da"), "X"),
    ("linebreak", F.replace("com superávit", "com\n\nsuperávit"), "F"),
    ("linebreak", M.replace("13,50", "13,\n50"), "M"),
    ("linebreak", E.replace("anunciou a", "anunciou\ra"), "E"),
    ("compound", M.rstrip(".") + " e o IBGE divulgou o PIB de 1,2%.", "MI"),
    ("compound", X.rstrip(".") + ", enquanto a CVM revogou a Instrução nº 724/2025.", "XR"),
    ("compound", F.rstrip(".") + "; " + E, "FE"),
    ("quotation", "Segundo a associação, o Governo Federal anunciou a suspensão do IOF.", ""),
    ("quotation", "A associação divulgou a seguinte alegação:\n" + X, ""),
    ("quotation", "Depoimento de terceiro (trecho literal):\n" + M, ""),
    ("quotation", "“" + R + "” — declarou um terceiro, sem confirmação.", ""),
    ("historical", "O Copom elevou a taxa Selic para 13,50% ao ano em 2024.", "M"),
    ("historical", "Arquivo de decisões de 2024.\n\n" + R, "R"),
    ("historical", "Em retrospecto, o IBGE divulgou o PIB de 1,2%.", "I"),
    ("historical", "Na série anterior, o Tesouro Nacional publicou o resultado fiscal com superávit de R$ 4 bilhões.", "F"),
    ("historical", "Registro retrospectivo de atos concluídos.\n\n" + E + "\n" + X, "EX"),
)

NOW = datetime(2026, 11, 19, 17, tzinfo=timezone.utc)
PAST = NOW - timedelta(days=2)


def run():
    catalog = OfficialSourceCatalog(tuple(OfficialSource(
        source_id=name, institution="Synthetic example", country_code="BR",
        kind=OfficialSourceKind.COMMUNICATION, candidate_url="https://example.org",
        capabilities={EventCategory.CONFIRMED_FACT},
    ) for name in ("fixture-br", "second-br")))
    extractor = OfficialEventExtractor(catalog)
    proto = DocumentObservation(source_id="fixture-br", document_id="a15",
                                revision=1, title="Synthetic", content=M,
                                published_at=PAST, received_at=NOW)
    results = []
    contract = []
    for n, (group, content, wanted) in enumerate(TEXT, 1):
        doc = replace(proto, content=content, content_sha256="")
        events = extractor.extract((doc,), as_of=NOW)
        actual = Counter(e.category.value for e in events)
        expected = Counter(CATEGORIES[code] for code in wanted)
        valid_evidence = all(
            doc.content[e.content_start:e.content_end] == e.description
            and 0 <= e.content_start < e.content_end <= len(doc.content)
            and e.content_sha256 == doc.content_sha256
            and (e.source_id, e.document_id, e.revision) == doc.key
            and e.state is DocumentState.UNVERIFIED
            for e in events
        )
        valid_time = all(
            e.published_at == doc.published_at and e.available_at == doc.received_at
            and e.published_at <= e.available_at <= NOW
            and e.published_at.tzinfo is timezone.utc and e.available_at.tzinfo is timezone.utc
            for e in events
        )
        results.append(dict(id=n, group=group, expected=expected, actual=actual,
                            tp=actual & expected, fp=actual - expected, fn=expected - actual,
                            provenance_ok=valid_evidence, time_ok=valid_time))

    def check(label, group, operation, expected=True):
        try:
            actual = operation()
        except (TypeError, KeyError, ValueError) as exc:
            actual = (type(exc).__name__, str(exc))
        passed = (isinstance(actual, tuple) and actual[0] == expected[0]
                  and expected[1] in actual[1]) if isinstance(expected, tuple) else actual == expected
        contract.append(dict(label=label, group=group, passed=passed, observed=actual))

    past = replace(proto, received_at=NOW - timedelta(days=1))
    revision = replace(proto, revision=3)
    other = replace(past, document_id="reposted")
    another_source = replace(past, source_id="second-br")
    alternate = replace(past, content=I, content_sha256="")
    forged = replace(past)
    object.__setattr__(forged, "content_sha256", sha256(F.encode()).hexdigest())
    tampered = replace(past)
    object.__setattr__(tampered, "state", "UNVERIFIED")

    def extract(*docs, cutoff=NOW):
        return extractor.extract(docs, as_of=cutoff)

    check("one microsecond before UTC cutoff", "time",
          lambda: len(extract(proto, cutoff=NOW - timedelta(microseconds=1))), ("ValueError", "cutoff"))
    check("same cutoff expressed at UTC+05:30", "time",
          lambda: extract(proto) == extract(proto, cutoff=NOW.astimezone(timezone(timedelta(hours=5, minutes=30)))))
    check("future publication and receiving clocks", "time",
          lambda: extract(replace(proto, published_at=NOW + timedelta(hours=1),
                                  received_at=NOW + timedelta(hours=2))), ("ValueError", "cutoff"))
    check("historical publication received today", "time",
          lambda: extract(replace(proto, published_at=NOW - timedelta(days=3650)))[0].available_at == NOW)
    check("revision gaps preserve order", "identity",
          lambda: [event.revision for event in extract(revision, past)], [1, 3])
    check("revision with equal receive timestamps", "time",
          lambda: len(extract(proto, revision)) == 2)
    check("chronology inverted across revision gap", "time",
          lambda: extract(proto, replace(past, revision=4)), ("ValueError", "higher revision"))
    check("republication uses distinct identity", "identity",
          lambda: len({event.event_id for event in extract(past, other)}) == 2)
    check("same document ID for distinct sources", "identity",
          lambda: len({event.event_id for event in extract(past, another_source)}) == 2)
    check("normalization conflict in content", "identity",
          lambda: extract(past, alternate), ("ValueError", "conflicting document identity"))
    check("normalization conflict in clocks", "identity",
          lambda: extract(past, proto), ("ValueError", "conflicting document identity"))
    check("digest substituted from different document", "provenance",
          lambda: extract(forged), ("ValueError", "provenance"))
    check("state replaced by same-valued string", "provenance",
          lambda: extract(tampered), ("ValueError", "provenance"))
    check("uncatalogued source with otherwise valid document", "provenance",
          lambda: extract(replace(past, source_id="outside-a15")), ("KeyError", "outside-a15"))
    check("repeated and reversed input batch", "replay",
          lambda: extract(past, other) == extract(other, past, other, past))
    check("fresh extractor replay", "replay",
          lambda: extract(proto) == OfficialEventExtractor(catalog).extract((proto,), as_of=NOW))

    def replay_conflict():
        service = OfficialIngestionService(catalog)
        payload = {name: getattr(past, name) for name in (
            "source_id", "document_id", "revision", "title", "content", "published_at", "received_at",
        )}
        service.ingest((payload,), as_of=NOW)
        return service.ingest((payload | {"content": I},), as_of=NOW + timedelta(minutes=1))

    check("A5 retained conflict across later cutoff", "identity",
          replay_conflict, ("ValueError", "conflicting replay"))

    print(json.dumps({"text": results, "contract": contract}, indent=2, ensure_ascii=True, default=str))


if __name__ == "__main__":
    run()
