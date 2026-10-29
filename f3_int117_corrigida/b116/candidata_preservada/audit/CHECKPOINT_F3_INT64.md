# F3-INT-64

Monitor independente de condicoes necessarias: rejeicoes e prepare preservam snapshot, commit incrementa versao e estende memoria e prefixos. Contraprova de adulteracao que preserva invariantes demonstra que monitor nao substitui replay completo.

Testes novos: 17/17. Regressao integral da auditoria isolada: 734/734.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-65: comparacao diferencial entre monitor de invariantes e replay integral dos traces.
