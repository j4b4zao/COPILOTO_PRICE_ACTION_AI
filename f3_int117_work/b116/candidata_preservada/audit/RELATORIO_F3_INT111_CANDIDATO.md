# F3-INT-111 — auditoria adversarial candidata

Base: F3-INT-110 FINAL. Testes novos: 12/12 no ambiente local de construção.

## Contraexemplos e limites
- Restauração conjunta de DB e pins: o observador pode aceitar estado anterior; **impossível detectar** sem referência externa independente e não restaurada. O booleano de atestação não é prova.
- PIN ausente ou inválido: fail-closed; pin derivado do próprio DB não demonstra independência.
- PIN antigo ou divergente: resultado inconclusivo, sem promoção.
- Corrupção, ausência do banco, divergência de escopo: fail-closed.
- Concorrência entre observação e ação: consulta não constitui lock/fencing e não autoriza decisão operacional. Teste usa injeção de resultado inconclusivo, **não** prova exclusão concorrente real.
- ACK perdido: status observado não garante entrega exatamente uma vez nem durabilidade física.

## Implementação
`tools/f3_int111_adversarial_reconciliation.py`: avaliação **somente consultiva**, flags de segurança invariavelmente falsas.
`tests/test_f3_int111_adversarial_reconciliation.py`: 12 cenários adversariais.

## Limites e pendências
Não há autenticação da origem dos pins, atestação confiável, commit distribuído, fencing, prova de durabilidade física ou autorização operacional. Regressão histórica integral pendente no Windows. `ULTIMO_MARCO.json` permanece F3-INT-110. F3 permanece OPEN.
