# F3-INT-110 — continuidade transacional offline (CANDIDATO)

Base: `C:\COPILOTO_F3_INT108`. Último marco definitivo: F3-INT-109.
Nenhum módulo anterior, teste aprovado ou checkpoint definitivo foi alterado.
`ULTIMO_MARCO.json` permanece em F3-INT-109. F3=OPEN; sete bloqueios false.

## 1. Arquivos examinados

- `audit/ESCOPO_F3_INT110_PRELIMINAR.md`.
- `audit/tools/f3_int108_typed_chain_guard.py` e seu teste homônimo.
- `audit/tools/f3_int109_offline_consumption_store.py` e seu teste homônimo.
- Marcador e checkpoint FINAL 109, como base de preservação e de segurança.

108 verifica cadeia, pin, piso e histórico; 109 adiciona armazenamento SQLite,
âncora de estado e transação local. O contrato 109 declara explicitamente que
rollback conjunto, cópias do banco e confirmação perdida não estão resolvidos.

## 2. Contraexemplos ANTES da implementação

Executado `reproduce_f3_int110_before.py` contra os módulos anteriores intactos,
antes da criação da nova fachada. Resultado: **9/9 testes OK, 50,996 s no
unittest; 55,062 s no subprocess; exit 0**. O teste adversarial passa quando
reproduz o comportamento defeituoso ou o limite arquitetural esperado.
Evidências: `CONTRAEXEMPLOS_F3_INT110.log` e
`CONTRAEXEMPLOS_F3_INT110_RESULTADO.json`.

| Cenário | Observação reproduzida | Classificação |
|---|---|---|
| A: banco e âncora restaurados juntos | A mesma cadeia é consumida de novo depois de voltar ao snapshot inicial. | Limitação arquitetural conhecida; exige referência fora do domínio restaurado. |
| B: confirmação perdida após commit | Retorna COMMIT_OUTCOME_UNKNOWN; consumo existe e repetição com âncora antiga é rejeitada. | Limite declarado de confirmação/reconciliação, não defeito novo. |
| C: reinício durante transação | Processo filho morto após escrita e antes do commit; reabertura recupera o estado anterior. | Proteção existente confirmada; não duplicada. |
| D: âncora antiga | STATE_ANCHOR_MISMATCH após consumo confirmado. | Proteção existente confirmada. |
| E: concorrentes no mesmo arquivo | Segundo consumidor encontra STORE_BUSY enquanto a transação está aberta. | Proteção local existente confirmada. |
| E: bancos clonados | Duas cópias aceitam a mesma evidência independentemente. | Exige coordenação/fencing externo; transação local não resolve. |
| F: histórico diferente da âncora | Alteração válida do piso é rejeitada por STATE_ANCHOR_MISMATCH. | Proteção existente confirmada. |
| G: trigger ignora UPDATE | 109 retorna sucesso, mas consumo e piso continuam antigos; nova chamada aceita novamente. | Falha real de confirmação da escrita, sob esquema SQLite alterado. |
| H: trigger desfaz UPDATE | UPDATE informa linha afetada, mas AFTER UPDATE restaura OLD.payload; 109 confirma consumo inexistente. | Segunda variante da mesma falha de implementação. |

Reprodução, com o Python instalado e a partir da base:

```
$env:PYTHONPATH='C:\COPILOTO_F3_INT108\audit;C:\COPILOTO_F3_INT108\audit\tests'
python -B audit/reproduce_f3_int110_before.py
```

Fixtures sintéticas reais de 109 são usadas, com conexões fechadas explicitamente.
Nenhum banco operacional ou serviço externo participa desses testes.

## 3. Falha confirmada e condição necessária

O digest de estado 109 vincula o payload, não o esquema SQLite. Um banco cujo
payload inicial ainda corresponde à âncora pode conter os seguintes triggers:

```
CREATE TRIGGER discard BEFORE UPDATE ON state
BEGIN SELECT RAISE(IGNORE); END;

CREATE TRIGGER undo AFTER UPDATE ON state
BEGIN UPDATE state SET payload=OLD.payload WHERE id=1; END;
```

São variantes testadas separadamente, não instaladas simultaneamente.
Na primeira variante não há linha atualizada; na segunda a linha é contada,
mas o conteúdo final volta ao valor anterior. O código 109 não confere o número
de linhas nem relê a transição antes de confirmar. O commit pode concluir sem
persistir o consumo esperado e a API ainda retorna CONSUMED_FIXTURE_UNAUTHENTICATED.
Isso difere da confirmação perdida: aqui uma confirmação positiva é devolvida
para um consumo que não existe no registro.

O defeito depende de banco/esquema alterado ou equivalente desvio na escrita;
não foi demonstrada duplicação espontânea em um banco normal criado por 109.
O código e a tabela originais não foram modificados na investigação: somente
arquivos de fixtures temporárias receberam triggers adversariais.

## 4. Correção isolada

Novo `audit/tools/f3_int110_confirmed_consumption.py`, API
`consume_chain_confirmed`, com o formato de estado e o resultado de 109:

1. Mantém a conferência de âncora, escopo, piso, cadeia e capacidade.
2. Executa a atualização dentro de BEGIN IMMEDIATE.
3. Exige exatamente uma linha afetada.
4. Relê e valida o estado inteiro, na mesma transação, comparando com o próximo
   estado esperado: escopo, geração, piso e histórico, não apenas um hash calculado.
5. Faz commit e retorna sucesso somente após essa confirmação.

UPDATE ignorado ou revertido retorna `STATE_WRITE_NOT_CONFIRMED`, sem novo
digest ou confirmação. Readback estruturalmente corrompido rejeita. O fechamento
da conexão antes do commit desfaz também efeitos laterais dos triggers.
Trigger benigno que não altera a transição esperada continua permitido.

Reutilizados `_connect`, `_load`, `_encode`, `_digest`, tratamento de erros e
verificador 108 expostos no módulo 109. Não foram reimplementadas validações de
identidade, hashes da cadeia ou esquema de payload. A fachada precisa controlar
a transação: chamar o consumidor 109 e conferir somente depois do commit seria
tarde para desfazer a operação. Os helpers privados criam acoplamento explícito
à versão 109; seus hashes foram preservados e a compatibilidade é testada.

As APIs legadas permanecem intactas, inclusive seu limite demonstrado. A proteção
nova exige escolher explicitamente a fachada 110. Não há migração de banco,
reinicialização permissiva, reparo automático ou novo protocolo de autenticação.

## 5. Testes

19 testes novos cobrem sucesso equivalente ao resultado legado, triggers de
ignore/undo/piso incorreto/registro inválido, trigger benigno, rollback de efeitos
laterais, repetição após remoção do trigger defeituoso, continuidade normal,
âncora antiga, consumidor concorrente, confirmação perdida, interrupção antes e
depois da escrita, morte real de processo antes/depois do commit, rollback
conjunto como limite explícito, histórico divergente, entradas inválidas e locks.

Foram incluídos também os 29 testes 109 e os 16 testes 108. Comando:

```
python -B -m unittest test_f3_int110_confirmed_consumption.ConfirmedConsumptionTests test_f3_int109_offline_consumption_store.ConsumptionStoreTests test_f3_int108_typed_chain_guard.ChainGuardTests -v
```

Diretório: `audit`; PYTHONPATH com audit e audit/tests; sem bytecode e com saída
UTF-8. Métricas finais em `RESULTADO_F3_INT110_ESPECIFICOS.json` e log completo
em `LOG_F3_INT110_ESPECIFICOS.txt`. O candidato só é preparado se os 64 testes
passarem e os hashes anteriores permanecerem iguais.

A regressão histórica completa da F3-INT-110 não foi executada nesta etapa.
Os 1322 testes aprovados são evidência definitiva anterior, não nova aprovação
integral de 110. A descoberta integral esperada com os 19 novos é de 1341 testes.

## 6. Limitações e garantias externas

- Restaurar banco e âncora juntos continua permitindo replay, inclusive pela
  fachada nova; um teste documenta esse limite. Hash ou contador no mesmo backup
  não fornece uma referência independente.
- Confirmação perdida continua exigindo reconciliação independente. O banco e
  a retenção da âncora não possuem commit distribuído. Não foi criada uma API
  que simplesmente recalcule a âncora do banco não confiável e a aceite.
- SQLite serializa o mesmo arquivo, não cópias, hosts ou domínios independentes.
  Não há fencing distribuído nem garantia de exatamente uma entrega ao chamador.
- Morte de processo não equivale a falha física de energia/disco/filesystem.
  FULL/DELETE solicitado não comprova durabilidade de hardware.
- Readback protege a transição observada dentro de uma transação SQLite normal;
  pressupõe engine e semântica de commit confiáveis. Não constitui auditoria
  completa de formatos SQLite hostis, SO comprometido ou manipulação fora dos locks.
- Hashes e âncoras não autenticam origem. Gestão confiável de identidades,
  referências e chaves continua externa ao modelo.
- Capacidade e domínio de revisões continuam limitados conforme 109.

## 7. Arquivos criados e preservação

- `audit/tools/f3_int110_confirmed_consumption.py`.
- `audit/tests/test_f3_int110_confirmed_consumption.py`.
- `audit/reproduce_f3_int110_before.py`.
- `audit/CONTRAEXEMPLOS_F3_INT110.log` e resultado JSON dos contraexemplos.
- `audit/PRESERVACAO_F3_INT110.json`: snapshot de 338 arquivos anteriores.
- Log e resultado dos testes específicos, este relatório e checkpoint CANDIDATO.

Scripts auxiliares de preparação/execução estão fora dos módulos de auditoria.
Nenhum arquivo aprovado anterior foi editado. Próximos passos dentro desta etapa:
revisar o candidato e executar a regressão integral antes de eventual consolidação.
Não houve avanço para F3-INT-111.

F3=OPEN; orders_allowed, live_certified, flow_complete, f3_resolved,
native_prototype_authorized, strict_deadline_guaranteed e
authenticated_witness_verified permanecem false. Auditoria exclusivamente offline,
sem Profit, Excel, RTD, DDE, corretora ou ordens. Sem certificação operacional.
