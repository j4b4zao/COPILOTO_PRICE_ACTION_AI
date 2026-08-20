# RC13.6 — Plano Oficial de Migração

Baseado em `RC13_DUPLICATION_REPORT.md`. Este plano não altera código e usa
apenas dependências estáticas observadas no workspace. Antes de remover um
módulo legado, validar também consumidores externos, imports dinâmicos e
scripts operacionais fora do repositório.

## Padrão de execução de cada etapa

1. Criar testes de caracterização para a implementação que será preservada.
2. Migrar consumidores para a implementação oficial indicada.
3. Executar validação da etapa e manter o legado disponível por uma release.
4. Remover o legado somente após uma release sem acessos e com rollback testado.

Rollback padrão: reverter o commit da etapa; se houver persistência ou contrato
externo, reintroduzir temporariamente o import/adapter legado sem mesclar regras
de negócio entre as duas versões.

## Ordem recomendada

1. Bases e contratos: `EngineBase`, `Trend`, `MarketState`, `Result`.
2. Dados de entrada: `DataValidator`.
3. Eventos e contexto: `Event`, `ContextEngine`, `MarketRegime`.
4. Estratégias e setups: `SetupBase`, `TrendPullback`, `StrategyResult`.
5. Engines analíticas: `SmartMoneyEngine`, `PremiumDiscount`, `SetupDetector`.
6. Fluxos periféricos: `TradeManager`, `ConfigManager`, `AnalysisResult`.
7. Só então descontinuar arquivos órfãos e pipelines legados.

## Plano por grupo duplicado

### 1. EngineBase

- Oficial RC13: `ai/engine_base.py`.
- Legada: `core/engine_base.py`.
- Dependentes oficiais: `ai/score_engine.py`, `alerts/alert_manager.py`,
  `analysis/market_regime.py`, `analysis/market_structure.py`,
  `analysis/liquidity_analysis.py`, `analysis/volume_analysis.py`,
  `analysis/price_action/price_action.py`, `analysis/smart_money/*.py`,
  `brain/evidence_engine.py`, `decision/decision_engine.py`,
  `execution/execution_engine.py`, `risk/risk_manager.py` e
  `strategies/strategy_engine.py`.
- Dependentes legados: nenhum import estático de `core/engine_base.py`.
- Impacto: unifica o contrato `executar(context)`, metadados e hooks das engines.
- Risco: **Alto** — é a raiz da hierarquia RC13.
- Validação: importar todas as engines; verificar `issubclass(EngineBase)` e
  executar testes de pipeline com engines habilitadas/desabilitadas.
- Rollback: restaurar `core/engine_base.py` e os imports antigos, sem modificar
  o contrato da versão `ai`.

### 2. ContextEngine

- Oficial RC13: `brain/context_engine.py` é a candidata, pois é importada por
  `analysis/analysis_pipeline.py` e `core/engine_manager.py`.
- Legada: `context/context_engine.py`, sem import estático.
- Arquivos dependentes: `analysis/analysis_pipeline.py`, `core/engine_manager.py`.
- Impacto: a candidata deve receber `AnalysisContext`, produzir
  `ContextResult` e herdar `EngineBase`; hoje opera sobre atributos legados de
  `market`.
- Risco: **Alto** — participa da sequência de execução, mas o contrato atual é
  incompatível com RC13.
- Validação: cenários de tendência, reversão e lateralização; confirmar campos
  `context.context.market_state`, `bias`, `score`, `confidence` e `valid`.
- Rollback: manter o módulo legado isolado; reverter somente o registro da
  candidata se os resultados divergirem.

### 3. MarketState

- Oficial RC13: `core/market_state.py`.
- Legada: `market/market_state.py`.
- Dependentes oficiais: `market_data/collector.py` por meio de `AnalysisContext`,
  `models/market_result.py` e `models/market_context.py`.
- Dependentes legados: `core/analysis.py`, `core/copilot.py`,
  `teste_integracao.py`.
- Impacto: o legado usa atualização e atributos diferentes; consumidores devem
  migrar para `symbol`, `last_price`, `candles`, `ready` e `update(...)` RC13.
- Risco: **Alto** — é o objeto de dados central.
- Validação: coleta de candle, histórico, `ready`, preço e reset de mercado.
- Rollback: preservar um adapter de leitura para `market/market_state.py` por
  uma release; não converter dados por cópia silenciosa.

### 4. DataValidator

- Oficial RC13: `core/data_validator.py` (`DataValidator.validate`).
- Legada: `validation/data_validator.py` (`validar(dados)`).
- Dependentes oficiais: `market_data/collector.py`.
- Dependentes legados: `core/system_initializer.py` instancia a versão legada.
- Impacto: há divergência de assinatura e de ponto de uso; o inicializador deve
  deixar de expor uma instância incompatível ou receber um adapter explícito.
- Risco: **Alto** — risco de aceitar/rejeitar dados de mercado de forma diferente.
- Validação: matriz OHLCV inválida/válida, símbolo vazio e volume negativo.
- Rollback: manter a validação legada apenas como adapter com testes comparativos.

### 5. SetupBase

- Oficial RC13: `strategies/setups/setup_base.py`.
- Legada: `strategies/setup_base.py`.
- Dependentes oficiais: `strategies/setups/trend_pullback.py`,
  `strategies/setups/trend_breakout.py`, `strategies/setups/liquidity_sweep.py`,
  `strategies/setup_registry.py` e `strategies/strategy_engine.py`.
- Dependentes legados: `strategies/trend_pullback.py`.
- Impacto: consolida retorno em `StrategyResult` para os setups carregados pelo
  `SetupRegistry`.
- Risco: **Médio** — a árvore oficial já está isolada.
- Validação: ordenação de setups, prioridade, setup inválido e escolha do melhor.
- Rollback: restaurar apenas o import de `strategies/trend_pullback.py`.

### 6. AnalysisResult

- Oficial RC13: nenhuma.
- Legadas: `analysis/analysis_result.py` e `core/analysis_result.py`.
- Dependentes: nenhum import estático.
- Impacto: decidir se o conceito é substituído por `AnalysisContext` ou removido.
- Risco: **Baixo**.
- Validação: busca textual e importação completa do projeto.
- Rollback: restaurar os dois arquivos sem alterar consumidores RC13.

### 7. ConfigManager

- Oficial RC13: nenhuma.
- Legadas: `config/config_manager.py` e `optimization/config_manager.py`.
- Dependentes: nenhum import estático; pertencem a fluxos isolados.
- Impacto: definir um único contrato de configuração antes de consolidar.
- Risco: **Médio** — pode envolver arquivos persistidos.
- Validação: carregar/salvar configurações existentes sem alteração de formato.
- Rollback: preservar ambos os caminhos de arquivo e reverter o adaptador.

### 8. Event

- Oficial RC13: `core/event.py`.
- Legada: `core/events.py`.
- Dependentes oficiais: `analysis/analysis_pipeline.py`; `core/event_bus.py`
  consome objetos com `type`.
- Dependentes legados: nenhum para `core/events.py`.
- Impacto: normalizar todos os publicadores para o dataclass `Event(type, data)`.
- Risco: **Médio** — eventos podem ter consumidores externos.
- Validação: publicar cada `EventType`, confirmar entrega e conteúdo do payload.
- Rollback: manter alias de import para `core.events.Event` durante uma release.

### 9. MarketRegime

- Oficial RC13: `analysis/market_regime.py`.
- Legada: `market/market_regime.py`.
- Dependentes oficiais: `core/engine_manager.py`.
- Dependentes legados: nenhum import estático.
- Impacto: a versão oficial precisa de `context.regime`, que ainda não existe em
  `AnalysisContext`; resolver esse contrato antes de remover a legada.
- Risco: **Alto** — a engine é registrada, mas o resultado não possui destino.
- Validação: contextos de alta, baixa e range com resultado `RegimeResult`.
- Rollback: desregistrar a engine oficial ou restaurar o estado anterior; não
  executar simultaneamente as duas versões.

### 10. PremiumDiscount

- Oficial RC13: nenhuma.
- Legadas: `analysis/premium_discount.py`, `zones/premium_discount.py`.
- Dependentes: `core/analysis.py` importa a versão `analysis`; a versão `zones`
  não tem import estático.
- Impacto: decidir se o resultado deve ganhar tipo próprio no `AnalysisContext`.
- Risco: **Médio** — não integra a pipeline RC13.
- Validação: zonas premium, discount, equilíbrio e dados incompletos.
- Rollback: manter a implementação chamada por `core/analysis.py` intacta.

### 11. SetupDetector

- Oficial RC13: nenhuma.
- Legadas: `analysis/setup_detector.py` e
  `analysis/price_action/setups/setup_detector.py`.
- Dependências: o detector aninhado usa `PullbackSetup`; ambos não possuem
  consumidores estáticos.
- Impacto: decidir se a detecção deve permanecer no `StrategyEngine`/`SetupRegistry`
  ou ser eliminada.
- Risco: **Baixo**.
- Validação: garantir que `StrategyEngine` continua encontrando os três setups RC13.
- Rollback: nenhuma alteração de produção até existir consumidor confirmado.

### 12. SmartMoneyEngine

- Oficial RC13: `analysis/smart_money/smart_money_engine.py`.
- Legada: `analysis/smart_money_engine.py`.
- Dependentes: as engines RC13 concretas importam diretamente `EngineBase`, não
  a base `SmartMoneyEngine`; a versão legada não tem import estático.
- Impacto: decidir se as engines concretas devem herdar da base RC13 ou se a base
  deve ser removida; não combinar o resultado dinâmico `market.smart_money` com
  resultados tipados sem migração explícita.
- Risco: **Médio**.
- Validação: FVG, imbalance, order block e liquidity pool em candles conhecidos.
- Rollback: manter as engines concretas independentes e reverter apenas a herança.

### 13. StrategyResult

- Oficial RC13: `models/strategy_result.py`.
- Legada: `strategies/strategy_result.py`.
- Dependentes oficiais: `core/analysis_context.py`, `strategies/strategy_engine.py`
  e os três setups em `strategies/setups/`.
- Dependentes legados: nenhum para `strategies/strategy_result.py`.
- Impacto: consolidar atributos, limpeza e validade em `ResultBase`.
- Risco: **Médio** — resultado é consumido por score, risco, decisão e log.
- Validação: setup válido/inválido, score, razões e reset do contexto.
- Rollback: restaurar import de resultado legado apenas para consumidores legados.

### 14. TradeManager

- Oficial RC13: nenhuma.
- Legadas: `trade/trade_manager.py`, `replay/trade_manager.py`.
- Dependentes: não há import estático; `replay` usa também `TradeSimulator`.
- Impacto: separar claramente operação real e replay antes de compartilhar código.
- Risco: **Médio** — possível impacto financeiro/simulação.
- Validação: abertura, fechamento, P&L e repetição de sinais em replay.
- Rollback: restaurar a implementação específica de cada fluxo.

### 15. Trend

- Oficial RC13: `enums/trend.py`.
- Legada: `models/enums.py::Trend`.
- Dependentes oficiais: `analysis/market_structure.py`,
  `analysis/price_action/price_action.py`, `analysis/market_regime.py`,
  `models/structure_result.py`, `models/price_action_result.py` e setups RC13.
- Dependentes legados: `models/swing.py` e `analysis/swing_detector.py` usam
  outros enums de `models/enums.py`.
- Impacto: não migrar todo `models/enums.py`; extrair apenas `Trend` após garantir
  igualdade de valores e comparações.
- Risco: **Alto** — enum influencia ramificações de tendência.
- Validação: equivalência dos valores UP/DOWN/SIDEWAYS/UNKNOWN e cenários de BOS.
- Rollback: manter conversor temporário entre os dois enums.

### 16. TrendPullback

- Oficial RC13: `strategies/setups/trend_pullback.py`.
- Legada: `strategies/trend_pullback.py`.
- Dependentes oficiais: `strategies/setup_registry.py` e `StrategyEngine`.
- Dependentes legados: nenhum import estático.
- Impacto: preservar o setup RC13 com `StrategyResult`; descontinuar o retorno
  legado somente após testes de estratégia equivalentes.
- Risco: **Médio**.
- Validação: cenários de pullback de compra, venda e ausência de setup.
- Rollback: restaurar o registro anterior e manter os dois módulos separados.

## Critérios globais de conclusão

- Todos os imports apontam para implementações oficiais ou adapters declarados.
- Não há duas definições ativas do mesmo contrato no fluxo RC13.
- `AnalysisContext`, `ResultBase` e `ai.EngineBase` são os únicos contratos
  compartilhados pelas engines RC13.
- Testes de caracterização e de integração passam para coleta, análise, estratégia,
  score, risco, decisão, eventos e replay.
- A busca estática não encontra consumidores das versões legadas antes de removê-las.
- Cada remoção ocorre em commit isolado, com rollback testado.
