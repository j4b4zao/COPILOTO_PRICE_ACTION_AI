# F3-INT-117 — auditoria de comportamento

Data: 24/10/2026. Base: F3-INT-116 FINAL. Candidata: F3_INT117_CANDIDATA_COMPLETA_20261024.zip.

**Parecer conclusivo: REPROVADO para aprovação da candidata enquanto o achado B1 não for corrigido.**

A integridade do pacote foi confirmada independentemente pelo usuário. Esta revisão examinou o comportamento do escritor, os limites das conclusões dos testes e a relação entre fontes e evidências. Integridade de distribuição e aprovação semântica são verificações diferentes.

## 1. O que foi feito nesta revisão

- Lidos novamente os dois módulos da etapa 117, seus testes, a comparação com o armazenamento 109 e os registros da auditoria técnica anterior.
- Recalculados os hashes dos quatro fontes novos e dos 229 fontes fixados na execução. Nenhum mudou.
- Reconfirmados os hashes dos logs de específicos/regressão, a igualdade entre seus registros execution.json e RESULTADO e os 3.559 arquivos da base FINAL original.
- Revisadas as evidências dos três cenários em cada log: normal, FULL e READONLY.
- Conferidos os registros da reexecução anterior dos 21 específicos sob `python -O` e do contraexemplo de capacidade.

As 14 verificações de atualização/consistência desta revisão passaram. O arquivo VERIFICACAO_COMPORTAMENTO.json registra os resultados e os eventos relevantes de cada cenário.

**Não foram executados novos testes nesta rodada.** Os fontes são os mesmos, o contraexemplo já está reproduzido e não surgiu divergência que exigisse repetir ensaios. Isso atende à instrução de executar testes direcionados adicionais somente quando necessários. A revisão não transforma uma execução anterior em uma execução nova.

## 2. Achado bloqueante B1: limite do histórico omitido no escritor

O armazenamento original `f3_int109_offline_consumption_store.consume_chain` rejeita uma nova admissão quando `len(state['consumed']) >= 4096`, antes de escrever. A rotina `f3_int117_sqlite_write_faults.write_once` não tem a mesma barreira: após validar a cadeia e a fórmula da transição, passa ao UPDATE e ao commit.

O contraexemplo preservado foi executado com `python -O`, em bancos descartáveis, com um estado inicial aceito pelo leitor original, 4.096 entradas e piso de revisão 5.000:

| Caminho executado | Resultado | Estado persistido |
|---|---|---|
| `consume_chain` original | `HISTORY_CAPACITY_EXHAUSTED` | Estado anterior preservado |
| `write_once`, modo normal | `committed=true`, `commit_returned`, sem erro SQLite | 4.097 entradas; `_load` rejeita a reabertura com `Invalid consumption history` |

A integridade estrutural do SQLite não impede esse resultado: o erro é de validade do estado da aplicação. `PRAGMA integrity_check` pode passar e o payload continuar violando o contrato do leitor.

Evidências preservadas:

- `../AUDITORIA_F3_INT117_20261024/DIFERENCA_CAPACIDADE_REVISAO5000.json`.
- `../AUDITORIA_F3_INT117_20261024/REPRODUCAO_REVISAO5000.py`.
- Uma reprodução anterior, com revisão 2, em `DIFERENCA_INVARIANTE_CAPACIDADE.json` no mesmo diretório.

**Alcance do achado:** o contraexemplo chama diretamente `write_once`, fora das pequenas fixtures produzidas atualmente por `run_experiment/growth_fixture`. Não demonstra que os cenários FULL/READONLY registrados tenham gerado estado inválido. Demonstra que a fronteira que efetivamente grava não impõe um limite conservador e pode aceitar uma entrada válida para produzir um estado inválido. Esse é o motivo do bloqueio da aprovação do escritor.

**Correção necessária:** rejeitar o limite de histórico na própria fronteira de escrita antes de UPDATE/COMMIT, ou impor nela um domínio explicitamente menor e conservador. Acrescentar testes de 4.095 e 4.096 entradas, inclusive sob `-O`, conferindo estado, bytes, ausência de commit na rejeição e limpeza. Nenhuma mudança no armazenamento FINAL é necessária para isso.

## 3. Comparação das invariantes com F3-INT-109

| Aspecto | Armazenamento original | Sonda independente | Conclusão |
|---|---|---|---|
| Esquema e estado canônico | `_load`, `_encode`, `_digest` | Reutiliza as mesmas funções | Paridade nas verificações reutilizadas |
| Âncora anterior | Compara digest do estado com a âncora | Compara estado completo e digest | Validação conservadora para a fixture |
| Escopo | Compara context, purpose e run_id | Compara escopo da fixture | Compatível no domínio exercitado |
| Cadeia e revisão mínima | `verify_typed_chain` | Mesmo verificador e expectativas | Compatível nos argumentos usados |
| Transição | Geração +1, piso após último batch, histórico ordenado | Exige a mesma fórmula para after-state | Fórmula comum não substitui limites de domínio |
| Capacidade | Rejeita ao atingir 4.096 | Falta a barreira em `write_once` | B1: commit de estado inválido demonstrado |
| Revisão esgotada | Status explícito `REVISION_DOMAIN_EXHAUSTED` | Rejeição indireta do verificador, propagando exceção | Fecha a operação, mas não há equivalência de status |
| Transação | BEGIN IMMEDIATE, UPDATE e commit | Mesmo encadeamento de API | Não são as mesmas implementações de escritor |
| Erros | Mapeia exceções para `StoreResult` | Devolve eventos/código/fase ou propaga `ProbeError` | FULL/READONLY na sonda não testam os respectivos ramos de erro do escritor 109 |
| Entrada admitida | Janela de batches, `base_registry` opcional | Um batch na revisão seguinte em `run_experiment` | Domínio mais estreito na entrada principal da sonda |
| Histórico | Estado do consumo | Seed canônico sintético | Não prova a origem ou admissão real de cada entrada |

Os módulos são compatíveis em várias verificações compartilhadas, mas **não são semanticamente equivalentes em todos os limites**. Os testes não podem ser usados para afirmar equivalência integral ou cobertura dos mesmos caminhos internos.

## 4. Erros SQLite e fase exata

| Cenário registrado | Mecanismo | Código nativo | Fase |
|---|---|---|---|
| FULL | `max_page_count=2` aplicado e lido de volta na conexão de escrita | `SQLITE_FULL`, 13 | UPDATE |
| READONLY | URI `mode=ro`, com `query_only=0` | `SQLITE_READONLY`, 8 | UPDATE |
| Controle normal | Mesmos bytes iniciais, sem o limite de duas páginas | Sem erro | Commit retornou |

O controle cresceu de duas para três páginas de 512 bytes. A igualdade dos bytes iniciais do controle e do alvo é verificada antes da tentativa. Assim, o teste demonstra necessidade real de crescimento e um limite efetivo na conexão que faz a escrita.

O código captura `sqlite3.DatabaseError` e extrai `sqlite_errorcode`/`sqlite_errorname` da exceção. Não foi localizada construção artificial desses erros nem substituição global das funções SQLite nos módulos novos. No READONLY, a conexão efetivamente aberta com `mode=ro` tenta escrever; não se trata apenas de um indicador declarado ou de uma exceção Python injetada.

Os dois logs registram `update_entered` seguido de `sqlite_error_UPDATE`. Não há `update_returned`, `commit_entered` ou `commit_returned` nessas tentativas. **Não se alega falha dentro do commit.** A fase registrada é a chamada da API, não um ponto interno do motor SQLite.

## 5. Integridade, reabertura e reconciliação

Para os cenários FULL/READONLY distribuídos, as evidências correspondem às verificações implementadas:

- Conexão encerrada em `finally`, seguida de nova conexão para reabertura.
- `PRAGMA integrity_check` retorna `ok`.
- Payload canônico reaberto coincide integralmente com o before-state esperado.
- Hash dos bytes do banco coincide com o anterior à tentativa.
- Âncoras before/after são calculadas antes da tentativa e o arquivo retido permanece idêntico.
- Reconciliação retorna `NOT_COMMITTED_OBSERVED_UNAUTHENTICATED`; no controle normal, retorna `COMMITTED_OBSERVED_UNAUTHENTICATED`.
- Referências divergentes retornam `RECONCILIATION_UNRESOLVED`; referência vazia retorna `INVALID_RECONCILIATION_PIN`. Nenhum resultado concede retry.

Essas verificações são mais fortes que testar apenas a mensagem da exceção. Ainda assim, não cobrem todos os estados válidos de entrada do escritor, como B1 demonstra.

As referências de reconciliação são passadas em memória; o arquivo retido é conferido byte a byte. O ensaio não demonstra recarga dessas referências depois de um reinício completo de processo ou custódia autenticada.

## 6. Replay e ausência de retry

Os replays explícitos passam pelo `consume_chain` original, inalterado:

- Com âncora diferente do estado atual: `STATE_ANCHOR_MISMATCH`.
- Com âncora atual e revisão já ultrapassada: `STALE_CHAIN_REVISION`.
- No controle normal, a cadeia recém-gravada também é rejeitada nas duas modalidades.
- Estado persistido é comparado novamente após as rejeições.

Limites dessa evidência:

1. O teste com âncora atual exercita a barreira do piso de revisão. Não isola a barreira `CHAIN_ALREADY_CONSUMED` de outras proteções.
2. A âncora chamada de antiga no cenário sintético é construída a partir de um estado hipotético anterior; não é evidência de uma admissão histórica autenticada ou de rollback físico de um banco real.
3. A operação cuja escrita falhou não é declarada consumida. Os replays exercitam cadeias já registradas; não são uma nova tentativa automática da operação que falhou.

A inspeção confirma uma chamada a `write_once` por experimento. As iterações de calibração usam bancos novos e controles separados. Não há retry automático nesse fluxo. Contudo, `automatic_retries=0` é um campo preenchido pelo programa, não um contador independente: verificar somente esse campo poderia deixar passar uma futura regressão de retry não contabilizado.

## 7. Testes, falsos positivos e comportamento fail-closed

Os 21 testes existentes passaram na execução registrada e na reauditoria anterior sob um interpretador real `python -O`. Os módulos novos não dependem de instruções `assert` para suas verificações críticas.

Esses resultados não invalidam B1: não há teste de capacidade do escritor novo entre os 21. Os 12 métodos da classe de escrita compartilham três resultados produzidos em `setUpClass`; são várias verificações sobre esses três ensaios, não 12 injeções independentes. O teste nativo sob `-O` acrescenta duas execuções específicas.

O runner rejeita contagens incorretas, IDs novos ausentes/duplicados, falhas, skips inesperados, hashes divergentes e limpeza não confirmada. A entrada `run_experiment` também rejeita modos desconhecidos. Os auxiliares `write_once` e `validate_attempt` não repetem todos esses controles de modo em sua própria fronteira; isso é uma oportunidade de endurecimento adicional. B1 permanece a divergência bloqueante demonstrada.

Há fechamento conservador nos cenários exercitados, mas **não se pode concluir fail-closed geral do escritor** enquanto ele puder fazer commit da transição 4.096 → 4.097.

## 8. Fontes, logs e resultados

Os quatro SHA-256 atuais coincidem com os da versão anteriormente auditada:

| Fonte relativo a `f3_int117_work/audit` | SHA-256 |
|---|---|
| tools/f3_int117_sqlite_write_faults.py | `7775676060ac7dc4a189593b45c78227263613cf82513265115c5af1440f5682` |
| tools/f3_int117_run_audit.py | `0dcbc2b0f8e268ef7d20b6e2608f09667a9526b9dba8a0eb6de9629beb950437` |
| tests/test_f3_int117_sqlite_write_faults.py | `446a5d0ebe862e543a260d2706c0025410dbef501ed84cccfade5116496ed06c` |
| tests/test_f3_int117_runner.py | `a2735a75992e8b15a98ed79addd79a9b5fde6e2e5b81f15e92f204ef56f32f94` |

Os 229 fontes fixados em ANTES e RESULTADO continuam correspondendo aos arquivos atuais. Os logs não mudaram e seus metadados de execução continuam iguais aos registrados em RESULTADO.

Resultados arquivados:

- Específicos: 21 testes, 21 aprovados, zero skips/falhas/erros.
- Regressão: 1.459 testes, 1.458 aprovados, um skip, zero falhas/erros.
- Reauditoria anterior integral sob `-O`: 21/21 aprovados, zero skips/falhas/erros.

A regressão não foi reexecutada nesta revisão. Sua evidência é a execução arquivada e vinculada localmente aos fontes por hashes/inventários. Isso não é uma atestação autenticada da execução.

Os números de integridade têm escopos distintos: 7.129 entradas no manifesto do projeto; 7.136 arquivos de payload no manifesto de pacote; 7.137 membros no ZIP ao incluir o próprio manifesto de pacote. O resultado independente informado pelo usuário é compatível com essa estrutura.

## 9. Recursos, preservação e limites

Os registros dos Jobs originais e da reauditoria anterior confirmam zero processos ativos e nenhuma thread IPC remanescente. As fixtures declaradas removidas têm verificação correspondente no código; os contraexemplos também removeram seus bancos temporários. Isso não é uma afirmação sobre todos os processos ou temporários da máquina.

Foram reconferidos os 3.559 arquivos históricos da base original sem divergência. Nenhum código da candidata, teste distribuído ou checkpoint FINAL foi alterado nesta revisão. O último marco permanece F3-INT-116 FINAL.

Limitações remanescentes:

- Skip de symlink no Windows por permissão.
- FULL por limite de páginas não simula disco físico cheio; `mode=ro` não testa ACLs.
- Sem ensaio de IOERR, VFS customizado, falha interna de commit ou perda de energia.
- Comportamento observado no SQLite 3.49.1, sem garantia do mesmo ponto de erro em todas as builds.
- Sem comprovação de durabilidade física, custódia autenticada, origem independente ou entrega exatamente uma vez.
- Comparações antes/depois não detectam alteração transitória restaurada.

**Conclusão:** os erros nativos e a preservação nos cenários FULL/READONLY atuais estão sustentados pelas evidências. A candidata continua REPROVADA devido a B1. Exige-se corrigir a barreira de escrita, acrescentar a cobertura de fronteira e produzir nova validação da versão corrigida antes de nova aprovação.

F3 OPEN; sete flags false; operações reais bloqueadas. Nenhuma promoção ou correção de implementação foi realizada.
