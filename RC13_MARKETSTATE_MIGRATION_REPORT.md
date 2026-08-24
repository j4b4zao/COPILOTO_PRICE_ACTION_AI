# RC13.6 — Sprint 3: Migração do grupo MarketState / MarketResult

## Implementação oficial

- `core.market_state.MarketState` é a única implementação oficial de estado de mercado da RC13.
- `models.market_result.MarketResult` permanece como alias de compatibilidade para `core.market_state.MarketState`.
- `market.market_state.MarketState` foi mantida, mas está marcada com `# LEGACY - DO NOT USE`.

## Arquivos alterados

- `market/market_state.py`: marcação explícita da versão legada.
- `core/analysis.py`: import direcionado para `core.market_state`.
- `core/copilot.py`: import direcionado para `core.market_state`.
- `teste_integracao.py`: import direcionado para `core.market_state`.
- `RC13_MARKETSTATE_MIGRATION_REPORT.md`: relatório desta etapa.

## Dependências afetadas

Consumidores oficiais preservados:

- `core/analysis_context.py` usa `models.market_result.MarketResult`.
- `models/market_result.py` aponta para `core.market_state.MarketState`.
- `market_data/collector.py` atualiza `AnalysisContext.market` pelo contrato oficial.
- `models/market_context.py` já usa `core.market_state.MarketState`.
- As engines RC13 consomem `context.market` e permanecem no mesmo tipo.

Consumidores migrados nesta sprint: `core/analysis.py`, `core/copilot.py` e `teste_integracao.py`.

## Impacto e riscos

- **Alto:** `core/analysis.py`, `core/copilot.py` e `teste_integracao.py` são fluxos legados e invocam métodos/atributos como `atualizar`, `data`, `hora`, `negocios` e `mostrar`, que não fazem parte de `core.market_state.MarketState`. Os imports agora são canônicos, mas esses fluxos precisam de uma migração de contrato própria antes de execução.
- **Médio:** a classe legada possui parâmetros extras em `update(...)`, incluindo `new_candle`; nenhum consumidor RC13 deve depender deles.
- **Baixo:** `MarketResult` é alias, não uma segunda implementação; portanto `AnalysisContext` mantém compatibilidade de tipo e criação padrão.

## Validação

- Sintaxe dos 219 arquivos Python analisada por AST sem erros.
- Nenhum import ativo de `market.market_state` permanece no workspace.
- `AnalysisContext().market` foi confirmado como instância de `core.market_state.MarketState` e de `models.market_result.MarketResult`.
- As 17 engines RC13 continuam importáveis e recebem o mesmo `context.market`.

## Próximos passos

1. Migrar os fluxos legados de `core/analysis.py` e `core/copilot.py` para o contrato `AnalysisContext` em sprint dedicada.
2. Substituir `teste_integracao.py` por um teste de integração RC13 que use `Collector` e `AnalysisContext`.
3. Após confirmar consumidores externos, remover `market/market_state.py` em uma release posterior.
