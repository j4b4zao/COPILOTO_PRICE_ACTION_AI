"""Ponte ProfitDLL runtime -> Level2 provider -> BookDepthService.

Somente leitura. Reutiliza a sessão runtime já inicializada/assinada e entrega
snapshots compatíveis com a infraestrutura BookDepth existente.
"""

from __future__ import annotations

from market.book_depth_service import BookDepthService
from market_data.book_depth_level2_provider import NormalizedLevel2BookDepthProvider


class ProfitDLLSessionLevel2Reader:
    """Adapta ProfitDLLMarketDataSession ao contrato BookDepthLevel2Reader."""

    VERSION = "RC1-PROFITDLL-SESSION-LEVEL2-READER"
    SOURCE = "PROFITDLL"

    def __init__(self, session):
        if session is None or not callable(getattr(session, "snapshot", None)):
            raise TypeError("session deve expor snapshot(symbol).")
        self.session = session

    def read_book_depth(self, symbol: str) -> dict:
        symbol = str(symbol or "").upper().strip()
        if not symbol:
            raise ValueError("Símbolo obrigatório.")
        status = getattr(self.session, "status", None)
        if status is not None:
            if not bool(getattr(status, "initialized", False)):
                raise RuntimeError("ProfitDLL session não inicializada.")
            if not bool(getattr(status, "subscribed", False)):
                raise RuntimeError("ProfitDLL session sem assinatura ativa.")
            current = str(getattr(status, "symbol", "") or "").upper().strip()
            if current and current != symbol:
                raise RuntimeError("Símbolo solicitado difere da assinatura ativa.")
        payload = self.session.snapshot(symbol)
        if not isinstance(payload, dict):
            raise RuntimeError("BookDepth ainda indisponível na sessão ProfitDLL.")
        return payload


class ProfitDLLBookDepthBridge:
    """Composição pronta para uso pelo pipeline observacional de BookDepth."""

    VERSION = "RC1-PROFITDLL-BOOKDEPTH-BRIDGE"

    def __init__(self, session, *, levels: int = 10):
        self.session = session
        self.reader = ProfitDLLSessionLevel2Reader(session)
        self.provider = NormalizedLevel2BookDepthProvider(
            self.reader,
            source="PROFITDLL",
            max_levels=levels,
        )
        self.service = BookDepthService(self.provider, levels=levels)

    def snapshot(self, symbol: str):
        return self.service.snapshot(symbol)

    def refresh(self, context):
        return self.service.refresh(context)
