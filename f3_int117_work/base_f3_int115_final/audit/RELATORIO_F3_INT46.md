# RELATÓRIO F3-INT-46 — Auditoria simulada multiépoca

Escopo: reconfigurações de múltiplas épocas, rollback de composição, repetições, saltos, predecessores incorretos, partições prolongadas (representadas por estado `partitioned`), quóruns insuficientes e suspeita de conluio.

## Implementação
- `tools/f3_int46_multiepoch_simulator.py`: avalia uma cadeia de Membership com pins explícitos por época, continuidade estrita e avaliação de quóruns adjacentes por `assess_joint`.
- `tests/test_f3_int46_multiepoch.py`: 16 novos testes isolados.
- Sem alterações no núcleo operacional ou integrações externas.

## Execução
- Testes novos: 16/16 OK.
- Regressão completa: 398/398 OK, 28,510 segundos; log `TESTES_F3_INT46_COMPLETOS.log`.
- Testes de exploração mantêm limites predefinidos; ausência de contraexemplos nesses limites não é prova de exaustividade.

## Limitações e segurança
- Pins, votos, testemunhas, épocas e estado de partição são entradas controladas no simulador, não fatos autenticados.
- A validação por pares adjacentes não constitui prova de consenso global, independência de testemunhas, armazenamento durável, autenticação, tolerância a falhas bizantinas ou proteção real contra rollback.
- F3=OPEN. `orders_allowed=false`, `live_certified=false`, `flow_complete=false`, `f3_resolved=false`, `native_prototype_authorized=false`, `strict_deadline_guaranteed=false`, `authenticated_witness_verified=false`.
- Não houve interação com Profit, Excel, DDE/RTD, ordens, sistema Windows ou mercado ao vivo.

## Próxima etapa proposta
F3-INT-47: examinar reconfigurações com mudanças não adjacentes, evidências de histórico truncado e limites do modelo de quórum conjunto sob adversários coordenados.
