# RELATÓRIO F3-INT-43 — Partições e testemunhos simulados

## Escopo
Implementado `tools/f3_int43_partition_reconciliation_simulator.py`, com comparação offline e determinística de duas visões locais de transferência de autoridade e declarações de testemunhas fornecidas pelo chamador. Sem I/O, redes, chaves, APIs nativas ou operações de mercado.

## Resultado
- Novos testes: 14/14 (`TESTES_F3_INT43.log`).
- Regressão: 352/352 (`REGRESSAO_F3_INT43.log`).
- Status: sem falhas finais.

## Casos cobertos
Fork após prefixo comum, ausência de testemunhas, histórico idêntico não autenticado, prefixo incompleto, testemunho conflitante, testemunho futuro, identidade duplicada, independência não declarada, testemunho malformado, entrada inválida, histórico local inválido e acordo forjado.

## Limites de confiança
`independent=True` é mera declaração do fixture, não prova de independência. Testemunhos não são assinados nem autenticados. Hashes, igualdade e concordância não estabelecem consenso, autoridade nativa, durabilidade ou segurança operacional. Todos os resultados mantêm `authenticated=False`, `authoritative=False`, `closure_authorized=False`, `witness_verified=False`; `safe_to_promote` retorna `False`.

## Segurança
F3=OPEN. `orders_allowed=false`, `live_certified=false`, `flow_complete=false`, `f3_resolved=false`, `native_prototype_authorized=false`, `strict_deadline_guaranteed=false`, `authenticated_witness_verified=false`.

## Próximo passo sugerido
F3-INT-44: simular falhas bizantinas de testemunhas, conluio e mudança de composição de testemunhas, sem inferir autenticidade real.
