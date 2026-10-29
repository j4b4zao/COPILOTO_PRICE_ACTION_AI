# F3-INT-52

Continuidade exata de prefixos de membros e votos entre rodadas simuladas; rejeicao de reescrita, truncamento e mutacao parcial de estado. Expectativa de status herdado corrigida; ver CORRECOES_F3_INT52.md.

Testes novos: 23/23. Regressao integral da auditoria isolada: 526/526.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-53: intercalacoes adversariais de recuperacoes concorrentes sobre o mesmo snapshot simulado.
