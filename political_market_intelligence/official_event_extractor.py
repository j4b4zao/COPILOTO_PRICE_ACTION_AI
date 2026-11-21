"""Extract unverified event observations from normalized local documents."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from hashlib import sha256
import json
import re

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
_FISCAL_AMOUNT = r"R\$\s*[0-9]+(?:[,.][0-9]+)? (?:milhões|bilhões)"
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
_LAYOUT_BREAK = r"\r?\n[ \t]*(?:\r?\n[ \t]*)?"
_WRAPPED_WORD = re.compile(rf"(?<=[^\W\d_])-{_LAYOUT_BREAK}(?=[^\W\d_])")
_WRAPPED_DECIMAL = re.compile(rf"(?<=[0-9][,.]){_LAYOUT_BREAK}(?=[0-9])")
_COMPOUND = re.compile(r"\s+e\s+|,\s+enquanto\s+", re.IGNORECASE)
_HISTORICAL_PREFIX = re.compile(r"^(?:Em retrospecto|Na série anterior),\s+", re.IGNORECASE)
_HISTORICAL_YEAR = re.compile(r" em ([0-9]{4})$", re.IGNORECASE)


def _statement_spans(content):
    """Keep context headings separate from the statements they qualify."""
    start = 0
    for line in re.finditer(r"[^\r\n]+", content):
        heading = line[0].strip().lstrip("#").lstrip()
        if (_FACTUAL_HEADING.fullmatch(heading) or _DOCUMENT_HEADING.fullmatch(heading)
                or _NONFACTUAL_CONTEXT.match(heading)
                or _THIRD_PARTY_INTRO.fullmatch(heading)
                or _BACKWARD_QUALIFIER.fullmatch(heading)):
            yield from _split_statements(content, start, line.start())
            yield line.span()
            start = line.end()
    yield from _split_statements(content, start, len(content))


def _split_statements(content, start, end):
    joined_until = start
    for boundary in _BOUNDARY.finditer(content, start, end):
        if boundary.start() < joined_until:
            continue
        if boundary.start() != boundary.end():
            joined_until = _continuation_end(content, start, boundary, end)
            if joined_until > boundary.start():
                continue
        yield start, boundary.start()
        start = boundary.end()
    yield start, end


def _continuation_end(content, start, boundary, end):
    """Return the end of a complete permitted statement, or the boundary."""
    split = boundary.start()
    lead = " ".join(content[start:split].split())
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
        middle_boundary = _BOUNDARY.search(content, next_start, end)
        if middle_boundary and middle_boundary.start() != middle_boundary.end():
            middle = content[next_start:middle_boundary.start()]
            tail_start = middle_boundary.end()
            following = _BOUNDARY.search(content, tail_start, end)
            tail_end = following.start() if following else end
            tail = content[tail_start:tail_end]
            if (not _EXTRA_LINE_BREAK.match(middle) and not _EXTRA_LINE_BREAK.match(tail)
                    and _MEASURE_MIDDLE.fullmatch(" ".join(middle.split()))
                    and _MEASURE_END.fullmatch(" ".join(tail.split()))):
                return tail_end
    if _INCOMPLETE_STATEMENTS.fullmatch(lead):
        next_start = boundary.end()
        following = _BOUNDARY.search(content, next_start, end)
        tail_end = following.start() if following else end
        if not _EXTRA_LINE_BREAK.match(content, next_start, end):
            reconstructed = _normalize_statement(content[start:tail_end])
            if any(rule.fullmatch(reconstructed) for _, rule in _RULES):
                return tail_end
    return split


def _normalize_statement(statement):
    text = _WRAPPED_DECIMAL.sub("", _WRAPPED_WORD.sub("", statement))
    return " ".join(text.split()).rstrip(".;!…")


def _category(statement, publication_year):
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
    return next((category for category, rule in _RULES if rule.fullmatch(text)), None)


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
            preceding_count = 0
            for start, end in _statement_spans(doc.content):
                raw = doc.content[start:end]
                statement = raw.strip()
                start += len(raw) - len(raw.lstrip())
                text = " ".join(statement.split())
                if not text:
                    continue
                if claim_end is not None and start >= claim_end:
                    third_party_claim = False
                    claim_end = None
                context = text.lstrip("#").lstrip()
                if _BACKWARD_QUALIFIER.fullmatch(context):
                    if preceding_count:
                        del events[-preceding_count:]
                    preceding_count = 0
                    continue
                preceding_count = 0
                if _FACTUAL_HEADING.fullmatch(context):
                    blocked = False
                    third_party_claim = False
                    claim_end = None
                    continue
                if _DOCUMENT_HEADING.fullmatch(context):
                    continue
                if _THIRD_PARTY_INTRO.fullmatch(context):
                    third_party_claim = True
                    claim_end = None
                    continue
                if _NONFACTUAL_CONTEXT.match(context):
                    blocked = True
                if blocked:
                    continue
                matches = _match_statement(statement, doc.published_at.year)
                if third_party_claim and matches:
                    if claim_end is None:
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
