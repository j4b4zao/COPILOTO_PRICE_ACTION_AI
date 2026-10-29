# RELATÓRIO F3-INT-41 — Simulação de transferência de workers

Implementado `tools/f3_int41_worker_handoff_simulator.py`, sem dependência operacional.

14 testes adicionais: fencing de writer antigo, handoff sem release, geração pulada, token repetido, parent causal inválido, release duplicado, conflito de writer e expectativa de geração.

**Limitação:** os eventos e tokens são dados injetados em memória; não há assinatura, prova de origem, consenso, isolamento entre processos, persistência durável ou garantia de fencing nativo. `fixture_consistent=True` apenas significa consistência no modelo.

**Estado:** F3=OPEN. `orders_allowed=false`, `live_certified=false`, `flow_complete=false`, `f3_resolved=false`, `native_prototype_authorized=false`, `strict_deadline_guaranteed=false`, `authenticated_witness_verified=false`.

Próximo: F3-INT-42 — adversários que falsificam release, token e epoch em visões divergentes, mantendo fail-closed.
