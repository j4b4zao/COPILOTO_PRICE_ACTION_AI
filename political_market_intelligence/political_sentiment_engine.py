"""Versioned, deterministic economic interpretation of offline transcripts."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re
import unicodedata

from .event_model import EventCategory, EventRecord, EvidenceReference, _utc
from .speech_monitor import SpeechFixture, SpeechMonitor


class EconomicTopic(str, Enum):
    FISCAL_POLICY = "FISCAL_POLICY"
    PUBLIC_SPENDING = "PUBLIC_SPENDING"
    PUBLIC_DEBT = "PUBLIC_DEBT"
    INFLATION = "INFLATION"
    INTEREST_RATES = "INTEREST_RATES"
    EXCHANGE_RATE = "EXCHANGE_RATE"
    TRADE_POLICY = "TRADE_POLICY"
    STATE_INTERVENTION = "STATE_INTERVENTION"
    POLITICAL_UNCERTAINTY = "POLITICAL_UNCERTAINTY"


class EconomicTone(str, Enum):
    RISK_ON = "RISK_ON"
    RISK_OFF = "RISK_OFF"
    MIXED = "MIXED"
    NEUTRAL = "NEUTRAL"
    UNCERTAIN = "UNCERTAIN"


class MarketAsset(str, Enum):
    WIN = "WIN"
    WDO = "WDO"


class ImpactDirection(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    NEUTRAL = "NEUTRAL"
    UNCERTAIN = "UNCERTAIN"


RULES_VERSION = "PMI-ECON-PT-RC1.1"
_TOPIC_TERMS = {
    EconomicTopic.FISCAL_POLICY: r"fiscal|orcamento|superavit primario|deficit primario",
    EconomicTopic.PUBLIC_SPENDING: r"(?:gastos?|despesas?) public[oa]s?|controle de gastos",
    EconomicTopic.PUBLIC_DEBT: r"divida(?: publica)?|endividamento publico",
    EconomicTopic.INFLATION: r"inflacao|ipca",
    EconomicTopic.INTEREST_RATES: r"juros|selic|politica monetaria",
    EconomicTopic.EXCHANGE_RATE: r"cambio|cambial|dolar|taxa de cambio",
    EconomicTopic.TRADE_POLICY: r"tarifas? (?:comerciais|de importacao)|comercio exterior|exportacoes|importacoes",
    EconomicTopic.STATE_INTERVENTION: r"intervencao (?:estatal|do estado)|controle de precos|estatizacao",
    EconomicTopic.POLITICAL_UNCERTAINTY: r"incerteza politica|crise politica|instabilidade politica",
}
_POSITIVE = (
    r"responsabilidade fiscal|consolidacao fiscal|melhora fiscal|controle de gastos|"
    r"reducao da divida|queda da inflacao|inflacao em queda|estabilidade politica"
)
_NEGATIVE = (
    r"deterioracao fiscal|descontrole fiscal|aumento da divida|alta da inflacao|"
    r"inflacao em alta|crise politica|instabilidade politica"
)
_AMBIGUOUS = (
    r"nao|talvez|depende|pode|podem|poderia|possivel|incert[ao]s?|incerteza(?: politica)?|"
    r"se|mas|porem|contudo|avaliamos|consideramos"
)
_ASSET_CLAIM = re.compile(r"\b(alta|queda)\s+(?:para|do|de)\s+(win|wdo)\b")


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.casefold())
    unaccented = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(unaccented.split())


def _has(pattern: str, text: str) -> bool:
    return re.search(r"\b(?:" + pattern + r")\b", text) is not None


def _classify(text: str) -> tuple[tuple[EconomicTopic, ...], EconomicTone, float, tuple[str, ...]]:
    topics = set()
    excerpts = []
    positive = negative = ambiguous = False
    for match in re.finditer(r"[^.!?;\n]+[.!?;]?", text):
        excerpt = match.group().strip()
        normalized = _normalize(excerpt)
        clause_topics = {topic for topic, terms in _TOPIC_TERMS.items() if _has(terms, normalized)}
        topics.update(clause_topics)
        favorable = _has(_POSITIVE, normalized)
        unfavorable = _has(_NEGATIVE, normalized)
        hedge = excerpt.endswith("?") or _has(_AMBIGUOUS, normalized)
        positive |= favorable
        negative |= unfavorable
        ambiguous |= hedge
        if clause_topics or favorable or unfavorable or hedge or _ASSET_CLAIM.search(normalized):
            excerpts.append(excerpt)

    if not topics:
        tone, confidence = EconomicTone.NEUTRAL, 0.0
    elif positive and negative:
        tone, confidence = EconomicTone.MIXED, 0.5
    elif ambiguous:
        tone, confidence = EconomicTone.UNCERTAIN, 0.25
    elif positive:
        tone, confidence = EconomicTone.RISK_ON, 0.75
    elif negative:
        tone, confidence = EconomicTone.RISK_OFF, 0.75
    else:
        tone, confidence = EconomicTone.NEUTRAL, 0.5

    return tuple(topic for topic in EconomicTopic if topic in topics), tone, confidence, tuple(excerpts)


@dataclass(frozen=True, slots=True, kw_only=True)
class EconomicInterpretation:
    """Evidence-backed interpretation; confidence describes rules, never probabilities."""

    transcript: EventRecord
    available_at: datetime
    supporting_excerpts: tuple[str, ...] | None = None
    topics: tuple[EconomicTopic, ...] = field(init=False)
    economic_tone: EconomicTone = field(init=False)
    confidence: float = field(init=False)
    evidence_refs: tuple[EvidenceReference, ...] = field(init=False)
    rules_version: str = field(init=False, default=RULES_VERSION)
    category: EventCategory = field(init=False, default=EventCategory.AI_INTERPRETATION)

    def __post_init__(self) -> None:
        transcript = self.transcript
        if (
            type(transcript) is not EventRecord
            or transcript.category is not EventCategory.VERIFIED_TRANSCRIPT
            or not transcript.evidence
        ):
            raise ValueError("interpretation requires a verified transcript with evidence")
        available = _utc(self.available_at, "available_at")
        if not transcript.is_available_at(available):
            raise ValueError("interpretation cannot precede its transcript evidence")
        topics, tone, confidence, excerpts = _classify(transcript.content)
        if self.supporting_excerpts is not None and self.supporting_excerpts != excerpts:
            raise ValueError("supporting_excerpts must exactly match the rule evidence")
        reference = EvidenceReference(*transcript.key, transcript.available_at)
        object.__setattr__(self, "available_at", available)
        object.__setattr__(self, "supporting_excerpts", excerpts)
        object.__setattr__(self, "topics", topics)
        object.__setattr__(self, "economic_tone", tone)
        object.__setattr__(self, "confidence", confidence)
        object.__setattr__(self, "evidence_refs", (reference, *transcript.evidence))

    @property
    def event_id(self) -> str:
        return self.transcript.event_id

    @property
    def source_id(self) -> str:
        return self.transcript.source_id

    @property
    def transcript_revision(self) -> int:
        return self.transcript.revision

    def is_available_at(self, as_of: datetime) -> bool:
        return _utc(as_of, "as_of") >= self.available_at


@dataclass(frozen=True, slots=True, kw_only=True)
class ImpactHypothesis:
    interpretation: EconomicInterpretation
    asset: MarketAsset
    available_at: datetime
    direction: ImpactDirection = field(init=False)
    supporting_excerpts: tuple[str, ...] = field(init=False)
    category: EventCategory = field(init=False, default=EventCategory.IMPACT_HYPOTHESIS)
    observational_only: bool = field(init=False, default=True)
    order_execution_allowed: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        if type(self.interpretation) is not EconomicInterpretation:
            raise ValueError("hypothesis requires an economic interpretation")
        if not isinstance(self.asset, MarketAsset):
            raise ValueError("asset requires WIN or WDO")
        available = _utc(self.available_at, "available_at")
        if not self.interpretation.is_available_at(available):
            raise ValueError("hypothesis cannot precede its interpretation")
        claims = {}
        for excerpt in self.interpretation.supporting_excerpts:
            for match in _ASSET_CLAIM.finditer(_normalize(excerpt)):
                if match[2] == self.asset.value.lower():
                    direction = ImpactDirection.UP if match[1] == "alta" else ImpactDirection.DOWN
                    claims.setdefault(direction, []).append(excerpt)

        tone = self.interpretation.economic_tone
        if not self.interpretation.topics:
            direction = ImpactDirection.NEUTRAL
        elif tone in (EconomicTone.MIXED, EconomicTone.UNCERTAIN) or len(claims) > 1:
            direction = ImpactDirection.UNCERTAIN
        elif claims:
            direction = next(iter(claims))
        elif tone is EconomicTone.NEUTRAL:
            direction = ImpactDirection.NEUTRAL
        else:
            direction = ImpactDirection.UNCERTAIN
        object.__setattr__(self, "available_at", available)
        object.__setattr__(self, "direction", direction)
        object.__setattr__(self, "supporting_excerpts", tuple(dict.fromkeys(
            excerpt for excerpts in claims.values() for excerpt in excerpts
        )))

    def is_available_at(self, as_of: datetime) -> bool:
        return _utc(as_of, "as_of") >= self.available_at


class PoliticalSentimentEngine:
    """Interpret only the non-conflicting A3 transcript revisions at the replay cutoff."""

    def __init__(self, speech_monitor: SpeechMonitor) -> None:
        self._speech_monitor = speech_monitor

    def interpret(
        self, fixtures: tuple[SpeechFixture, ...], *, as_of: datetime,
    ) -> tuple[EconomicInterpretation, ...]:
        as_of = _utc(as_of, "as_of")
        snapshot = self._speech_monitor.collect(fixtures, as_of=as_of)
        return tuple(
            EconomicInterpretation(transcript=record, available_at=as_of)
            for record in snapshot.verified_records
        )

    def hypothesize(
        self, interpretation: EconomicInterpretation, *,
        fixtures: tuple[SpeechFixture, ...], as_of: datetime,
    ) -> tuple[ImpactHypothesis, ImpactHypothesis]:
        as_of = _utc(as_of, "as_of")
        if type(interpretation) is not EconomicInterpretation:
            raise ValueError("hypothesis requires an economic interpretation")
        if not interpretation.is_available_at(as_of):
            raise ValueError("hypothesis cannot precede its interpretation")
        snapshot = self._speech_monitor.collect(fixtures, as_of=as_of)
        if interpretation.transcript not in snapshot.verified_records:
            raise ValueError("hypothesis requires a current verified transcript without conflicts")
        return (
            ImpactHypothesis(interpretation=interpretation, asset=MarketAsset.WIN, available_at=as_of),
            ImpactHypothesis(interpretation=interpretation, asset=MarketAsset.WDO, available_at=as_of),
        )

