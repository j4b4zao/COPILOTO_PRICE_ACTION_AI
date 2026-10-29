# F3-INT-96

Replay completo de testemunhos sob politica explicita, rejeitando mudanca de contexto e de traces. Limite de busca e cobertura parcial indicados; politicas sao fixtures do chamador, nao autorizacoes.

Testes novos: 9/9. Regressao integral da auditoria isolada: 1116/1116.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-97: codec JSON schema2 com politica explicita vinculada aos traces.
