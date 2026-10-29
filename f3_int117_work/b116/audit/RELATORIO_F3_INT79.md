# F3-INT-79

Linhagem sobre resumos imutaveis de envelopes, ate 128 pacotes e 128MiB agregados, com contagens contiguas e substituicoes declaradas. Limite de arquivos explicito por envelope; nenhuma mudanca em fontes historicos ou flags. Correcao de fixture documentada.

Testes novos: 13/13. Regressao integral da auditoria isolada: 924/924.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-80: contratos diferenciais de envelopes sob politicas explicitas.
