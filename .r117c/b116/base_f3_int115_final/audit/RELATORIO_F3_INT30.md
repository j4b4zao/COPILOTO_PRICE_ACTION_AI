# F3-INT-30 — Auditoria causal com falha injetada
Data: 2026-10-20. Escopo exclusivamente simulado, offline.

## Alteração
Adicionado `tests/test_f3_int30_causal_fault_injection.py`. Nenhuma modificação nos modelos de recuperação ou Architecture C.

## Evidência de execução
- Testes novos: 4/4, 0,076 s, exit 0.
- Regressão completa: 235/235, 27,462 s, exit 0.
- Injeção **sintética**: um closer propositalmente defeituoso aceita ticket stale após QUALIFY -> MUTATION -> CLOSE.
- O redutor por deleção recuperou sequência causal de três eventos, com 1-minimalidade local (não mínimo global).
- Modelo simulado real rejeitou quatro variantes: mudança de geração, conflito tardio, Job negativo, cleanup negativo.
- INT13: 180.000 transições, limite atingido, zero contraexemplos relatados.
- INT14: 30.000 transições, limite atingido, zero violações relatadas.
- INT15: 4.692 avaliações, zero falhas; não exaustivo.

## Limitações
A falha injetada não foi encontrada no modelo. O redutor foi exercitado contra um oráculo artificial, não uma falha nativa. Os resultados não comprovam autenticidade criptográfica, Job real, deadline estrito, nem segurança operacional.
F3=OPEN. Nenhuma autorização operacional ou certificação nativa. Sete flags de autorização devem permanecer false.
