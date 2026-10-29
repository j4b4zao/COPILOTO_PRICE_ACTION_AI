# F3-INT-117 CANDIDATA — 24/10/2026

Status: CANDIDATA PARA AUDITORIA. Base F3-INT-116 FINAL. Nenhuma promocao. F3 OPEN; sete flags false; offline/simulation_only true, certification false, retry_allowed false. Nenhuma operacao real.

## Arquivos criados e preservacao

Quatro fontes novos; nenhum fonte herdado modificado:
- audit/tests/test_f3_int117_runner.py
- audit/tests/test_f3_int117_sqlite_write_faults.py
- audit/tools/f3_int117_run_audit.py
- audit/tools/f3_int117_sqlite_write_faults.py
- audit/EVIDENCIAS_F3_INT117/: inventarios, logs e metadados das duas execucoes supervisionadas.
- audit/RELATORIO_F3_INT117_CANDIDATA.md, audit/MANIFESTO_F3_INT117_CANDIDATA.json e sidecar.
- Scripts de preparacao/empacotamento e inventario externo preservados em candidate_build/ no ZIP.

Todos os 3559 arquivos da base FINAL foram conferidos antes/depois na origem, na candidata e em b116/. Os marcadores do workspace e o checkpoint F3-INT-116 FINAL continuam inalterados. Os 1438 testes herdados nao foram editados. A copia da base e somente insumo de auditoria; nunca recebe escrita dos experimentos.

## Implementacao e resultados SQLite

A sonda usa apenas conexoes proprias e diretorios TemporaryDirectory. Nao substitui store._connect, consume_chain, sqlite3.connect nem outros globais. O escritor offline independente reutiliza _load/_encode/_digest e verify_typed_chain da base; nao e uma nova instrumentacao de consume_chain. Reconciliacao e replay usam os modulos herdados inalterados.
Fixtures contem historico canonico sintetico, explicitamente nao autenticado. Ancoras before/after sao calculadas e retidas antes da tentativa. Uma calibracao limitada prepara copias independentes, comprova crescimento real no controle e exige identidade dos bytes iniciais entre controle e alvo.

| Cenario | Resultado nativo | Fase observada | Estado reaberto |
|---|---|---|---|
| Controle sem limite | Commit concluido | COMMIT retornou | after-state integral |
| Limite de paginas | SQLITE_FULL (13) | UPDATE | before-state integral |
| Conexao URI mode=ro | SQLITE_READONLY (8) | UPDATE | before-state integral |

O controle cresceu de 2 para 3 paginas de 512 bytes. FULL aplicou e leu de volta max_page_count=2 na mesma conexao usada pelo escritor. A tentativa falhou antes de entrar em commit. READONLY usou acesso ro com query_only=0; o codigo veio do motor, nao de excecao Python fabricada. As duas falhas mantiveram tambem o hash dos bytes do banco.
Apos fechamento/reabertura: integrity_check=ok, estado canonico comparado integralmente, ancoras preservadas e reconciliacao NOT_COMMITTED_OBSERVED_UNAUTHENTICATED nas falhas; COMMITTED_OBSERVED_UNAUTHENTICATED no controle. Referencias divergentes retornaram RECONCILIATION_UNRESOLVED; ancora ausente retornou INVALID_RECONCILIATION_PIN. Nenhum desses estados concede retry.
Replay de cadeia ja registrada: STATE_ANCHOR_MISMATCH com ancora antiga e STALE_CHAIN_REVISION com ancora atual. No controle positivo, a cadeia recem-gravada tambem foi rejeitada nas duas modalidades. A operacao cuja escrita falhou nao e falsamente declarada consumida: ela nao foi repetida; automatic_retries=0. As tentativas explicitas de replay exercitam cadeias ja consumidas, nao um retry automatico da operacao que falhou.

## Execucoes e integridade dos fontes

Runner independente executado com python -O -B em .r117, outra pasta, com cwd na raiz do workspace. Os testes tambem verificam relocacao com espacos. O supervisor herdado executa suites em modo normal; os testes novos lancam subprocessos -O reais e exercitam FULL/READONLY sob otimizacao. Ambos os novos modulos de ferramentas possuem zero assert critico.
Os 21 IDs novos foram fixados antes da execucao, e todos aparecem exatamente uma vez em cada suite. O runner rejeita ausencias/duplicatas, resumo divergente, erros, skips inesperados, mudanca de fonte e limpeza nao confirmada. Falha no primeiro conjunto impede iniciar regressao. Antes/depois e RESULTADO fixam os mesmos fontes da versao empacotada.

- ESPECIFICOS: 21 testes, 21 aprovados, 0 skipped, 0 falhas, 0 erros; exit code 0; supervisao 40.123 s. Cleanup confirmado, zero processos ativos e threads IPC remanescentes.
- REGRESSAO_COMPLETA: 1459 testes, 1458 aprovados, 1 skipped, 0 falhas, 0 erros; exit code 0; supervisao 637.586 s. Cleanup confirmado, zero processos ativos e threads IPC remanescentes.

Os 21 testes novos cobrem erros nativos, crescimento comprovado e limite efetivo, fase exata da API, controle positivo, integridade/estado reaberto, reconciliacao, replay, referencias invalidas, ausencia de patches globais, remocao das fixtures, flags, entradas invalidas, -O, portabilidade, output historico e falhas do runner. Testes de metadados de erro/limpeza usam dependencia supervisor explicita; a execucao completa usa Job Objects e resultados reais.

## Problemas e limitacoes

- Durante desenvolvimento foram corrigidos somente detalhes de binding de referencia de funcao e captura da classe AuditError em modulos de teste relocalizados. O primeiro log de desenvolvimento nao e evidencia de aprovacao; a aprovacao candidata depende das novas suites supervisionadas da versao final.
- Um skip herdado de symlink no Windows permanece por falta de permissao. Nenhum teste foi relaxado para eliminar esse skip.
- FULL por limite de paginas nao significa disco fisico cheio. READONLY por URI nao testa ACLs do Windows. Nao houve SQLITE_IOERR, VFS customizado, morte dentro do motor ou perda de energia.
- A fase registrada e a chamada da API SQLite (UPDATE nos dois casos), nao um ponto interno do motor nem falha durante commit.
- Este escritor de ensaio independente nao comprova que todas as rotas internas de consume_chain foram exercitadas por esses dois erros. As rotas herdadas de consumo/replay/reconciliacao continuam cobertas pela regressao e pelos replays explicitos.
- Fixtures/ancoras/hashes locais nao constituem custodia autenticada, proveniencia independente, exactly-once ou garantia entre computadores. Rollback conjunto de banco e ancoras continua um limite.
- Cleanup confirmado cobre os Jobs supervisionados e as fixtures dos ensaios bem-sucedidos, nao todos os processos ou temporarios do computador. Comparacoes antes/depois nao detectam alteracoes transitorias restauradas.

## Pacote e reexecucao

ZIP inclui toda a arvore f3_int117_work, base b116 completa, todos os historicos herdados, fontes novos, evidencias e artefatos de preparacao. Manifesto fixa todo o projeto exceto ele proprio e seu sidecar. CRC, caminhos e SHA-256 de cada membro verificados depois da escrita. Hash do ZIP e validacao final ficam fora do proprio pacote para evitar autorreferencia.
Reexecucao em pasta nova: python -O -B <projeto>/audit/tools/f3_int117_run_audit.py --output EVIDENCIAS_NOVAS. --base e relativo a raiz do projeto; default b116. Nenhum output existente e sobrescrito.

Aguardar auditoria antes de qualquer promocao para FINAL.
