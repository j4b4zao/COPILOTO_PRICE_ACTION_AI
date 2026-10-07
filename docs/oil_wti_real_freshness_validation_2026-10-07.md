# OIL / WTI Real Freshness Validation — 2026-10-07

## Scope and Evidence

Evidência real fornecida pelo operador, consolidada sem nova consulta ao endpoint.
Auditoria de código realizada na branch `sync-fmp-codex-20261007`, HEAD
`ebd6d70 Add diagnostic WTI freshness probe RC1`.

| Campo | Valor observado |
| --- | --- |
| Probe | AmericasOilWatchWTIFreshnessProbe RC1 |
| diagnostic_only | true |
| operational_influence_allowed | false |
| automatic_activation | false |
| fallback_allowed | false |
| endpoint | https://americasoilwatch.com/api/v1/wti |
| asset | OIL |
| symbol | CL=F |
| reference_timestamp | 2026-10-07T14:24:11+00:00 |
| maximum_staleness_seconds | 3600 |
| provider | Yahoo Finance (CL=F) |
| dataSource | Yahoo Finance (CL=F) |
| price | 89.94 |
| change | 0.56 |
| raw_observedAt | 2026-10-07T13:01:03.000Z |
| normalized timestamp | 2026-10-07T13:01:03+00:00 |
| age_seconds | 4988 |
| freshness_status | STALE |
| request_status | OK |
| quoteType | intraday |
| quoteStatus | current |
| raw_other_timestamps.fetchedAt | 2026-10-07T13:11:03.969Z |
| validation_status | VALID |

## Temporal Chain

Todos os timestamps usados nos cálculos têm timezone explícito, em UTC.

| Marco | Timestamp |
| --- | --- |
| observedAt | 2026-10-07T13:01:03.000Z |
| fetchedAt (evidência bruta) | 2026-10-07T13:11:03.969Z |
| reference_timestamp | 2026-10-07T14:24:11+00:00 |
| HTTP Date (evidência bruta) | Wed, 07 Oct 2026 14:24:12 GMT |

| Cálculo | Segundos | Intervalo |
| --- | ---: | --- |
| reference_timestamp - observedAt | 4988 | 83 minutos e 8 segundos |
| fetchedAt - observedAt | 600.969 | 10 minutos e 0.969 segundo |
| reference_timestamp - fetchedAt | 4387.031 | 73 minutos e 7.031 segundos |

Verificação: `600.969 + 4387.031 = 4988` segundos.
Somente `reference_timestamp - observedAt` determina freshness. Os outros
intervalos são documentais e não substituem esse cálculo.

## HTTP Cache Evidence

| Header | Valor bruto |
| --- | --- |
| Date | Wed, 07 Oct 2026 14:24:12 GMT |
| Age | 247 |
| Cache-Control | public |

`Age=247` corresponde a 4 minutos e 7 segundos, aproximadamente 4 minutos.
Esse valor não explica sozinho os 83 minutos e 8 segundos de idade de
`observedAt`. Os headers não substituem `observedAt`, não são somados ou
subtraídos de `age_seconds` e não estabelecem a origem do atraso.

## Contract Audit and Decisions

Arquivos auditados:

- `external_context/providers/americas_oil_watch_wti_transport.py`
- `tools/americas_oil_watch_wti_freshness_probe_rc1.py`
- `tests/test_americas_oil_watch_wti_freshness_probe_rc1.py`

O transporte usa `observedAt`, rejeita timestamp sem timezone e não substitui
esse campo por `fetchedAt`. O probe exige enable explícito, referência com
timezone e threshold positivo e finito; normaliza o timestamp para UTC e
calcula a idade com a referência explícita, sem relógio implícito.

Classificação estrita preservada:

- `age_seconds < 0`: FUTURE.
- `0 <= age_seconds <= 3600`: FRESH.
- `age_seconds > 3600`: STALE.

Nesta evidência, `4988 > 3600`, portanto STALE está correto. `VALID` descreve a
validação dos campos pelo probe; `OK` descreve a requisição. Nenhum deles
significa FRESH. Não foi identificado erro de parsing ou cálculo temporal que
explique esta evidência. Nenhum arquivo Python foi alterado nesta consolidação.

Manter `observedAt` como timestamp de freshness e
`maximum_staleness_seconds=3600`. Não relaxar o threshold, implementar
tolerância, reutilizar STALE como FRESH, trocar fonte ou criar fallback.
`fetchedAt` e headers HTTP permanecem apenas evidência bruta.

A camada continua estritamente observacional/diagnóstica, sem ativação ou
integração automática e sem influência em Score, Risk, Decision, Alert, ordens
ou `Bot.mostrar`.

## Interpretation Boundaries

- HTTP Age não prova a origem do atraso.
- fetchedAt não prova instante do mercado e não substitui observedAt para freshness.
- quoteStatus=current não prova freshness suficiente nem substitui a auditoria temporal.
- Não atribuir definitivamente o atraso a Yahoo Finance ou Americas Oil Watch sem evidência adicional.
- A causa pode estar em Yahoo Finance, Americas Oil Watch, pipeline intermediário ou outra camada upstream; esta amostra não permite decidir entre essas hipóteses.
- A semântica de observedAt como instante de mercado não foi comprovada de forma independente nesta consolidação; a política existente foi preservada.
- Permanecem as limitações previamente identificadas no transporte: provider/dataSource por substring e ausência de validação de números finitos. Elas não explicam o cálculo temporal desta amostra; o probe tem validações mais estritas e o transporte não foi modificado.

## Validated Offline Gate

Resultado previamente validado informado pelo operador:

```text
50 passed in 1.44s
```

Referente a:

- `tests/test_americas_oil_watch_wti_freshness_probe_rc1.py`
- `tests/test_americas_oil_watch_wti_probe_rc1.py`
- `tests/test_americas_oil_watch_wti_transport_rc1.py`

Nenhum teste adicional foi executado nesta etapa documental.

## SECOND REAL SAMPLE

Segunda amostra real fornecida pelo operador, sem nova consulta nesta etapa:

| Campo | Amostra 2 |
| --- | --- |
| reference_timestamp | 2026-10-07T14:33:50+00:00 |
| price | 89.94 |
| change | 0.56 |
| observedAt | 2026-10-07T13:01:03+00:00 |
| fetchedAt | 2026-10-07T13:11:03.969Z |
| age_seconds | 5567 |
| freshness_status | STALE |
| HTTP Date | 14:33:51 GMT |
| HTTP Age | 225 |

Comparação com a primeira amostra:

| Evidência | Amostra 1 | Amostra 2 | Delta |
| --- | --- | --- | --- |
| reference_timestamp | 2026-10-07T14:24:11+00:00 | 2026-10-07T14:33:50+00:00 | 579 segundos |
| observedAt | 2026-10-07T13:01:03+00:00 | 2026-10-07T13:01:03+00:00 | 0 segundos |
| fetchedAt | 2026-10-07T13:11:03.969Z | 2026-10-07T13:11:03.969Z | 0 segundos |
| age_seconds | 4988 | 5567 | 579 segundos |
| price | 89.94 | 89.94 | inalterado |
| change | 0.56 | 0.56 | inalterado |
| freshness_status | STALE | STALE | inalterado |
| HTTP Date | 14:24:12 GMT | 14:33:51 GMT | evidência bruta |
| HTTP Age | 247 | 225 | evidência bruta |

Há forte evidência de conteúdo observado inalterado entre capturas separadas
por 579 segundos. A classificação descritiva é `OBSERVATION_UNCHANGED`.
As duas capturas não demonstram o comportamento em cada instante intermediário
nem provam qual camada causou isso. Não atribuir automaticamente a causa a
Yahoo Finance, Americas Oil Watch ou cache. HTTP Age é apenas evidência e não
substitui observedAt ou determina o estado descritivo.

O comparador offline `tools/americas_oil_watch_wti_sample_comparator_rc1.py`
recebe objetos JSON capturados pelo probe RC1, ou listas desses objetos,
ordena pela referência explícita e compara pares adjacentes válidos. Campos
incompatíveis ou timestamps inválidos/naive produzem `INSUFFICIENT_EVIDENCE`.
Sem referência avançando, ou com observedAt regredindo, o par também permanece
`INSUFFICIENT_EVIDENCE`. fetchedAt pode estar ausente, sem substituição.

Exemplo de uso com arquivos locais contendo apenas JSON do probe:

```powershell
python -m tools.americas_oil_watch_wti_sample_comparator_rc1 --enable amostra1.json amostra2.json
```

Nenhuma rede, troca de fonte, fallback, alteração do threshold 3600, ativação
ou influência operacional. Nenhuma conclusão de direção de mercado é derivada
desta comparação.
