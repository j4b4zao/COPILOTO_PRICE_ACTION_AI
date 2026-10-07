# FMP Real Freshness Validation — 2026-10-07

Ferramenta: `FMPQuoteVsIntraday1MinFreshnessComparator RC1`

- `diagnostic_only=true`
- `operational_influence_allowed=false`
- `reference_timestamp=2026-10-07T13:56:25+00:00`
- `maximum_staleness_seconds=3600`

## FMP /stable/quote

| Símbolo | price | change | timestamp | age_seconds | status |
| --- | ---: | ---: | --- | ---: | --- |
| ^GSPC | 7775.55 | -0.55481 | 2026-10-07T13:56:26+00:00 | -1 | FUTURE |
| ^IXIC | 27403.604 | -0.71117 | 2026-10-07T13:56:28+00:00 | -3 | FUTURE |
| ^VIX | 15.66 | 4.33045 | 2026-10-07T13:56:16+00:00 | 9 | FRESH |

## FMP /stable/historical-chart/1min

- `^GSPC -> HTTP 402`
- `^IXIC -> HTTP 402`
- `^VIX -> HTTP 402`

## Decisões arquiteturais

1. `/stable/quote` demonstrou timestamps praticamente contemporâneos durante esta execução real.
2. A evidência anterior de dados STALE não deve ser atribuída a erro de conversão de timestamp do nosso `FMPQuoteTransport`.
3. `/stable/historical-chart/1min` não está disponível para a credencial/plano utilizado nesta validação (HTTP 402).
4. NÃO promover `historical-chart/1min`.
5. NÃO criar fallback automático quote -> intraday.
6. Manter `maximum_staleness_seconds=3600`.
7. Manter política fail-closed: qualquer `age_seconds < 0` continua FUTURE.
8. Portanto -1 segundo e -3 segundos continuam FUTURE. NÃO implementar tolerância de clock nesta etapa.
9. `age_seconds=9` continua FRESH.
10. Esta camada continua estritamente observacional/diagnóstica.
11. Nenhuma influência em Score, Risk, Decision, Alert, ordens ou `Bot.mostrar`.
12. Nenhuma ativação automática.
13. Nenhuma conclusão de direção para WIN deve ser derivada desta validação.

## Remaining Issues

- DXY continua sem fonte exata gratuita aprovada.
- US10Y continua sem fonte intraday exata gratuita aprovada.
- OIL ainda precisa de validação adicional de freshness.
- Pequenos timestamps FUTURE da FMP permanecem classificados estritamente como FUTURE até existir evidência suficiente para qualquer política diferente.

## Validated Tests Before This Checkpoint

30 passed no gate combinado:

- `tests/test_fmp_quote_vs_intraday_1min_probe_rc1.py`
- `tests/test_fmp_index_freshness_probe_rc1.py`
