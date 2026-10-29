# F3-INT-115 CANDIDATA CORRIGIDA

Resultado da validacao: False. Apenas revisao; sem promocao para FINAL.
F3 OPEN; sete flags false; offline/simulacao. ULTIMO_MARCO permanece F3-INT-114 FINAL.

## Cinco correcoes implementadas

1. Concorrencia: escritor retido em BEGIN IMMEDIATE; concorrente deve retornar STORE_BUSY antes de CONTINUE. STATE_ANCHOR_MISMATCH nao e aceito como prova de sobreposicao.
2. IPC: deadlines absolutos/watchdog por processo, write supervisionado, stdout/stderr drenados em paralelo, limites de bytes/filas, kill e join dos leitores/escritores. Entrada do worker tambem esta sob watchdog externo.
3. SHA-256: todas as fontes Python, inclusive 115 e dependencias, fixadas antes e comparadas apos cada execucao e no finally. Alteracao, adicao e exclusao falham fechadas.
4. Timeout: Job Objects Windows com KILL_ON_JOB_CLOSE; gate impede execucao antes da contencao. Descendentes herdam o Job; timeout preserva log parcial e execution.json; finally encerra a arvore e confere zero processos ativos/threads de IPC. Falha de contencao nao usa fallback permissivo.
5. ACK/replay: testes com ancora atual e anterior, dois retries concorrentes, ACK UNKNOWN/LOST/RECEIVED, referencias divergentes, escritor pendente e rollback apos limpeza do supervisor; consultas mantem retry false.

## Arquivos alterados

- `tests/test_f3_int115_multiprocess_recovery.py`: `b76bda86e579883607a4d40981f7cb2e9e65b20e19c87e95e6b4d38978e38366` -> `56b5d83f26a10b6acf9ae896342a493bef29cf0d21b44600bfc266d7e84da3d3`; copia original: `PRESERVADO_F3_INT115_PRE_CORRECAO_20261023/tests/test_f3_int115_multiprocess_recovery.py`.
- `tools/f3_int115_run_candidate.py`: `875f66e5a8aea645b8ad7bf6d41067c2d6f6e134ba9ff4c95a2fe4347d61a3bd` -> `b01a1ad10f8a0374ed30c8f21c63c111e3bebfe5a8d5c37544b2faf45e88391b`; copia original: `PRESERVADO_F3_INT115_PRE_CORRECAO_20261023/tools/f3_int115_run_candidate.py`.

Novos arquivos de codigo: tools/f3_int115_process_control.py, tests/test_f3_int115_process_control.py.
A candidata anterior completa foi preservada byte a byte no diretorio PRESERVADO_F3_INT115_PRE_CORRECAO_20261023.
O manifesto candidato antigo continua descrevendo a revisao anterior; valide-o nesse diretorio preservado.

## Testes e evidencias

- ESPECIFICOS: 28 testes; 28 aprovados, 0 falhas, 0 erros, 0 skips; exit code 0; timeout=False; 97.732 s; cleanup={'active_processes': 0, 'live_io_threads': [], 'direct_exit_code': 0}; fontes alteradas=[].
- REGRESSAO_COMPLETA: 1416 testes; 1414 aprovados, 1 falhas, 0 erros, 1 skips; exit code 1; timeout=False; 794.403 s; cleanup={'active_processes': 0, 'live_io_threads': [], 'direct_exit_code': 1}; fontes alteradas=[].

Testes de controle provocam bloqueio de stdin, falta de stdout, stderr volumoso, overflow, timeout de espera, timeout com descendente e saida do pai deixando descendente. Tambem testam deteccao de mudanca/exclusao/adicao de fonte e footer incompleto.
O skip esperado da regressao e symlink sem permissao; consulte a saida para a ocorrencia real.

772 arquivos historicos: divergencias=[].
Candidata anterior arquivada: divergencias=[].
Arquivos preexistentes durante a execucao: divergencias=['AUDITORIA_F3_INT115_PRE_FINAL_20261023/SUPERVISAO_RUNNER.log'].
Fontes alteradas durante execucao: [].
Excecao do runner: None.

## Limites

- Deadlines sao de supervisao local e podem sofrer atraso do SO; nao ha garantia de tempo real.
- Contencao usa APIs locais Windows; falha de SO/kernel ou processo hostil com privilegio superior nao foi validada.
- Hash antes/depois nao detecta alteracao transitoria restaurada e nao autentica executavel/custodia independentemente.
- Sem prova de durabilidade fisica, seguranca entre computadores ou entrega exatamente uma vez.
- Kill nos checkpoints nao equivale a falha dentro de commit ou queda de energia.
- Sem rede, corretora, Profit, Excel, RTD/DDE, ordens reais ou INT-116.
- Logs e manifesto desta revisao sao novos; relatorios/checkpoints anteriores nao foram substituidos.
