"""
tests/test_full_pipeline_risk_rejected.py

Teste de BLOQUEIO por RISCO RC2.3.

Objetivo:
    Market/PA/Context/Strategy/Score favoráveis
        ↓
    Risk rejeita por R:R insuficiente
        ↓
    Decision = WAIT

Importante:
    Este teste NÃO altera nenhum engine do projeto.
    Ele prepara diretamente um AnalysisContext controlado.
"""

from core.analysis_context import AnalysisContext

from ai.score_engine import ScoreEngine
from risk.risk_manager import RiskManager
from decision.decision_engine import DecisionEngine


def preparar_cenario(context):

    context.market.symbol = "WINV26"
    context.market.timeframe = "M1"
    context.market.last_price = 172400.0
    context.market.volume = 220000.0

    # ----------------------------------------------------------
    # PRICE ACTION
    # ----------------------------------------------------------

    context.price_action.valid = True
    context.price_action.bias = "BUY"
    context.price_action.bos = True
    context.price_action.choch = False
    context.price_action.score = 90
    context.price_action.confluences = 10
    # Evidências direcionais fortes para que o ScoreEngine
    # ultrapasse o limiar sem depender de Liquidity.

    # ----------------------------------------------------------
    # CONTEXT
    # ----------------------------------------------------------

    context.context.valid = True
    context.context.bias = "BUY"
    context.context.score = 90
    context.context.market_state = "FAVORABLE"
    context.context.confluences = 5

    # ----------------------------------------------------------
    # STRATEGY
    # ----------------------------------------------------------

    context.strategy.clear()

    context.strategy.valid = True
    context.strategy.signal = "BUY"
    context.strategy.setup_id = "TEST_RISK_REJECTED"
    context.strategy.name = "Risk Rejected Test"
    context.strategy.setup_type = "TREND"
    context.strategy.score = 100.0
    context.strategy.probability = 1.0
    context.strategy.quality = "A+"
    context.strategy.priority = 10
    context.strategy.direction = "BUY"
    context.strategy.confluences = 5

    # ----------------------------------------------------------
    # LIQUIDITY
    #
    # Não usamos liquidez para autorizar o risco.
    # ----------------------------------------------------------

    context.liquidity.valid = True
    context.liquidity.sweep_down = True
    context.liquidity.buy_side = True
    context.liquidity.sell_side = False
    context.liquidity.liquidity_price = 172100.0
    context.liquidity.confluences = 1

    # ----------------------------------------------------------
    # ESTRUTURA CONTROLADA PARA O RISK MANAGER
    #
    # Entrada = 172400
    # Stop estrutural = 172100
    # Último topo estrutural = 172500
    #
    # Risco = 300 pontos
    # Retorno = 100 pontos
    # R:R esperado = 0.33
    #
    # Importante:
    # NÃO preenchemos context.risk diretamente.
    # O RiskManager deve calcular e rejeitar o cenário.
    # ----------------------------------------------------------

    if hasattr(context.structure, "valid"):
        context.structure.valid = True

    if hasattr(context.structure, "trend"):
        from enums.trend import Trend
        context.structure.trend = Trend.UP

    if hasattr(context.structure, "hh"):
        context.structure.hh = True

    if hasattr(context.structure, "hl"):
        context.structure.hl = True

    if hasattr(context.structure, "bos_up"):
        context.structure.bos_up = True

    if hasattr(context.structure, "last_high"):
        context.structure.last_high = 172500.0

    if hasattr(context.structure, "last_low"):
        context.structure.last_low = 172100.0

    # Volume não é necessário para autorizar o risco neste teste.
    if hasattr(context.volume, "valid"):
        context.volume.valid = False


def executar_teste():

    context = AnalysisContext()

    preparar_cenario(context)

    ScoreEngine().executar(context)
    RiskManager().executar(context)
    DecisionEngine().executar(context)

    return context


def mostrar_resultado(context):

    print()
    print("=" * 72)
    print("TESTE FULL PIPELINE RISK REJECTED RC2.3")
    print("=" * 72)

    print()
    print("PRICE ACTION")
    print("-" * 72)
    print(f"valid        : {context.price_action.valid}")
    print(f"bias         : {context.price_action.bias}")
    print(f"bos          : {context.price_action.bos}")
    print(f"score        : {context.price_action.score}")

    print()
    print("CONTEXT")
    print("-" * 72)
    print(f"valid        : {context.context.valid}")
    print(f"bias         : {context.context.bias}")
    print(f"score        : {context.context.score}")
    print(f"market_state : {context.context.market_state}")

    print()
    print("STRATEGY")
    print("-" * 72)
    print(f"valid        : {context.strategy.valid}")
    print(f"signal       : {context.strategy.signal}")
    print(f"score        : {context.strategy.score}")

    print()
    print("SCORE")
    print("-" * 72)
    print(f"valid        : {context.score.valid}")
    print(f"total        : {context.score.total}")
    print(f"bias         : {context.score.bias}")
    print(f"confidence   : {context.score.confidence}")

    if getattr(context.score, "breakdown", None):
        print(f"breakdown    : {context.score.breakdown}")

    print()
    print("RISK")
    print("-" * 72)
    print(f"entry_price  : {context.risk.entry_price}")
    print(f"stop_loss    : {context.risk.stop_loss}")
    print(f"take_profit  : {context.risk.take_profit}")
    print(f"risk_reward  : {context.risk.risk_reward}")
    print(f"risk_level   : {context.risk.risk_level}")
    print(f"risk_score   : {context.risk.risk_score}")
    print(f"approved     : {context.risk.approved}")
    print(f"valid        : {context.risk.valid}")

    if getattr(context.risk, "reasons", None):
        print()
        print("RISK REASONS")
        print("-" * 72)
        for reason in context.risk.reasons:
            print(f"- {reason}")

    print()
    print("DECISION")
    print("-" * 72)
    print(f"valid        : {context.decision.valid}")
    print(f"approved     : {context.decision.approved}")
    print(f"action       : {context.decision.action}")
    print(f"direction    : {context.decision.direction}")
    print(f"signal       : {context.decision.signal}")


def validar(context):

    # ----------------------------------------------------------
    # SCORE deve ser suficiente
    # ----------------------------------------------------------

    assert context.score.total >= 70
    assert context.score.valid is True
    assert context.score.bias == "BUY"

    # ----------------------------------------------------------
    # STRATEGY válida
    # ----------------------------------------------------------

    assert context.strategy.valid is True
    assert context.strategy.signal == "BUY"

    # ----------------------------------------------------------
    # RISK deve rejeitar
    # ----------------------------------------------------------

    assert context.risk.entry_price > 0
    assert context.risk.stop_loss > 0
    assert context.risk.take_profit > 0
    assert context.risk.valid is False
    assert context.risk.approved is False

    # R:R propositalmente insuficiente
    assert context.risk.risk_reward < 1.0

    # ----------------------------------------------------------
    # DECISION deve bloquear
    # ----------------------------------------------------------

    assert context.decision.valid is False
    assert context.decision.approved is False
    assert context.decision.action == "WAIT"
    assert context.decision.direction == "NONE"
    assert context.decision.signal == "NONE"


def main():

    try:

        context = executar_teste()

        mostrar_resultado(context)

        validar(context)

    except AssertionError as erro:

        print()
        print("=" * 72)
        print("❌ TESTE RISK REJECTED FALHOU")
        print("=" * 72)

        if erro:
            print(f"AssertionError: {erro}")

        raise

    except Exception as erro:

        print()
        print("=" * 72)
        print("❌ ERRO NO TESTE RISK REJECTED")
        print("=" * 72)

        print(f"{type(erro).__name__}: {erro}")

        raise

    print()
    print("=" * 72)
    print("🏆 TESTE FULL PIPELINE RISK REJECTED APROVADO")
    print("=" * 72)


if __name__ == "__main__":
    main()