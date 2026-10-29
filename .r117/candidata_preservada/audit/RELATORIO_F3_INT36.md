# F3-INT-36 — Auditoria simulada de âncora e rollback

Escopo: exclusivamente Python em memória, em diretório isolado. Nenhum código operacional, integração Profit/Excel, API nativa ou ordens.

## Implementação
- `tools/f3_int36_anchor_rollback_simulator.py`: avalia cópias contra âncora (sequência e checksum) fornecida pelo chamador, diferencia rollback/incompletude, conflito de âncora, sufixo não verificado e divergência entre cópias.
- `tests/test_f3_int36_anchor_rollback.py`: oito testes, incluindo adulteração, rollback, âncora inválida, divergência pós-âncora e não promoção.
- Modelo principal de recuperação e módulos anteriores inalterados.

## Resultados executados
- Testes novos isolados: 8/8, sem falhas.
- Regressão completa: 268/268, sem falhas, 26.987 s (unittest).
- Exploração F3-INT-13: 180000 transições tentadas, zero contraexemplos, parou no limite de transições; não exaustiva.

## Limitações essenciais
A âncora é uma **hipótese fornecida pelo chamador**, não autenticada. Um adversário capaz de substituir âncora e registros pode reescrever o histórico. Não há armazenamento durável, assinatura, hardware seguro, consenso, bloqueio entre processos, recuperação nativa ou prova de fechamento real. O código sempre nega promoção de autoridade e autorização de encerramento.

## Estado
F3=OPEN; orders_allowed=false; live_certified=false; flow_complete=false; f3_resolved=false; native_prototype_authorized=false; strict_deadline_guaranteed=false; authenticated_witness_verified=false.

## Próximo passo
F3-INT-37: avaliar ataques simulados à própria âncora (rollback coordenado de âncora + registro) e especificar requisitos para fonte externa autenticada, sem implementar integração nativa.
