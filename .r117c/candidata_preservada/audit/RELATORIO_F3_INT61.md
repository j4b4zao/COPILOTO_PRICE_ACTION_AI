# F3-INT-61

Preflight offline sem extracao: nomes portaveis, dispositivos Windows, normalizacao Unicode, colisoes de caixa e conflitos arquivo/diretorio; preserva rejeicoes de integridade herdadas.

Testes novos: 12/12. Regressao integral da auditoria isolada: 691/691.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-62: JSON de checkpoint estrito e rejeicao de logs ambiguos.
