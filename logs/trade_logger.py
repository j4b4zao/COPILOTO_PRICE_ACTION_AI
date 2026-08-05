"""
logs/trade_logger.py

Trade Logger

RC11

Responsável por registrar todas as operações
realizadas pelo COPILOTO PRICE ACTION AI.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.event_types import EventType

from models.trade_record import TradeRecord


class TradeLogger:

    NAME = "TradeLogger"

    VERSION = "RC11"

    ENABLED = True

    FILE_NAME = "data/trades.json"

    def __init__(self, event_bus=None):

        self.event_bus = event_bus

        self.file = Path(self.FILE_NAME)

        self.file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not self.file.exists():

            self.file.write_text(
                "[]",
                encoding="utf-8",
            )

        if self.event_bus:

            self.event_bus.subscribe(

                EventType.DECISION_UPDATED,

                self.on_decision,

            )

    # ==========================================================
    # EVENTO
    # ==========================================================

    def on_decision(self, event):

        context = event.payload

        decision = context.decision

        if not decision.approved:

            return

        record = self.create_record(context)

        self.save(record)

    # ==========================================================
    # CRIAR REGISTRO
    # ==========================================================

    def create_record(self, context):

        market = context.market

        strategy = context.strategy

        risk = context.risk

        score = context.score

        structure = context.structure

        volume = context.volume

        liquidity = context.liquidity

        # SMART MONEY

        order_block = context.order_block

        fair_value_gap = context.fair_value_gap

        record = TradeRecord()

        # ======================================================
        # MERCADO
        # ======================================================

        record.symbol = market.symbol

        record.timeframe = market.timeframe

        record.entry = market.last_price

        # ======================================================
        # SETUP
        # ======================================================

        record.setup = strategy.name

        record.signal = strategy.signal

        # ======================================================
        # RISCO
        # ======================================================

        record.stop_loss = risk.stop_loss

        record.take_profit = risk.take_profit

        record.risk_reward = risk.risk_reward

        record.risk_level = risk.risk_level

        # ======================================================
        # SCORE
        # ======================================================

        record.score = score.total

        record.grade = score.grade

        record.confidence = score.confidence

        # ======================================================
        # CONTEXTO
        # ======================================================

        record.trend = str(structure.trend)

        record.volume = volume.current

        # ======================================================
        # LIQUIDEZ
        # ======================================================

        if liquidity.buy_side:

            record.liquidity = "BUY_SIDE"

        elif liquidity.sell_side:

            record.liquidity = "SELL_SIDE"

        else:

            record.liquidity = "NONE"

        # ======================================================
        # ORDER BLOCK
        # ======================================================

        if order_block.bullish:

            record.order_block = "BULLISH"

        elif order_block.bearish:

            record.order_block = "BEARISH"

        else:

            record.order_block = "NONE"

        record.order_block_strength = (
            order_block.strength
        )

        record.order_block_score = (
            order_block.score
        )

        record.order_block_mitigated = (
            order_block.mitigated
        )

        record.order_block_tested = (
            order_block.tested
        )

        # ======================================================
        # FAIR VALUE GAP
        # ======================================================

        if fair_value_gap.bullish:

            record.fair_value_gap = "BULLISH"

        elif fair_value_gap.bearish:

            record.fair_value_gap = "BEARISH"

        else:

            record.fair_value_gap = "NONE"

        record.fair_value_gap_strength = (
            fair_value_gap.strength
        )

        record.fair_value_gap_score = (
            fair_value_gap.score
        )

        record.fair_value_gap_filled = (
            fair_value_gap.filled
        )

        record.fair_value_gap_tested = (
            fair_value_gap.tested
        )

        return record

    # ==========================================================
    # SALVAR
    # ==========================================================

    def save(self, record: TradeRecord):

        trades = self.load()

        trades.append(record.to_dict())

        with self.file.open(

            "w",

            encoding="utf-8",

        ) as f:

            json.dump(

                trades,

                f,

                indent=4,

                ensure_ascii=False,

            )

    # ==========================================================
    # CARREGAR
    # ==========================================================

    def load(self):

        with self.file.open(

            "r",

            encoding="utf-8",

        ) as f:

            return json.load(f)

    # ==========================================================
    # LIMPAR
    # ==========================================================

    def clear(self):

        with self.file.open(

            "w",

            encoding="utf-8",

        ) as f:

            json.dump([], f)

    # ==========================================================
    # ESTATÍSTICAS
    # ==========================================================

    def total_trades(self):

        return len(self.load())