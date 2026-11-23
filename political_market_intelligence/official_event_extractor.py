"""Extract unverified event observations from normalized local documents."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from hashlib import sha256
import json
import re
from unicodedata import normalize

from .official_document_normalizer import (
    DocumentObservation, DocumentState, OfficialDocumentNormalizer, _utc,
)
from .official_source_catalog import OfficialSourceCatalog


class OfficialEventCategory(str, Enum):
    ECONOMIC_INDICATOR = "ECONOMIC_INDICATOR"
    MONETARY_POLICY = "MONETARY_POLICY"
    FISCAL_COMMUNICATION = "FISCAL_COMMUNICATION"
    ECONOMIC_MEASURE = "ECONOMIC_MEASURE"
    FOREIGN_TRADE = "FOREIGN_TRADE"
    REGULATORY_CHANGE = "REGULATORY_CHANGE"


@dataclass(frozen=True, slots=True)
class ExtractedOfficialEvent:
    event_id: str
    source_id: str
    document_id: str
    revision: int
    category: OfficialEventCategory
    description: str
    published_at: datetime
    available_at: datetime
    content_sha256: str
    content_start: int
    content_end: int
    state: DocumentState


_PERCENT = r"[+-]?[0-9]+(?:[,.][0-9]+)?\s*%"
_INDICATOR = r"(?:o IPCA|o PIB|o IBC-Br|a taxa de desemprego)"
_FISCAL_VALUE = r"R\$\s*[0-9]+(?:[,.][0-9]+)?"
_FISCAL_UNIT = r"(?:milhões|bilhões)"
_FISCAL_AMOUNT = rf"{_FISCAL_VALUE} {_FISCAL_UNIT}"
_FISCAL_LEAD = r"O Tesouro Nacional (?:divulgou|publicou) (?:o resultado primário|o resultado fiscal) com"
_FISCAL_COMPLEMENT = rf"(?:déficit|superávit) de {_FISCAL_AMOUNT}"
_MEASURE_ACTION = r"(?:a redução|o aumento|a suspensão)"
_MEASURE_TAX = r"(?:IPI|IOF|imposto de renda)"
_RATE_DECISION = (
    rf"(?:manteve|elevou|reduziu|fixou|decidiu manter) "
    rf"a (?:taxa )?Selic (?:em|para) {_PERCENT}(?: ao ano)?"
)
_REGULATION_REFERENCE = r"(?:a )?(?:Resolução|Instrução) (?:CVM )?(?:n[º°]\s*)?[0-9]+(?:/[0-9]{4})?"
_RULES = tuple((category, re.compile(pattern, re.IGNORECASE)) for category, pattern in (
    (OfficialEventCategory.ECONOMIC_INDICATOR,
     rf"(?:O IBGE|O Banco Central) (?:divulgou {_INDICATOR} de|"
     rf"informou que {_INDICATOR} foi de) {_PERCENT}|"
     rf"O IBGE confirmou que não é falso que divulgou {_INDICATOR} de {_PERCENT}"),
    (OfficialEventCategory.MONETARY_POLICY,
     rf"(?:Não se pode negar que )?(?:o Copom|o Banco Central) {_RATE_DECISION}"),
    (OfficialEventCategory.FISCAL_COMMUNICATION,
     rf"(?:{_FISCAL_LEAD} {_FISCAL_COMPLEMENT}|"
     rf"O Tesouro Nacional informou (?:déficit|superávit) primário de {_FISCAL_AMOUNT})"
     rf"(?:: dado divulgado no boletim)?"),
    (OfficialEventCategory.ECONOMIC_MEASURE,
     rf"O Governo Federal anunciou (?:{_MEASURE_ACTION} do {_MEASURE_TAX}|"
     rf"que (?:reduziu|aumentou|suspendeu) o {_MEASURE_TAX})"),
    (OfficialEventCategory.FOREIGN_TRADE,
     r"(?:A Secex|O MDIC) (?:publicou|divulgou) (?:o boletim|os dados) da balança comercial"),
    (OfficialEventCategory.REGULATORY_CHANGE,
     rf"(?:A CVM|O Banco Central) (?:publicou|alterou|revogou|editou) {_REGULATION_REFERENCE}|"
     rf"Não é verdade que a CVM não tenha revogado {_REGULATION_REFERENCE}"),
))

_INCOMPLETE_STATEMENTS = re.compile(
    rf"(?:{_FISCAL_LEAD}|"
    r"O Tesouro Nacional (?:divulgou|publicou) (?:o resultado primário|o resultado fiscal)"
    rf"(?: com (?:déficit|superávit) de R\$\s*[0-9]+(?:[,.][0-9]+)?)?|"
    r"(?:O Copom|O Banco Central) (?:decidiu|"
    r"(?:manteve|elevou|reduziu|fixou|decidiu manter) a (?:taxa )?Selic "
    r"(?:em|para)(?: [+-]?[0-9]+[,.])?)|"
    rf"(?:O IBGE|O Banco Central) (?:divulgou {_INDICATOR} de(?: [+-]?[0-9]+[,.])?|"
    rf"informou que {_INDICATOR} foi)|"
    r"(?:A CVM|O Banco Central) (?:alte-|(?:publicou|alterou|revogou|editou)"
    r"(?: (?:a )?(?:Resolução|Instrução) (?:CVM )?n[º°])?)|"
    r"(?:A Secex|O MDIC) (?:publicou|divulgou) (?:o boletim|os dados) da)",
    re.IGNORECASE,
)

_NONFACTUAL_CONTEXT = re.compile(
    r"(?:hipóteses?|simulaç(?:ão|ões)|minutas?|cenários? (?:hipotéticos?|simulados?)|"
    r"projeç(?:ão|ões)|desmentidos?|negaç(?:ão|ões)|"
    r"afirmaç(?:ão|ões) (?:desmentid[ao]s?|negad[ao]s?)|"
    r"(?:o comunicado|a nota) (?:desmentiu|negou) (?:a seguinte|a) afirmação|"
    r"para fins (?:exclusivamente )?(?:ilustrativos|de simulação)|"
    r"suponha(?:-se)? (?:o|um) cenário|versão de trabalho|texto sob revisão|"
    r"estimativa (?:ainda não realizada|para o próximo)|"
    r"não procede a (?:alegação|afirmação) (?:a seguir|abaixo)|"
    r"caso (?:a|o) .{1,120}? seja concedid[ao]|"
    r"se (?:o cenário se confirmar|a condição se cumprir)|"
    r"exercício com dados (?:inventados|fictícios)|"
    r"premissa contrafactual|rascunho de circulação interna|"
    r"exemplo do anúncio projetado para amanhã|"
    r"a versão abaixo descreve uma decisão de amanhã, ainda pendente)\b",
    re.IGNORECASE,
)
_THIRD_PARTY_INTRO = re.compile(
    r"(?:(?:a informação|a afirmação) (?:abaixo|a seguir) é uma alegação "
    r"(?:da associação|de terceiros?)|"
    r"a associação (?:divulgou|apresentou) a seguinte alegação|"
    r"a narrativa a seguir foi apresentada por uma associação|"
    r"depoimento de terceiro \(trecho literal\))[:.]?",
    re.IGNORECASE,
)
_AUTHORITY_ATTRIBUTION = re.compile(
    r"Segundo (o Copom|o Banco Central|o IBGE|o Tesouro Nacional|o Governo Federal|"
    r"a Secex|o MDIC|a CVM), (.+)", re.IGNORECASE,
)
_BACKWARD_QUALIFIER = re.compile(
    r"(?:(?:correção|errata|retratação)\s*:\s*"
    r"(?:o dado|a informação|a publicação) (?:referid[ao] )?acima "
    r"(?:nunca foi divulgad[ao]|não ocorreu|não foi divulgad[ao]|foi desmentid[ao])|"
    r"(?:a nota|o comunicado) desmente (?:integralmente )?a (?:frase|afirmação) anterior|"
    r"a frase anterior descreve uma decisão prevista para (?:amanhã|o futuro)|"
    r"(?:o Tesouro|a fonte|o órgão) nega que essa divulgação tenha ocorrido)[.!]?",
    re.IGNORECASE,
)
_REFERENCE_CORRECTION = re.compile(
    r"retificação\s*:\s*onde se lê ([0-9]+/[0-9]{4}), leia-se ([0-9]+/[0-9]{4})[.!]?",
    re.IGNORECASE,
)
_OTHER_ACT_YEAR = re.compile(
    r"nota de paginação\s*:\s*([0-9]{4}) é o ano da resolução nº ([0-9]+)"
    r"(?:, listad[ao] na tabela seguinte)?[.!]?",
    re.IGNORECASE,
)
_ACT_NUMBER_YEAR = re.compile(r"(?<![0-9])([0-9]+)/\s*([0-9]{4})(?![0-9])")
_CONDITION_HEADING = re.compile(r"se a diretoria aprovar a proposta\s*:", re.IGNORECASE)
_SIMULATION_HEADING = re.compile(r"fórmula de simulação para teste interno\s*:", re.IGNORECASE)
_FACTUAL_HEADING = re.compile(
    r"(?:fatos (?:confirmados|documentados)|resultados (?:realizados|oficiais|efetivos)|"
    r"(?:seção|contexto) factual|decisões (?:tomadas|oficiais)|deliberação registrada)\s*:?",
    re.IGNORECASE,
)
_DOCUMENT_HEADING = re.compile(
    r"(?:[0-9]+\.\s+)?(?:resumo executivo|boletim de resultados|notas da reunião)\s*:?",
    re.IGNORECASE,
)
_PARAGRAPH_BREAK = r"\r?\n[ \t]*\r?\n"
_BOUNDARY = re.compile(rf"(?<=[.!?;])(?=\s)|{_PARAGRAPH_BREAK}")
_PARAGRAPH_BOUNDARY = re.compile(_PARAGRAPH_BREAK)
_EXTRA_LINE_BREAK = re.compile(r"[ \t]*\r?\n")
_FISCAL_AMOUNT_LEAD = re.compile(rf"{_FISCAL_LEAD}(?: (?:déficit|superávit) de)?", re.IGNORECASE)
_FISCAL_COMPLETE = re.compile(rf"{_FISCAL_LEAD} {_FISCAL_COMPLEMENT}[.!]?", re.IGNORECASE)
_MEASURE_MIDDLE = re.compile(rf"anunciou {_MEASURE_ACTION}", re.IGNORECASE)
_MEASURE_END = re.compile(rf"do {_MEASURE_TAX}[.!]?", re.IGNORECASE)
_FISCAL_REPORT_LEAD = re.compile(
    r"O Tesouro Nacional (?:divulgou|publicou) (?:o resultado primário|o resultado fiscal)",
    re.IGNORECASE,
)
_FISCAL_VALUE_MIDDLE = re.compile(rf"com (?:déficit|superávit) de {_FISCAL_VALUE}", re.IGNORECASE)
_FISCAL_UNIT_END = re.compile(rf"{_FISCAL_UNIT}[.!]?", re.IGNORECASE)
_MEASURE_ACTION_MIDDLE = re.compile(_MEASURE_ACTION, re.IGNORECASE)
_TRADE_DATA_MIDDLE = re.compile(r"os dados da balança", re.IGNORECASE)
_TRADE_DATA_END = re.compile(r"comercial[.!]?")
_CVM_INSTRUCTION_MIDDLE = re.compile(r"a Instrução n[º°]", re.IGNORECASE)
_CVM_INSTRUCTION_END = re.compile(r"[0-9]+/[0-9]{4}[.!]?")
_EXPLICIT_COMPLEMENT_QUALIFIER = re.compile(
    r"(?:se houver (?:aprovação|autorização)|"
    r"é falso que o fato (?:abaixo|a seguir) tenha ocorrido|"
    r"o fato (?:abaixo|a seguir) é hipotético|"
    r"(?:informação desmentida|retratação|alegação de terceiros)"
    r" (?:sobre o fato )?(?:abaixo|a seguir))[:.!]?",
    re.IGNORECASE,
)
_QUALIFIER_TERMINAL = re.compile(r" *(\.\.\.|…|[:.!])$")
_FRAGMENT_GAP = rf"{_PARAGRAPH_BREAK}[ \t]*"
_FRAGMENTED_SUBJECT_TAILS = {
    "o tesouro nacional": re.compile(
        rf"[ \t]*divulgou o resultado primário{_FRAGMENT_GAP}"
        rf"com superávit de R\$ [0-9]+{_FRAGMENT_GAP}milhões[.!]?",
        re.IGNORECASE,
    ),
    "o governo": re.compile(
        rf"[ \t]*Federal anunciou{_FRAGMENT_GAP}a suspensão{_FRAGMENT_GAP}do IPI[.!]?",
        re.IGNORECASE,
    ),
    "o copom": re.compile(
        rf"[ \t]*reduziu a taxa Selic para{_FRAGMENT_GAP}[0-9]+,[0-9]+% ao ano[.!]?",
        re.IGNORECASE,
    ),
    "o ibge": re.compile(
        rf"[ \t]*divulgou o IBC-Br de{_FRAGMENT_GAP}[0-9]+,[0-9]+%[.!]?",
        re.IGNORECASE,
    ),
}
_EXTENDED_GAP_TAILS = {
    "o copom reduziu a taxa selic para": re.compile(
        r"(?:\n[ \t]*\n[ \t]*\n[ \t]*\n|\r\n[ \t]*\r\n[ \t]*\r\n[ \t]*\r\n)"
        r"[ \t]*[0-9]+,[0-9]+% ao ano[.!]?",
        re.IGNORECASE,
    ),
    "o ibge divulgou o ibc-br de": re.compile(
        r"\r\n(?:[ \t]+\r\n[ \t]*|\r\n[ \t]+)\r\n"
        r"[ \t]*[0-9]+,[0-9]+%[.!]?",
    ),
}
_FRAGMENTED_NUMERIC_STATEMENTS = (
    re.compile(
        rf"O Copom{_FRAGMENT_GAP}reduziu a taxa Selic para{_FRAGMENT_GAP}"
        rf"[0-9]+,(?P<number_gap>{_FRAGMENT_GAP})[0-9]+% ao ano[.!]?",
        re.IGNORECASE,
    ),
    re.compile(
        r"O IBGE divulgou o IBC-Br de [0-9]+,"
        r"(?P<number_gap>\r?\n[ \t]*\r?\n[ \t]*\r?\n[ \t]*)[0-9]+%[.!]?",
        re.IGNORECASE,
    ),
)
_FRAGMENTED_INSTRUCTION_LEAD = re.compile(
    rf"A CVM editou {_CVM_INSTRUCTION_MIDDLE.pattern}", re.IGNORECASE,
)
_FRAGMENTED_INSTRUCTION_TAIL = re.compile(
    rf"{_FRAGMENT_GAP}[0-9]+/{_FRAGMENT_GAP}[0-9]{{4}}[.!]?",
)
_FRAGMENTED_INSTRUCTION = re.compile(
    _FRAGMENTED_INSTRUCTION_LEAD.pattern + _FRAGMENTED_INSTRUCTION_TAIL.pattern, re.IGNORECASE,
)
_LAYOUT_BREAK = r"\r?\n[ \t]*(?:\r?\n[ \t]*)?"
_FRAGMENTED_RESOLUTION_LEAD = re.compile(r"A CVM publicou a Resolução CVM n[º°]", re.IGNORECASE)
_FRAGMENTED_RESOLUTION_TAIL = re.compile(
    rf"{_FRAGMENT_GAP}[0-9]+/(?:[ \t]*{_LAYOUT_BREAK})?[0-9]{{4}}[.!]?",
)
_FRAGMENTED_RESOLUTION = re.compile(
    _FRAGMENTED_RESOLUTION_LEAD.pattern + _FRAGMENTED_RESOLUTION_TAIL.pattern, re.IGNORECASE,
)
_WRAPPED_WORD = re.compile(rf"(?<=[^\W\d_])-{_LAYOUT_BREAK}(?=[^\W\d_])")
_WRAPPED_DECIMAL = re.compile(rf"(?<=[0-9][,.]){_LAYOUT_BREAK}(?=[0-9])")
_COMPOUND = re.compile(r"\s+e\s+|,\s+enquanto\s+", re.IGNORECASE)
_HISTORICAL_PREFIX = re.compile(r"^(?:Em retrospecto|Na série anterior),[ \t]+", re.IGNORECASE)
_HISTORICAL_YEAR = re.compile(r" em ([0-9]{4})$", re.IGNORECASE)


def _statement_spans(content):
    """Keep context headings separate from the statements they qualify."""
    start = 0
    for line in re.finditer(r"[^\r\n]+", content):
        heading = line[0].strip().lstrip("#").lstrip()
        qualifier = normalize("NFC", " ".join(heading.split()))
        if (_FACTUAL_HEADING.fullmatch(qualifier) or _DOCUMENT_HEADING.fullmatch(heading)
                or _NONFACTUAL_CONTEXT.match(qualifier)
                or _THIRD_PARTY_INTRO.fullmatch(qualifier)
                or _BACKWARD_QUALIFIER.fullmatch(qualifier)
                or _REFERENCE_CORRECTION.fullmatch(qualifier)
                or _OTHER_ACT_YEAR.fullmatch(qualifier)
                or _CONDITION_HEADING.fullmatch(qualifier)
                or _SIMULATION_HEADING.fullmatch(qualifier)):
            yield from _split_statements(content, start, line.start())
            yield line.span()
            start = line.end()
    yield from _split_statements(content, start, len(content))


def _split_statements(content, start, end):
    joined_until = start
    previous = ""
    for boundary in _BOUNDARY.finditer(content, start, end):
        if boundary.start() < joined_until:
            continue
        if boundary.start() != boundary.end():
            joined_until = _continuation_end(content, start, boundary, end, previous)
            if joined_until > boundary.start():
                continue
        yield start, boundary.start()
        statement = content[start:boundary.start()]
        if statement.strip():
            previous = statement
        start = boundary.end()
    yield start, end


def _continuation_end(content, start, boundary, end, previous):
    """Return the end of a complete permitted statement, or the boundary."""
    split = boundary.start()
    raw_lead = content[start:split]
    lead = " ".join(raw_lead.split())
    next_start = boundary.end()
    if _FISCAL_AMOUNT_LEAD.fullmatch(lead):
        extra_break = _EXTRA_LINE_BREAK.match(content, next_start, end)
        if extra_break:
            next_start = extra_break.end()
        following = _BOUNDARY.search(content, next_start, end)
        tail_end = following.start() if following else end
        tail = content[next_start:tail_end]
        if not _EXTRA_LINE_BREAK.match(tail) and _FISCAL_COMPLETE.fullmatch(
            " ".join(content[start:tail_end].split())
        ):
            return tail_end
    elif lead.casefold() == "o governo federal":
        return _three_fragment_end(content, boundary, end, _MEASURE_MIDDLE, _MEASURE_END)
    elif lead.casefold() == "o governo federal anunciou":
        return _three_fragment_end(content, boundary, end, _MEASURE_ACTION_MIDDLE, _MEASURE_END)
    elif lead.casefold() == "a secex divulgou":
        return _explicit_complement_end(
            content, boundary, end, previous, _TRADE_DATA_MIDDLE, _TRADE_DATA_END,
        )
    elif lead.casefold() == "a cvm editou":
        regulation_end = _explicit_complement_end(
            content, boundary, end, previous, _CVM_INSTRUCTION_MIDDLE, _CVM_INSTRUCTION_END,
        )
        if regulation_end > split:
            return regulation_end
    elif _FISCAL_REPORT_LEAD.fullmatch(lead):
        fiscal_end = _three_fragment_end(content, boundary, end, _FISCAL_VALUE_MIDDLE, _FISCAL_UNIT_END)
        if fiscal_end > split:
            return fiscal_end
    if _INCOMPLETE_STATEMENTS.fullmatch(lead):
        next_start = boundary.end()
        following = _BOUNDARY.search(content, next_start, end)
        tail_end = following.start() if following else end
        if not _EXTRA_LINE_BREAK.match(content, next_start, end):
            reconstructed = _normalize_statement(content[start:tail_end])
            if any(rule.fullmatch(reconstructed) for _, rule in _RULES):
                return tail_end
    tail_rule = _FRAGMENTED_SUBJECT_TAILS.get(lead.casefold())
    if tail_rule is not None and not _qualifies_following_complement(previous):
        tail = tail_rule.match(content, boundary.end(), end)
        if tail and (tail.end() == end or _BOUNDARY.match(content, tail.end(), end)):
            return tail.end()
    gap_rule = _EXTENDED_GAP_TAILS.get(lead.casefold())
    if gap_rule is not None and not _qualifies_following_complement(previous):
        tail = gap_rule.match(content, split, end)
        if tail and (tail.end() == end or _BOUNDARY.match(content, tail.end(), end)):
            return tail.end()
    statement_start = split - len(raw_lead.lstrip())
    for rule in _FRAGMENTED_NUMERIC_STATEMENTS:
        match = rule.match(content, statement_start, end)
        if (match and (match.end() == end or _BOUNDARY.match(content, match.end(), end))
                and not _qualifies_following_complement(previous)):
            return match.end()
    # Compare the lead canonically, but match the tail on the original document.
    canonical_lead = normalize("NFC", raw_lead.lstrip())
    for candidate, lead_rule, tail_rule in (
        (canonical_lead, _FRAGMENTED_INSTRUCTION_LEAD, _FRAGMENTED_INSTRUCTION_TAIL),
        (_HISTORICAL_PREFIX.sub("", canonical_lead), _FRAGMENTED_RESOLUTION_LEAD, _FRAGMENTED_RESOLUTION_TAIL),
    ):
        if not lead_rule.fullmatch(candidate):
            continue
        tail = tail_rule.match(content, split, end)
        if (tail and (tail.end() == end or _BOUNDARY.match(content, tail.end(), end))
                and not _qualifies_following_complement(previous)):
            return tail.end()
    return split


def _explicit_complement_end(content, boundary, end, previous, middle_rule, tail_rule):
    if _qualifies_following_complement(previous):
        return boundary.start()
    return _three_fragment_end(content, boundary, end, middle_rule, tail_rule)


def _qualifies_following_complement(previous):
    context = normalize("NFC", " ".join(previous.split()).lstrip("#").lstrip())
    context = _QUALIFIER_TERMINAL.sub(
        lambda match: "." if match[1] in {"...", "…"} else match[1], context,
    )
    return _EXPLICIT_COMPLEMENT_QUALIFIER.fullmatch(context) is not None


def _regulatory_reference(event):
    if event.category is OfficialEventCategory.REGULATORY_CHANGE:
        match = _ACT_NUMBER_YEAR.search(event.description)
        if match:
            return "/".join(match.groups())
    return None


def _has_conflicting_pagination_year(event, note_year, note_number):
    reference = _regulatory_reference(event)
    if not reference or not reference.endswith("/" + note_year):
        return False
    literal = event.description
    canonical = normalize("NFC", literal)
    if (re.search(r"/[ \t]*" + _PARAGRAPH_BREAK, literal)
            and re.match(r"A CVM editou\s+a Instrução", canonical, re.IGNORECASE)):
        return True
    return (
        _FRAGMENTED_RESOLUTION.fullmatch(_HISTORICAL_PREFIX.sub("", canonical)) is not None
        and re.search(r"/[ \t]*\r?\n", literal) is not None
        and reference.split("/")[0].lstrip("0") != note_number.lstrip("0")
    )


def _three_fragment_end(content, boundary, end, middle_rule, tail_rule):
    middle_boundary = _BOUNDARY.search(content, boundary.end(), end)
    if not middle_boundary or middle_boundary.start() == middle_boundary.end():
        return boundary.start()
    middle = content[boundary.end():middle_boundary.start()]
    following = _BOUNDARY.search(content, middle_boundary.end(), end)
    tail_end = following.start() if following else end
    tail = content[middle_boundary.end():tail_end]
    if (not _EXTRA_LINE_BREAK.match(middle) and not _EXTRA_LINE_BREAK.match(tail)
            and middle_rule.fullmatch(" ".join(middle.split()))
            and tail_rule.fullmatch(" ".join(tail.split()))):
        return tail_end
    return boundary.start()


def _normalize_statement(statement):
    text = _WRAPPED_DECIMAL.sub("", _WRAPPED_WORD.sub("", statement))
    return " ".join(text.split()).rstrip(".;!…")


def _category(statement, publication_year):
    canonical = normalize("NFC", statement)
    if (_FRAGMENTED_INSTRUCTION.fullmatch(canonical)
            or _FRAGMENTED_RESOLUTION.fullmatch(_HISTORICAL_PREFIX.sub("", canonical))):
        return OfficialEventCategory.REGULATORY_CHANGE
    for rule in _FRAGMENTED_NUMERIC_STATEMENTS:
        match = rule.fullmatch(statement)
        if match:
            left, right = match.span("number_gap")
            statement = statement[:left] + statement[right:]
            break
    text = _normalize_statement(statement)
    text = _HISTORICAL_PREFIX.sub("", text.removeprefix("• "))
    attribution = _AUTHORITY_ATTRIBUTION.fullmatch(text)
    if attribution:
        authority, claim = attribution.groups()
        if claim.startswith("“") and claim.endswith("”"):
            claim = claim[1:-1].rstrip(".")
        if not claim.casefold().startswith(authority.casefold() + " "):
            return None
        text = claim
    year = _HISTORICAL_YEAR.search(text)
    if year:
        if int(year[1]) >= publication_year:
            return None
        text = text[:year.start()]
    for category, rule in _RULES:
        candidate = normalize("NFC", text) if category is OfficialEventCategory.REGULATORY_CHANGE else text
        if rule.fullmatch(candidate):
            return category
    return None


def _match_statement(statement, publication_year):
    """Match a full statement or a compound with independently explicit clauses."""
    category = _category(statement, publication_year)
    if category is not None:
        return ((category, 0, len(statement)),)
    if _AUTHORITY_ATTRIBUTION.match(" ".join(statement.split())):
        return ()

    matches = []
    for start, end in _clause_spans(statement):
        category = _category(statement[start:end], publication_year)
        if category is None:
            return ()
        matches.append((category, start, end))
    return matches


def _clause_spans(statement):
    start = 0
    for connector in _COMPOUND.finditer(statement):
        yield start, connector.start()
        start = connector.end()
    yield start, len(statement)


class OfficialEventExtractor:
    """Stateless extraction over A4 documents or an A5 snapshot.

    Each eligible revision contributes its own observations. Exact duplicates
    collapse within a batch. Retain input history to detect conflicts on replay.
    Rules recognize complete statements in factual sections of the body.
    Evidence offsets are half-open character indices into the original content.
    """

    def __init__(self, catalog: OfficialSourceCatalog) -> None:
        self._normalizer = OfficialDocumentNormalizer(catalog)

    def extract(
        self, documents: tuple[DocumentObservation, ...] | list[DocumentObservation],
        *, as_of: datetime,
    ) -> tuple[ExtractedOfficialEvent, ...]:
        cutoff = _utc(as_of, "as_of")
        if type(documents) not in (tuple, list):
            raise TypeError("documents require a tuple or list")
        by_key = {}
        for doc in documents:
            if type(doc) is not DocumentObservation:
                raise TypeError("expected a normalized DocumentObservation")
            if doc.state is not DocumentState.UNVERIFIED:
                raise ValueError("invalid document provenance: state must be DocumentState.UNVERIFIED")
            payload = {field: getattr(doc, field) for field in self._normalizer.REQUIRED}
            normalized = self._normalizer.normalize(payload, as_of=cutoff)
            if doc != normalized or not doc.content_sha256:
                raise ValueError("document provenance does not match normalization")
            if by_key.setdefault(doc.key, normalized) != normalized:
                raise ValueError(f"conflicting document identity: {doc.key}")

        events = []
        previous = None
        for doc in sorted(by_key.values(), key=lambda item: item.key):
            if (previous is not None and previous.key[:2] == doc.key[:2]
                    and previous.received_at > doc.received_at):
                raise ValueError("higher revision received before lower revision")
            previous = doc
            blocked = False
            third_party_claim = False
            claim_end = None
            regulatory_claim = False
            condition_pending = False
            document_start = len(events)
            preceding_count = 0
            for start, end in _statement_spans(doc.content):
                raw = doc.content[start:end]
                statement = raw.strip()
                start += len(raw) - len(raw.lstrip())
                text = " ".join(statement.split())
                if not text:
                    continue
                if claim_end is not None and start >= claim_end and not regulatory_claim:
                    third_party_claim = False
                    claim_end = None
                context = text.lstrip("#").lstrip()
                correction_context = normalize("NFC", context)
                correction = _REFERENCE_CORRECTION.fullmatch(correction_context)
                if correction:
                    if correction[1] != correction[2] and not (blocked or third_party_claim or condition_pending):
                        candidates = [
                            index for index in range(document_start, len(events))
                            if _regulatory_reference(events[index]) == correction[1]
                        ]
                        if len(candidates) == 1:
                            del events[candidates[0]]
                    preceding_count = 0
                    continue
                other_year = _OTHER_ACT_YEAR.fullmatch(correction_context)
                if other_year and preceding_count == 1 and not (blocked or third_party_claim or condition_pending):
                    if _has_conflicting_pagination_year(events[-1], *other_year.groups()):
                        events.pop()
                    preceding_count = 0
                    continue
                if _BACKWARD_QUALIFIER.fullmatch(correction_context):
                    if preceding_count:
                        del events[-preceding_count:]
                    preceding_count = 0
                    continue
                preceding_count = 0
                if _FACTUAL_HEADING.fullmatch(correction_context):
                    blocked = False
                    third_party_claim = False
                    claim_end = None
                    regulatory_claim = False
                    condition_pending = False
                    continue
                if _DOCUMENT_HEADING.fullmatch(context):
                    continue
                if _THIRD_PARTY_INTRO.fullmatch(correction_context):
                    third_party_claim = True
                    claim_end = None
                    regulatory_claim = False
                    continue
                if _CONDITION_HEADING.fullmatch(correction_context):
                    condition_pending = True
                    continue
                if _NONFACTUAL_CONTEXT.match(correction_context) or _SIMULATION_HEADING.fullmatch(correction_context):
                    blocked = True
                if blocked:
                    continue
                matches = _match_statement(statement, doc.published_at.year)
                if condition_pending and matches:
                    condition_pending = False
                    continue
                if third_party_claim and matches:
                    regulatory = all(category is OfficialEventCategory.REGULATORY_CHANGE
                                     for category, _, _ in matches)
                    if regulatory_claim and claim_end is not None and start >= claim_end and not regulatory:
                        third_party_claim = False
                        regulatory_claim = False
                        claim_end = None
                    else:
                        regulatory_claim = regulatory_claim or regulatory
                        if claim_end is None or regulatory_claim:
                            boundary = _PARAGRAPH_BOUNDARY.search(doc.content, start + len(statement))
                            claim_end = boundary.end() if boundary else len(doc.content)
                        continue
                for category, left, right in matches:
                    evidence_start, evidence_end = start + left, start + right
                    identity = json.dumps((*doc.key, doc.content_sha256, evidence_start,
                                           evidence_end, category.value))
                    events.append(ExtractedOfficialEvent(
                        event_id=sha256(identity.encode("utf-8")).hexdigest(),
                        source_id=doc.source_id, document_id=doc.document_id,
                        revision=doc.revision, category=category, description=statement[left:right],
                        published_at=doc.published_at, available_at=doc.received_at,
                        content_sha256=doc.content_sha256,
                        content_start=evidence_start, content_end=evidence_end, state=doc.state,
                    ))
                    preceding_count += 1
        return tuple(events)
