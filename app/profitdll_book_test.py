"""CLI local para testar BookDepth real via ProfitDLL.

Uso seguro:
  python -m app.profitdll_book_test --dll C:\\caminho\\ProfitDLL64.dll --preflight

Para modo live, defina no terminal local:
  set PROFITDLL_ACTIVATION_KEY=...
  set PROFITDLL_USER=...
  set PROFITDLL_PASSWORD=...

Depois execute:
  python -m app.profitdll_book_test --dll C:\\caminho\\ProfitDLL64.dll --symbol WINV26 --live
"""

from __future__ import annotations

import argparse
import sys

from market_data.profitdll_local_bootstrap import ProfitDLLLocalBootstrap


def build_parser():
    parser = argparse.ArgumentParser(description="Teste somente leitura da ProfitDLL/BookDepth.")
    parser.add_argument("--dll", required=True, help="Caminho da ProfitDLL64.dll")
    parser.add_argument("--symbol", default="WINV26", help="Ativo a assinar")
    parser.add_argument("--exchange", default="F", help="Bolsa/feed legado")
    parser.add_argument("--cycles", type=int, default=20, help="Quantidade de ciclos de observação")
    parser.add_argument("--interval", type=float, default=0.5, help="Intervalo entre ciclos em segundos")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true", help="Somente valida DLL/capacidades; não faz login")
    mode.add_argument("--live", action="store_true", help="Inicializa Market Data e observa BookDepth")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    bootstrap = ProfitDLLLocalBootstrap()

    if args.preflight:
        report = bootstrap.preflight(args.dll)
        print(bootstrap.render_preflight(report))
        return 0 if report.loaded and report.market_login and report.book_mode != "UNSUPPORTED" else 2

    try:
        bootstrap.start_live(args.dll, symbol=args.symbol, exchange=args.exchange)
        print("[PROFITDLL LIVE] sessão iniciada em modo somente leitura.")
        available = bootstrap.observe(symbol=args.symbol, cycles=args.cycles, interval=args.interval)
        print(f"[PROFITDLL LIVE] snapshots_disponiveis={available}/{max(1, args.cycles)}")
        return 0 if available > 0 else 3
    except KeyboardInterrupt:
        print("\n[PROFITDLL LIVE] encerrado pelo usuário.")
        return 130
    except Exception as exc:
        print(f"[PROFITDLL ERROR] {exc}")
        return 1
    finally:
        bootstrap.close()


if __name__ == "__main__":
    sys.exit(main())
