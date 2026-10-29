# F3-INT-70

Codec JSON fechado, limitado e sem classes dinamicas; testemunhos de crash sao reconstruidos e seus traces completos comparados por digest. Exemplo canonico de 3907 bytes e formato documentado. Digests nao autenticam origem.

Testes novos: 18/18. Regressao integral da auditoria isolada: 816/816.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-71: corpus deterministico de mutacoes adversariais do formato JSON.
