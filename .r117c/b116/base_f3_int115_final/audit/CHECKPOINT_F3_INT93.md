# F3-INT-93

Corpus limitado de 25 mutacoes de bundle: quatro transformacoes validas com contratos de identidade e mutacoes invalidas rejeitadas. Limites pequenos proprios de bytes, entradas e cobertura, sem alegacao de exaustividade.

Testes novos: 6/6. Regressao integral da auditoria isolada: 1087/1087.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-94: verificacao integrada de pacote, bundle anexado, catalogo, replay e pin de observacoes.
