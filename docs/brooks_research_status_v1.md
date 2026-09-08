# Brooks Research Status V1

Data de consolidacao: 2026-09-05

## Escopo

Camada paralela de pesquisa inspirada nos livros Trading Price Action Trends, Trading Price Action Ranges e Trading Price Action Reversals, de Al Brooks.

Esta camada e estritamente research-only e observational-only. Nao altera o nucleo validado do COPILOTO_PRICE_ACTION_AI e nao possui permissao para influenciar Score, Risk, Decision, Alert ou execucao.

## Contrato global de seguranca

- research_only = True
- observational_only = True
- predictive_claim_allowed = False
- score_influence_allowed = False
- risk_influence_allowed = False
- decision_influence_allowed = False
- alert_influence_allowed = False
- order_execution_allowed = False
- hypothesis_freeze_allowed = False
- promotion_allowed = False

Os testes desta camada validam contratos, semantica, isolamento, sequencias e integridade da evidencia. Eles nao demonstram desempenho preditivo ou rentabilidade.

## Familias formalizadas

| Familia | Identificador | Estado |
| --- | --- | --- |
| Breakout Pullback | BROOKS_BREAKOUT_PULLBACK_V1 | Classificador + EXACT_CANDLE validados |
| Trend Pullback | BROOKS_TREND_PULLBACK_V1 | Classificador + capture + runner + EXACT_CANDLE validados |
| Failed Breakout | BROOKS_FAILED_BREAKOUT_V1 | Classificador + EXACT_CANDLE validados; CHOCH alinhado ao MarketStructure RC17 |
| Major Trend Reversal | BROOKS_MAJOR_TREND_REVERSAL_V1 | Classificador + capture + EXACT_CANDLE validados |
| Wedge / Three Pushes | BROOKS_WEDGE_THREE_PUSHES_V1 | Detector/classificador + capture + EXACT_CANDLE validados |
| Trading Range Reversal | BROOKS_TRADING_RANGE_REVERSAL_V1 | Classificador + capture + EXACT_CANDLE validados |
| Stop / Target Rules | BROOKS_STOP_TARGET_RULES_V1 | Classificador/management research-only validado; sem auditor EXACT_CANDLE dedicado |

## Infraestrutura de pesquisa

- Brooks Research Registry/Suite: validado.
- Brooks Research Evidence Suite V1: validado; agrega os seis auditores EXACT_CANDLE.
- Stop/Target Rules permanece explicitamente CLASSIFIER_ONLY_NO_EXACT_AUDITOR na Evidence Suite.
- Brooks Selection Session Manifest V1: validado.
- Brooks Selection Runner V1: validado.
- Brooks Selection Launcher V1: validado.
- Separacao SELECTION x OOS: obrigatoria.
- OOS exige selection_cutoff e sessao estritamente posterior ao cutoff.
- Sessoes temporalmente sobrepostas sao rejeitadas.
- Identidade EXACT_CANDLE e ultima revisao sao preservadas pelos auditores dedicados.

## Testes controlados confirmados

Total Brooks confirmado ate esta consolidacao: **271 testes aprovados**.

Esse total inclui os classificadores, auditores EXACT_CANDLE, capture helpers, runners, Registry/Suite, Evidence Suite, Selection Manifest, Selection Runner, Selection Launcher e os testes especificos do contrato Failed Breakout/CHOCH.

## Baseline EXACT_CANDLE anterior ao runner enriquecido

- A Evidence Suite V1 foi executada em modo `SELECTION` sobre as tres sessoes
  independentes `154917`, `163915` e `172520`; todas foram admitidas e nenhuma
  sobreposicao temporal foi encontrada.
- O relatorio foi salvo em
  `data/profit_rtd_price_action_exact_selection/brooks_research_evidence_suite_clean_20260905.json`.
- Breakout Pullback aceitou as tres sessoes, mas observou zero sequencias
  completas. Failed Breakout tambem aceitou as tres e observou zero matches.
- Trend Pullback e as familias enriquecidas de Major Trend Reversal, Wedge e
  Trading Range nao encontraram sessoes elegiveis porque essas capturas antigas
  nao possuem todos os campos explicitos dos novos contratos.
- O resultado e apenas um baseline parcial: `hypothesis_freeze_allowed=False`,
  `promotion_allowed=False` e `oos_collection_allowed=False`. A proxima coleta
  pelo launcher Brooks permanece em modo `SELECTION`.

## Failed Breakout / CHOCH

A revisao de 2026-09-05 confirmou que o MarketStructure RC17 produz `structure.choch` como booleano. O auditor Failed Breakout foi alinhado a esse contrato sem modificar o produtor operacional:

- breakout UP: CHOCH verdadeiro com trend DOWN representa invalidacao estrutural;
- breakout DOWN: CHOCH verdadeiro com trend UP representa invalidacao estrutural;
- CHOCH na mesma direcao do breakout nao invalida;
- choch falso nao invalida.

## Coleta real seguinte

Nao coletar nova evidencia real durante mercado fechado/inativo.

### Tentativa real de 2026-09-08 09:37

- O preflight RTD confirmou atividade real: 51 atualizacoes analisaveis, 34
  mudancas de preco e crescimento de 2 candles M1 em 90 ciclos.
- Uma sessao enriquecida foi executada em modo `SELECTION`: 600 ciclos, 395
  amostras analisaveis, 202 skips, 3 erros de coleta e zero falhas Delta.
- Os tres erros foram `Agressor incompativel com T&T RTD`; por isso a sessao
  terminou `COMPLETED_WITH_WARNINGS`, `data_ready=False` e foi rejeitada pelo
  manifesto. Ela nao conta como evidencia de selecao.
- O arquivo persistido tambem revelou que os flags Brooks eram adicionados ao
  retorno somente depois da gravacao. O runner foi corrigido para persistir os
  mesmos flags de captura e seguranca no JSON; a correcao esta em `88c2761`.
- A sessao e o relatorio rejeitados sao preservados apenas como diagnostico.
  Nao existe selection cutoff, freeze, promocao ou permissao OOS decorrente
  desta tentativa.

Na proxima sessao de mercado, a entrada operacional padrao e:

```powershell
cd C:\COPILOTO_PRICE_ACTION_AI
python -m tools.profit_rtd_brooks_selection_launcher WINV26
```

A coleta inicial permanece em modo SELECTION. Nao classificar as primeiras sessoes como OOS e nao promover nenhuma hipotese com base apenas nelas.

## Fluxo de evidencia

```text
Brooks Enriched Capture
        -> Selection Runner
        -> Selection Manifest
        -> Research Evidence Suite
        -> analise SELECTION
        -> selection_cutoff somente quando formalmente definido
        -> futuras sessoes independentes OOS
```

## Proximas etapas

1. Coletar novas sessoes Brooks enriquecidas quando o mercado estiver ativo.
2. Gerar/validar o Selection Manifest das sessoes reais.
3. Rodar a Research Evidence Suite sobre a evidencia de selecao.
4. Manter sessoes sobrepostas em quarentena.
5. Somente depois de um cutoff formal, iniciar evidencia OOS independente.
6. Manter qualquer avaliacao de desempenho separada da validacao semantica/safety.

## Estado

BROOKS_RESEARCH_LAYER_V1 = OFFLINE_INFRASTRUCTURE_READY_FOR_SELECTION_COLLECTION
