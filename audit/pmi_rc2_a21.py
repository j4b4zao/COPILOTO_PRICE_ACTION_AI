"""Audit multifragment continuity without changing extraction."""

from collections import Counter
from dataclasses import replace
import json
import re

from audit.pmi_rc2_a15 import CATEGORIES, NOW, PAST
from audit.pmi_rc2_a18 import CASES as A18_CASES
from political_market_intelligence.event_model import EventCategory
from political_market_intelligence.official_document_normalizer import DocumentObservation, DocumentState
from political_market_intelligence.official_event_extractor import OfficialEventExtractor
from political_market_intelligence.official_source_catalog import OfficialSource, OfficialSourceCatalog, OfficialSourceKind


F = "O Tesouro Nacional divulgou o resultado primário com superávit de R$ 9 milhões."
E = "O Governo Federal anunciou a suspensão do IPI."
M = "O Copom reduziu a taxa Selic para 9,75% ao ano."
I = "O IBGE divulgou o IBC-Br de 0,8%."
R = "A CVM editou a Instrução nº 54/2021."
X = "A Secex divulgou os dados da balança comercial."


def broken(text, *points, gap="\n\n"):
    for point in points:
        text = text.replace(point + " ", point + gap, 1)
    return text


F3 = broken(F, "primário", "R$ 9")
E3 = broken(E, "anunciou", "suspensão")
E4 = broken(E, "Governo", "anunciou", "suspensão")
M3 = broken(M, "Copom", "para")
I3 = broken(I, "IBGE", "de")
F4 = broken(F, "Nacional", "primário", "R$ 9")

# Each row gives the expected asserted categories and boundary disposition.
CASES = (
    ("fiscal-three", F3, "F", "continue"),
    ("fiscal-four", F4, "F", "continue"),
    ("measure-three", E3, "E", "continue"),
    ("measure-four", E4, "E", "continue"),
    ("monetary-three", M3, "M", "continue"),
    ("indicator-three", I3, "I", "continue"),
    ("trade-three", broken(X, "divulgou", "balança"), "X", "continue"),
    ("regulatory-three", broken(R, "editou", "nº"), "R", "continue"),
    ("two-empty-lines", broken(F, "com", gap="\n\n\n"), "F", "continue"),
    ("three-empty-lines", broken(M, "para", gap="\n\n\n\n"), "M", "continue"),
    ("crlf-two-empty-lines", broken(I, "de", gap="\r\n \r\n\t\r\n"), "I", "continue"),
    ("line-wrap-plus-paragraph-break", F3.replace("Tesouro Nacional", "Tesouro\nNacional"), "F", "continue"),
    ("multifragment-decimal", M3.replace("9,75", "9,\n\n75"), "M", "continue"),
    ("decimal-with-two-empty-lines", I.replace("0,8", "0,\n\n\n8"), "I", "continue"),
    ("regulatory-reference", broken(R, "nº").replace("54/2021", "54/\n\n2021"), "R", "continue"),
    ("literal-offset-after-emoji", "Nota 🧾.\r\n\r\n  " + F3 + "\r\n\r\n" + X, "FX", "continue"),
    ("completed-fact-before-fragments", R + "\n\n" + E3, "RE", "continue"),
    ("single-fiscal-boundary-control", broken(F, "com"), "F", "continue"),
    ("single-monetary-boundary-control", broken(M, "para"), "M", "continue"),
    ("period-interrupts", F3.replace("primário\n", "primário.\n"), "", "block"),
    ("semicolon-interrupts", E3.replace("anunciou\n", "anunciou;\n"), "", "block"),
    ("question-interrupts", M3.replace("para\n", "para?\n"), "", "block"),
    ("different-subject", "O Copom decidiu\n\n" + R + "\n\n" + I, "RI", "separate"),
    ("incompatible-subject-between", "O Tesouro Nacional divulgou o resultado primário com\n\n"
     + "A comissão se reuniu.\n\nsuperávit de R$ 9 milhões.", "", "block"),
    ("section-switch", "O Governo Federal anunciou\n\n## Fatos documentados\n\na suspensão\n\ndo IPI.", "", "block"),
    ("heading-between", "O Governo Federal anunciou\n\n## Agenda fiscal\n\na suspensão\n\ndo IPI.", "", "block"),
    ("hypothesis-first", "Hipótese para estudo:\n" + E3, "", "block"),
    ("hypothesis-middle", "O Governo Federal anunciou\n\nHipótese de teste:\n\na suspensão\n\ndo IPI.", "", "block"),
    ("unmarked-hypothesis", "Premissa contrafactual para esta atividade.\n\n" + E3, "", "block"),
    ("draft", "Minuta para revisão:\n" + F3, "", "block"),
    ("unmarked-draft", "Rascunho de circulação interna, sem publicação.\n\n" + F3, "", "block"),
    ("future-projection", "Projeção para o fim do ano:\n" + M3, "", "block"),
    ("unmarked-future-preview", "Exemplo do anúncio projetado para amanhã.\n\n" + M3, "", "block"),
    ("intermediate-negation", "O Governo Federal anunciou\n\nque não suspendeu\n\no IPI.", "", "block"),
    ("negative-qualifier", "Não procede a afirmação a seguir:\n\n" + F3, "", "block"),
    ("later-retraction", F3 + "\n\nRetratação: a informação acima foi desmentida.", "", "block"),
    ("retraction-plus-independent-fact", E3 + "\n\nA nota desmente a frase anterior.\n\n" + R, "R", "block"),
    ("third-party", "A afirmação abaixo é uma alegação de terceiros.\n\n" + F3, "", "block"),
    ("unmarked-third-party", "A narrativa a seguir foi apresentada por uma associação.\n\n" + E3, "", "block"),
    ("quoted-fragments", "“" + M3 + "” — declarou a associação.", "", "block"),
    ("independent-no-period", I[:-1] + "\n\n\n" + X[:-1] + "\n\n" + R, "IXR", "separate"),
    ("independent-full-stops", M + "\n\n" + F + "\n\n\n\n" + E, "MFE", "separate"),
    ("neutral-heading-and-separate-event", "O Copom decidiu\n\n## Resumo executivo\n" + M + "\n\n" + R, "MR", "separate"),
    ("draft-then-factual", "Minuta:\n" + E3 + "\n\n## Resultados oficiais\n" + R, "R", "block"),
    ("unresolved-condition", "Se a condição se cumprir:\n\n" + E4, "", "block"),
)


def run():
    source = OfficialSource(
        source_id="synthetic-a21", institution="Synthetic", country_code="BR",
        kind=OfficialSourceKind.COMMUNICATION, candidate_url="https://example.org/",
        capabilities={EventCategory.CONFIRMED_FACT},
    )
    extractor = OfficialEventExtractor(OfficialSourceCatalog((source,)))
    references = [
        (f"A18-{name}", text, expected, disposition)
        for name, text, expected, disposition in A18_CASES
        if name in {"fiscal-three-breaks", "measure-arbitrary-wrap"}
    ]
    assert len(references) == 2 and len(CASES) >= 40
    result = []
    for label, content, wanted, disposition in (*references, *CASES):
        doc = DocumentObservation(
            source_id=source.source_id, document_id=label, revision=1, title="Synthetic",
            content=content, published_at=PAST, received_at=NOW,
        )
        events = extractor.extract((doc,), as_of=NOW)
        actual = Counter(e.category.value for e in events)
        expected = Counter(CATEGORIES[c] for c in wanted)
        # Counterfactual only. The original document and extractor stay intact.
        flattened = re.sub(r"\r?\n(?:[ \t]*\r?\n)+", "\n", content)
        joined = replace(doc, content=flattened, content_sha256="")
        flat_actual = Counter(e.category.value for e in extractor.extract((joined,), as_of=NOW))
        result.append(dict(
            label=label, disposition=disposition, expected=expected, actual=actual,
            fp=actual - expected, fn=expected - actual,
            flattened=flat_actual, flattened_fp=flat_actual - expected,
            flattened_fn=expected - flat_actual,
            spans=[(e.content_start, e.content_end, e.description) for e in events],
            evidence_ok=all(
                0 <= e.content_start < e.content_end <= len(content)
                and content[e.content_start:e.content_end] == e.description
                and e.content_sha256 == doc.content_sha256
                and (e.source_id, e.document_id, e.revision) == doc.key
                and e.state is DocumentState.UNVERIFIED
                and (e.published_at, e.available_at) == (PAST, NOW)
                for e in events
            ),
            replay_ok=events == extractor.extract((doc, doc), as_of=NOW),
        ))
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    run()
