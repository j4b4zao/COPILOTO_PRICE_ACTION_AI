# F3-INT-74

Linhagem offline com substituicoes declaradas por etapa, caminho e hashes antes/depois; motivos sao anotacoes do chamador, nao autorizacao. Rejeita alteracoes nao declaradas, remocoes, deltas duplicados ou sem uso e preserva verificacao estrita anterior.

Testes novos: 19/19. Regressao integral da auditoria isolada: 866/866.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-75: contratos cruzados de declaracoes e fontes adversariais em linhagens simuladas.
