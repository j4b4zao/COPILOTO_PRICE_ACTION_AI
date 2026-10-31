# F3-INT-121 A14.4 — FINAL DOCUMENTAL
Data: 2026-10-29. Fonte de execução: log Windows fornecido pelo usuário (não reexecutado independentemente).

- Testes específicos: 3/3 em modo normal e 3/3 em modo -O, segundo log anteriormente fornecido.
- Regressão integral: 178/178 em 527.013 s (normal), 178/178 em 516.726 s (-O); 356/356; 0 falhas registradas.
- Cenários: supervisor primeiro, worker primeiro, encerramentos em rápida sucessão; contraprovas detectadas e limpeza externa confirmada no escopo.
- Limite: não prova simultaneidade exata nem todos os interleavings do Windows.
- F3=OPEN; offline=true; simulation_only=true; real_operations_authorized=false; production_certification=false.
- Próxima etapa A14.5: repetibilidade das contraprovas em múltiplos espécimes; implementação autorizada pelo pedido de prosseguimento.
