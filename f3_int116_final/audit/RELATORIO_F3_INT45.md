# Relatório F3-INT-45 — Quóruns conjuntos e partições

## Escopo
Simulador Python puro, offline, de transições entre dois conjuntos de testemunhas, interseção matemática de quóruns, partições e falhas de confiança. Não conecta à plataforma de negociação, Excel, APIs nativas, ordens ou mercado real.

## Implementação
- `tools/f3_int45_joint_quorum_simulator.py`: valida membership, pins de época, vínculo predecessor, votos duplicados ou estranhos, comprometimento e conluio declarado.
- Calcula condição suficiente para interseção de **quaisquer** quóruns antigos e novos: `threshold_old + threshold_new > |members_old ∪ members_new|`. Um mero conjunto de membros sobrepostos não é suficiente.
- Mesmo com condição satisfeita e votos compartilhados, retorna `JOINT_FIXTURE_UNAUTHENTICATED`; sob partição, `PARTITION_CONTESTED_UNAUTHENTICATED`.
- `safe_to_promote` sempre retorna `False`.

## Testes
- Novos: 14/14 aprovados.
- Regressão: 382/382 aprovados, 0 falhas, 27.626 segundos.
- Na primeira rodada, um teste utilizava predecessor válido ao esperar transição inválida; corrigiu-se apenas o fixture de teste, depois executou-se a regressão completa.

## Limitações
Os conjuntos, votos, pins e marcadores de comprometimento são fornecidos pelo chamador. A verificação não comprova assinatura, identidade, independência, consenso distribuído, durabilidade, fencing real ou autenticidade de testemunhas. Não é prova de segurança nativa.

## Invariantes
F3=OPEN. `orders_allowed`, `live_certified`, `flow_complete`, `f3_resolved`, `native_prototype_authorized`, `strict_deadline_guaranteed` e `authenticated_witness_verified` continuam `false`.

## Próxima proposta
F3-INT-46: explorar sequências de reconfiguração de múltiplas épocas, rollback de membership e partições prolongadas, mantendo os bloqueios.
