"""CLI offline para avaliar JSON de validacao Profit RTD (RC19)."""

from __future__ import annotations

import argparse
import sys

from market_data.profit_rtd_validation_evaluator import ProfitRTDValidationEvaluator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Avalia um JSON exportado de validacao Profit RTD."
    )
    parser.add_argument("path", help="Caminho do JSON exportado pela sessao RTD.")
    return parser


def run_validation(path: str, *, evaluator=None) -> int:
    engine = evaluator or ProfitRTDValidationEvaluator()
    try:
        result = engine.evaluate_file(path)
    except (OSError, ValueError, TypeError) as exc:
        print("PROFIT_RTD_VALIDATION=ERROR")
        print(f"reason={type(exc).__name__}:{exc}")
        return 1

    print(f"PROFIT_RTD_VALIDATION={result.status}")
    print(f"symbol={result.symbol}")
    print(f"total_cycles={result.total_cycles}")
    print(f"continuity_rate={result.continuity_rate:.4f}")
    print(f"update_rate={result.update_rate:.4f}")
    print(f"total_new_trades={result.total_new_trades}")
    print(f"baseline_resets={result.baseline_resets}")
    print(f"continuity_loss_cycles={result.continuity_loss_cycles}")
    print(f"symbol_reset_cycles={result.symbol_reset_cycles}")
    print(f"observational_only={result.observational_only}")
    print(f"score_influence_allowed={result.score_influence_allowed}")
    print(f"decision_influence_allowed={result.decision_influence_allowed}")
    print(f"order_execution_allowed={result.order_execution_allowed}")
    print("reasons=" + ("|".join(result.reasons) if result.reasons else "OK"))
    return 0 if result.approved else 2


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return run_validation(args.path)


if __name__ == "__main__":
    sys.exit(main())
