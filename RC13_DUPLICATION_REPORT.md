# RC13.5 — Relatório de Duplicações Arquiteturais

Data da auditoria: 2026-08-06  
Escopo: 219 arquivos Python do workspace (excluídos `.git` e `ambiente`).

## Método

Esta é uma auditoria estática. Foram lidos os `import`/`from import`, as
declarações de classes, as relações de herança e chamadas construtoras diretas.
"Nunca importado" significa que nenhum módulo do workspace faz import estático
do arquivo; "nunca instanciado" significa que nenhuma chamada construtora direta
foi localizada. Imports dinâmicos, reflexão e execução externa não são cobertos.

## Versões canônicas RC13 e duplicações

| Classe | Versão RC13/canônica | Versão legada ou concorrente | Evidência |
|---|---|---|---|
| `EngineBase` | `ai/engine_base.py` | `core/engine_base.py` | Todas as engines RC13 importam `ai.engine_base`; a versão `core` não possui subclasses diretas. |
| `ContextEngine` | `brain/context_engine.py` (candidata do pipeline RC13, ainda incompatível) | `context/context_engine.py` | A primeira é importada por `AnalysisPipeline` e `EngineManager`; a segunda não é importada. |
| `MarketState` | `core/market_state.py` | `market/market_state.py` | `Collector`, `MarketContext` e o alias RC13 `MarketResult` usam a versão `core`. |
| `DataValidator` | `core/data_validator.py` | `validation/data_validator.py` | `Collector` usa a versão `core`; `SystemInitializer` ainda instancia a versão legada. |
| `SetupBase` | `strategies/setups/setup_base.py` | `strategies/setup_base.py` | `SetupRegistry` carrega os setups da subpasta `setups`; o outro atende `strategies/trend_pullback.py`, não importado. |
| `AnalysisResult` | Nenhuma | `analysis/analysis_result.py`, `core/analysis_result.py` | Ambas sem import estático; duplicação legada. |
| `ConfigManager` | Nenhuma | `config/config_manager.py`, `optimization/config_manager.py` | Ambas pertencem a fluxos isolados. |
| `Event` | `core/event.py` | `core/events.py` | O pipeline RC13 importa `core.event.Event`; `core/events.py` não é importado. |
| `MarketRegime` | `analysis/market_regime.py` | `market/market_regime.py` | A versão de `analysis` é registrada no `EngineManager`. |
| `PremiumDiscount` | Nenhuma RC13 | `analysis/premium_discount.py`, `zones/premium_discount.py` | Nenhuma participa do pipeline RC13. |
| `SetupDetector` | Nenhuma RC13 | `analysis/setup_detector.py`, `analysis/price_action/setups/setup_detector.py` | Ambas fora do fluxo principal. |
| `SmartMoneyEngine` | `analysis/smart_money/smart_money_engine.py` | `analysis/smart_money_engine.py` | A versão aninhada herda `EngineBase`; a versão raiz trabalha com `market` legado. |
| `StrategyResult` | `models/strategy_result.py` | `strategies/strategy_result.py` | `AnalysisContext` importa o modelo em `models`. |
| `TradeManager` | Nenhuma | `trade/trade_manager.py`, `replay/trade_manager.py` | Fluxos independentes e sem import estático. |
| `Trend` | `enums/trend.py` | `models/enums.py` | Engines RC13 importam `enums.trend.Trend`. |
| `TrendPullback` | `strategies/setups/trend_pullback.py` | `strategies/trend_pullback.py` | O registro ativo usa a versão em `strategies/setups`. |

## Árvore de herança das engines

```text
abc.ABC
├── ai.engine_base.EngineBase                         [base RC13]
│   ├── analysis.market_regime.MarketRegime
│   ├── analysis.market_structure.MarketStructure
│   ├── analysis.liquidity_analysis.LiquidityAnalysis
│   ├── analysis.volume_analysis.VolumeAnalysis
│   ├── analysis.price_action.price_action.PriceAction
│   ├── analysis.smart_money.smart_money_engine.SmartMoneyEngine [abstrata]
│   ├── analysis.smart_money.imbalance.Imbalance
│   ├── analysis.smart_money.order_block.OrderBlock
│   ├── analysis.smart_money.fair_value_gap.FairValueGap
│   ├── analysis.smart_money.liquidity_pool.LiquidityPool
│   ├── brain.evidence_engine.EvidenceEngine
│   ├── strategies.strategy_engine.StrategyEngine
│   ├── ai.score_engine.ScoreEngine
│   ├── risk.risk_manager.RiskManager
│   ├── decision.decision_engine.DecisionEngine
│   ├── alerts.alert_manager.AlertManager
│   └── execution.execution_engine.ExecutionEngine
├── core.engine_base.EngineBase                        [legada; sem subclasses diretas]
└── core.base_module.BaseModule                         [legada]
    ├── brain.explain_engine.ExplainEngine
    └── analysis.price_action.setups.setup_detector.SetupDetector
```

As classes de estratégia não são engines RC13, mas formam outra árvore:

```text
strategies.setups.setup_base.SetupBase
├── strategies.setups.trend_pullback.TrendPullback
├── strategies.setups.liquidity_sweep.LiquiditySweep
└── strategies.setups.trend_breakout.TrendBreakout
```

## Arquivos nunca importados

```text
adaptive/adaptive_engine.py
analysis/analysis_result.py
analysis/liquidity_engine.py
analysis/multi_timeframe.py
analysis/pipeline/analyzer.py
analysis/pipeline/pipeline_executor.py
analysis/pipeline/pipeline_step.py
analysis/pipeline/registry.py
analysis/price_action/setups/setup_detector.py
analysis/price_action/trend/trend_analysis.py
analysis/price_action_engine.py
analysis/pullback.py
analysis/setup_detector.py
analysis/setup_validator.py
analysis/smart_money/smart_money_engine.py
analysis/smart_money_engine.py
analysis/swing_detector.py
app/run.py
app/teste.py
backtest/backtest_engine.py
brain/confidence_engine.py
brain/event_engine.py
brain/evidence_engine.py
brain/explain_engine.py
brain/knowledge_engine.py
brain/learning_engine.py
config/config.py
config/config_manager.py
context/context_builder.py
context/context_engine.py
core/analysis_result.py
core/constants.py
core/copilot.py
core/core_engine.py
core/engine.py
core/engine_base.py
core/engine_manager.py
core/engine_profiler.py
core/events.py
core/kernel.py
core/module.py
core/registry.py
core/scheduler.py
core/weights.py
dashboard/dashboard.py
dashboard/dashboard_engine.py
enums/decision.py
enums/market_status.py
enums/session.py
enums/signal.py
market/candle_engine.py
market/market_regime.py
market_data/profit_adapter.py
models/decision_model.py
models/market_data.py
models/market_structure_model.py
models/price_action_model.py
models/regime_result.py
models/risk_model.py
models/score_model.py
models/signal_result.py
monitor/debug_monitor.py
optimization/config_manager.py
optimization/optimization_engine.py
performance/performance_engine.py
replay/replay_engine.py
replay/report/report_generator.py
replay/report/report_printer.py
replay/trade_manager.py
reports/daily_report.py
setup_performance/setup_tracker.py
strategies/breakout_strategy.py
strategies/price_action_strategy.py
strategies/strategy_result.py
strategies/trend_pullback.py
strategies/validators/context_validator.py
strategies/validators/liquidity_validator.py
strategies/validators/price_action_validator.py
strategies/validators/trend_validators.py
teste_integracao.py
teste_profit.py
teste_reader.py
tests/test_pipeline.py
trade/trade_manager.py
zones/premium_discount.py
```

## Classes nunca instanciadas

Foram excluídos desta lista `Enum`, dataclasses de resultado e classes base
abstratas, que naturalmente não precisam ser instanciadas diretamente.

```text
AdaptiveEngine                    adaptive/adaptive_engine.py
AnalysisResult                    analysis/analysis_result.py
LiquidityEngine                   analysis/liquidity_engine.py
MultiTimeframe                    analysis/multi_timeframe.py
PipelineExecutor                  analysis/pipeline/pipeline_executor.py
PipelineRegistry                  analysis/pipeline/registry.py
SetupDetector                     analysis/setup_detector.py
PriceActionEngine                 analysis/price_action_engine.py
Pullback                          analysis/pullback.py
SmartMoneyEngine                  analysis/smart_money_engine.py
SwingDetector                     analysis/swing_detector.py
BacktestEngine                    backtest/backtest_engine.py
EvidenceEngine                    brain/evidence_engine.py
ExplainEngine                     brain/explain_engine.py
ContextBuilder                    context/context_builder.py
Copilot                           core/copilot.py
CoreEngine                        core/core_engine.py
CopilotEngine                     core/engine.py
EngineManager                     core/engine_manager.py
EngineProfiler                    core/engine_profiler.py
Kernel                            core/kernel.py
Registry                          core/registry.py
Scheduler                         core/scheduler.py
Dashboard                         dashboard/dashboard.py
DashboardEngine                   dashboard/dashboard_engine.py
CandleEngine                      market/candle_engine.py
MarketStructureEngine             market/market_structure_engine.py
ProfitAdapter                     market_data/profit_adapter.py
DebugMonitor                      monitor/debug_monitor.py
OptimizationEngine                optimization/optimization_engine.py
PerformanceEngine                 performance/performance_engine.py
ReplayEngine                      replay/replay_engine.py
ReportGenerator                   replay/report/report_generator.py
ReportPrinter                     replay/report/report_printer.py
TradeManager                      replay/trade_manager.py
DailyReport                       reports/daily_report.py
SetupTracker                      setup_performance/setup_tracker.py
BreakoutStrategy                  strategies/breakout_strategy.py
PriceActionStrategy               strategies/price_action_strategy.py
TrendPullback                     strategies/trend_pullback.py
ContextValidator                  strategies/validators/context_validator.py
LiquidityValidator                strategies/validators/liquidity_validator.py
PriceActionValidator              strategies/validators/price_action_validator.py
TrendValidator                    strategies/validators/trend_validators.py
TradeManager                      trade/trade_manager.py
```

## Órfãos

Classes simultaneamente nunca importadas e nunca instanciadas:

```text
AdaptiveEngine; AnalysisResult (analysis e core); LiquidityEngine;
MultiTimeframe; PriceActionEngine; Pullback; SetupDetector (raiz);
SetupValidator; SmartMoneyEngine (raiz); SwingDetector; BacktestEngine;
EvidenceEngine; ExplainEngine; ConfigManager (config); ContextBuilder;
Copilot; CoreEngine; CopilotEngine; core.EngineBase; EngineManager;
EngineProfiler; Kernel; Module; Registry; Scheduler; Dashboard;
DashboardEngine; CandleEngine; ProfitAdapter; MarketData;
MarketStructureModel; RegimeResult; SignalResult; DebugMonitor;
ConfigManager (optimization); OptimizationEngine; PerformanceEngine;
ReplayEngine; TradeManager (replay); DailyReport; SetupTracker;
BreakoutStrategy; PriceActionStrategy; TradeManager (trade);
ContextValidator; LiquidityValidator; PriceActionValidator; TrendValidator;
ReportGenerator; ReportPrinter; Analyzer; PipelineExecutor; PipelineStep;
PipelineRegistry; SmartMoneyEngine (analysis/smart_money);
SetupDetector (analysis/price_action/setups); TrendAnalysis.
```

## Conclusões

1. A arquitetura RC13 canônica está concentrada em `AnalysisContext`,
   `ai.EngineBase`, os resultados em `models/` e as engines que recebem
   `executar(context)`.
2. `core/engine_base.py`, `market/`, `context/`, `analysis/pipeline/` e vários
   módulos de análise raiz representam gerações paralelas/legadas.
3. Há dois riscos prioritários: a dupla `EngineBase` e o `ContextEngine` que o
   pipeline importa, mas que ainda não implementa o contrato RC13.
4. Nenhuma remoção é recomendada sem confirmar uso dinâmico ou externo dos
   arquivos listados como órfãos.
