# F3-INT-29 — Sequências longas e redução determinística

Data: 2026-10-20. Escopo: exclusivamente SIMULATED. F3=OPEN.

## Mudança
Adicionado `tests/test_f3_int29_long_sequences.py`. Nenhuma alteração no modelo de recuperação ou Architecture C.

## Execução real
- Testes isolados F3-INT-29: 4/4, 7,323 segundos, exit 0.
- 720 permutações determinísticas de seis ações, com qualificação e fechamento ao final.
- 24 sequências adicionais de qualificação, duas falhas intercaladas e fechamento.
- Redutor por deleção de uma ação validado em oráculo sintético com gatilhos alternativos. Apenas 1-minimalidade local, não mínimo global.
- Regressão: 231/231, 29,229 segundos, exit 0.
- Exploração legada INT10: 12.000 transições, limite de transições, zero contraexemplos.
- Exploração legada INT13: 180.000 transições, limite de transições, zero contraexemplos.
- Exploração legada INT14: 30.000 transições, limite de arestas, zero violações.
- INT15: 4.692 avaliações, 207/207 pares canônicos; não exaustivo.

## Limitações
A cobertura é limitada a fixtures, sequências e oráculos escolhidos. Nenhum contraexemplo novo foi observado, portanto o redutor não foi validado em falha real do modelo. Não há prova criptográfica, nativa, de deadline estrito, Job real ou autorização operacional. F3 permanece OPEN; os sete flags de segurança permanecem false.
