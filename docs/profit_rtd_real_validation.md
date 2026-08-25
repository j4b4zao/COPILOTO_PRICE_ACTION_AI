# Profit RTD — roteiro de validação em pregão real

Este roteiro valida a fonte deduplicada de Times & Trades RTD sem alterar o comportamento oficial do Score/Decision.

## Pré-condições

- `ENABLE_PROFIT_RTD_ORDER_FLOW = False` continua sendo o default do projeto.
- `ENABLE_ORDER_FLOW_SCORE = False` deve permanecer desativado durante a validação.
- O teste real só deve ser feito após confirmar que `Profit.xlsx`, Livro de Ofertas e Times & Trades estão atualizando via RTD.

## Ativação manual para a sessão

1. Alterar temporariamente `ENABLE_PROFIT_RTD_ORDER_FLOW = True` em `config/settings.py`.
2. Não alterar `ENABLE_ORDER_FLOW_SCORE`.
3. Executar o sistema normalmente.
4. Observar os logs `[PROFIT RTD VALIDATION]`, `[DELTA SOURCE]` e `[DELTA QUALITY]`.

## O que deve ser observado

- crescimento de `cycles`;
- crescimento de `new_trades` durante atividade de mercado;
- `updates` coerentes com novos negócios deduplicados;
- continuidade majoritariamente `CONTIGUOUS`;
- ausência de repetidos `OVERLAP_LOST_REBASE`;
- resets apenas quando esperados, por baseline ou troca de ativo;
- nenhuma alteração de Score/Decision/execution decorrente da fonte RTD.

## Encerramento

Ao final da sessão, usar `ProfitRTDSessionCloseUtility` ou `Collector.export_profit_rtd_validation_session(...)` para salvar o JSON de validação.

O arquivo exportado deve ser preservado junto com o SHA-256 retornado pelo recibo.

## Critério RC13

Avaliar o snapshot com `ProfitRTDValidationAcceptanceEvaluator`.

- `PASS`: critérios mínimos configurados atendidos.
- `REVIEW`: amostra curta, poucos negócios, baixa taxa de update ou continuidade abaixo do alvo sem violação grave.
- `FAIL`: quebra excessiva de continuidade ou qualquer capacidade operacional indevida.

O resultado `PASS` não altera automaticamente nenhuma feature flag. Qualquer promoção do RTD para default ou integração com Score exige RC separado e comparação com dados reais.

## Pós-sessão

Restaurar `ENABLE_PROFIT_RTD_ORDER_FLOW = False` até que a validação real e a comparação com a fonte legada sejam revisadas e aprovadas.
