# F3-INT-51

Memoria imutavel simulada entre rodadas; replay de rodadas e evidencias, rollback, conflito de pin, limites cumulativos e rejeicao atomica sem consumir estado. Falha inicial de prefixo de status corrigida; ver CORRECOES_F3_INT51.md.

Testes novos: 25/25. Regressao integral da auditoria isolada: 503/503.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-52: continuidade do historico e vinculo de prefixo entre rodadas de recuperacao.
