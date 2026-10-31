# F3-INT-121 A14.3 — Relatório final documental

Data: 2026-10-29. Base: A14.3 R2 corrigida.

## Evidências de execução (logs fornecidos pelo usuário)
- Regressão Windows Python normal: 175 testes, 402.365 s, OK.
- Regressão Windows Python -O: 175 testes, 464.727 s, OK.
- Total: 350 execuções, nenhuma falha ou erro relatado.
- A14.3: atraso de 0.35 s e falha injetada **antes** de Peer.close, não falha nativa da API Windows.
- Em ambos os modos, logs registram sobreviventes durante atraso e zero processos ativos após limpeza.
- A correção R2 eliminou descoberta duplicada da classe A11: 2 testes específicos por modo, conforme log anterior.

## Limites
A validação de Windows é proveniente de logs fornecidos pelo usuário; não houve execução Windows independente neste ambiente. Este fechamento é documental e não certifica comportamento operacional nem ordens reais.

## Próxima etapa
A14.4: variar ordem de encerramento do supervisor e descendentes, em fixture isolada, com contenção e limpeza garantida em finally. Implementação ainda não autorizada por este checkpoint.

F3=OPEN; offline=true; simulation_only=true; real_operations_authorized=false.
