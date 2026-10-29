# F3-INT-83

Modelo sequencial de propostas concorrentes de importacao: revalidacao completa no commit, snapshots obsoletos e candidatos forjados rejeitados, versao limitada e deteccao canonica de replay na rebase. Reset integral pelo chamador permanece limitacao demonstrada.

Testes novos: 17/17. Regressao integral da auditoria isolada: 975/975.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-84: divergencias de ordem e conteudo em agendas de importacao.
