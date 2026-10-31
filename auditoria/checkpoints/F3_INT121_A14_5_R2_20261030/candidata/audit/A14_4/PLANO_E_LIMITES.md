# F3-INT-121 A14.4 — Candidata, ordem de encerramento

Data: 2026-10-29. Três testes Windows isolados:

1. Supervisor primeiro: proteção interna ativa, exigir os quatro handles sinalizados antes da limpeza externa.
2. Worker primeiro: proteção interna propositalmente desativada no espécime negativo, depois supervisor; exigir detecção de descendentes restantes antes da limpeza externa.
3. Worker e supervisor em rápida sucessão: sem espera entre pedidos de término, espécime negativo; exigir detecção de descendentes restantes antes da limpeza externa. **Não prova simultaneidade real do Windows**.

Em todos os casos: processos fixados por ProcessRef e associação ao Job externo, limpeza externa incondicional no finally, confirmação de zero processos após limpeza, nenhum acesso operacional ou autorização real.

Candidata: verificação de sintaxe e ZIP local apenas. Necessita testes específicos e regressões completas no Windows, modo normal e -O. Esperado: 178 testes por modo se descoberta não duplicar classes.

F3=OPEN; offline=true; simulation_only=true; real_operations_authorized=false.
