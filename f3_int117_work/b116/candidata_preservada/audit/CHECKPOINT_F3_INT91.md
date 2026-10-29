# F3-INT-91

Registro tipado de evidencias distinto do registro de testemunhos consumidos: pares de IDs de referencia e observacoes, namespace separado, rejeicao atomica de replay e falhas. Reset pelo chamador permite replay novamente.

Testes novos: 13/13. Regressao integral da auditoria isolada: 1073/1073.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-92: relacao entre identidade de referencias e igualdade de observacoes finitas.
