# COPILOTO PRICE ACTION AI — Auditoria de Consolidação pós-livros

Data: 2026-08-22

## Objetivo

Consolidar as camadas diagnósticas criadas a partir dos três livros de Al Brooks sem alterar prematuramente o núcleo operacional validado `Strategy -> Score -> Risk -> Decision -> Alert`.

## Estado atual confirmado

1. `analysis/analysis_pipeline.py` não executa diretamente as dezenas de camadas novas dos livros. O pipeline oficial continua restrito às engines estabilizadas: MarketRegime, MultiTimeframeAnalysis, MarketStructure, LiquidityAnalysis, VolumeAnalysis, OrderFlow, PriceAction, Smart Money, ContextEngine, StrategyEngine, ScoreEngine, RiskManager e DecisionEngine.
2. `analysis/price_action/price_action.py` integra apenas um subconjunto controlado de Dynamics já incorporado ao PriceActionResult: BarDynamics, BreakoutDynamics, SignalEntryDynamics, ReversalBarDynamics, CompositeSignalDynamics, OutsideBarDynamics, CloseQualityDynamics, ChartPerspectiveDynamics, SecondEntryDynamics, LateEntryDynamics, PatternEvolutionDynamics, TrendLineDynamics, ChannelLineDynamics, ChannelBehaviorDynamics, MicrochannelDynamics e HorizontalSwingDynamics.
3. `core/analysis_context.py` ainda não possui um container específico para os diagnósticos experimentais dos livros. Isso protege o contrato atual do AnalysisContext e evita inflar PriceActionResult com dezenas de campos sem validação estatística.

## Decisão arquitetural

Não integrar os módulos de livros diretamente no PriceActionResult nem no ScoreEngine.

Criar futuramente um container intermediário e isolado, sugerido como `BookDiagnosticsResult`, mantido separado do resultado operacional. O fluxo recomendado é:

`Market/Structure/Regime -> PriceAction oficial -> BookDiagnostics experimental -> Evidence/Context -> Strategy -> Score -> Risk -> Decision`

Nenhum diagnóstico dos livros deve pontuar o ScoreEngine até passar por replay/backtest e demonstrar ganho incremental sem dupla contagem.

## Classificação das camadas

### Nível A — Evidências primárias candidatas à integração futura

São leituras diretamente observáveis no preço e potencialmente úteis como evidência bruta:

- always_in_dynamics
- trend_strength_dynamics
- breakout_strength_dynamics
- second_entry_dynamics (já integrado)
- wedge_pullback_dynamics
- wedge_reversal_dynamics
- major_trend_reversal_dynamics
- climactic_reversal_dynamics
- tight_trading_range_dynamics
- triangle_dynamics
- broad_channel_dynamics
- spike_channel_dynamics
- trend_from_open_dynamics
- opening_pattern_reversal_dynamics
- gap_opening_dynamics
- previous_day_pattern_dynamics

Recomendação: estes são os primeiros candidatos a um experimento de replay, mas inicialmente apenas como `Evidence`, nunca como pontos diretos.

### Nível B — Contexto e regime

Não devem criar entrada sozinhos; servem para modular confiança e contexto:

- key_times_dynamics
- inflexion_time_dynamics
- overnight_session_dynamics
- premarket_pattern_dynamics
- market_suitability_dynamics
- timeframe_chart_dynamics
- higher_timeframe_context_dynamics
- opening_range_dynamics
- trending_range_day_dynamics
- reversal_day_dynamics
- trend_resumption_day_dynamics

Recomendação: integrar futuramente no ContextEngine ou em um `BookContextResult`, com peso limitado e sem veto automático inicialmente.

### Nível C — Síntese / meta-diagnóstico

Recebem ou combinam outras leituras; não podem ser somadas ao Score junto com seus componentes, pois isso causaria dupla contagem:

- breakout_playbook_dynamics
- trading_range_playbook_dynamics
- detailed_day_trading_dynamics
- best_trade_dynamics
- composite_signal_dynamics (já integrado, exige cuidado)
- trader_equation_dynamics
- two_reason_trade_dynamics
- trade_style_dynamics

Recomendação: usar para explicabilidade, ranking e checklist. Não conceder pontos independentes se as evidências-base já pontuam.

### Nível D — Gestão, execução e disciplina

Pertencem a Risk/Execution/Checklist, não ao PriceAction Score:

- stop_entry_dynamics
- limit_entry_dynamics
- protective_trailing_stop_dynamics
- profit_taking_target_dynamics
- scaling_trade_dynamics
- extreme_scalping_dynamics
- option_suitability_dynamics
- trade_trap_dynamics
- trading_guidelines_dynamics

Recomendação: manter fora do ScoreEngine. Validar depois como filtros de risco, alertas ou checklist.

## Duplicações funcionais prioritárias

### Breakout

Há sobreposição entre:
- breakout_dynamics
- breakout_strength_dynamics
- initial_breakout_dynamics
- breakout_failure_test_dynamics
- trend_breakout_entry_dynamics
- breakout_playbook_dynamics
- gap_opening_dynamics

Plano: `breakout_dynamics` deve ser a fonte primária do ciclo de breakout. Os demais devem consumir/interpretar esse resultado em vez de recalcular o mesmo fenômeno.

### Reversal

Há sobreposição entre:
- reversal_bar_dynamics
- reversal_pattern_dynamics
- reversal_strength_dynamics
- reversal_trade_example_dynamics
- major_trend_reversal_dynamics
- failure_reversal_dynamics
- failed_reversal_magnet_dynamics
- climactic_reversal_dynamics

Plano: separar claramente `reversal signal bar`, `reversal structure`, `reversal strength` e `reversal setup family`.

### Timeframe

Há sobreposição entre:
- analysis/multi_timeframe_analysis.py
- timeframe_chart_dynamics
- higher_timeframe_context_dynamics

Plano: `MultiTimeframeAnalysis` deve permanecer como fonte oficial M15/M5/M1. Os diagnósticos Brooks devem consumir seu resultado, não criar uma segunda autoridade de timeframe.

### Sessão / abertura

Há sobreposição entre:
- key_times_dynamics
- inflexion_time_dynamics
- overnight_session_dynamics
- premarket_pattern_dynamics
- previous_day_pattern_dynamics
- opening_pattern_reversal_dynamics
- opening_range_dynamics
- gap_opening_dynamics
- trend_from_open_dynamics

Plano: criar futuramente um `SessionContext` único com níveis e fase da sessão, evitando cada módulo recalcular horários e níveis.

### Trade quality

Há sobreposição entre:
- best_trade_dynamics
- trader_equation_dynamics
- two_reason_trade_dynamics
- trading_guidelines_dynamics
- risk/trade_quality.py
- models/trade_checklist.py

Plano: a autoridade final de risco continua sendo RiskManager. Os módulos Brooks devem alimentar checklist/explicabilidade e só virar veto depois de validação estatística.

## Riscos detectados

1. Dupla contagem de evidências se módulos compostos e módulos-base entrarem simultaneamente no ScoreEngine.
2. Explosão do schema do `PriceActionResult` se todas as camadas forem adicionadas diretamente.
3. Autoridades concorrentes para tendência, breakout, reversão e multi-timeframe.
4. Recalcular as mesmas séries de candles dezenas de vezes em cada loop pode aumentar custo e latência.
5. Alguns módulos de livro são pedagógicos/contextuais, não sinais operacionalizáveis.
6. Integração sem replay pode melhorar cenários controlados e piorar dados reais por overfitting conceitual.

## Arquitetura proposta RC seguinte

### Passo 1 — BookDiagnosticsResult

Criar um resultado isolado com grupos, não dezenas de campos soltos:

- `trend`
- `breakout`
- `reversal`
- `range`
- `session`
- `execution`
- `discipline`

Cada grupo deve conter somente `status`, `direction`, `quality`, `flags` e `reasons` padronizados.

### Passo 2 — BookDiagnosticsEngine

Criar uma engine diagnóstica com prioridade após PriceAction e antes de ContextEngine. Inicialmente `ENABLED=False` ou `score_enabled=False`.

### Passo 3 — Adapter/normalização

Cada módulo Brooks deve ser adaptado para um contrato comum, evitando formatos heterogêneos de dict/dataclass e nomes diferentes para a mesma ideia.

### Passo 4 — Replay A/B

Comparar:

- baseline atual
- baseline + uma família diagnóstica por vez
- baseline + combinações aprovadas

Métricas mínimas:

- precisão direcional
- taxa de WAIT correta
- falso positivo
- expectativa em R
- drawdown
- estabilidade por regime
- estabilidade M15/M5/M1

### Passo 5 — Promoção gradual

Somente módulos que provarem ganho incremental devem ser promovidos na ordem:

`Diagnostics -> Evidence -> Context/Checklist -> Score/Risk`

Nunca promover vários módulos correlacionados ao mesmo tempo.

## Primeira shortlist para experimento

Prioridade 1:
- AlwaysInDynamics
- TrendStrengthDynamics
- BreakoutStrengthDynamics
- MajorTrendReversalDynamics
- WedgeReversalDynamics
- TightTradingRangeDynamics

Prioridade 2:
- KeyTimesDynamics
- GapOpeningDynamics
- PreviousDayPatternDynamics
- OpeningPatternReversalDynamics
- HigherTimeframeContextDynamics

Prioridade 3:
- TradingGuidelinesDynamics
- BestTradeDynamics
- TraderEquationDynamics

## Conclusão

A biblioteca Brooks foi incorporada com segurança porque permaneceu majoritariamente desacoplada do núcleo. O próximo avanço deve ser arquitetural, não quantitativo: criar `BookDiagnosticsResult + BookDiagnosticsEngine`, padronizar as saídas e então iniciar experimentos A/B de uma família por vez.

Não alterar ScoreEngine, RiskManager ou DecisionEngine nesta fase.