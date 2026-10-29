# Auditoria tecnica F3-INT-117 ? 24/10/2026

**PARECER: REPROVADO para aprovacao da candidata, ate corrigir B1.** Os ensaios de SQLITE_FULL/SQLITE_READONLY e seus resultados informados foram confirmados. A reprovacao decorre de uma divergencia de invariante demonstrada no escritor independente, fora das pequenas fixtures atuais; nao de adulteracao de logs ou de erros SQLite fabricados.

## B1 ? escritor permite ultrapassar capacidade do historico

Fonte: audit/tools/f3_int117_sqlite_write_faults.py, write_once (linha 97), validacao/UPDATE (linhas 135?141). Comparacao: audit/tools/f3_int109_offline_consumption_store.py, HISTORY_CAPACITY_EXHAUSTED (linha 177).
A sonda nao repete o bloqueio len(state["consumed"]) >= 4096 do armazenamento original. Ensaio adversarial sob python -O, somente em dois bancos descartaveis, usou estado inicial aceito por _load com 4096 entradas canonicas e next_revision=5000; cadeia nova valida de revisao 5000:

| Implementacao | Resultado | Estado apos tentativa |
|---|---|---|
| consume_chain original | HISTORY_CAPACITY_EXHAUSTED | estado anterior preservado e reaberto |
| write_once da sonda, modo normal | committed=true, commit_returned, sem erro SQLite | historico com 4097 entradas; reabertura falha com ValueError: Invalid consumption history |

Evidencia: DIFERENCA_CAPACIDADE_REVISAO5000.json. Reproducao preservada em REPRODUCAO_REVISAO5000.py. O ensaio tambem foi reproduzido com revisao 2 em DIFERENCA_INVARIANTE_CAPACIDADE.json. Ambas as fixtures foram removidas. A integridade fisica SQLite passa antes da rejeicao semantica pelo _load; portanto integrity_check sozinho nao demonstra validade do dominio.
Esta chamada direta e fora do dominio estreito atualmente produzido por run_experiment/growth_fixture (historico sintetico pequeno). Nao houve falso sucesso nos cenarios FULL/READONLY distribuidos, nem dano a arquivo historico. O bloqueio e uma decisao de auditoria sobre fail-closed do escritor: seu limite de dominio nao e imposto na fronteira que efetivamente grava, e uma entrada canonica aceita pode gerar estado que o proprio leitor rejeita. Nao se exige tornar a sonda um armazenamento de producao; exige-se rejeitar essa escrita ou impor e testar explicitamente um dominio menor antes do UPDATE.

### Correcao necessaria

- Acrescentar na propria fronteira de escrita a rejeicao de historico no limite, antes de UPDATE/COMMIT, ou uma restricao explicita de dominio pelo menos tao conservadora. Nao modificar o armazenamento FINAL.
- Adicionar testes de fronteira: 4095 entradas permite no maximo chegar a 4096; 4096 entradas rejeita a nova admissao sem mudar bytes/estado e sem entrar em commit. Incluir execucao real sob -O e limpeza das fixtures.
- Revisar os demais limites/precondicoes da fronteira de escrita e documentar a diferenca entre sonda restrita e armazenamento original. Atualizar fontes, evidencias, relatorio, manifesto e pacote apos os testes especificos e regressao completa da correcao.

## Comparacao de invariantes e escopo

| Invariante/comportamento | Comparacao |
|---|---|
| Estado canonico, esquema e digest | Mesmo _load/_encode/_digest herdados; before-state tambem comparado integralmente na sonda |
| Identidade, escopo, revisao minima e cadeia | Mesmo verify_typed_chain, digest esperado e conjunto consumido |
| Transicao | Mesmos generation+1, next_revision=ultima revisao+1 e historico ordenado |
| Transacao | BEGIN IMMEDIATE, UPDATE unico e commit; fechamento em finally |
| Journal/configuracao | DELETE, synchronous FULL, trusted_schema OFF e timeout zero; sonda adiciona modo ro ou limite de paginas |
| Capacidade 4096 | Original rejeita antes da escrita; escritor da sonda omite o bloqueio ? B1 |
| Dominio de revisao esgotado | Original tem status REVISION_DOMAIN_EXHAUSTED explicito; sonda depende da rejeicao do verificador e propaga ProbeError. Fecha, mas nao e equivalencia de status |
| Entrada e retorno | Original aceita janela de batches e base_registry opcional e devolve StoreResult; sonda opera uma revisao consecutiva e devolve dict de eventos/erro. Nao e substituto do original |
| Historico das fixtures | Seed direto e sintetico; nao e prova de que cada entrada foi admitida por cadeia previa real |
| Tratamento de erro | Erros da API SQLite sao capturados com codigo e fase; a sonda nao testa os ramos de _db_error de consume_chain para esses dois erros |

O relatorio candidato declara corretamente o escritor independente e limita os resultados ao UPDATE; nao declara equivalencia completa com consume_chain. B1 deve ser documentado e tratado mesmo com essa limitacao, para impedir commit de estado semanticamente invalido na propria rotina de escrita.

## Resultados confirmados

- SQLITE_FULL real, codigo primario/nativo 13: limite efetivo de duas paginas lido de volta na conexao de escrita. Controle com os mesmos bytes iniciais cresceu de duas para tres paginas de 512 bytes.
- SQLITE_READONLY real, codigo 8: conexao URI mode=ro, query_only=0; nenhuma excecao SQLite fabricada ou patch global foi localizado nos dois novos modulos.
- Ambos falharam em UPDATE, com update_entered e sqlite_error_UPDATE, sem update_returned, commit_entered ou commit_returned. Os testes nao confundem esse resultado com erro no commit.
- Nos ensaios distribuidos, reabertura, integrity_check, payload completo e hash dos bytes nas falhas conferem. Ancoras before/after sao retidas antes da tentativa e permanecem inalteradas. Reconciliacao correta, referencias ausentes/divergentes sem retry e rejeicao dos replays exercitados.
- Replay testado e de cadeia previamente registrada e, no controle positivo, da cadeia recem-commitada. A operacao que falhou nao foi falsamente marcada como consumida e nao foi repetida automaticamente.

## Execucao, portabilidade e recursos

- Evidencia original: 21/21 especificos; regressao 1459 testes, 1458 aprovados, 1 skipped, zero falhas/erros. Logs, respectivos execution.json e RESULTADO sao consistentes. A regressao completa nao foi reexecutada nesta auditoria; seu conteudo foi verificado por hash e comparado aos fontes.
- Reexecucao independente nesta auditoria: todos os 21 especificos sob um interpretador real python -O; 21 aprovados, zero skips/falhas/erros. ESPECIFICOS_REAUDITORIA_O.log e REEXECUCAO.json registram esse novo ensaio. Os dois contraexemplos sao adicionais e mostram cobertura que faltava aos 21 testes existentes.
- Zero assert critico nos dois modulos novos. As verificacoes explicitamente levantam excecoes sob otimizacao.
- Portabilidade: fontes/base/logs da execucao completa arquivada em .r117 coincidem com os distribuidos. O teste com pasta contendo espacos foi reexecutado; ele verifica resolucao de raiz e rejeicao de base ausente, nao executa sozinho uma regressao completa com base real. A evidencia positiva completa de relocacao e a execucao .r117 registrada.
- Jobs supervisionados originais e o Job da reauditoria confirmam active_processes=0 e live_io_threads=[]. Identidades/handles de processos constam nos metadados. Fixtures dos ensaios e dos contraexemplos foram removidas; todas as conexoes observadas fecharam. Nao se conclui nada sobre todos os processos/temporarios do computador.

## Arquivos e hashes

| Arquivo relativo a f3_int117_work/audit | SHA-256 |
|---|---|
| tools/f3_int117_sqlite_write_faults.py | `7775676060ac7dc4a189593b45c78227263613cf82513265115c5af1440f5682` |
| tools/f3_int117_run_audit.py | `0dcbc2b0f8e268ef7d20b6e2608f09667a9526b9dba8a0eb6de9629beb950437` |
| tests/test_f3_int117_sqlite_write_faults.py | `446a5d0ebe862e543a260d2706c0025410dbef501ed84cccfade5116496ed06c` |
| tests/test_f3_int117_runner.py | `a2735a75992e8b15a98ed79addd79a9b5fde6e2e5b81f15e92f204ef56f32f94` |

- 7129/7129 entradas do manifesto candidato corretas, sidecar correto; CRC e hashes dos membros do ZIP conferidos.
- 3559/3559 arquivos historicos conferidos na base original, na candidata, em b116 e na base relocalizada. Nova conferencia da base original apos os ensaios tambem sem divergencias.
- 229/229 fontes Python coincidem com ANTES, RESULTADO, copia relocalizada, manifesto e ZIP. Os 7131 arquivos da candidata permaneceram intactos durante a auditoria.
- 65/65 verificacoes de consistencia passaram. Isso confirma integridade e coerencia das evidencias; nao substitui a analise semantica que encontrou B1.
- ZIP auditado: F3_INT117_CANDIDATA_COMPLETA_20261024.zip; SHA-256 ef2c88a9b28dfda119eeb78524b3f00c0fc523d2f7878cf97a58e7bbe92b08ae.
- Hashes dos logs e dos quatro fontes constam integralmente em CONSISTENCIA.json. O log de regressao aprovado tem SHA-256 a3b86babf86dd015b9fece06b93d73f02dd1960ead21aa065da237d8721a2047.

## Outras observacoes e possiveis falsos positivos

- automatic_retries=0 e um campo preenchido pelo codigo, nao um contador independente de chamadas. A inspecao confirma uma unica write_once por experimento; os loops de calibracao usam fixtures novas e sao controles. O teste isolado do campo constante nao detectaria uma futura introducao de retry nao contabilizado.
- Os 12 metodos de teste de escrita compartilham os tres resultados criados em setUpClass. Sao 12 verificacoes sobre tres ensaios, nao 12 injecoes independentes. O teste -O cria mais dois ensaios nativos.
- A rejeicao com ancora atual observada e STALE_CHAIN_REVISION: ela demonstra recusa de replay pelo piso de revisao, nao isola por si a barreira CHAIN_ALREADY_CONSUMED. A validacao herdada tem cobertura propria, preservada na regressao.
- write_once e validate_attempt nao rejeitam explicitamente todo modo desconhecido na propria fronteira; run_experiment o faz antes de chama-los. E recomendavel fortalecer tambem os auxiliares ou tornar seu contrato restrito explicito, sem ampliar escopo operacional.
- As ancoras da reconciliacao sao passadas pela memoria do ensaio; o arquivo retido e conferido byte a byte. Isso nao demonstra recarga dessas referencias apos reinicio completo de processo nem custodia independente.

## Limites permanentes e preservacao

Permanece o skip de symlink do Windows. FULL por limite de paginas nao e disco fisico cheio; mode=ro nao e teste de ACL. Nao houve IOERR, perda de energia ou falha dentro do commit. Versao observada: SQLite 3.49.1; nao se garante o mesmo ponto de erro em todas as builds. Comparacoes antes/depois nao detectam alteracao transitoria restaurada. Hashes e referencias locais nao autenticam custodia, procedencia, exactly-once ou durabilidade fisica.
Nenhum fonte/teste candidato, manifesto distribuido ou checkpoint FINAL foi modificado. Apenas artefatos novos desta auditoria foram criados fora da candidata. F3 OPEN, sete flags false, operacoes reais bloqueadas. ULTIMO_MARCO continua F3-INT-116 FINAL. Nenhuma promocao realizada.
