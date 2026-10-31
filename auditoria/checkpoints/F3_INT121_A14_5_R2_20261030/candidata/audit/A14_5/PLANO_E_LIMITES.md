# A14.5 — Candidata: repetibilidade das contraprovas

Dois testes Windows: três espécimes frescos worker-first e três espécimes frescos em rápida sucessão, todos com proteção interna desativada **somente no espécime negativo**. Reutiliza A14.4, que exige descendentes sobreviventes antes da limpeza e zero processos após limpeza, com limpeza externa em finally.

A14.5 não prova ausência de intermitência em produção, cobertura exaustiva de agendamentos nem simultaneidade exata. Não modifica código operacional. A regressão esperada é 180 testes por modo (178+2), desde que não haja duplicação na descoberta.

F3=OPEN; offline=true; simulation_only=true; real_operations_authorized=false.
