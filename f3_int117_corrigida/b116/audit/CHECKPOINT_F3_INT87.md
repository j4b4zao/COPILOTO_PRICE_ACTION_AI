# F3-INT-87

Monitor independente de condicoes necessarias para importacoes comuns e com politica; versao, append de registro, recibos e preservacao de contexto. Contraprova de forja que preserva invariantes: monitor nao substitui replay.

Testes novos: 15/15. Regressao integral da auditoria isolada: 1022/1022.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-88: replay de testemunhos de divergencia de conteudo, ordem e versao nas agendas de importacao.
