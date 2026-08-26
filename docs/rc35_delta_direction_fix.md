# RC35 — Delta direction fix

A auditoria das sessoes RC32/RC34 mostrou `BEARISH_ALIGNED=0` mesmo durante janelas com `recent_delta` fortemente negativo.

Causa: `dominance` representa magnitude (0..1), enquanto o sinal direcional reside em `recent_delta`. O RC29 e RC32 tratavam `dominance` como se fosse assinado.

Correcao:
- direcao do Delta vem do sinal de `recent_delta`;
- forca vem de `abs(dominance)`;
- Book continua usando o sinal de `imbalance`;
- Score, Decision e execucao permanecem bloqueados;
- testes de regressao cobrem bearish, bullish, divergent e neutral.

As sessoes RC32 anteriores nao devem ser usadas para promocao de thresholds; elas foram produzidas com classificacao direcional defeituosa e servem apenas como evidencia diagnostica da falha.
