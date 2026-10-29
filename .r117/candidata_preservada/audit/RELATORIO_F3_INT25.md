# F3-INT-25 — Auditoria adversarial de inventários (somente simulação)

Base: F3-INT-24, sem alteração dos módulos de modelo. Novo módulo: `tests/test_f3_int25_inventory_adversarial.py`.

## Resultado
- Novos testes: 8/8 PASS, 0 falhas.
- Regressão combinada: 211/211 PASS, 0 falhas/erros, 19.614 s.
- Explorações anteriores integradas na regressão: INT10 12.000 transições, INT13 180.000 transições, INT14 30.000 transições e INT15 4.692 transições; nenhuma violação relatada nessas explorações limitadas.
- Não foi criada exploração de estados nova específica para F3-INT-25.

## Cobertura adicionada
Ordem inversa de reconciliação, tentativa não reconhecida, CREATED sem processo, FAILED com processo residual declarado, evidência idêntica duplicada, conflito material tardio após emissão de ticket, cobertura de saída/contenção de descendentes e geração nova invalidando ticket antigo.

## Limites
Todos os testes utilizam premissas de fixtures e objetos Python sintéticos. Não demonstram autenticação real, inventário nativo completo, atomicidade entre processos, Job Object, deadline estrito ou segurança para negociação. Os cenários são selecionados e não constituem prova exaustiva. A especificação F3-INT-19 não foi alterada.

F3=OPEN; orders_allowed=false; live_certified=false; flow_complete=false; f3_resolved=false; native_prototype_authorized=false; strict_deadline_guaranteed=false; authenticated_witness_verified=false.
