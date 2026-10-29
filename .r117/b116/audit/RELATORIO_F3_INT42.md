# RELATÓRIO F3-INT-42 — Transferências falsificadas e visões divergentes

Novo simulador `tools/f3_int42_adversarial_handoff_simulator.py` compara duas visões de eventos em memória e uma referência fixada por hipótese. São identificados conflitos entre bifurcações, sufixos incompletos, referências ausentes e referências conflitantes.

14 novos testes adversariais aprovados; regressão total 338/338 aprovada.

**Limites:** a referência fixada é apenas injetada pelo teste. Não existe prova de origem, assinatura, relógio confiável, consenso distribuído, persistência durável ou fencing nativo. Eventos forjados podem ser localmente consistentes. O resultado não autentica qualquer autoridade.

**Estado:** F3=OPEN; orders_allowed=false, live_certified=false, flow_complete=false, f3_resolved=false, native_prototype_authorized=false, strict_deadline_guaranteed=false, authenticated_witness_verified=false.

Próximo: F3-INT-43 — simular reconciliação sob partições e testemunhos independentes, sem promoção operacional.
