# F3-INT-38 — Relatório técnico

Escopo: simulação isolada do ciclo de vida de credenciais. Base: pacote F3-INT-37.

## Resultado
- 10/10 novos testes passaram.
- 286/286 testes da regressão completa passaram em 26,658 s.
- Nenhuma alteração no código operacional ou no modelo de recuperação principal.
- Novo módulo `tools/f3_int38_credential_lifecycle_simulator.py` e nova suíte `tests/test_f3_int38_credential_lifecycle.py`.

## Cobertura
Validade temporal inclusiva no início e exclusiva no fim; revogação; comprometimento; geração abaixo do piso; identidade divergente; credencial malformada; referência de integridade divergente; referência idêntica mas não autenticada. Um erro detectado no primeiro teste de referência divergente foi corrigido no módulo novo antes da regressão final.

## Limitações
Relógios, emissores, revogações, chaves e referências são fixtures, sem assinatura digital verificada, fonte de tempo confiável, revogação externa autenticada ou prova nativa. O modelo não concede autoridade. F3=OPEN; orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed e authenticated_witness_verified permanecem false.

## Próxima etapa sugerida
F3-INT-39: rotação de chaves e janelas de revogação, incluindo evidências atrasadas e relógios divergentes, exclusivamente simuladas.
