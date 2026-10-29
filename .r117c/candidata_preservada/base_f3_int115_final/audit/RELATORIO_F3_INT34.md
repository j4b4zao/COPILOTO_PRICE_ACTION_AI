# Relatório F3-INT-34 — simulação isolada

## Resultado
- Regressão completa: **254/254**, 33,209 s, zero falhas/erros.
- Novos testes: **6/6**.
- Modelo de recuperação `tools/f3_int20_evidence_recovery_model.py`: **inalterado**.
- Novo módulo isolado `tools/f3_int34_persistence_simulator.py`: autoridade única **em memória**, sequência encadeada por SHA-256 e fencing por geração.
- Injeções de falha: antes e depois do append, corrupção, repetição, reordenação, lacunas, troca de worker.
- Exploração F3-INT-13: 180.000 transições, sem contraexemplos detectados dentro do limite (não exaustivo).

## Limites
Este teste **não** implementa nem valida escrita atômica em disco, fsync, transações, recuperação de energia, concorrência real, processos independentes ou consenso distribuído. A simulação trata `append` como passo indivisível por hipótese. SHA-256 aqui detecta alteração acidental do registro simulado; não autentica testemunhas. `CLOSED_RECOVERED` não libera negociação.

## Segurança
F3=OPEN. `orders_allowed`, `live_certified`, `flow_complete`, `f3_resolved`, `native_prototype_authorized`, `strict_deadline_guaranteed`, `authenticated_witness_verified` permanecem false. Nenhuma alteração no projeto operacional, Profit/Excel, RTD/DDE, ordens ou APIs nativas.

## Próxima etapa F3-INT-35
Especificar protocolo de recuperação e reconciliação entre snapshots divergentes, com testes de impossibilidade de inferir autoridade a partir de uma cópia isolada; continuar sem alegações de persistência real.
