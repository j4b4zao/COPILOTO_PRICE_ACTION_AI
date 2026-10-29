# F3-INT-94

Verificacao integrada pacote->bundle->catalogo->testemunho->traces->observacoes. Pins externos conferidos em cada camada e limite proprio de anexo; cadeia consistente nao e autenticacao independente nem certificacao.

Testes novos: 11/11. Regressao integral da auditoria isolada: 1098/1098.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-95: agendas de importacao sob politica imutavel explicitamente vinculada ao contexto.
