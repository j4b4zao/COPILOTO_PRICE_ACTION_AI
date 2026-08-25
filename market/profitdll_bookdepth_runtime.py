"""Runtime integrado ProfitDLL -> BookDepth monitor, somente leitura."""

from __future__ import annotations

from market.book_depth_runtime_monitor import BookDepthRuntimeMonitor
from market_data.profitdll_book_depth_bridge import ProfitDLLBookDepthBridge


class ProfitDLLBookDepthRuntime:
    """Composição final para observar BookDepth real vindo da ProfitDLL."""

    VERSION = "RC1-PROFITDLL-BOOKDEPTH-RUNTIME"

    def __init__(self, session, *, levels: int = 10, monitor=None):
        if session is None:
            raise ValueError("session é obrigatória.")
        self.session = session
        self.bridge = ProfitDLLBookDepthBridge(session, levels=levels)
        self.monitor = monitor if monitor is not None else BookDepthRuntimeMonitor(self.bridge.service)

    @property
    def last_snapshot(self):
        return self.monitor.last_snapshot

    @property
    def last_source_report(self):
        return self.monitor.last_source_report

    @property
    def last_quality_report(self):
        return self.monitor.last_quality_report

    def poll(self, symbol: str):
        return self.monitor.poll(symbol)

    def refresh(self, context):
        return self.monitor.refresh(context)

    def session_summary(self):
        return self.monitor.session_summary()

    def render(self) -> str:
        status = getattr(self.session, "status", None)
        prefix = "[PROFITDLL] "
        if status is not None:
            prefix += (
                f"state={getattr(status, 'state', 'UNKNOWN')} "
                f"mode={getattr(status, 'book_mode', 'UNKNOWN')} "
                f"symbol={getattr(status, 'symbol', '')} "
                f"events={getattr(status, 'callback_events', 0)}\n"
            )
        else:
            prefix += "state=UNKNOWN\n"
        return prefix + self.monitor.render()
