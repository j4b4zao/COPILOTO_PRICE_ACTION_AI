# F3-INT-60

Verificador offline de bytes ZIP com limites, nomes originais, SHA256 externo, manifesto integral, checkpoint atual, sete flags false e logs compativeis com contagens. Hashes sao fornecidos pelo chamador e nao autenticam origem. Ver CORRECOES_F3_INT60.md.

Testes novos: 22/22. Regressao integral da auditoria isolada: 679/679.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-61: portabilidade e colisoes de nomes em pacotes adversariais.
