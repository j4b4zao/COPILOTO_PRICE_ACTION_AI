# F3-INT-54

Exploracao limitada e deterministica de agendas prepare/commit; divergencia de vencedores e de snapshots compartilhados com mesma versao, rastros completos e indicador de cobertura incompleta.

Testes novos: 24/24. Regressao integral da auditoria isolada: 572/572.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-55: testemunhos reproduziveis de divergencia e rejeicao de traces adulterados.
