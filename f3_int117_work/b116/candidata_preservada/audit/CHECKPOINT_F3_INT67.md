# F3-INT-67

Exploracao limitada de programas prepare/crash/commit obsoleto/reprepare/commit. Familia de dois atores com 252 intercalacoes e oracle local de geracoes e preservacao de snapshots; tres atores com cobertura explicitamente parcial.

Testes novos: 9/9. Regressao integral da auditoria isolada: 774/774.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-68: testemunhos reproduziveis de divergencias entre agendas com crash/restart.
