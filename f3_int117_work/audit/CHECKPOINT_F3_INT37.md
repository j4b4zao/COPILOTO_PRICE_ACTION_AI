# CHECKPOINT F3-INT-37

- Concluído: 8 testes novos; regressão 276/276.
- Demonstrado ataque coordenado ao registro e à âncora: cadeia autoconsistente não autentica origem.
- Comparação com referência externa simulada rejeita divergências, mas não autentica a referência.
- Código principal preservado; nenhuma integração operacional.
- F3=OPEN; `orders_allowed`, `live_certified`, `flow_complete`, `f3_resolved`, `native_prototype_authorized`, `strict_deadline_guaranteed`, `authenticated_witness_verified` = false.
- Próximo: F3-INT-38, revogação/expiração/comprometimento simulados e política fail-closed.
