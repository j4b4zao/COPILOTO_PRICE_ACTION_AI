"""
monitor/debug_monitor.py

Debug Monitor

RC10.2 - OBSERVABILIDADE MULTI-TIMEFRAME / ORDER FLOW

Monitor oficial do COPILOTO PRICE ACTION AI.
"""

from datetime import datetime

from core.event_types import EventType
from monitor.multi_timeframe_monitor import MultiTimeframeMonitor
from monitor.order_flow_monitor import OrderFlowMonitor


class DebugMonitor:

    NAME = "DebugMonitor"

    VERSION = "RC10.2"

    ENABLED = True

    def __init__(self, event_bus):

        self.event_bus = event_bus

        self.event_bus.subscribe(
            EventType.LOOP_COMPLETED,
            self.on_loop_completed,
        )

    # ==========================================================
    # EVENTO
    # ==========================================================

    def on_loop_completed(self, event):

        self.show(event.data)

    # ==========================================================
    # EXIBIÇÃO
    # ==========================================================

    def show(self, context):

        print("\n" + "=" * 70)

        print(
            f"COPILOTO PRICE ACTION AI    "
            f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        )

        print("=" * 70)

        self._market(context)

        self._multi_timeframe(context)

        self._structure(context)

        self._liquidity(context)

        self._volume(context)

        self._order_flow(context)

        self._price_action(context)

        self._order_block(context)

        self._fair_value_gap(context)

        self._context(context)

        self._strategy(context)

        self._score(context)

        self._risk(context)

        self._decision(context)

        print("=" * 70)

    # ==========================================================
    # MARKET
    # ==========================================================

    def _market(self, context):

        market = context.market

        print("\n[ MARKET ]")

        print(f"Ativo..........: {market.symbol}")
        print(f"TimeFrame......: {market.timeframe}")
        print(f"Preço..........: {market.last_price:.2f}")
        print(f"Candles........: {market.candle_count}")

    # ==========================================================
    # MULTI-TIMEFRAME (RC3.4 - INFORMATIVO)
    # ==========================================================

    def _multi_timeframe(self, context):

        print("\n" + MultiTimeframeMonitor.render(context))

    # ==========================================================
    # STRUCTURE
    # ==========================================================

    def _structure(self, context):

        s = context.structure

        print("\n[ STRUCTURE ]")

        print(f"Trend..........: {s.trend}")

        print(f"HH.............: {s.hh}")
        print(f"HL.............: {s.hl}")
        print(f"LH.............: {s.lh}")
        print(f"LL.............: {s.ll}")

        print(f"BOS UP.........: {s.bos_up}")
        print(f"BOS DOWN.......: {s.bos_down}")

        print(f"CHOCH..........: {s.choch}")

    # ==========================================================
    # LIQUIDITY
    # ==========================================================

    def _liquidity(self, context):

        l = context.liquidity

        print("\n[ LIQUIDITY ]")

        print(f"Buy Side.......: {l.buy_side}")
        print(f"Sell Side......: {l.sell_side}")

        print(f"Sweep Up.......: {l.sweep_up}")
        print(f"Sweep Down.....: {l.sweep_down}")

        print(f"Equal High.....: {l.equal_highs}")
        print(f"Equal Low......: {l.equal_lows}")

    # ==========================================================
    # VOLUME
    # ==========================================================

    def _volume(self, context):

        v = context.volume

        print("\n[ VOLUME ]")

        print(f"Current........: {v.current:.0f}")
        print(f"Level..........: {v.level}")
        print(f"Strength.......: {v.strength:.2f}")

    def _order_flow(self, context):

        print("\n" + OrderFlowMonitor.render(context))

    # ==========================================================
    # PRICE ACTION
    # ==========================================================

    def _price_action(self, context):

        p = context.price_action

        print("\n[ PRICE ACTION ]")

        print(f"Hammer.........: {p.hammer}")
        print(f"Shooting.......: {p.shooting_star}")

        print(f"Bull Engulf....: {p.bullish_engulfing}")
        print(f"Bear Engulf....: {p.bearish_engulfing}")

        print(f"Inside Bar.....: {p.inside_bar}")
        print(f"Outside Bar....: {p.outside_bar}")

        print(f"Breakout.......: {p.breakout}")
        print(f"Pullback.......: {p.pullback}")
        print(f"Continuation...: {p.continuation}")
        print(f"Rejection......: {p.rejection}")

    # ==========================================================
    # ORDER BLOCK (RC10)
    # ==========================================================

    def _order_block(self, context):

        ob = context.order_block

        print("\n[ ORDER BLOCK ]")

        print(f"Valid..........: {ob.valid}")

        print(f"Bullish........: {ob.bullish}")
        print(f"Bearish........: {ob.bearish}")

        print(f"High...........: {ob.high:.2f}")
        print(f"Low............: {ob.low:.2f}")

        print(f"Entry..........: {ob.entry_price:.2f}")

        print(f"Mitigated......: {ob.mitigated}")
        print(f"Tested.........: {ob.tested}")
        print(f"Touches........: {ob.touches}")

        print(f"Strength.......: {ob.strength:.2f}")
        print(f"Score..........: {ob.score:.2f}")

    # ==========================================================
    # FAIR VALUE GAP (RC11)
    # ==========================================================

    def _fair_value_gap(self, context):

        fvg = context.fair_value_gap

        print("\n[ FAIR VALUE GAP ]")

        print(f"Valid..........: {fvg.valid}")

        print(f"Bullish........: {fvg.bullish}")
        print(f"Bearish........: {fvg.bearish}")

        print(f"High...........: {fvg.high:.2f}")
        print(f"Low............: {fvg.low:.2f}")

        print(f"Midpoint.......: {fvg.midpoint:.2f}")

        print(f"Filled.........: {fvg.filled}")
        print(f"Tested.........: {fvg.tested}")
        print(f"Touches........: {fvg.touches}")

        print(f"Strength.......: {fvg.strength:.2f}")
        print(f"Score..........: {fvg.score:.2f}")
        print(f"Confidence.....: {fvg.confidence:.2f}")

    # ==========================================================
    # CONTEXT
    # ==========================================================

    def _context(self, context):

        c = context.context

        print("\n[ CONTEXT ]")

        print(f"State..........: {c.market_state}")
        print(f"Bias...........: {c.bias}")
        print(f"Score..........: {c.score:.2f}")
        print(f"Confidence.....: {c.confidence:.2f}")

    # ==========================================================
    # STRATEGY
    # ==========================================================

    def _strategy(self, context):

        s = context.strategy

        print("\n[ STRATEGY ]")

        print(f"Setup..........: {s.name}")
        print(f"Signal.........: {s.signal}")
        print(f"Score..........: {s.score:.2f}")
        print(f"Quality........: {s.quality}")

    # ==========================================================
    # SCORE
    # ==========================================================

    def _score(self, context):

        s = context.score

        print("\n[ SCORE ]")

        print(f"Total..........: {s.total:.2f}")
        print(f"Grade..........: {s.grade}")
        print(f"Confidence.....: {s.confidence:.2f}")

        if s.breakdown:

            print("\nBreakdown")

            for engine, value in s.breakdown.items():

                print(f"{engine:<18} {value:.2f}")

    # ==========================================================
    # RISK
    # ==========================================================

    def _risk(self, context):

        r = context.risk

        print("\n[ RISK ]")

        print(f"Approved.......: {r.approved}")
        print(f"Level..........: {r.risk_level}")
        print(f"Score..........: {r.risk_score}")
        print(f"RR.............: {r.risk_reward:.2f}")

    # ==========================================================
    # DECISION
    # ==========================================================

    def _decision(self, context):

        d = context.decision

        print("\n[ DECISION ]")

        print(f"Action.........: {d.action}")
        print(f"Approved.......: {d.approved}")
