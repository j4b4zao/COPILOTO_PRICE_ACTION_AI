# RC13.6 — Sprint 2: Migração do grupo EngineBase

## Implementação oficial

`ai.engine_base.EngineBase` é a única implementação oficial da RC13. Ela
define o contrato `executar(context: AnalysisContext) -> AnalysisContext`, os
metadados `NAME`, `VERSION`, `ENABLED`, `PRIORITY` e os hooks opcionais.

`core.engine_base.EngineBase` foi mantida somente para compatibilidade e está
marcada com `# LEGACY - DO NOT USE`.

## Arquivos alterados

- `core/engine_base.py`: marcação explícita da implementação legada.
- `RC13_ENGINEBASE_MIGRATION_REPORT.md`: relatório desta etapa.

## Imports atualizados

Nenhum import precisou ser alterado: todos os 17 imports explícitos de
`EngineBase` já apontavam para `ai.engine_base`.

Subclasses RC13 confirmadas:

```text
ScoreEngine, AlertManager, MarketRegime, MarketStructure,
LiquidityAnalysis, VolumeAnalysis, PriceAction, SmartMoneyEngine,
OrderBlock, LiquidityPool, Imbalance, FairValueGap, EvidenceEngine,
StrategyEngine, RiskManager, DecisionEngine e ExecutionEngine.
```

## Validação

- Sintaxe: todos os 219 arquivos Python do projeto analisados por AST.
- Imports: `ai.engine_base`, `core.engine_base` e todas as subclasses foram
  importados com sucesso.
- Herança: cada uma das 17 subclasses foi validada com
  `issubclass(classe, ai.engine_base.EngineBase)`.
- Escopo: não há import ativo de `core.engine_base`.

## Riscos encontrados

- A cópia legada possui `execute(context)` com medição de tempo, recurso ausente
  na base oficial. Não há uso estático de `.execute(...)`, mas consumidores
  externos ou dinâmicos precisam ser confirmados antes da remoção.
- O cabeçalho histórico de `core/engine_base.py` indicava incorretamente
  `ai/engine_base.py`; ele foi substituído pela marcação de legado.

## Próximos passos

1. Monitorar por uma release qualquer import externo de `core.engine_base`.
2. Decidir se a medição de tempo legada deve ser absorvida por infraestrutura
   separada, como `EngineProfiler`, sem reintroduzir uma segunda base.
3. Após validação externa, remover `core/engine_base.py` em uma sprint dedicada.
