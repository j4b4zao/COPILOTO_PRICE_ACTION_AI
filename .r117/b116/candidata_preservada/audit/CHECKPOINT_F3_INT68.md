# F3-INT-68

Testemunhos reproduziveis de divergencia entre agendas com crash/restart, replay de traces completos, rejeicao de flags, geracoes, status e snapshots adulterados; cobertura finita explicita.

Testes novos: 12/12. Regressao integral da auditoria isolada: 786/786.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-69: minimizacao limitada de pares de traces preservando predicado de crash e commit obsoleto.
