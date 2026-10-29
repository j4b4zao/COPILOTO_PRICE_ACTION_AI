# FMP index freshness — evidência real de 2026-10-07

Diagnóstico observacional RC1. Evidência fornecida pelo operador, obtida durante
o pregão; esta auditoria não repetiu a consulta real nem validou um artefato bruto.

Referência explícita: `2026-10-07T13:56:25+00:00`.
`maximum_staleness_seconds = 3600`, sem alteração.

| Símbolo | /stable/quote price | change (changePercentage) | Timestamp UTC | age_seconds | Status | /stable/historical-chart/1min |
| --- | ---: | ---: | --- | ---: | --- | --- |
| ^GSPC | 7775.55 | -0.55481 | 2026-10-07T13:56:26+00:00 | -1 | FUTURE | HTTP 402 |
| ^IXIC | 27403.604 | -0.71117 | 2026-10-07T13:56:28+00:00 | -3 | FUTURE | HTTP 402 |
| ^VIX | 15.66 | 4.33045 | 2026-10-07T13:56:16+00:00 | 9 | FRESH | HTTP 402 |

## Constatações e decisão atual

Nesta amostra, `/stable/quote` forneceu timestamps praticamente em tempo real
durante o pregão. Isso não garante freshness em outras consultas ou horários.
O endpoint 1min não esteve disponível para a credencial/plano atual: HTTP 402
nos três índices. Não promover esse endpoint nem usá-lo como fallback.

Manter classificação estrita: qualquer `age_seconds < 0` é `FUTURE`, inclusive
-1 e -3 segundos. Zero até 3600 segundos, inclusive, é `FRESH`; acima de 3600 é
`STALE`. Nenhuma tolerância futura foi autorizada ou implementada.

Os dois probes classificam estritamente; `FMPQuoteTransport` apenas normaliza
o timestamp Unix para UTC e não calcula freshness. O comparador consulta as
duas fontes por finalidade diagnóstica, independentemente do status do quote,
e mantém os resultados separados. Ele não substitui quote por intraday.
HTTP 402 permanece `{"status": "HTTP_ERROR", "http_status": 402}` no campo
intraday; quote indisponível permanece `null` no comparador.

Nenhuma influência operacional, integração automática, sinal BUY/SELL,
alteração de ordens ou modificação dos módulos operacionais. Threshold de 3600
segundos preservado; nenhuma promoção do endpoint 1min.

## Limites da evidência

Pequenos FUTURE podem envolver diferença de relógios ou a referência capturada
antes das respostas sequenciais, mas a causa não foi estabelecida. Não inferir
autorização para tolerância. Timestamps intraday sem offset continuam
`AMBIGUOUS_TIMEZONE`, sem assumir timezone nem calcular freshness.

## Validação offline

Testes cobrem -1, -3, 0, 9, 3600 e 3601 segundos nos dois diagnósticos e em
ambas as fontes do comparador. Também cobrem HTTP 402 e ausência de substituição
do quote FUTURE, STALE ou indisponível, mesmo com intraday FRESH.

```powershell
python -m pytest tests/test_fmp_quote_vs_intraday_1min_probe_rc1.py tests/test_fmp_index_freshness_probe_rc1.py tests/test_fmp_quote_transport_rc1.py tests/test_external_per_asset_provider_configuration_rc1.py -q
```
