# F3-INT-108 — auditoria offline de continuidade

Base: `C:\COPILOTO_F3_INT108\audit`. Data: 22/10/2026.
`tools/`, `tests/` e `ULTIMO_MARCO.json` existem. O marcador e
`CHECKPOINT_F3_INT107_FINAL.json` registram F3-INT-107 definitivo, 18 testes
especificos e 1277 de regressao aprovados na execucao anterior informada.
Esse registro nao equivale a uma reexecucao integral nesta etapa.

## Arquivos examinados

- `tools/f3_int105_typed_identity_envelope.py` e seu teste homonimo.
- `tools/f3_int106_typed_batch_manifest.py` e seu teste homonimo.
- `tools/f3_int107_typed_batch_chain.py` e seu teste homonimo.
- `tools/f3_int104_domain_scoped_commitment.py` (validacao do escopo/revisao).
- `ULTIMO_MARCO.json`, `CHECKPOINT_F3_INT107_FINAL.json` e
  `RELATORIO_F3_INT107_FINAL.md`.

## Contraexemplos anteriores a correcao

A execucao inline foi concluida com exit 0 antes da criacao do novo modulo.
Saida registrada em `legacy_before_fix.log`; reprodutor equivalente em
`reproduce_f3_int108_legacy.py`. Executar da pasta audit:

```
python -B reproduce_f3_int108_legacy.py
```

Fixture: lotes `(audit/x, revisao 1)`, `(report/y, revisao 2)`,
`(audit/z, revisao 3)`, mesmo segmento, contexto `audit:fixture/A`, proposito
`evidence-review`, execucao `run:1`.

| Entrada | Resultado INT-107 sem expectativa |
|---|---|
| Cadeia completa | CHAIN_FIXTURE_UNAUTHENTICATED |
| Remocao do primeiro lote | CHAIN_FIXTURE_UNAUTHENTICATED |
| Remocao do ultimo lote | CHAIN_FIXTURE_UNAUTHENTICATED |
| Apenas primeiro lote antigo | CHAIN_FIXTURE_UNAUTHENTICATED |
| Lote intermediario trocado por report/other na mesma revisao | CHAIN_FIXTURE_UNAUTHENTICATED |
| Identidade audit/x repetida na revisao seguinte | CHAIN_FIXTURE_UNAUTHENTICATED |

Os hashes diferem: nao houve colisao nem quebra da vinculacao criptografica.
A lacuna demonstrada e a admissao sem referencia externa obrigatoria quando
o construtor e empregado como verificador de continuidade/completude. INT-107
permite expectativas opcionais e nao registra consumo nem piso de revisao.
O status legado declara apenas consistencia de fixture nao autenticada.
Repeticao de identidade em revisoes distintas nao e, por si, vulnerabilidade:
nao foi criada proibicao geral que alterasse essa semantica.

## Correcao isolada

Novo `tools/f3_int108_typed_chain_guard.py`, API `verify_typed_chain`:

- exige `expected_digest` valido e independente da entrada;
- exige `minimum_revision` inteiro inclusivo, mantido pelo chamador;
- exige historico explicito `consumed_chain_digests` como frozenset de ate 4096 hashes;
- delega recomputacao, validacao de filhos, sequencia e comparacao do hash a INT-107;
- rejeita cadeia cuja primeira revisao fique abaixo do piso;
- rejeita hash ja consumido; nao modifica historico automaticamente.

O pin completo existente ja detecta remocao e substituicao. Nao foram
duplicados hashes de encadeamento, validacoes de contexto, tipos, revisoes,
identidades internas ou expectativas de lotes. Contexto, proposito, run_id e
revisao divergentes sao recusados pela comparacao delegada ao pin retido.

Contrato de uso: selecionar previamente o pin da janela completa esperada,
carregar piso e historico retidos, verificar a entrada e, somente em sucesso,
reter seu digest no historico e avancar o piso alem da ultima revisao admitida.
Uma revisao final 2147483647 esgota esse dominio: nao se deve reiniciar o piso.
Uma janela parcialmente sobreposta a revisoes anteriores e rejeitada pelo piso;
esta fachada verifica janelas completas novas, nao extensoes cumulativas com
prefixo ja consumido. Seu resultado de sucesso conserva o status nao autenticado.

Os seis arquivos legados e os dois marcadores permanecem preservados;
`preserved_sha256.json` registra seus hashes. Nenhum checkpoint INT-108 e criado.

## Arquivos novos

- `tools/f3_int108_typed_chain_guard.py`.
- `tests/test_f3_int108_typed_chain_guard.py` (16 testes).
- `reproduce_f3_int108_legacy.py`.
- Este relatorio, `legacy_before_fix.log`, `specific_tests.log`,
  `preserved_sha256.json` e registro final de verificacao.

## Testes

Com PYTHONPATH incluindo audit e audit/tests, Python 3.13, sem bytecode:

```
python -B -m unittest test_f3_int105_typed_identity_envelope test_f3_int106_typed_batch_manifest test_f3_int107_typed_batch_chain test_f3_int108_typed_chain_guard.ChainGuardTests -v
```

Resultado: **64/64 testes OK em 296,591 segundos**, zero falhas ou skips
reportados pelo unittest. Saida em `specific_tests.log`. O PowerShell retornou
1 por tratar stderr do Python como NativeCommandError no pipeline de captura;
esse codigo de shell nao e apresentado como exit 0 do interpretador.
Para verificar o codigo real sem essa ambiguidade, os 16 testes novos foram
reexecutados via subprocess com stderr redirecionado diretamente ao arquivo:
`new_tests.log` e `new_tests_result.json` registram resultado e codigo do Python.
Essa confirmacao passou em **16/16 testes, 83,653 segundos no unittest,
84,291 segundos incluindo o subprocess, exit 0**.
Nao houve reexecucao integral dos 1277 testes nesta etapa.
Os testes novos cobrem sucesso, cortes nas extremidades e no meio,
substituicao intermediaria, replay consumido, pin antigo com piso novo,
limite inclusivo, contexto/proposito/run/revisao divergentes, argumentos
obrigatorios, entradas invalidas, delegacao, imutabilidade e sete bloqueios.

## Riscos e limites

Pins, piso e historico continuam sendo estado do chamador. Se forem gerados
da propria entrada adversarial ou restaurados em conjunto com uma cadeia
antiga, esta podera ser aceita. Ausencia de armazenamento confiavel e de
consumo atomico permite corrida entre chamadas concorrentes. O limite de
4096 hashes exige politica externa de retencao; apagar historico pode permitir
replay se o piso tambem nao o impedir. Nao ha prova de origem ou de veracidade.
As APIs legadas permanecem construtores disponiveis com expectativas opcionais.
A fachada deve ser escolhida explicitamente para verificacao estrita.

## Proximos passos dentro da etapa

Revisar o contrato da nova fachada e fornecer expectativas de uma referencia
independente ao usa-la em auditoria. Uma regressao integral futura deve ser
registrada separadamente antes de qualquer atualizacao de marco definitivo.
Nao houve avanco para F3-INT-109.

F3=OPEN. orders_allowed, live_certified, flow_complete, f3_resolved,
native_prototype_authorized, strict_deadline_guaranteed e
authenticated_witness_verified permanecem false em sucesso e rejeicao.
Sem Profit, Excel, RTD, DDE, corretora, rede operacional ou ordens.
Hashes nao autenticam origem; nenhuma certificacao operacional e declarada.
