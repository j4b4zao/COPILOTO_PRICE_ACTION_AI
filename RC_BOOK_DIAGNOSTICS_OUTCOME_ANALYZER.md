# BookDiagnostics RC11 — Outcome Analyzer

RC11 consolida os labels futuros do RC10 em métricas quantitativas para pesquisa offline e replay.

## Objetivo

Avaliar quais estados do BookDiagnostics apresentam comportamento futuro mais favorável antes de qualquer promoção para Evidence, Context, Score ou Risk.

## Métricas

- amostras totais e direcionais;
- MFE médio em R;
- MAE médio em R;
- edge observacional `avg_mfe_r - avg_mae_r`;
- taxa de TARGET antes do STOP para o cenário hipotético 1R;
- taxa de STOP antes do TARGET;
- ambiguidade alvo/stop na mesma barra;
- alinhamento entre direção do BookDiagnostics e direção futura;
- métricas equivalentes do trade oficial quando os níveis oficiais são comparáveis.

## Agrupamentos

- synthesis state;
- direção BookDiagnostics;
- market environment;
- reversal pressure;
- trend control;
- agreement/conflict com a decisão oficial.

## Regra arquitetural

RC11 permanece estritamente observacional/offline. Nenhuma métrica produzida pelo analyzer altera AnalysisContext, Strategy, Score, Risk, Decision ou execução.

A promoção futura de qualquer diagnóstico exige tamanho mínimo de amostra, resultado estável em replay e validação A/B fora da amostra.
