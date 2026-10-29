# F3-INT-85

Tentativas limitadas de importacao com commits concorrentes interpostos; rebase preserva deteccao canonica de replay. Esgotamento nao apaga commits de contendores e nao implica sucesso eventual; registros continuam memoria do chamador.

Testes novos: 11/11. Regressao integral da auditoria isolada: 996/996.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-86: politicas de envelope vinculadas ao snapshot e a proposta de importacao.
