# F3-INT-35 — Reconciliação simulada de cópias

Escopo: exclusivamente simulação Python em memória; nenhuma interação com sistema operacional nativo, trading, Profit ou ordens.

## Implementação
- Novo `tools/f3_int35_reconciliation_simulator.py`: valida cada cadeia com replay, compara prefixos, identifica divergência e verifica opcionalmente âncora de integridade fornecida externamente.
- Novo `tests/test_f3_int35_reconciliation.py`: seis testes de cópias idênticas, prefixo, divergência, corrupção, âncora ausente e âncora válida sem promoção.
- Código anterior preservado.

## Resultados
- Novos testes: 6/6.
- Regressão completa: 260/260, 30.471 segundos, sem falhas.
- A comparação de cópias não estabelece consenso, eleição de líder, commit durável ou identidade da fonte da âncora.
- Uma âncora fornecida pelo chamador não é autenticada pelo simulador.
- A verificação de integridade por SHA-256 não fornece autenticação contra um agente capaz de reescrever os registros e recalcular hashes.
- Não foram executadas nesta etapa provas de persistência real, testes entre processos ou validação nativa.

## Estado de segurança
F3=OPEN. `orders_allowed=false`, `live_certified=false`, `flow_complete=false`, `f3_resolved=false`, `native_prototype_authorized=false`, `strict_deadline_guaranteed=false`, `authenticated_witness_verified=false`.

## Próximo passo sugerido
F3-INT-36: testar modelo simulado de âncora confiável e rollback, mantendo a distinção entre integridade, autenticação e durabilidade.
