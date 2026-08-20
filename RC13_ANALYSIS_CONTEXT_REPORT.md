# RC13.6 — Sprint 4: Consolidação de AnalysisContext

## Implementação oficial

`core.analysis_context.AnalysisContext` é o único contrato oficial RC13 para
comunicação entre collector, engines e resultados. É um dataclass com `slots`
e expõe resultados tipados por domínio.

Contratos paralelos preservados, mas marcados como legados:

- `models.market_context.MarketContext`;
- `core.analysis_result.AnalysisResult`;
- `analysis.analysis_result.AnalysisResult`.

`context/context_builder.py` ainda referencia `MarketContext`, mas não tem
consumidor estático e usa atributos incompatíveis com o contexto RC13. O import
não foi redirecionado para evitar alteração de regra de negócio.

## Dependências RC13

- `market_data/collector.py`: instancia e retorna `AnalysisContext`.
- `analysis/analysis_pipeline.py`: instancia o contexto compartilhado.
- `ai/engine_base.py` e `analysis/smart_money/smart_money_engine.py`: usam o
  tipo `AnalysisContext` nas assinaturas.
- Engines RC13, estratégias, logs, monitor e replay consomem campos de
  `context` diretamente.
- `models.market_result.MarketResult` é alias de
  `core.market_state.MarketState`.

## Resultados utilizados

| Campo de AnalysisContext | Tipo | Herda ResultBase |
|---|---|---|
| `structure` | `StructureResult` | Sim |
| `liquidity` | `LiquidityResult` | Sim |
| `volume` | `VolumeResult` | Sim |
| `price_action` | `PriceActionResult` | Sim |
| `imbalance` | `ImbalanceResult` | Sim |
| `order_block` | `OrderBlockResult` | Sim |
| `fair_value_gap` | `FairValueGapResult` | Sim |
| `liquidity_pool` | `LiquidityPoolResult` | Sim |
| `context` | `ContextResult` | Sim |
| `evidence` | `EvidenceResult` | Sim |
| `strategy` | `StrategyResult` | Sim |
| `score` | `ScoreResult` | Sim |
| `risk` | `RiskResult` | Sim |
| `decision` | `DecisionResult` | Sim |
| `alert` | `AlertResult` | Sim |

`market` não herda `ResultBase`: é exclusivamente
`core.market_state.MarketState`, por meio do alias `MarketResult`.

## Impacto e riscos

- **Alto:** `AnalysisContext` usa `slots`; engines legadas que escrevem
  atributos dinâmicos não podem ser conectadas sem migração explícita.
- **Alto:** `analysis/market_regime.py` espera `context.regime`, campo ainda
  ausente do contexto oficial. Isso é uma lacuna pré-existente de modelagem.
- **Médio:** `ContextBuilder` e `MarketContext` mantêm um contrato paralelo de
  resultados registrados por tipo; não devem ser misturados ao contexto tipado.
- **Baixo:** todos os 15 resultados declarados no contexto herdam `ResultBase`
  e possuem `clear()`, compatível com `AnalysisContext.clear_results()`.

## Validação

- Sintaxe: 219 arquivos Python analisados por AST sem erros.
- Imports: `AnalysisContext`, `MarketState`, todos os 15 ResultBase e as engines
  RC13 foram importados com sucesso.
- Contexto: `AnalysisContext().market` é `core.market_state.MarketState` e cada
  resultado declarado é instanciado no tipo esperado.
- Compatibilidade: `clear_results()` foi executado e todos os resultados
  permaneceram utilizáveis.

Durante a validação, os métodos `clear()` de `ImbalanceResult`,
`FairValueGapResult` e `LiquidityPoolResult` falharam ao usar `super()` com
dataclasses `slots=True`. Foram ajustados para a chamada equivalente e explícita
`ResultBase.clear(self)`, sem mudar a regra de limpeza.

## Próximos passos

1. Decidir se `RegimeResult` será incorporado a `AnalysisContext` antes de ativar
   `MarketRegime` no fluxo RC13.
2. Migrar ou aposentar `ContextBuilder` e `MarketContext` em uma sprint isolada.
3. Migrar os dois `AnalysisResult` legados para consumidores tipados antes de
   removê-los.
