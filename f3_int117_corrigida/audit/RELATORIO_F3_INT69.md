# F3-INT-69

Minimizacao limitada de pares de traces com divergencia, crash/restart e commit obsoleto; um evento minimo por remocao isolada, sem alegacao de minimo global. Exemplo reduzido de 20 a 7 eventos em 55 checagens.

Testes novos: 12/12. Regressao integral da auditoria isolada: 798/798.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-70: serializacao JSON fechada de testemunhos e replay com digests de traces completos.
