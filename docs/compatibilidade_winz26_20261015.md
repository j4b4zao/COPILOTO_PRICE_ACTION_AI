# Auditoria de aquisição — 15/10/2026

Escopo: verificação da mudança informada de WINV26 para WINZ26, sem ampliar a RC3.18.3.3K. Inspeção estática de connectors, market_data, config, app e ferramentas Python relacionadas. Nenhum arquivo histórico, workbook, código de aquisição ou lógica de rollover foi alterado nesta auditoria. Alterações locais preexistentes foram preservadas.

## Compatibilidade com WINZ26

O ProfitReader é compatível por inspeção: `connectors/profit_reader.py:45` obtém `ativo` diretamente da coluna A da linha configurada (A2 por padrão). Não existe filtro fixo WINV26 nesse leitor, nos conectores ou em market_data/config pesquisados. A leitura ocorre a cada chamada; não há cache do símbolo. Isso confirma o comportamento do código, sem confirmar o conteúdo atual do Excel por conexão real.

`market_data/profit_rtd_workbook_reader.py:64–74` normaliza o símbolo e rejeita divergência entre o solicitado e o presente no workbook. Book e Times & Trades precisam corresponder ao contrato solicitado; atualizar apenas a cotação não demonstra que as demais fontes estejam alinhadas.

### Referências fixas com efeito operacional

| Arquivo e linha | Efeito |
| --- | --- |
| `app/profitdll_book_test.py:26` | Default de assinatura WINV26 no utilitário DLL quando `--symbol` é omitido. |
| `tools/profit_rtd_brooks_collection_preflight.py:18,73` | Default WINV26 na função e na CLI de preflight. |
| `tools/profit_rtd_brooks_readiness_report.py:20,76` | Default WINV26 na função e na CLI de readiness. |
| `tools/profit_rtd_brooks_smoke_report.py:33,152` | Default WINV26 na função e na CLI de smoke report. |

Esses defaults não substituem A2 no ProfitReader, mas podem solicitar ou validar o contrato antigo nas ferramentas auxiliares. Para WINZ26, o parâmetro explícito evita o default. Nenhuma dessas ferramentas foi executada.

Referências em exemplos, fixtures e seleções históricas foram preservadas. Em particular, os validadores das sessões 11/12 e as listas de sessões antigas não devem receber substituição global de símbolo.

### Isolamento e limitações existentes

- Deduplicação da cotação: `market_data/profit_source_integrity.py:21–29,38–46` inclui ativo no fingerprint e detecta troca de símbolo.
- Deduplicação T&T: `market_data/profit_rtd_times_trades_deduplicator.py:49–52` estabelece nova baseline com SYMBOL_RESET, sem emitir negócios antigos como novos.
- OrderFlow RTD: `market_data/profit_rtd_order_flow_state_adapter.py:54–72` zera cumulativos e limpa o estado na troca. O caminho legado limpa OrderFlow em `market_data/collector.py:159–160`.
- Candles: `core/multi_timeframe_state.py:124–140` reutiliza os builders e mercados sem reset por símbolo nessa atualização. `core/market_state.py:61` substitui o rótulo do ativo. Uma troca dentro da mesma instância pode conservar candles/estado do contrato anterior.
- Renko: `core/renko_state.py:90–105` inicializa pelo estado de preço existente, sem condição de troca de símbolo nessa entrada; uma instância já aquecida pode conservar estado anterior.
- Volume: `market_data/collector.py:108–109,126,316–322` resolve e retém o último volume válido antes de identificar o ativo. Se o primeiro volume de WINZ26 for inválido após WINV26, pode reutilizar o volume do contrato antigo.

Assim, a compatibilidade de leitura está confirmada estaticamente, mas o isolamento completo em troca de contrato na mesma instância NÃO está confirmado. Para aquisição WINZ26, usar uma sessão nova, com estados novos, fontes alinhadas e saídas separadas das de WINV26. Não reutilizar uma instância aquecida em WINV26. Corrigir os pontos acima exigiria trabalho adicional sobre transição/isolamento, não realizado nesta etapa.

### Validação

Nenhuma conexão ao Excel ou Profit foi iniciada. A tentativa de executar verificações com objetos falsos não chegou a executar Python: o alias `python.exe` está inacessível, e `py -0p` informou que não há instalações Python. Portanto, não há resultado de testes executados; as conclusões são de inspeção estática.

Somente este relatório foi criado. Não houve migração, concatenação, renomeação ou reprocessamento de dados WINV26/WINZ26, nem mudança da lógica de rollover ou do escopo funcional da RC3.18.3.3K.
