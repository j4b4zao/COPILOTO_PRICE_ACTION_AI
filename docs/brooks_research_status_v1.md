# Brooks Research Status V1

Data de consolidacao: 2026-09-14

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
| Stop / Target Rules | BROOKS_STOP_TARGET_RULES_V1 | Classificador + capture + EXACT_CANDLE validados; somente evidencia prospectiva |

## Infraestrutura de pesquisa

- Brooks Research Registry/Suite: validado.
- Brooks Research Evidence Suite V1: validado; agrega os sete auditores EXACT_CANDLE.
- Stop/Target Rules possui auditor dedicado, com desfecho iniciado somente no
  candle posterior ao sinal e sem alvo sintetico.
- Brooks Selection Session Manifest V1: validado.
- Brooks Selection Runner V1: validado.
- Brooks Selection Launcher V1: validado.
- Separacao SELECTION x OOS: obrigatoria.
- OOS exige selection_cutoff e sessao estritamente posterior ao cutoff.
- Sessoes temporalmente sobrepostas sao rejeitadas.
- Identidade EXACT_CANDLE e ultima revisao sao preservadas pelos auditores dedicados.

## Testes controlados confirmados

Total Brooks confirmado ate esta consolidacao: **310 testes aprovados**.

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

### Decima primeira sessao real aceita de 2026-09-10 17:16

- Uma primeira tentativa foi interrompida ainda no warm-up porque o Excel
  entregou timestamp no campo de volume e depois uma planilha com layout que
  nao era Times & Trades. Nenhum artefato dessa tentativa foi produzido.
- Depois da reabertura explicita de `times&trades.xlsx` e `livroOfertas.xlsx`,
  o preflight de 90 ciclos declarou `MARKET_ACTIVITY_READY`: 52 amostras
  analisaveis, 20 mudancas de preco, crescimento de 1 candle e zero erros.
- A sessao limpa `SELECTION` de 600 ciclos terminou `COMPLETED` e
  `data_ready=True`: 255 amostras analisaveis, 345 skips, zero erros de coleta,
  zero preco ausente e zero falhas ou indisponibilidade Delta.
- Todas as 255 amostras tiveram contexto de trade nao pronto; a sessao terminou
  `trade_context_ready=False`, sem warning ou rejeicao tecnica.
- A Evidence Suite aceitou as onze sessoes limpas, sem sobreposicao ou
  rejeicao, e permanece sem sequencia completa ou match suficiente.
- `hypothesis_freeze_allowed=False` e `promotion_allowed=False`; OOS permanece
  bloqueado e toda a evidencia continua exclusivamente observacional.

### Diagnostico offline de lacunas apos onze sessoes

- O `BROOKS_EVIDENCE_GAP_REPORT_V1` consolidou 98 candles EXACT_CANDLE nas 11
  sessoes limpas, sem reabrir Excel/Profit e sem reinterpretar os auditores.
- Failed Breakout produziu 17 sequencias candidatas e zero matches; 13 ficaram
  explicitamente em `BREAKOUT_FAILURE_NOT_OBSERVED`.
- Trend Pullback produziu 1 candidato incompleto, invalidado por
  `TRADING_RANGE_TRANSITION`. Breakout Pullback permaneceu sem sequencia
  completa, embora todas as fases do contrato tenham aparecido no agregado.
- Major Trend Reversal, Wedge e Trading Range Reversal permaneceram sem
  sequencia candidata. Stop/Target continua `CLASSIFIER_ONLY_NO_EXACT_AUDITOR`.
- O veredito permanece `MORE_INDEPENDENT_SELECTION_EVIDENCE_REQUIRED`; o
  relatorio nunca libera freeze, OOS, promocao ou influencia operacional.

### Captura Stop/Target para sessoes futuras

- A captura `BROOKS_STOP_TARGET_RULES_V1` foi adicionada ao runner Brooks para
  novas sessoes, sem reconstruir artificialmente as 11 sessoes anteriores.
- Quando uma entrada Brooks estiver explicitamente disparada, a captura usa o
  fechamento e o extremo oposto do proprio candle-sinal apenas para registrar
  a geometria observacional do stop.
- Um alvo so e registrado quando existe range estrutural valido e o limite
  oposto fica no lado correto da entrada. A captura nao cria alvo 2R sintetico.
- Os campos sao research-only; Score, Risk, Decision, Alert e execucao
  permanecem sem influencia. O auditor EXACT_CANDLE de evolucao Stop/Target
  continua como proxima etapa e dependera de novas sessoes com essa captura.

### Decima segunda sessao real aceita de 2026-09-11 09:30

- A sessao `SELECTION` de 600 ciclos terminou `COMPLETED` e `data_ready=True`:
  324 amostras analisaveis, 276 skips, zero erros de coleta, zero preco ausente
  e zero falhas ou indisponibilidade Delta.
- Todas as 324 amostras tiveram contexto de trade nao pronto; a sessao terminou
  `trade_context_ready=False`, sem warning nem rejeicao tecnica, conforme a
  separacao entre prontidao dos dados e prontidao do contexto de trade.
- Foram observados 9 candles M1 distintos e direcoes Stop/Target em 227 linhas
  BUY e 97 SELL. Entretanto, as 324 linhas ficaram `NOT_ELIGIBLE`, com entrada,
  stop e alvo zerados, porque a captura era executada antes de o runner anexar
  `candle_evidence` ao item.
- Portanto, essa primeira tentativa nao conta como evidencia Stop/Target e nao
  sera reconstruida retroativamente. A sessao continua tecnicamente valida para
  as outras familias Brooks.
- A captura foi corrigida com fallback somente-leitura para
  `context.market.last_candle` quando o item ainda nao possui
  `candle_evidence`. Um teste reproduz exatamente essa ordem do runner.
- A Evidence Suite recomposta aceitou 12 de 12 sessoes, rejeitou zero e nao
  encontrou sequencia completa ou match suficiente. `hypothesis_freeze_allowed`
  e `promotion_allowed` continuam `False`; OOS permanece bloqueado.
- Toda a camada continua `observational_only=True`, sem influencia em Score,
  Risk, Decision, Alert ou execucao.

### Decima terceira sessao real aceita de 2026-09-14 09:16

- O preflight de atividade real terminou `MARKET_ACTIVITY_READY`: 49 amostras
  analisaveis, 36 mudancas de preco, crescimento de 2 candles e zero erros.
- A sessao `SELECTION` de 600 ciclos terminou `COMPLETED` e `data_ready=True`:
  359 amostras analisaveis, 241 skips, zero erros de coleta, zero preco ausente
  e zero falhas ou indisponibilidade Delta.
- Todas as 359 amostras tiveram contexto de trade nao pronto e a sessao
  terminou `trade_context_ready=False`, sem warning nem rejeicao tecnica.
- A correcao Stop/Target foi confirmada prospectivamente: 359 linhas foram
  capturadas, 308 tiveram geometria de stop valida e 51 ficaram inelegiveis.
  Houve 245 direcoes BUY, 114 SELL e 10 candles M1 distintos.
- Nenhuma das 359 linhas possuia alvo estrutural valido. O capturador manteve
  `target_source=NONE`, sem criar alvo ou reward/risk sintetico.
- A Evidence Suite aceitou 13 de 13 sessoes e rejeitou zero. O relatorio de
  lacunas consolidou 117 candles EXACT_CANDLE; Failed Breakout passou a 22
  candidatos e zero matches, enquanto Trend Pullback continua com 1 candidato
  incompleto por `TRADING_RANGE_TRANSITION`.
- O auditor EXACT_CANDLE Stop/Target foi integrado depois desta coleta. Das 13
  sessoes, somente a de 14/09 foi aceita para essa familia: as 11 anteriores nao
  possuem o schema e a de 11/09 foi excluida por
  `NO_PROSPECTIVE_STOP_TARGET_EVIDENCE`.
- A ultima revisao de cada candle produziu 9 observacoes prospectivas, todas sem
  alvo estrutural e, portanto, sem desfecho avaliavel. A lacuna correta e
  `NO_EVALUABLE_STRUCTURAL_TARGET`, nao ausencia de captura.
- `hypothesis_freeze_allowed=False`, `promotion_allowed=False` e OOS continua
  bloqueado. Score, Risk, Decision, Alert e execucao permanecem sem influencia.

### Decima quarta sessao real aceita de 2026-09-14 09:52

- O preflight terminou `MARKET_ACTIVITY_READY`: 59 amostras analisaveis, 39
  mudancas de preco, crescimento de 2 candles e `reasons=OK`. Um erro
  transitorio isolado nao impediu o gate de confirmar atividade real.
- A sessao independente `SELECTION` de 600 ciclos terminou `COMPLETED` e
  `data_ready=True`: 373 amostras analisaveis, 227 skips, zero erros de coleta,
  zero preco ausente e zero falhas ou indisponibilidade Delta.
- Todas as 373 amostras tiveram contexto de trade nao pronto e a sessao
  terminou `trade_context_ready=False`, sem warning nem rejeicao tecnica.
- Stop/Target registrou 373 linhas: 323 geometrias de stop elegiveis, 50
  inelegiveis, 339 direcoes BUY, 34 SELL e 10 candles M1 distintos.
- Novamente nao houve alvo estrutural valido; nenhum alvo sintetico foi criado.
- A Evidence Suite aceitou 14 de 14 sessoes e rejeitou zero. O auditor
  Stop/Target aceitou as duas sessoes prospectivas, totalizou 19 candles-sinal
  deduplicados e manteve zero desfechos avaliaveis.
- O relatorio de lacunas consolidou 127 candles EXACT_CANDLE e manteve
  `NO_EVALUABLE_STRUCTURAL_TARGET` e o veredito geral
  `MORE_INDEPENDENT_SELECTION_EVIDENCE_REQUIRED`.
- OOS, freeze e promocao continuam bloqueados; toda influencia operacional
  permanece desabilitada.

### Tentativa rejeitada de 2026-09-14 15:40

- O preflight anterior terminou `MARKET_ACTIVITY_READY`, com 68 amostras
  analisaveis, 29 mudancas de preco, crescimento de 1 candle e zero erros.
- A tentativa completou os 600 ciclos, com 432 amostras analisaveis, 168 skips,
  zero erros de coleta e zero preco ausente.
- Durante a janela houve reinicializacao da fonte Delta. O validador registrou
  11 amostras Delta ainda nao prontas e 1 falha Delta, encerrando a sessao como
  `COMPLETED_WITH_WARNINGS`, `data_ready=False` e
  `DELTA_NOT_READY_OR_INVALID`.
- O manifesto aplicou `DATA_READY_REQUIRED` e o outcome foi `REJECTED`. O
  arquivo permanece somente em quarentena diagnostica e nao integra a Evidence
  Suite, os 14 registros validos ou a evidencia Stop/Target.

### Decima quinta sessao real aceita de 2026-09-14 16:00

- Depois da rejeicao tecnica, um novo preflight confirmou recuperacao da fonte:
  42 amostras analisaveis, 27 mudancas de preco, crescimento de 1 candle e zero
  erros, encerrando `MARKET_ACTIVITY_READY` com `reasons=OK`.
- A nova sessao independente `SELECTION` terminou `COMPLETED` e
  `data_ready=True`: 317 amostras analisaveis, 283 skips, zero erros de coleta,
  zero preco ausente e zero falhas ou indisponibilidade Delta.
- Todas as 317 amostras tiveram contexto de trade nao pronto; a sessao terminou
  `trade_context_ready=False`, sem warning nem rejeicao tecnica.
- Stop/Target registrou 258 geometrias elegiveis, com 76 direcoes BUY, 241 SELL
  e 9 candles M1 distintos. Nao houve alvo estrutural valido e nenhum alvo
  sintetico foi criado.
- A Evidence Suite aceitou 15 de 15 sessoes validas e rejeitou zero. A tentativa
  das 15:40 permaneceu fora dos caminhos de entrada.
- O auditor Stop/Target agora aceita 3 sessoes prospectivas, soma 27 sinais
  deduplicados e continua com zero desfechos avaliaveis. O agregado possui 136
  candles EXACT_CANDLE e 26 candidatos Failed Breakout, ainda com zero matches.
- O veredito permanece `MORE_INDEPENDENT_SELECTION_EVIDENCE_REQUIRED`; OOS,
  freeze, promocao e influencia operacional continuam bloqueados.

### Gate de historico Brooks para alvos estruturais

- O diagnostico das tres sessoes prospectivas encontrou
  `brooks_trading_range_valid=False` em todas as 1.049 amostras, sempre com
  `state=NO_RANGE` e limites estruturais zerados.
- A causa era uma incompatibilidade de janela: o detector de Trading Range
  exige 14 candles fechados, enquanto o warm-up encerrava ao obter estrutura
  basica, normalmente com 6 a 10 candles. Os 600 ciclos seguintes nao eram
  suficientes para atingir o minimo de range de forma consistente.
- O RC54 base recebeu o parametro opcional `min_history_candles`, com default
  zero para preservar seu comportamento. Somente o runner Brooks fixa 15
  candles totais, equivalentes aos 14 fechados exigidos mais o candle atual.
- O gate e fail-closed: se o limite de warm-up terminar antes dos 15 candles, a
  sessao nao comeca e nenhum arquivo e aceito como evidencia.
- Para novas coletas Brooks deve ser mantido o default de 4.800 ciclos de
  warm-up; 1.800 ciclos podem ser insuficientes quando o processo inicia sem
  historico local.
- A mudanca afeta apenas prontidao da coleta research-only e nao altera
  PriceAction, Score, Risk, Decision, Alert ou execucao.

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

1. Coletar novas sessoes independentes ate surgir alvo estrutural prospectivo
   que permita ao auditor Stop/Target observar desfecho sem reconstrucao.
2. Gerar/validar o Selection Manifest das sessoes reais.
3. Rodar a Research Evidence Suite sobre a evidencia de selecao.
4. Manter sessoes sobrepostas em quarentena.
5. Somente depois de um cutoff formal, iniciar evidencia OOS independente.
6. Manter qualquer avaliacao de desempenho separada da validacao semantica/safety.

## Estado

BROOKS_RESEARCH_LAYER_V1 = SELECTION_COLLECTION_ACTIVE_MORE_EVIDENCE_REQUIRED
