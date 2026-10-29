# F3-INT-117 CANDIDATA CORRIGIDA - 24/10/2026

Status: CANDIDATA, aguardando nova auditoria. F3 OPEN; sete flags false; offline/simulation_only true; certification false. Operacoes reais bloqueadas, retry_allowed false e nenhuma promocao.

## Causa raiz e regra original

O escritor independente reutilizava _load e verify_typed_chain, que aceitam um historico inicial com ate 4096 entradas. Faltava a barreira adicional de consume_chain da F3-INT-109: apos uma cadeia valida, se len(consumed) >= 4096, devolver HISTORY_CAPACITY_EXHAUSTED antes de construir/gravar o novo estado. Sem essa barreira, append gerava 4097 entradas e commit de um estado que o leitor rejeitava.
Ordem original preservada: ancora -> escopo -> dominio de revisao -> verificacao da cadeia (incluindo piso e digest consumido) -> capacidade -> transicao -> UPDATE -> commit. A capacidade nao e antecipada para mascarar erros de ancora, escopo ou cadeia. Nenhum historico e truncado, limpo ou reinicializado.

## Correcao e arquivos

- audit/tools/f3_int117_sqlite_write_faults.py: barreira de capacidade na propria write_once, status de rejeicao conservadores e mesma precedencia da base; modos desconhecidos recusados tambem nos auxiliares. Erros nativos continuam registrados com codigo/fase. Connection observer e writer explicitos permitem verificacao local, sem patches globais.
- audit/tools/f3_int117_run_audit.py: lista fixa ampliada para os 35 IDs, 1473 testes esperados na regressao e output novo EVIDENCIAS_F3_INT117_CORRECAO.
- audit/tests/test_f3_int117_runner.py: ajuste apenas do nome de output e da contagem de testes na fixture negativa simulada; mesmos nove IDs e mesmas assercoes. Contagem valida evita que um erro de resumo mascare o erro de execucao/limpeza que o teste pretende exercitar.
- Novo audit/tests/test_f3_int117_capacity_boundary.py: 14 testes adicionais, com fixtures novas por teste e comparacao direta com consume_chain original.
- Relatorio, manifesto, sidecar e evidencias atualizados. Versoes substituidas arquivadas em audit/PRESERVADO_117_PRE_CORRECAO. Nenhum arquivo FINAL foi editado.

## Fronteiras e verificacoes independentes

| Cenario | Resultado observado | SQL da conexao da sonda |
|---|---|---|
| 4095 entradas, cadeia nova valida | Inclusao ate 4096; estado reaberto igual ao original | 1 UPDATE e 1 COMMIT autorizados |
| 4096 entradas, cadeia nova valida | HISTORY_CAPACITY_EXHAUSTED; mesmos bytes e estado | 0 UPDATEs e 0 COMMITs autorizados |
| Mesma fixture, encher e tentar operacao seguinte | Primeiro commit valido; proxima inclusao recusada | Segunda conexao sem escrita/commit |
| Ancora/escopo/cadeia invalidos no limite | Mesmos status prioritarios do original | Nenhuma escrita |
| Revisao esgotada | REVISION_DOMAIN_EXHAUSTED antes da cadeia/capacidade | Nenhuma escrita |
| Digest consumido com piso permissivo | CHAIN_ALREADY_CONSUMED antes da capacidade | Nenhuma escrita |
| After-state fornecido inconsistente | ProbeError antes de UPDATE | Nenhuma escrita |

As observacoes independentes usam set_authorizer e set_trace_callback na conexao explicitamente entregue ao teste; os callbacks permitem as operacoes e registram comandos/preparacoes. Nao substituem sqlite3.connect, _connect, consume_chain ou qualquer global. Valores BLOB de traces sao resumidos no log, sem perder tipo e contagem dos comandos.
Hashes dos bytes, PRAGMA integrity_check e leitura canonica por conexao nova sao conferidos apos rejeicao. Os replays usam ancoras realmente retidas antes/depois de um commit do proprio teste. A referencia e lida do arquivo retido antes da reconciliacao. A tentativa que excederia o limite mantem o before-state observado e retry_allowed false; o digest after nesse caso descreve apenas a proposta rejeitada, nunca um estado declarado admitido.
Seis verificacoes selecionadas de fronteira, ordem, historico consumido e reconciliacao/replay foram executadas novamente por subprocesso -O com verificacao explicita de __debug__. stdout/stderr desse subprocesso constam do registro boundary_optimized nos logs.

## Preservacao dos erros SQLite

SQLITE_FULL=13 e SQLITE_READONLY=8 continuam sendo erros nativos no UPDATE, antes de commit. O controle comprova crescimento de duas para tres paginas e o limite e aplicado na mesma conexao. Dois controles adicionais usam fixtures novas e contam externamente a entrada no writer: uma chamada, uma conexao observada, uma preparacao de UPDATE e nenhum COMMIT. Nenhuma operacao que falhou foi automaticamente repetida.
O campo legado automatic_retries=0 foi preservado para compatibilidade, mas deixou de ser a unica verificacao: os novos testes contam chamadas fora do escritor e registram operacoes da conexao. O campo isolado nao e tratado como prova independente.

## Testes e regressao

Os 21 IDs anteriores foram mantidos e os 12 testes de escrita anteriores permanecem byte a byte. Os 14 novos IDs se somam aos existentes. A fixture negativa do runner foi atualizada para o numero correto, sem remover assercoes ou aceitar falhas/skips extras. O runner foi executado com -O em .r117c, pasta relocalizada; as suites do supervisor herdado rodam em modo normal e possuem subprocessos -O explicitos.

- ESPECIFICOS: 35 testes, 35 aprovados, 0 skipped, 0 falhas, 0 erros; exit code 0; supervisao 118.267 s; cleanup confirmado, zero processos ativos e threads IPC remanescentes.
- REGRESSAO_COMPLETA: 1473 testes, 1472 aprovados, 1 skipped, 0 falhas, 0 erros; exit code 0; supervisao 798.503 s; cleanup confirmado, zero processos ativos e threads IPC remanescentes.

## Evidencias de integridade

Base F3-INT-116 FINAL: 3559 arquivos conferidos antes/depois na origem, no projeto e em b116, incluindo as copias relocalizadas. Candidata reprovada: 7131 arquivos preservados. Marcadores, checkpoints e ZIPs anteriores mantiveram os hashes.
233 fontes Python inventariados, incluindo fontes historicos arquivados, coincidem em ANTES, RESULTADO, copia relocalizada e distribuicao. Esses inventarios fixam arquivos; nao afirmam que cada arquivo historico foi importado ou executado.
Logs da versao corrigida: audit/EVIDENCIAS_F3_INT117_CORRECAO. Logs EVIDENCIAS_F3_INT117 sao historicos da versao reprovada e nao sao usados como aprovacao desta correcao. O manifesto candidato antigo se aplica a raiz historico117/ do ZIP; o novo manifesto fixa a candidata corrigida inteira, sem autorreferencia.
O ZIP inclui projeto corrigido completo, base b116, candidato reprovado completo em historico117/ e artefatos de preparacao/validacao. CRC, nomes e hashes de cada membro conferidos apos escrita. Hash do ZIP fica em sidecar externo.

## Limitacoes remanescentes

- Os 12 testes legados ainda compartilham tres resultados em setUpClass; foram mantidos para nao remover cobertura. Os 14 testes novos nao compartilham os bancos de fronteira; FULL e READONLY adicionais usam fixtures novas e contadores independentes.
- A barreira CHAIN_ALREADY_CONSUMED agora e isolada com piso permissivo numa fixture sintetica. Isso demonstra a precedencia do verificador; nao autentica a origem de cada entrada. Replay com ancoras reais before/after de um commit separado tambem e exercitado.
- O escritor continua sendo uma sonda independente, nao substituto de consume_chain. Resultados/erros de fixture fora do dominio exercitado podem ter formas diferentes do StoreResult original. Nao se declara equivalencia integral de todas as rotas internas.
- Observadores sao locais a conexao e a verificacao de chamadas e externa ao writer, mas nao e uma atestacao autenticada contra codigo malicioso. Sem patch global e sem autorizacao de retry.
- Persiste um skip de symlink do Windows por permissao. As falhas FULL/READONLY observadas sao no UPDATE, nao no interior do commit. Limite de paginas nao e disco fisico cheio e mode=ro nao e ACL do Windows.
- Sem IOERR/VFS, custodia autenticada, resistencia comprovada a perda de energia, durabilidade fisica, exactly-once ou garantia entre computadores. Hashes antes/depois nao detectam alteracoes transitorias restauradas.
- A limpeza confirmada cobre os Jobs supervisionados e as fixtures usadas, nao todos os processos/temporarios da maquina.

Aguardar nova auditoria. ULTIMO_MARCO continua F3-INT-116 FINAL. Nao foi criado checkpoint F3-INT-117 FINAL.

## Validacao integral adicional com python -O

Todos os 35 testes especificos da mesma versao foram executados integralmente em um interpretador real -O: 35 aprovados, zero skips, falhas ou erros; exit code 0. Cleanup do Job confirmado, zero processos ativos e threads IPC remanescentes. Esta execucao adicional cobre tambem os casos de precedencia e auxiliares alem dos seis cenarios selecionados ja incorporados aos testes. Evidencias completas: audit/EVIDENCIAS_F3_INT117_CORRECAO/O/. Nenhum fonte foi alterado entre a regressao de 1473 testes e esta execucao; os mesmos hashes dos 233 fontes inventariados foram reconferidos. A regressao nao precisou ser repetida, pois nao houve mudanca de codigo.

Entrega R2 inclui essas evidencias suplementares. O primeiro ZIP corrigido foi preservado com SHA-256 7cdc16b1b6a3dd21c2a865a125984ca62e41fd325c8d71e7687f9ee950bf23a3. R2 altera somente relatorio, manifesto e inclusao das evidencias -O; codigo e testes sao os mesmos. Status CANDIDATA para nova auditoria.
