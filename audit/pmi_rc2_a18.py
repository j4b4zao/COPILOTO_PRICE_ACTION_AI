"""A18 paragraph continuity audit against the unmodified A17 extractor."""

from dataclasses import replace
from collections import Counter
import json
import re

from audit.pmi_rc2_a15 import CATEGORIES, NOW, PAST, TEXT
from political_market_intelligence.event_model import EventCategory
from political_market_intelligence.official_document_normalizer import DocumentObservation, DocumentState
from political_market_intelligence.official_event_extractor import OfficialEventExtractor
from political_market_intelligence.official_source_catalog import OfficialSource, OfficialSourceCatalog, OfficialSourceKind


F = "O Tesouro Nacional publicou o resultado fiscal com déficit de R$ 7 milhões."
M = "O Copom fixou a Selic em 11,75% ao ano."
I = "O IBGE divulgou a taxa de desemprego de 6,7%."
R = "A CVM alterou a Resolução nº 291/2022."
E = "O Governo Federal anunciou o aumento do IOF."
X = "O MDIC divulgou os dados da balança comercial."

# Each row records the expected asserted events and the expected disposition
# of the paragraph boundary, independently of what the extractor recognizes.
CASES = (
    ("fiscal-preposition", F.replace("com déficit", "com\n\ndéficit"), "F", "continue"),
    ("fiscal-three-breaks", F.replace("de R$", "de\n\n\nR$"), "F", "continue"),
    ("fiscal-value-unit", F.replace("7 milhões", "7\n\nmilhões"), "F", "continue"),
    ("fiscal-crlf-tabs", F.replace("resultado fiscal", "resultado fiscal\r\n \t\r\n "), "F", "continue"),
    ("monetary-preposition", M.replace("em 11", "em\n\n11"), "M", "continue"),
    ("monetary-auxiliary", "O Copom decidiu\n\nmanter a Selic em 11,75% ao ano.", "M", "continue"),
    ("monetary-decimal", M.replace("11,75", "11,\n\n75"), "M", "continue"),
    ("monetary-rate-unit", M.replace("% ao ano", "%\n\nao ano"), "M", "continue"),
    ("indicator-preposition", I.replace("de 6", "de\n\n6"), "I", "continue"),
    ("indicator-auxiliary", "O IBGE informou que a taxa de desemprego foi\n\nde 6,7%.", "I", "continue"),
    ("indicator-decimal", I.replace("6,7", "6,\r\n\r\n7"), "I", "continue"),
    ("regulation-after-verb", R.replace("alterou a", "alterou\n\na"), "R", "continue"),
    ("regulation-after-number-symbol", R.replace("nº 291", "nº\n\n291"), "R", "continue"),
    ("regulation-hyphenation", R.replace("alterou", "alte-\n\nrou"), "R", "continue"),
    ("trade-preposition", X.replace("da balança", "da\n\nbalança"), "X", "continue"),
    ("measure-arbitrary-wrap", E.replace("Federal anunciou", "Federal\n\nanunciou").replace("aumento do", "aumento\n\ndo"), "E", "continue"),
    ("punctuation-two-events", R + "\n\n" + I, "RI", "separate"),
    ("multiple-blank-lines-independent", X + "\n\n\n\n" + M, "XM", "separate"),
    ("complete-clause-without-period", R[:-1] + "\n\n" + X, "RX", "separate"),
    ("subject-change-after-preposition", F.split("déficit")[0].rstrip() + "\n\n" + R, "R", "block"),
    ("unrelated-quantity", "O Tesouro Nacional publicou o resultado fiscal com\n\n7 participantes compareceram à reunião.", "", "block"),
    ("header-between-fragments", "O Copom fixou a Selic em\n\n## Decisões oficiais\n\n11,75% ao ano.", "", "block"),
    ("negative-continuation", "O Copom decidiu\n\nnão manter a Selic em 11,75% ao ano.", "", "block"),
    ("negative-second-paragraph", I + "\n\nErrata: a informação acima não foi divulgada.", "", "block"),
    ("hypothetical-fragments", "Hipótese de estresse:\n" + F.replace("com déficit", "com\n\ndéficit"), "", "block"),
    ("conditional-fragments", "Se a condição se cumprir:\n" + M.replace("em 11", "em\n\n11"), "", "block"),
    ("retraction-of-interrupted", F.replace("com déficit", "com\n\ndéficit") + "\n\nRetratação: a informação acima foi desmentida.", "", "block"),
    ("draft-and-factual-release", "Minuta:\n" + M.replace("em 11", "em\n\n11") + "\n\n## Fatos documentados\n" + R, "R", "block"),
    ("context-switch-incomplete", "Minuta:\nO IBGE divulgou a taxa de desemprego de\n\n## Resultados oficiais\n\n6,7%.", "", "block"),
    ("third-party-quote", "Segundo a associação, o Copom fixou a Selic em\n\n11,75% ao ano.", "", "block"),
    ("quoted-paragraphs", "“" + F.replace("com déficit", "com\n\ndéficit") + "”", "", "block"),
    ("period-with-fragment", "O Tesouro Nacional publicou o resultado fiscal com.\n\nDéficit de R$ 7 milhões.", "", "block"),
    ("planned-release", "Projeção para o semestre seguinte:\n" + I.replace("de 6", "de\n\n6"), "", "block"),
    ("offset-after-unicode", "Nota 📄 de arquivo.\r\n\r\n\t" + E + "\r\n\r\n" + R, "ER", "separate"),
    ("fiscal-fragment-independent-fact", "O Tesouro Nacional publicou o resultado fiscal com\n\n" + F, "F", "separate"),
    ("third-party-introduction", "A informação abaixo é uma alegação da associação.\n\n" + M, "", "block"),
    ("fictional-exercise-fragments", "Exercício com dados inventados.\n\n"
     + F.replace("com déficit", "com\n\ndéficit"), "", "block"),
    ("embargoed-preview-fragments", "A versão abaixo descreve uma decisão de amanhã, ainda pendente.\n\n"
     + M.replace("em 11", "em\n\n11"), "", "block"),
)


def run():
    source = OfficialSource(
        source_id="synthetic-a18", institution="Synthetic", country_code="BR",
        kind=OfficialSourceKind.COMMUNICATION, candidate_url="https://example.org/",
        capabilities={EventCategory.CONFIRMED_FACT},
    )
    extractor = OfficialEventExtractor(OfficialSourceCatalog((source,)))
    _, reference, expected = TEXT[37]
    rows = []
    for label, content, wanted, boundary in (
        ("A15-38", reference, expected, "continue"), *CASES,
    ):
        doc = DocumentObservation(
            source_id=source.source_id, document_id=label, revision=1,
            title="Synthetic", content=content, published_at=PAST, received_at=NOW,
        )
        events = extractor.extract((doc,), as_of=NOW)
        actual = Counter(event.category.value for event in events)
        expected_counts = Counter(CATEGORIES[code] for code in wanted)
        # Counterfactual only. Feed a differently formatted synthetic document
        # to A17 to measure the risk of erasing paragraph boundaries.
        flattened = re.sub(r"\r?\n(?:[ \t]*\r?\n)+", "\n", content)
        joined_doc = replace(doc, content=flattened, content_sha256="")
        joined = Counter(event.category.value for event in extractor.extract((joined_doc,), as_of=NOW))
        rows.append(dict(
            label=label, boundary=boundary, expected=expected_counts, actual=actual,
            fp=actual - expected_counts, fn=expected_counts - actual,
            flattened=joined, flattened_fp=joined - expected_counts,
            flattened_fn=expected_counts - joined,
            spans=[(e.content_start, e.content_end, e.description) for e in events],
            evidence_ok=all(
                0 <= e.content_start < e.content_end <= len(content)
                and content[e.content_start:e.content_end] == e.description
                and e.content_sha256 == doc.content_sha256
                and e.state is DocumentState.UNVERIFIED
                and (e.source_id, e.document_id, e.revision) == doc.key
                for e in events
            ),
            replay_ok=events == extractor.extract((doc, doc), as_of=NOW),
        ))
    print(json.dumps(rows, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    run()
