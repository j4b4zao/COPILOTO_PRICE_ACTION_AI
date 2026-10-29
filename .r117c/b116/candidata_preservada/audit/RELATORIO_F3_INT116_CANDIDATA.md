# F3-INT-116 CANDIDATA CORRIGIDA — 24/10/2026

Correcao concluida; revisao pendente. Nao houve promocao. F3 OPEN, sete flags false, offline e simulation_only; certification false.

## Arquivos e portabilidade

- Modificado: audit/tools/f3_int116_run_audit.py. Nao ha caminhos absolutos fixos nem instrucoes assert. Caminhos resolvidos a partir de __file__, independentes do cwd.
- Adicionado: audit/tests/test_f3_int116_runner.py, com nove testes novos. Os oito testes de commit existentes foram preservados sem alteracao.
- Base FINAL incluida em base_f3_int115_final, relativa a raiz do projeto. --base aceita somente caminhos internos relativos; --output aponta uma pasta nova relativa a audit. Saidas existentes e escapes sao rejeitados.
- Verificacoes explicitas lancam AuditError para invariantes invalidas; arquivos ausentes ou dados malformados propagam excecoes e encerram com erro. Falhas durante os testes registram success=false e exception; nao iniciam a etapa seguinte.
- O runner nao altera manifestos nem checkpoints ao rodar; manifesto de distribuicao atualizado separadamente apos validacao para evitar sobrescrever evidencias historicas.

## Testes e relocacao

Runner completo executado com python -O -B em audit/F3_INT116_CORRECAO_20261024/Projeto em outra pasta, com cwd na raiz do workspace. A copia relocalizada foi comparada por SHA-256 antes/depois. O supervisor herdado executa as suites sem -O; os nove testes novos lancam subprocessos -O reais, e o runner principal esteve sob -O durante toda a auditoria.

- ESPECIFICOS: 17 testes; 17 aprovados; 0 skipped; zero falhas/erros; exit code 0; 19.674 s.
- REGRESSAO_COMPLETA: 1438 testes; 1437 aprovados; 1 skipped; zero falhas/erros; exit code 0; 540.219 s.

Novos testes cobrem -O, todos os sete locks, estado F3/offline/simulacao/certificacao, checkpoint divergente, evidencia adulterada, erro/timeout/exit code, processos e IPC remanescentes, contagem incompleta/skips, inventario adulterado, escape de caminho, base ausente, saida historica existente, relocacao independente do cwd e interrupcao do fluxo principal apos rejeicao. O teste do fluxo principal usa resultados simulados para falhas; a execucao relocalizada usa supervisao e suites reais.
Limpeza real confirmada nos dois Jobs: zero processos ativos e nenhuma thread IPC remanescente. A afirmacao cobre os processos supervisionados.

## Preservacao e integridade

Os 875 arquivos da base extraida FINAL permanecem identicos na base e em ambas as copias do projeto. Os 874 pins do manifesto FINAL foram conferidos pelo runner. Os 889 arquivos da candidata anterior continuam intactos em f3_int116_work. Runner anterior, relatorio e manifestos anteriores tambem foram arquivados em PRESERVADO_F3_INT116_PRE_CORRECAO. Nenhum checkpoint FINAL anterior foi alterado.
Manifesto atualizado inclui todos os arquivos de audit, exceto ele proprio e seu sidecar; ambos evitam autorreferencia. O manifesto de pacote cobre todo o payload, incluindo a base FINAL portatil, candidato anterior e evidencias. CRC e SHA-256 de cada membro do ZIP verificados apos a escrita.

## Limites

Um skip de symlink por permissao do Windows permanece. Hashes e ancoras locais nao autenticam custodia ou procedencia. Nao ha resistencia comprovada a perda de energia, exatamente uma vez ou garantia entre computadores. O patch de commit continua restrito a testes isolados. A base distribuida e a arvore extraida, nao o ZIP FINAL original. Nenhuma operacao real autorizada.

## Reexecucao

A partir de qualquer cwd: python -O -B <projeto>/audit/tools/f3_int116_run_audit.py --output EVIDENCIAS_NOVA_REVISAO. Usar sempre nome novo para preservar a evidencia existente.

Aguardar revisao antes de promover para FINAL.
