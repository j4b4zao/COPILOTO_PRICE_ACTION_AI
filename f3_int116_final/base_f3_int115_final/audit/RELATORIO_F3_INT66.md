# F3-INT-66

Modelo limitado de crash/restart de atores, descarte de propostas pendentes e rejeicao de geracoes obsoletas; snapshot compartilhado preservado, geracoes sao fixtures locais sem fencing nativo.

Testes novos: 19/19. Regressao integral da auditoria isolada: 765/765.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-67: exploracao limitada de intercalacoes de crash/restart de multiplos atores.
