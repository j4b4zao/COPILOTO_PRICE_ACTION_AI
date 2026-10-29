# F3-INT-72

Ingestao atomica de lote offline com limite de bytes, registros e memoria; hashes de transporte, replay de cada testemunho e deteccao de duplicatas canonicas inclusive com formatacao diferente. Rejeicao preserva identidade do registro anterior; reset pelo chamador permanece vulneravel.

Testes novos: 14/14. Regressao integral da auditoria isolada: 836/836.

F3=OPEN. Sete bloqueios operacionais permanecem false: orders_allowed, live_certified, flow_complete, f3_resolved, native_prototype_authorized, strict_deadline_guaranteed, authenticated_witness_verified.

Todos os pins, digests, membros e votos sao fixtures do chamador. Resultados simulados nao certificam autenticidade, consenso, persistencia, independencia de testemunhas, fencing nativo ou operacao real. Nenhuma conexao com sistemas reais ou envio de ordens.

Escopo da regressao: todos os testes do pacote F3 isolado; a suite operacional do repositorio principal nao foi executada.

Proximo: F3-INT-73: verificacao de linhagem de pacotes e preservacao de fontes anteriores.
