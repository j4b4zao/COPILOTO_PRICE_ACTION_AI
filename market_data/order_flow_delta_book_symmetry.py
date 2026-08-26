"""RC37 - auditoria observacional da simetria Delta x Book.

Analisa sessoes shadow pos-RC35 sem alterar thresholds ou permitir influencia
operacional. O objetivo e explicar ausencia de BEARISH_ALIGNED distinguindo
falta de coocorrencia real de possivel assimetria dos sinais.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict

EXPECTED_DIRECTION_VERSION = "RC35_SIGNED_DELTA"

@dataclass(slots=True, frozen=True)
class DeltaBookSymmetryReport:
    sessions: int
    samples: int
    delta_positive_strong: int
    delta_negative_strong: int
    book_positive_strong: int
    book_negative_strong: int
    bullish_candidates: int
    bearish_candidates: int
    divergent_pos_delta_neg_book: int
    divergent_neg_delta_pos_book: int
    strong_delta_book_neutral: int
    status: str
    reasons: tuple[str, ...]
    observational_only: bool = True
    score_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    order_execution_allowed: bool = False
    def to_dict(self): return asdict(self)

class OrderFlowDeltaBookSymmetryAnalyzer:
    VERSION = "RC37-DELTA-BOOK-SYMMETRY"

    def evaluate(self, sessions: list[dict]) -> DeltaBookSymmetryReport:
        if not sessions:
            raise ValueError("Nenhuma sessao fornecida.")
        samples=[]
        for session in sessions:
            if session.get("direction_logic_version") != EXPECTED_DIRECTION_VERSION:
                raise ValueError("Sessao pre-RC35 ou sem versao direcional rejeitada.")
            if session.get("status") != "COMPLETED" or int(session.get("collection_errors", 0)) != 0:
                raise ValueError("Sessao incompleta ou com erro de coleta rejeitada.")
            if not session.get("observational_only", False) or session.get("score_influence_allowed", True) or session.get("decision_influence_allowed", True) or session.get("order_execution_allowed", True):
                raise ValueError("Sessao com permissoes operacionais rejeitada.")
            samples.extend(session.get("samples") or [])

        dp=dn=bp=bn=bull=bear=div_pn=div_np=neutral=0
        for s in samples:
            dom=abs(float(s.get("dominance",0) or 0))
            delta=float(s.get("recent_delta",0) or 0)
            imb=float(s.get("imbalance",0) or 0)
            dt=float(s.get("delta_threshold",0.35) or 0.35)
            bt=float(s.get("book_threshold",0.062149) or 0.062149)
            ds=1 if dom>=dt and delta>0 else -1 if dom>=dt and delta<0 else 0
            bs=1 if imb>=bt else -1 if imb<=-bt else 0
            dp += ds==1; dn += ds==-1; bp += bs==1; bn += bs==-1
            bull += ds==1 and bs==1
            bear += ds==-1 and bs==-1
            div_pn += ds==1 and bs==-1
            div_np += ds==-1 and bs==1
            neutral += ds!=0 and bs==0

        reasons=[]
        if dn and not bn: reasons.append("NEGATIVE_DELTA_PRESENT_BUT_NO_NEGATIVE_BOOK")
        if dn and bn and not bear: reasons.append("NEGATIVE_SIGNALS_PRESENT_BUT_NO_COOCCURRENCE")
        if not dn: reasons.append("NO_STRONG_NEGATIVE_DELTA")
        if not bn: reasons.append("NO_STRONG_NEGATIVE_BOOK")
        if bear: status="BEARISH_COOCCURRENCE_OBSERVED"
        elif dn and bn: status="NEGATIVE_SIGNALS_NOT_ALIGNED_IN_TIME"
        elif dn: status="BOOK_NEGATIVE_COVERAGE_MISSING"
        else: status="NEGATIVE_DELTA_COVERAGE_MISSING"
        return DeltaBookSymmetryReport(len(sessions),len(samples),dp,dn,bp,bn,bull,bear,div_pn,div_np,neutral,status,tuple(reasons) if reasons else ("OK",))
