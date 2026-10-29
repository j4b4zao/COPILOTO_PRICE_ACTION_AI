# F3-INT-109 — persistência e consumo offline (CANDIDATO)

Base: `C:\COPILOTO_F3_INT108`. Marco definitivo preservado: F3-INT-108.
F3=OPEN. Nenhuma alteração nos módulos ou checkpoints anteriores.

## Inspeção e contratos

Lidos `audit/ESCOPO_F3_INT109_PRELIMINAR.md` e os módulos de 105 a 108.
105 vincula identidade tipada ao escopo; 106 agrega identidades ordenadas;
107 vincula lotes, revisões e predecessores; 108 exige pin completo, piso e
histórico, mas não armazena nem consome estado. A nova camada chama 108
dentro de uma transação. Não repete a recomputação das evidências.

## Contraexemplos anteriores à implementação

`reproduce_f3_int109_before.py` foi executado antes de criar a implementação.
`before.log`: **5/5 testes OK, 63,932 s no unittest; exit 0**.
Os asserts demonstram a aceitação indesejada, não uma correção já existente.

| Caso | Demonstração |
|---|---|
| Rollback completo | Estado atual bloqueia; restaurar piso/histórico antigos permite aceitar a mesma cadeia novamente. |
| Reinício sem retenção | Duas verificações com histórico vazio e piso inicial aceitam a mesma evidência. |
| Dois consumidores | Duas verificações do mesmo snapshot aceitam a mesma cadeia; não há consumo atômico em 108. |
| Gravação interrompida | Fixture JSON truncada não pode ser lida; fallback explícito e inseguro do chamador ao estado inicial permite replay. |
| Corrupção legível | Apagar o consumo e reduzir o piso em JSON sintaticamente válido permite nova aceitação. |

As fixtures de JSON e fallback são adaptadores deliberadamente ingênuos nos
testes. Não existe persistência JSON na F3-INT-108 e não se atribui a ela uma
falha de implementação de armazenamento inexistente. São limites demonstrados
de integração com estado externo. Comandos, incluindo audit/tests em PYTHONPATH:

```
python -B audit/reproduce_f3_int109_before.py
```

## Solução isolada

Novo módulo `audit/tools/f3_int109_offline_consumption_store.py`:

- `create_store`: inicialização explícita, exclusiva; recusa caminho existente
  e não recria silenciosamente bancos ausentes no consumo.
- `verify_store`: confere estrutura canônica e digest do registro contra uma
  âncora independente obrigatória fornecida pelo chamador.
- `consume_chain`: `BEGIN IMMEDIATE`, leitura e conferência da âncora, escopo
  fixado, chamada à F3-INT-108, atualização conjunta de consumo/piso/geração,
  e commit. O resultado de sucesso só sai após o commit.
- Histórico limitado a 4096: esgotamento rejeita, sem apagar registros.
  Revisão final máxima esgota o domínio; não reinicia o piso.
- SQLite em modo journal DELETE e synchronous FULL. Sem rede, serviços ou
  dependências além da biblioteca padrão. O ponto privado `_checkpoint` permite
  injetar interrupções determinísticas e matar apenas processos filhos de teste.

O digest de estado tem domínio próprio e inclui escopo, geração, piso e
histórico. A representação JSON é canônica, com esquema fechado, tamanho
limitado e validação de tipos. Corrupção sintática/estrutural rejeita; alteração
legível ou restauração rejeita se a âncora externa retida não corresponder.
Erros de banco e bloqueios são rejeições, sem fallback para histórico vazio.

Relação com os contraexemplos: retenção no banco cobre reinício; transação
cobre a janela entre verificar e registrar consumo; journal cobre interrupção
do processo antes do commit; âncora independente cobre rollback do banco e
adulteração coerente do registro enquanto a âncora atual for preservada.

## Contrato de uso e confirmação incerta

O chamador retém independentemente o `state_digest` retornado na criação e,
após consumo confirmado, o novo `state_digest`. O pin de cadeia continua sendo
uma referência independente. Não se deve calcular a âncora a partir do banco
recebido e então tratá-la como confiável.

O commit do banco e a publicação/retencão dessa âncora externa não formam
uma transação distribuída. Uma interrupção após commit e antes da confirmação
pode deixar o banco avançado e o chamador com âncora antiga. A camada rejeita
a repetição e exige reconciliação independente, que não foi implementada.
O teste injetado retorna `COMMIT_OUTCOME_UNKNOWN`; morte real do processo não
retorna resultado. Não se deve restaurar o banco ou fabricar uma âncora para
forçar disponibilidade.

## Testes e evidências

Executados os testes novos do armazenamento e os 16 testes da F3-INT-108.
Comando e métricas finais constam em `RESULTADO_F3_INT109_ESPECIFICOS.json`
e `LOG_F3_INT109_ESPECIFICOS.txt`.

**Resultado final: 45/45 aprovados, sendo 29 novos e 16 de compatibilidade;
zero falhas, erros ou skips; exit 0; 99,822 s no unittest e 100,448 s incluindo
o subprocess.** Não houve ResourceWarning na execução final. Comando:

```
python -B -m unittest test_f3_int109_offline_consumption_store.ConsumptionStoreTests test_f3_int108_typed_chain_guard.ChainGuardTests -v
```

O checkpoint `CHECKPOINT_F3_INT109_CANDIDATO.json` foi preparado após essa
aprovação. Os 333 hashes do snapshot prévio conferiram, incluindo os módulos
anteriores, seus testes, checkpoints e o marcador definitivo. As fontes novas
testadas têm seus hashes registrados no resultado e no candidato.

Cobertura: criação/reabertura, persistência de consumo, avanço para nova cadeia,
reinício, snapshot antigo, rollback com âncora atual, rollback conjunto como
limite explícito, ausência de recriação, entradas inválidas, escopo, delegação,
concorrente bloqueado sob transação real, interrupções antes/depois da escrita,
confirmação perdida, morte de processo filho antes/depois do commit,
JSON inválido/profundo/não canônico, esquema adulterado, banco ilegível,
registros vazios/duplicados/excessivos, capacidade, domínio de revisões e locks.

A primeira execução terminou com **45 testes, 1 falha e 11 erros, 173,852 s**.
Os erros eram de limpeza de bancos com conexões abertas nos auxiliares de
teste; corrigido o fechamento explícito com `contextlib.closing`. A falha
comparava fixtures recriadas independentemente no pai e no filho, que tinham
digests diferentes. O teste agora transmite os mesmos bytes da fixture ao
filho, em JSON/base64, sem recriação nem desserialização executável.
`LOG_F3_INT109_TENTATIVA1.txt` preserva essa tentativa. O primeiro capturador
também encontrou um erro de decodificação da saída nativa; a nova execução
fixa `PYTHONIOENCODING=utf-8`. Nenhum módulo anterior foi alterado.
A regressão histórica completa não foi executada nesta etapa; os 1293 testes
da F3-INT-108 são evidência anterior, não uma nova aprovação integral de 109.

## Arquivos e preservação

- Novo módulo de armazenamento e novo teste em `audit/tools` e `audit/tests`.
- `audit/reproduce_f3_int109_before.py`, `audit/before.log` e
  `audit/preserved_before.json` (snapshot prévio de 333 arquivos).
- Logs de testes, resultado JSON, este relatório e checkpoint candidato 109.
- Os scripts de execução/preparação ficam na área de trabalho auxiliar, fora
  dos módulos de auditoria e do projeto operacional.

O checkpoint CANDIDATO só é gerado após testes aprovados e conferência dos
hashes preservados. `audit/ULTIMO_MARCO.json` permanece em F3-INT-108.
O pacote ZIP definitivo de 108 não foi alterado nem substituído.

## Riscos remanescentes

- Rollback conjunto do banco e da âncora continua permitindo replay; há um
  teste positivo que comprova esse limite. Âncora local no mesmo backup não
  seria independente.
- O banco serializa consumidores do mesmo arquivo. Cópias independentes do
  banco, múltiplas máquinas e restauração concorrente não possuem fencing.
- A configuração SQLite e os testes de morte de processo não comprovam
  durabilidade contra queda de energia, defeito de disco/controladora ou
  filesystem que não cumpra as garantias esperadas. Não foi simulada falha física.
- Histórico cheio e revisão esgotada bloqueiam novos consumos. Não há política
  de compactação ou migração implementada.
- Falha de confirmação exige reconciliação; nenhuma recuperação permissiva
  ou garantia de exatamente uma entrega ao chamador é alegada.
- Hashes, pins e a âncora não autenticam origem. Banco/estado do chamador
  permanecem no domínio de confiança declarado. A superfície completa de
  arquivos SQLite hostis não foi auditada.

Próximos passos dentro da F3-INT-109: revisão do candidato e regressão completa
antes de eventual consolidação. Não houve avanço para F3-INT-110.

F3=OPEN; orders_allowed, live_certified, flow_complete, f3_resolved,
native_prototype_authorized, strict_deadline_guaranteed e
authenticated_witness_verified permanecem false. Sem Profit, Excel, RTD, DDE,
corretora ou ordens. Nenhuma certificação operacional.
