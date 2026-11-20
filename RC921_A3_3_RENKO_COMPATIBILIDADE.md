# RC921_A3_3_RENKO_COMPATIBILIDADE

**Status da caracterização: `RC921_A3_3_CARACTERIZACAO_APROVADA`.** Os cinco novos casos passaram. A regressão direcionada terminou com código 1 devido às duas expectativas históricas de Renko descritas abaixo. A suíte completa ficou fora do escopo da etapa.

- Branch `checkpoint/f3-int121-a14-36-20261105`
- HEAD `95c17e280e35566395cfe0179d179b7c6a6e86b0`, base consolidada RC9.20
- Execução offline com Python 3.13.5, pytest 9.2.0 e dados sintéticos

## Expectativas históricas preservadas

### Falha entre M15 e Renko

**Teste histórico:** `tests/test_pipeline_rc920_integrated_offline.py::test_e_f_g_falha_de_builder_bloqueia_ate_coletor_novo`.

**RC9.20.** Uma exceção na entrada de Renko deixava M1/M5/M15 com fechamento `180040` e volume `100`, Renko com fechamento `180000` e os marcadores de aceitação anteriores. O teste esperava que o coletor bloqueasse novas leituras até a substituição explícita.

**Motivo da obsolescência.** As atualizações anteriores ao Renko agora pertencem à versão candidata. Descartá-la preserva os candles e os marcadores publicados. A falha histórica foi reproduzida na primeira asserção divergente, pois o fechamento permaneceu `180000` e o volume `0`.

**Contrato RC9.21 e teste substituto.** Uma falha recuperável antes ou durante o Renko preserva M1/M5/M15, os tijolos, contadores e referências do contexto retido. Os quatro parâmetros de `test_renko_failure_preserves_publication_and_retry_attributes_volume_once` passaram. A injeção interna chegou a inserir um tijolo na versão candidata, que ficou isolada do histórico publicado. [Testes Renko A3.3](tests/test_pipeline_rc921_renko_transactional_regression.py)

### Bloqueio depois de falha de publicação

**Teste histórico:** `tests/test_pipeline_rc920_source_recovery_adversarial.py::test_r03_falha_de_publicacao_exige_novo_coletor`.

**RC9.20.** Após a exceção no Renko, a chamada seguinte deveria retornar `None` e registrar `PROFIT_QUOTE_REINITIALIZATION_REQUIRED`, ainda com a injeção de falha instalada.

**Motivo da obsolescência.** Na RC9.21, a próxima chamada pode preparar um novo ciclo após uma falha isolada. Como o teste histórico mantém a injeção ativa, a segunda chamada voltou a encontrar `RuntimeError("Renko")` na preparação.

**Contrato RC9.21 e testes substitutos.** Removida a falha transitória, o mesmo coletor aceita a mesma cotação ou uma nova. Os quatro casos parametrizados verificaram uma publicação, volume atribuído uma vez, contadores coerentes e deduplicação da repetição posterior. Já uma exceção na cópia isolada bloqueia o coletor antes de novas leituras. `test_renko_copy_failure_requires_explicit_new_collector` confirmou o bloqueio para a mesma cotação e uma nova e verificou a retomada em nova instância com bases novas. [Testes Renko A3.3](tests/test_pipeline_rc921_renko_transactional_regression.py)

## Execução e integridade

| Seleção | Aprovados | Falhas históricas obsoletas | Falhas novas |
|---|---:|---:|---:|
| RC9.18/19/20, Collector multitemporal e Renko | 155 | 2 | 0 |
| RC9.21-A3 | 18 | 0 | 0 |
| RC9.21-A3.2 | 3 | 0 | 0 |
| Novos casos Renko A3.3 | 5 | 0 | 0 |
| **Total** | **181** | **2** | **0** |

Os quatro testes históricos RTD fazem parte da primeira linha e passaram. A execução durou 22,12 s no pytest e gerou um aviso de depreciação no `anyio`. As duas falhas históricas foram executadas normalmente. O JUnit local está em `C:/Users/jb/AppData/Local/Temp/rc921-a33-6ccb83a97a0a4367bebfc84953e9eceb/results.xml`, com SHA-256 `4844dcac2a1e81126366e3e3ac37da0c779791c20f4734e729744c6d4cdc31d7`.

Os dois testes históricos foram preservados na árvore de trabalho e no checkpoint RC9.20. SHA-256 dos arquivos históricos:

- `test_pipeline_rc920_integrated_offline.py` — `df1ff1fdd5cab305e5dbe19503c0ebb1b4c828fcc06e5e629e8155ee220fe8a8`
- `test_pipeline_rc920_source_recovery_adversarial.py` — `6bfc94fb5194481dac6b2df26ac01a85c9a11bf659547267db72cab575e1e939`

Os checkpoints RC9.19 e RC9.20, `ULTIMO_MARCO.json`, o índice Git e os arquivos A2/A3/A3.2 mantiveram os hashes aferidos. Nenhum arquivo existente foi alterado. Commit e push ocorreram em zero casos.

## Proposta de migração

Em etapa autorizada, revisar somente os dois casos históricos no local original. Vincular os nomes antigos, os hashes e as falhas desta execução aos testes substitutos. Migrar asserções de avanço parcial e bloqueio permanente para preservação do estado e retry seguro. Manter o teste de reinicialização para falha na própria cópia e a evidência original na RC9.20 consolidada. Reexecutar a regressão direcionada com ambos os casos migrados presentes na coleta.

`F3=OPEN`, `offline=True`, `simulation_only=True`, `certification=False` e `real_operations_authorized=False`. Nenhuma conexão ao Profit real ou operação financeira ocorreu.
