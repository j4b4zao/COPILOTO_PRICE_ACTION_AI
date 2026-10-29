# F3-INT-28 — Exploração de sequências e minimização

Data: 2026-10-20. Domínio exclusivamente SIMULATED. F3=OPEN.

## Escopo
Partiu-se do ZIP F3-INT-27. Adicionado `tests/test_f3_int28_sequence_minimizer.py` sem modificar `tools/f3_int20_evidence_recovery_model.py` nem Architecture C.

## Execução real
- Testes específicos: 4/4 aprovados, 1,027 s.
- 120 permutações de cinco ações (criação A/B, Job NONEMPTY, cleanup FAILED, mudança de geração) mais quatro cenários de tickets obsoletos.
- Regressão: 227/227 aprovados, 20,501 s, exit code 0.
- Exploração INT10: 12.000 transições, sem contraexemplos, interrompida por limite de transições.
- Exploração INT13: 180.000 transições, sem contraexemplos, interrompida por limite de transições.
- Exploração INT14: 30.000 transições, sem violações, interrompida por limite de arestas.
- INT15: 4.692 combinações/arestas examinadas; 207/207 pares fase-evento canônicos; não exaustivo.

## Redutor
Implementado redutor determinístico por deleção de uma ação por vez, com verificação de preservação do predicado. Garante somente minimalidade local de 1 deleção; não garante sequência globalmente mínima. Validado com predicado sintético; nenhum contraexemplo real novo foi encontrado.

## Limitações
A exploração de 120 permutações é limitada à fixture e ações escolhidas. Não representa model checking exaustivo, concorrência nativa, autenticação criptográfica, Job Objects reais, garantias de deadline ou certificação operacional. Os sete flags permanecem false. Não foi realizada nenhuma operação real.
