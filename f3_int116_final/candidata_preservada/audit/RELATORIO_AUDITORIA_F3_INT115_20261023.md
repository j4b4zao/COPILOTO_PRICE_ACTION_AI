# Auditoria tecnica F3-INT-115 CANDIDATA

Data: 2026-10-23. Workspace: C:/COPILOTO_F3_INT114_FINAL.
Resultado: CANDIDATA mantida, com ressalvas tecnicas e correcoes necessarias antes de eventual promocao.
Nenhum defeito de dupla admissao ou autorizacao operacional foi observado nos cenarios executados.
A aprovacao dos testes nao elimina os defeitos de evidencia e robustez descritos abaixo.

## Integridade e escopo

- Manifesto candidato: 10/10 entradas SHA-256 coincidentes antes e depois.
- Manifesto candidato em si preservado; SHA-256: f5062851495e83a111949a2dae93c66f73f74823154c4df413a1f090856b1688.
- Historico: 772/772 arquivos existentes e coincidentes com o inventario do checkpoint, antes e depois.
- Conjunto protegido: 783 arquivos (772 historicos + 10 entradas + manifesto), todos preservados.
- Esta comparacao usa referencia local preexistente, nao autenticada independentemente. Nao comprova alteracoes anteriores a captura original do inventario, nem identidade do executavel.
- Nenhuma implementacao, teste, log, checkpoint ou manifesto candidato foi modificado pela auditoria.

## Revisao dos arquivos candidatos

- `CHECKPOINT_F3_INT115_CANDIDATA.json`: inventario historico, comandos, contagens e exit codes; SHA-256 `41aa42d767edd8d294024ed592aa105babf583c961734ba1f3e420430675d836`.
- `RELATORIO_F3_INT115_CANDIDATA.md`: alegacoes, limitacoes, hashes e tentativas preservadas; SHA-256 `abf7f0ebabef0ea870e684ae0f280faf6590ed15ce86414780a684c75c32040a`.
- `RESULTADO_F3_INT115_ESPECIFICOS.txt`: tentativa com 10 erros de importacao; nao evidencia aprovacao; SHA-256 `ef864db441a9b4bcc0c97856b7a9ad5a4c07e3808af7c7c9f8d11004b4d44473`.
- `RESULTADO_F3_INT115_ESPECIFICOS_CANDIDATA.txt`: tentativa com 8 aprovados e 2 falhas; nao evidencia aprovacao completa; SHA-256 `21d7ce77695e87787fac624567eae66555397a0043127ad2402ad817649bb852`.
- `RESULTADO_F3_INT115_ESPECIFICOS_VALIDACAO.txt`: validacao anterior: 10/10 aprovados; SHA-256 `469743be46136754085b2cb8303f3d0acfdbde224827f9ae639e94b3ebaf1954`.
- `RESULTADO_F3_INT115_REGRESSAO_WINDOWS.txt`: regressao interrompida; nao evidencia conclusao; SHA-256 `4741529bb8be6b4cd0faeb37aa6c8fbd7443388cc30a84040a6832b221dce90c`.
- `RESULTADO_F3_INT115_REGRESSAO_WINDOWS_VALIDACAO.txt`: regressao anterior: 1397 aprovados e 1 skip por symlink; nao repetida nesta auditoria; SHA-256 `4bb97bb6ad7e86833d72f5a6f71ad8de04b0033b3bf60ba82950f3736afc4b12`.
- `tests/test_f3_int115_multiprocess_recovery.py`: dez ensaios e worker subprocesso revisados integralmente; SHA-256 `b76bda86e579883607a4d40981f7cb2e9e65b20e19c87e95e6b4d38978e38366`.
- `tools/f3_int115_multiprocess_recovery.py`: wrapper conservador de reconciliacao; retry sempre false e safe_to_promote false; SHA-256 `ff92b7a3fa53c63e8c50bc5815a8e07880155eac3340b14e699c62a5cb7afd64`.
- `tools/f3_int115_run_candidate.py`: inventario, execucao, parsing, relatorio e manifesto revisados integralmente; SHA-256 `875f66e5a8aea645b8ad7bf6d41067c2d6f6e134ba9ff4c95a2fe4347d61a3bd`.

Tambem foram revisados os modulos historicos 109/110 e o marco 114, sem alteracao.

## Achados e correcoes propostas

### A1 - MEDIA - alegacao de simultaneidade mais forte que o teste

Evidencia: `tests/test_f3_int115_multiprocess_recovery.py:158`.

Dois processos prontos recebem GO sequencialmente. O perdedor pode retornar STATE_ANCHOR_MISMATCH; portanto a aceitacao tambem passa com execucao inteiramente serial. A sondagem reproduziu isso. Nao invalida o teste separado de lock retido, que comprova sobreposicao com STORE_BUSY. Correcao: renomear este teste para disputa sem garantia de sobreposicao; manter/adicionar barreiras que registrem a transacao retida e a tentativa concorrente dentro desse intervalo.

### A2 - MEDIA - esperas IPC nao sao integralmente limitadas

Evidencia: `tests/test_f3_int115_multiprocess_recovery.py:130`.

send() faz write/flush bloqueantes sem deadline. Um worker parado antes de consumir uma fixture maior que a capacidade do pipe pode bloquear o pai antes do timeout da fila. stderr nao e drenado enquanto o filho vive; se encher, o worker pode bloquear. Leitura de stderr apos wait normalmente recebe EOF, mas nao possui limite proprio. Threads leitoras daemon nao sao guardadas/joined e sua fila nao tem limite. Nao houve hang observado; e um defeito de robustez inferido do codigo. Correcao: supervisionar escrita/leitura de ambos os pipes com deadline, limite de bytes, kill/wait e join deterministico de todos os leitores. Nao resolver com sleeps.

### A3 - MEDIA - runner nao confere estabilidade das fontes candidatas

Evidencia: `tools/f3_int115_run_candidate.py:27`.

inventory() exclui por prefixo as fontes 115. Os hashes novos sao calculados depois dos testes. Uma alteracao concorrente das fontes candidatas nao seria detectada pelo inventario historico. A auditoria atual comparou fontes e manifesto antes/depois sem divergencias. Correcao: inventariar explicitamente fontes/dependencias antes da execucao e compara-las apos; separar apenas os caminhos de saida, sem exclusao generica por basename. Isso ainda nao autentica execucao.

### A4 - MEDIA - runner incompleto na trajetoria de timeout

Evidencia: `tools/f3_int115_run_candidate.py:49`.

TimeoutExpired nao e tratado. subprocess.run termina/aguarda o processo direto, mas os workers descendentes nao estao sob supervisao de arvore neste runner. O timeout pode impedir a geracao de checkpoint/relatorio e deixar descendentes ate EOF/encerramento. Nao foi provocado um timeout destrutivo nesta auditoria. Correcao: bloco try/finally que preserve evidencia parcial, registre timeout e exit status, supervisione apenas os processos proprios e finalize os workers antes do encerramento.

### A5 - BAIXA - cobertura original de retry apos ACK perdido e parcial

Evidencia: `tests/test_f3_int115_multiprocess_recovery.py:193`.

O retry original usa somente a ancora anterior; a rejeicao pode ocorrer antes do mecanismo anti-replay. Sondagem adicional com ancora posterior correta confirmou STALE_CHAIN_REVISION, sem mudanca da geracao fixada em 1. Correcao: incorporar esse caso a suite 115 e conferir ACK preservado como LOST/UNKNOWN, flags false e retry_allowed false em cada resultado.

## Concorrencia, atomicidade, isolamento e ACK

- Popen inicia interpretadores independentes, com PIDs diferentes do pai e entre concorrentes. Cada worker abre sua propria conexao sqlite3 para o mesmo arquivo local real; nao ha mock de SQLite.
- Threads sao exclusivamente leitores de stdout. Nao substituem processos na disputa pelo banco.
- A fixture e transmitida em JSON/base64; nenhum objeto de conexao e compartilhado. O hook _checkpoint e alterado apenas no interpretador filho.
- BEGIN IMMEDIATE precede leitura da ancora e verificacao anti-replay; UPDATE de consumed, generation e next_revision fica em uma transacao. Concorrente com lock retido recebe STORE_BUSY.
- A consulta posterior compara o hash de todo o estado esperado: generation=1, next_revision=2 e uma unica entrada consumed. Nos ensaios nao houve dupla admissao.
- Morte antes da escrita/apos UPDATE recuperou estado anterior; morte apos commit recuperou estado posterior sem reenviar confirmacao. Kill ocorre em checkpoints, nao dentro da chamada commit.
- A sondagem com escritor vivo mostrou NOT_COMMITTED observado seguido de COMMITTED apos liberar a transacao: e um snapshot, nao prova de ausencia futura de commit. retry permaneceu false.
- Banco ausente/corrompido, referencia ausente ou incorreta e ACK invalido produzem rejeicao ou estado nao resolvido. Nao ha recriacao automatica, reset ou fallback permissivo.
- Ausencia de ACK e representada pelo canal de retorno interrompido e pela entrada LOST da consulta; nao existe protocolo de transporte ou autenticacao de ACK sob teste.

## Novas execucoes

- ESPECIFICOS: 10 testes, 10 aprovados, 0 falhas, 0 erros, 0 skips; exit code 0; 36.184 s; `LOG_AUDITORIA_F3_INT115_ESPECIFICOS_20261023.txt`.
- SONDAGENS: 3 testes, 3 aprovados, 0 falhas, 0 erros, 0 skips; exit code 0; 27.002 s; `LOG_AUDITORIA_F3_INT115_SONDAGENS_20261023.txt`.

As 3 sondagens aprovadas confirmam limites/controles; nao significam que os achados foram corrigidos.

## Limites e restricoes

- Mesma maquina, usuario e filesystem; pins em diretorio separado nao estabelecem custodia independente.
- Sem prova de durabilidade fisica, falha de energia, seguranca entre hosts ou identidade autenticada do executavel.
- Interleavings limitados; sem stress prolongado, falha dentro de commit, disco cheio ou erro de I/O induzido.
- Nenhuma operacao de rede, corretora, Profit, Excel, RTD/DDE ou ordem real.
- F3 OPEN e sete flags false. ULTIMO_MARCO continua F3-INT-114 FINAL. Sem promocao ou INT-116.
- Correcoes descritas, nao aplicadas aos artefatos candidatos/historicos nesta auditoria.

## Artefatos da auditoria

- `tools/f3_int115_technical_audit_20261023.py`: runner e 3 sondagens reproduziveis.
- `EVIDENCIAS_AUDITORIA_F3_INT115_20261023.json`: hashes comparados, contagens, ambiente e comandos.
- `LOG_AUDITORIA_F3_INT115_ESPECIFICOS_20261023.txt`: repeticao integral dos dez testes.
- `LOG_AUDITORIA_F3_INT115_SONDAGENS_20261023.txt`: execucao das tres sondagens adicionais.
- `MANIFESTO_AUDITORIA_F3_INT115_20261023.json`: SHA-256 dos quatro artefatos anteriores e deste relatorio.
O manifesto nao contem seu proprio hash; seu hash sera apresentado separadamente.
