# Auditoria pre-FINAL F3-INT-115 - PROMOCAO INTERROMPIDA

Workspace: C:/COPILOTO_F3_INT114_FINAL. Data: 2026-10-23.
Resultado: REPROVADA nesta revalidacao. Ultimo marco definitivo permanece F3-INT-114 FINAL.
Nenhum checkpoint/relatorio/manifesto F3-INT-115 FINAL foi criado. ULTIMO_MARCO nao foi alterado. ZIP FINAL nao foi criado.

## Integridade

- Relatorio da candidata corrigida lido integralmente; cinco correcoes revisadas.
- 23/23 hashes da candidata corrigida conferidos antes e depois.
- 772/772 arquivos historicos preservados nos caminhos originais, inclusive ULTIMO_MARCO.
- 819 arquivos preexistentes na captura de auditoria e 210 fontes Python sem alteracoes durante a execucao.
- Concorrencia exige escritor retido, STORE_BUSY do concorrente antes de CONTINUE e PIDs diferentes. Esse ensaio passou.
- Ensaios de ACK perdido/replay passaram nesta execucao; nenhuma dupla admissao foi observada. retry e sete flags mantiveram false.
- Os testes especificos passaram, mas a regressao revelou falha na verificacao de limpeza de descendente. Nao e possivel aprovar todas as cinco correcoes para FINAL.

## Testes executados

- ESPECIFICOS: 28 testes; 28 aprovados, 0 falhas, 0 erros, 0 ignorados; exit code 0; 97.732 s.
- REGRESSAO_COMPLETA: 1416 testes; 1414 aprovados, 1 falhas, 0 erros, 1 ignorados; exit code 1; 794.403 s.

Skip: test_symlink_rejected - Symlink not permitted. A falha de limpeza e separada desse skip.

## Falha que impede a consolidacao

`tests/test_f3_int115_process_control.py:120`: `test_root_exit_still_cleans_living_descendant`.
A assercao `assertFalse(process_running(int(marker.read_text())))` recebeu True. O teste passou antes pelas assercoes de exit code 0 e contador active_processes=0; a consulta subsequente ao PID ainda o indicou ativo.
O log nao prova se houve atraso na sinalizacao de termino, reutilizacao de PID ou falha de contencao. Nenhuma dessas hipoteses foi tratada como causa confirmada. A identidade do processo descendente e seus timestamps/handles nao foram retidos no log.
O supervisor externo registrou zero processos no Job ao encerrar toda a regressao; isso nao anula a falha da assercao durante o teste.

```text
FAIL: test_root_exit_still_cleans_living_descendant (test_f3_int115_process_control.ProcessControlTests.test_root_exit_still_cleans_living_descendant)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\COPILOTO_F3_INT114_FINAL\audit\tests\test_f3_int115_process_control.py", line 120, in test_root_exit_still_cleans_living_descendant
    self.assertFalse(process_running(int(marker.read_text())))
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: True is not false

----------------------------------------------------------------------
Ran 1416 tests in 791.642s

FAILED (failures=1, skipped=1)
```

## Correcoes necessarias para nova tentativa

- Reter handles e identidade de criacao dos descendentes proprios antes do encerramento.
- Aguardar a sinalizacao de termino desses handles com deadline compartilhado, alem de conferir o contador do Job.
- Persistir PIDs, identidades, timestamps e resultados da limpeza para diferenciar corrida de termino, reutilizacao de PID e falha real de contencao.
- Nao substituir a verificacao por sleeps arbitrarios ou por aceitacao apenas do contador zero.
- Reexecutar especificos e regressao completa apos correcao; nenhuma nova promocao foi tentada nesta auditoria.

## Artefatos novos

- `tools/f3_int115_consolidate_final.py`: auditor/consolidador condicionado; somente a fase audit foi executada. A fase consolidate nao foi chamada.
- `AUDITORIA_F3_INT115_PRE_FINAL_20261023/ANTES.json`: hashes e inventario anteriores.
- `AUDITORIA_F3_INT115_PRE_FINAL_20261023/SUPERVISAO_RUNNER.log` e `.execution.json`: saida e exit code da revalidacao.
- `AUDITORIA_F3_INT115_PRE_FINAL_20261023/RESULTADO_AUDITORIA_REPROVADA.json`: resultado e limites do diagnostico.
- `F3_INT115_REVALIDACAO_FINAL_20261023/`: logs completos, inventarios, checkpoint de revalidacao com success=false e manifesto.
- `AUDITORIA_F3_INT115_PRE_FINAL_20261023/MANIFESTO_AUDITORIA_REPROVADA.json`: hashes dos artefatos desta tentativa.

## Restricoes e limites

F3 OPEN; sete flags false; sem ordens reais, corretora, Profit, Excel, RTD/DDE, rede ou INT-116.
Nao se alega custodia independente, durabilidade fisica, autenticacao do executavel ou seguranca entre computadores.
O pacote solicitado PACOTE_AUDITORIA_F3_INT115_FINAL.zip nao foi gerado, conforme a condicao de interromper a promocao em caso de falha.
