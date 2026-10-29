# F3-INT-97

Codec fechado schema2 inclui politica no snapshot e nos digests dos traces; catalogo externo limitado e replay completo sob o contexto declarado. Schemas historicos separados, sem classes dinamicas, sistemas reais ou certificacao.

Testes novos: 13/13. Regressao integral da auditoria isolada: 1129/1129.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-98: bundles e registro tipado para testemunhos schema2 sob politicas explicitas.
