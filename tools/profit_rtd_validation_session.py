"""CLI opt-in para sessao real de validacao Profit RTD (RC20)."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from config.settings import ENABLE_ORDER_FLOW_SCORE, PROFIT_RTD_TIMES_TRADES_PATH
from market_data.profit_rtd_session_close_utility import ProfitRTDSessionCloseUtility
from market_data.profit_rtd_validation_session_runner import ProfitRTDValidationSessionRunner


MAX_VALIDATION_CYCLES = 3600


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Executa uma sessao observacional e limitada do Times & Trades RTD do Profit. "
            "Nada e enviado para Score, Decision ou execucao."
        )
    )
    parser.add_argument("symbol", help="Ativo esperado, por exemplo WINV26 ou WDOU26.")
    parser.add_argument(
        "--cycles",
        required=True,
        type=int,
        help=f"Quantidade de ciclos de coleta (1..{MAX_VALIDATION_CYCLES}).",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.25,
        help="Intervalo em segundos entre ciclos (padrao: 0.25).",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Diretorio onde o JSON de validacao sera exportado.",
    )
    parser.add_argument("--session-id", default=None, help="Identificador opcional da sessao.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Permite sobrescrever somente o arquivo da mesma sessao explicitamente informado.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Segunda trava obrigatoria para iniciar a coleta RTD.",
    )
    return parser


def _build_real_collector():
    from connectors.excel_connector import ExcelConnector
    from market_data.collector import Collector
    from market_data.excel_range_gateway import ExcelRangeGateway
    from market_data.profit_rtd_order_flow_pipeline import ProfitRTDOrderFlowPipeline
    from market_data.profit_rtd_workbook_reader import ProfitRTDTimesTradesReader

    # Collector continua conectado ao Profit.xlsx pelo caminho legado/oficial.
    collector = Collector(enable_profit_rtd_order_flow=False)

    # T&T usa uma conexao Excel dedicada e separada da cotacao principal.
    tt_excel = ExcelConnector()
    if not tt_excel.conectar(PROFIT_RTD_TIMES_TRADES_PATH):
        raise RuntimeError("Nao foi possivel conectar ao workbook Times & Trades RTD.")

    tt_gateway = ExcelRangeGateway(tt_excel)
    tt_reader = ProfitRTDTimesTradesReader(tt_gateway)
    collector.profit_rtd_order_flow_pipeline = ProfitRTDOrderFlowPipeline(
        tt_reader,
        collector.order_flow,
    )
    collector.enable_profit_rtd_order_flow = True
    collector.profit_rtd_times_trades_excel = tt_excel
    return collector


def _build_real_preflight(collector):
    from market_data.excel_range_gateway import ExcelRangeGateway
    from market_data.profit_rtd_live_preflight import ProfitRTDLivePreflight
    from market_data.profit_rtd_workbook_reader import ProfitRTDTimesTradesReader

    tt_excel = getattr(collector, "profit_rtd_times_trades_excel", None)
    if tt_excel is None:
        raise RuntimeError("Collector sem conexao dedicada de Times & Trades RTD.")

    gateway = ExcelRangeGateway(tt_excel)
    reader = ProfitRTDTimesTradesReader(gateway)
    return ProfitRTDLivePreflight(reader)


def _print_receipt(receipt) -> None:
    print(f"PROFIT_RTD_SESSION={receipt.status}")
    print(f"symbol={receipt.symbol}")
    print(f"preflight={receipt.preflight_status}")
    print(f"requested_cycles={receipt.requested_cycles}")
    print(f"completed_cycles={receipt.completed_cycles}")
    print(f"emitted_contexts={receipt.emitted_contexts}")
    print(f"exported_cycles={receipt.exported_cycles}")
    print(f"observational_only={receipt.observational_only}")
    print(f"score_influence_allowed={receipt.score_influence_allowed}")
    print(f"decision_influence_allowed={receipt.decision_influence_allowed}")
    print(f"order_execution_allowed={receipt.order_execution_allowed}")
    print("reasons=" + ("|".join(receipt.reasons) if receipt.reasons else "OK"))
    if receipt.export_path:
        print(f"export_path={receipt.export_path}")
    if receipt.sha256:
        print(f"sha256={receipt.sha256}")


def run_validation_session(
    symbol: str,
    output_dir,
    *,
    cycles: int,
    interval_seconds: float = 0.25,
    session_id: str | None = None,
    overwrite: bool = False,
    execute: bool = False,
    collector=None,
    preflight=None,
    close_utility=None,
    order_flow_score_enabled: bool | None = None,
) -> int:
    if not execute:
        print("PROFIT_RTD_SESSION=NOT_STARTED")
        print("reason=EXECUTE_FLAG_REQUIRED")
        return 2

    score_enabled = (
        ENABLE_ORDER_FLOW_SCORE
        if order_flow_score_enabled is None
        else bool(order_flow_score_enabled)
    )
    if score_enabled:
        print("PROFIT_RTD_SESSION=NOT_STARTED")
        print("reason=ORDER_FLOW_SCORE_MUST_REMAIN_DISABLED")
        return 2

    if isinstance(cycles, bool) or not isinstance(cycles, int) or not (1 <= cycles <= MAX_VALIDATION_CYCLES):
        print("PROFIT_RTD_SESSION=NOT_STARTED")
        print(f"reason=CYCLES_MUST_BE_1_TO_{MAX_VALIDATION_CYCLES}")
        return 2

    try:
        interval = float(interval_seconds)
    except (TypeError, ValueError):
        print("PROFIT_RTD_SESSION=NOT_STARTED")
        print("reason=INTERVAL_MUST_BE_NON_NEGATIVE")
        return 2
    if interval < 0:
        print("PROFIT_RTD_SESSION=NOT_STARTED")
        print("reason=INTERVAL_MUST_BE_NON_NEGATIVE")
        return 2

    target_dir = Path(output_dir).expanduser().resolve()

    try:
        active_collector = collector if collector is not None else _build_real_collector()
        active_preflight = (
            preflight if preflight is not None else _build_real_preflight(active_collector)
        )
        closer = close_utility if close_utility is not None else ProfitRTDSessionCloseUtility()
        runner = ProfitRTDValidationSessionRunner(active_preflight, closer)
        receipt = runner.run(
            active_collector,
            symbol,
            target_dir,
            cycles=cycles,
            interval_seconds=interval,
            session_id=session_id,
            overwrite=overwrite,
            order_flow_score_enabled=False,
        )
    except Exception as exc:
        print("PROFIT_RTD_SESSION=ERROR")
        print(f"reason=BOOTSTRAP_ERROR:{type(exc).__name__}:{exc}")
        return 1

    _print_receipt(receipt)
    if receipt.status == "COMPLETED":
        return 0
    if receipt.status == "INTERRUPTED":
        return 130
    if receipt.status == "NOT_STARTED":
        return 2
    return 1


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return run_validation_session(
        args.symbol,
        args.output_dir,
        cycles=args.cycles,
        interval_seconds=args.interval,
        session_id=args.session_id,
        overwrite=args.overwrite,
        execute=args.execute,
    )


if __name__ == "__main__":
    sys.exit(main())
