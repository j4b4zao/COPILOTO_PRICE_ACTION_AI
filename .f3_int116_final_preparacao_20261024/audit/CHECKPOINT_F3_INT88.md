# F3-INT-88

Testemunhos reproduziveis de agendas de importacao, classificando conteudo, ordem e versao separadamente. Rejeita status e snapshots adulterados; busca por pares finitos com cobertura parcial explicita.

Testes novos: 12/12. Regressao integral da auditoria isolada: 1034/1034.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-89: formato JSON fechado com referencias SHA256 a catalogo externo de pacotes.
