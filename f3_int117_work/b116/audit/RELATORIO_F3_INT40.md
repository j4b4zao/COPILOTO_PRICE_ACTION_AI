# RELATÓRIO F3-INT-40 — concorrência de rotação/revogação

## Escopo
Extensão exclusivamente simulada, isolada, sem APIs nativas, persistência real ou conexão ao sistema de negociação.

## Mudanças
- `tools/f3_int40_concurrent_rotation_simulator.py`: reconstrói uma cadeia causal por identificadores de evento e parent, rejeita bifurcações, pais ausentes, IDs duplicados e mudanças de escritor sem handoff comprovado.
- `tests/test_f3_int40_concurrent_rotation.py`: 12 novos testes adversariais; histórico com eventos entregues em ordem diferente, forks, revogação, comprometimento e evidências inconsistentes.
- Nenhuma modificação no núcleo de recuperação nem nos simuladores anteriores.

## Resultados
- Regressão completa: 310/310 testes, zero falhas finais (27,720 segundos).
- Testes novos: 12/12.
- Exploração F3-INT-13: 180000 transições, sem contraexemplos detectados, encerramento por limite de transições.
- Durante o desenvolvimento, dois testes inicialmente falharam por códigos de rejeição esperados incorretos; corrigidas somente as expectativas e reexecutada a regressão.

## Limitações
Uma cadeia de eventos sem bifurcação não prova autenticidade, ordenação global, consenso, isolamento real ou transferência segura de autoridade. `fixture_eligible` não representa autorização operacional. A simulação é conservadora e rejeita handoff entre escritores sem prova externa; não implementa consenso.

## Estado
F3=OPEN. `orders_allowed`, `live_certified`, `flow_complete`, `f3_resolved`, `native_prototype_authorized`, `strict_deadline_guaranteed`, `authenticated_witness_verified`: todos `false`.
