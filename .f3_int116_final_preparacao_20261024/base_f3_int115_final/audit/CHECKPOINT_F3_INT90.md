# F3-INT-90

Bundle ZIP fechado e lido apenas em memoria: cobertura exata, hashes, limites e replay de catalogo e testemunhos. Metadados externos fixos para repetibilidade local, sem atestacao temporal. Exemplo .witnessbundle inclui catalogo sintetico.

Testes novos: 12/12. Regressao integral da auditoria isolada: 1060/1060.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-91: registro tipado atomico de referencias e observacoes finitas de evidencias.
