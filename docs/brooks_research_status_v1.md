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

### Tentativa real de 2026-09-08 15:03

- O preflight RTD confirmou atividade real: 46 amostras analisaveis, 22
  mudancas de preco, crescimento de 1 candle M1 e zero erros em 90 ciclos.
- O warm-up confirmou estrutura apos 789 ciclos e iniciou uma sessao
  enriquecida `SELECTION` de 600 ciclos. A sessao produziu 332 amostras
  analisaveis, 267 skips, zero falhas Delta e 1 erro de coleta.
- `SIDEWAYS + PA NONE` permaneceu apenas como contexto de trade nao pronto; os
  332 ciclos correspondentes nao entraram nos motivos de warning. A rejeicao
  ocorreu exclusivamente por `COLLECTION_ERRORS_PRESENT`/`DATA_READY_REQUIRED`.
- O erro tecnico foi uma classificacao valida `Direto` ou `Leilao` aceita pelo
  leitor RC22/RC23, mas ainda rejeitada pelos agregadores RC3/RC5. Esses tipos
  passaram a compor somente o volume total, sem inferir lado, alterar Delta ou
  deixar de rejeitar classificacoes desconhecidas.
- O JSON confirmou a persistencia dos flags Brooks e de isolamento. A sessao
  permanece somente diagnostica; nao cria cutoff, freeze, promocao ou OOS.

### Sessao real aceita de 2026-09-08 15:25

- Um novo preflight aprovou a fonte com 47 amostras analisaveis, 33 mudancas
  de preco, crescimento de 1 candle M1 e zero erros em 90 ciclos.
- Com o tratamento neutro de `Direto`/`Leilao` ativo, a sessao `SELECTION` de
  600 ciclos terminou `COMPLETED`, `data_ready=True` e sem warnings: 355
  amostras analisaveis, 245 skips, zero erros de coleta, zero preco ausente e
  zero falhas ou indisponibilidade Delta.
- Houve 320 amostras com contexto de trade nao pronto, sem contaminarem a
  prontidao tecnica. Ao final, a sessao observou `DOWN + SELL` e terminou com
  `trade_context_ready=True`.
- O manifesto unitario aceitou a sessao: `eligible_sessions=1`,
  `rejected_sessions=0`, `VALID_SELECTION`. Os flags Brooks e todas as travas
  de isolamento operacional foram persistidos.
- Este aceite adiciona evidencia de selecao, mas nao autoriza promocao nem OOS
  isoladamente. O proximo passo e consolidar todas as sessoes elegiveis no
  manifesto/evidence suite antes de qualquer freeze formal.

### Consolidacao offline apos a sessao 15:25

- O Selection Ledger encontrou 3 tentativas: 1 `VALID_SELECTION` e 2
  `REJECTED`. Somente a sessao `152552` conta como evidencia; as duas rejeitadas
  permanecem em quarentena diagnostica.
- A Research Evidence Suite aceitou exclusivamente a sessao limpa, sem
  rejeicoes internas. Foram auditados 9 candles EXACT_CANDLE.
- Breakout Pullback e Trend Pullback ainda possuem zero sequencias completas.
  O Trend Pullback observou 1 candidato SELL incompleto, invalidado por
  `TRADING_RANGE_TRANSITION`.
- Failed Breakout observou 2 sequencias DOWN, ambas sem falha de breakout
  confirmada. Major Trend Reversal, Wedge e Trading Range Reversal tiveram zero
  sequencias.
- `hypothesis_freeze_allowed=False`, `promotion_allowed=False` e a separacao
  operacional permanece integral. Sao necessarias novas sessoes independentes
  de selecao antes de considerar um cutoff formal ou qualquer fase OOS.

### Segunda sessao real aceita de 2026-09-08 15:44

- O preflight aprovou a fonte com 51 amostras analisaveis, 26 mudancas de
  preco, crescimento de 1 candle M1 e zero erros em 90 ciclos.
- A sessao independente `SELECTION` de 600 ciclos terminou `COMPLETED`,
  `data_ready=True`: 336 amostras analisaveis, 264 skips, zero erros de coleta,
  zero preco ausente e zero falhas ou indisponibilidade Delta.
- Houve 311 amostras com contexto de trade nao pronto sem gerar warning
  tecnico. A sessao terminou em `UP + BUY`, com `trade_context_ready=True`.
- A Evidence Suite conjunta aceitou as sessoes `152552` e `154439`, sem
  sobreposicao ou rejeicao. Cada sessao forneceu 9 candles EXACT_CANDLE.
- Failed Breakout passou a cobrir duas sequencias DOWN e duas UP, todas sem
  falha confirmada. Breakout Pullback e Trend Pullback continuam com zero
  sequencias completas; as demais familias tambem nao produziram matches.
- Mesmo com cobertura direcional BUY/SELL, `hypothesis_freeze_allowed=False` e
  `promotion_allowed=False`. A coleta continua em `SELECTION`; OOS permanece
  bloqueado ate evidencia suficiente e congelamento formal separado.

### Terceira sessao real aceita de 2026-09-09 09:57

- O preflight aprovou a fonte com 47 amostras analisaveis, 33 mudancas de
  preco, crescimento de 2 candles M1 e zero erros em 90 ciclos.
- A sessao independente `SELECTION` de 600 ciclos terminou `COMPLETED` e
  `data_ready=True`: 276 amostras analisaveis, 324 skips, zero erros de coleta,
  zero preco ausente e zero falhas ou indisponibilidade Delta.
- Todas as 276 amostras tiveram contexto de trade nao pronto e a sessao
  terminou `trade_context_ready=False`. Isso nao gerou warning nem rejeicao,
  confirmando em mercado real a separacao entre `DATA_READY` e
  `TRADE_CONTEXT_READY`.
- A Evidence Suite conjunta aceitou as tres sessoes limpas, sem sobreposicao ou
  rejeicao. Breakout Pullback e Trend Pullback continuam com zero sequencias
  completas; Failed Breakout, Major Trend Reversal, Wedge e Trading Range
  Reversal continuam com zero matches.
- `hypothesis_freeze_allowed=False` e `promotion_allowed=False`. A evidencia
  ainda e insuficiente para congelar candidato ou iniciar OOS.

### Quarta sessao real aceita de 2026-09-09 10:20

- O preflight aprovou a fonte com 23 amostras analisaveis, 16 mudancas de
  preco, crescimento de 1 candle M1 e zero erros em 90 ciclos.
- A sessao independente `SELECTION` de 600 ciclos terminou `COMPLETED` e
  `data_ready=True`: 373 amostras analisaveis, 227 skips, zero erros de coleta,
  zero preco ausente e zero falhas ou indisponibilidade Delta.
- Todas as 373 amostras tiveram contexto de trade nao pronto e a sessao
  terminou `trade_context_ready=False`, sem warning ou rejeicao tecnica.
- A Evidence Suite conjunta aceitou as quatro sessoes limpas, sem sobreposicao
  ou rejeicao. Breakout Pullback e Trend Pullback permanecem com zero
  sequencias completas; as demais familias permanecem com zero matches.
- `hypothesis_freeze_allowed=False` e `promotion_allowed=False`. A coleta
  permanece em `SELECTION`; nenhuma fase OOS esta autorizada.

### Quinta sessao real aceita de 2026-09-09 15:08

- O preflight declarou `MARKET_ACTIVITY_READY` com 45 amostras analisaveis,
  30 mudancas de preco e crescimento de 1 candle M1. Houve 1 erro transitorio
  no preflight, mas o gate terminou com `reasons=OK`.
- A sessao independente `SELECTION` de 600 ciclos terminou `COMPLETED` e
  `data_ready=True`: 332 amostras analisaveis, 268 skips, zero erros de coleta,
  zero preco ausente e zero falhas ou indisponibilidade Delta.
- Todas as 332 amostras tiveram contexto de trade nao pronto e a sessao
  terminou `trade_context_ready=False`, sem warning ou rejeicao tecnica.
- A Evidence Suite conjunta aceitou as cinco sessoes limpas, sem sobreposicao
  ou rejeicao. Todas as familias permanecem sem sequencia completa ou match.
- `hypothesis_freeze_allowed=False` e `promotion_allowed=False`; a coleta
  continua em `SELECTION` e OOS permanece bloqueado.

### Sexta sessao real aceita de 2026-09-09 16:07

- O preflight de 90 ciclos declarou `MARKET_ACTIVITY_READY`, com atividade
  real de preco, candles e RTD suficiente para iniciar a coleta.
- A sessao independente `SELECTION` de 600 ciclos terminou `COMPLETED` e
  `data_ready=True`: 341 amostras analisaveis, 259 skips, zero erros de coleta,
  zero preco ausente e zero falhas ou indisponibilidade Delta.
- Todas as 341 amostras tiveram contexto de trade nao pronto e a sessao
  terminou `trade_context_ready=False`, sem warning ou rejeicao tecnica.
- A Evidence Suite conjunta aceitou as seis sessoes limpas, sem sobreposicao
  ou rejeicao. Breakout Pullback e Trend Pullback permanecem sem sequencias
  completas; Failed Breakout, Major Trend Reversal, Wedge e Trading Range
  Reversal permanecem com zero matches.
- `hypothesis_freeze_allowed=False` e `promotion_allowed=False`; a evidencia
  continua exclusivamente observacional em `SELECTION` e OOS segue bloqueado.

### Setima sessao real aceita de 2026-09-10 09:39

- O preflight de 90 ciclos declarou `MARKET_ACTIVITY_READY`: 45 amostras
  analisaveis, 35 mudancas de preco, crescimento de 1 candle e `reasons=OK`.
- A sessao `SELECTION` de 600 ciclos terminou `COMPLETED` e `data_ready=True`:
  365 amostras analisaveis, 235 skips, zero erros de coleta, zero preco ausente
  e zero falhas ou indisponibilidade Delta.
- Todas as 365 amostras tiveram contexto de trade nao pronto; a sessao terminou
  `trade_context_ready=False`, sem warning ou rejeicao tecnica.
- A Evidence Suite aceitou as sete sessoes limpas, sem sobreposicao ou
  rejeicao. Nenhuma familia produziu sequencia completa ou match suficiente.
- `hypothesis_freeze_allowed=False` e `promotion_allowed=False`; OOS permanece
  bloqueado e toda a evidencia continua exclusivamente observacional.

### Oitava sessao real aceita de 2026-09-10 10:01

- O preflight de 90 ciclos declarou `MARKET_ACTIVITY_READY`: 58 amostras
  analisaveis, 41 mudancas de preco, crescimento de 2 candles, zero erros e
  `reasons=OK`.
- A sessao `SELECTION` de 600 ciclos terminou `COMPLETED` e `data_ready=True`:
  347 amostras analisaveis, 253 skips, zero erros de coleta, zero preco ausente
  e zero falhas ou indisponibilidade Delta.
- Todas as 347 amostras tiveram contexto de trade nao pronto; a sessao terminou
  `trade_context_ready=False`, sem warning ou rejeicao tecnica.
- A Evidence Suite aceitou as oito sessoes limpas, sem sobreposicao ou
  rejeicao. Nenhuma familia produziu sequencia completa ou match suficiente.
- `hypothesis_freeze_allowed=False` e `promotion_allowed=False`; OOS permanece
  bloqueado e toda a evidencia continua exclusivamente observacional.

### Nona sessao real aceita de 2026-09-10 10:22

- O preflight de 90 ciclos declarou `MARKET_ACTIVITY_READY`: 42 amostras
  analisaveis, 31 mudancas de preco, crescimento de 1 candle, zero erros e
  `reasons=OK`.
- A sessao `SELECTION` de 600 ciclos terminou `COMPLETED` e `data_ready=True`:
  290 amostras analisaveis, 310 skips, zero erros de coleta, zero preco ausente
  e zero falhas ou indisponibilidade Delta.
- Todas as 290 amostras tiveram contexto de trade nao pronto; a sessao terminou
  `trade_context_ready=False`, sem warning ou rejeicao tecnica.
- A Evidence Suite aceitou as nove sessoes limpas, sem sobreposicao ou
  rejeicao. Apesar da evolucao estrutural observada na janela, nenhuma familia
  produziu sequencia completa ou match suficiente.
- `hypothesis_freeze_allowed=False` e `promotion_allowed=False`; OOS permanece
  bloqueado e toda a evidencia continua exclusivamente observacional.

### Decima sessao real aceita de 2026-09-10 11:03

- O preflight de 90 ciclos declarou `MARKET_ACTIVITY_READY`: 65 amostras
  analisaveis, 47 mudancas de preco, crescimento de 1 candle, zero erros e
  `reasons=OK`.
- A sessao `SELECTION` de 600 ciclos terminou `COMPLETED` e `data_ready=True`:
  376 amostras analisaveis, 224 skips, zero erros de coleta, zero preco ausente
  e zero falhas ou indisponibilidade Delta.
- Todas as 376 amostras tiveram contexto de trade nao pronto; a sessao terminou
  `trade_context_ready=False`, sem warning ou rejeicao tecnica.
- A Evidence Suite aceitou as dez sessoes limpas, sem sobreposicao ou rejeicao.
  O BOS UP observado isoladamente nao completou uma sequencia Brooks; todas as
  familias permanecem sem match suficiente.
- `hypothesis_freeze_allowed=False` e `promotion_allowed=False`; OOS permanece
  bloqueado e toda a evidencia continua exclusivamente observacional.

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
