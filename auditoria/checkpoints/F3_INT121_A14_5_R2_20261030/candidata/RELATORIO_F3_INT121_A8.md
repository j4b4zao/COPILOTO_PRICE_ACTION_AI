# F3-INT-121 A8 — consumo e pedido de atestado no mesmo commit

Data: 28/10/2026. Classificação: ATOMIC_LOCAL_CONSUMPTION_OUTBOX_PROTOTYPE.

## Alteração

O A7 gravava o consumo e preparava a fila em transações separadas. O escritor
experimental A8 guarda as tabelas `state`, `metadata` e `outbox` em um único
arquivo SQLite. Uma única transação `BEGIN IMMEDIATE` valida a cadeia, atualiza
o histórico de consumo e insere o envelope assinado pendente.

O commit local passa a ter dois estados coerentes: antes dele, consumo e pedido
não existem; depois dele, ambos estão persistidos. A confirmação da testemunha
continua em outro banco, fora dessa transação. Não há transação distribuída.

Uma geração pendente impede que `consume()` admita a próxima. `dispatch()`
reenvia o envelope persistido, verifica o recibo da chave pública fixada e grava
o ACK local. Somente esse ACK libera a próxima geração do escritor cooperante.

`f3_int121_a8_atomic_store.py` fornece `AtomicConsumptionStore`. Ele reutiliza
os verificadores de envelope/recibo e ledger do A7, preservando os módulos
anteriores. O formato do payload `state` e o cálculo de digest permanecem
compatíveis com o armazenamento F3-INT-109 e a leitura A6.

## Regras preservadas e regra nova

- `journal_mode=DELETE`, `synchronous=FULL`, `trusted_schema=OFF`.
- Fonte, sequência e último digest do ledger precisam corresponder na abertura,
  antes de consumir e antes do commit local.
- Âncora, escopo, revisão, cadeia, replay e limite de 4096 continuam validados
  pelo mesmo contrato e helpers congelados do armazenamento examinado.
- Nova precedência: após validar o formato da âncora e a coerência persistida,
  um atestado pendente causa `ATTESTATION_PENDING` antes de analisar a próxima
  âncora/revisão/cadeia. Essa recusa não grava uma nova geração.
- Falha ao inserir o pedido desfaz a atualização de `state`, e vice-versa.
- Na falha de commit, `COMMIT_OUTCOME_UNKNOWN` exige reabertura e inspeção;
  não é convertido em sucesso nem em retry automático de consumo.
- Todas as sete travas dos resultados continuam False. `safe_to_promote`
  sempre retorna False, inclusive após consumo e ACK locais.

## Fluxo de uso local

```text
consume(cadeia + âncora)
  BEGIN IMMEDIATE
  validar fonte/ledger e ausência de pendência
  validar cadeia e capacidade
  UPDATE state + INSERT outbox(pedido assinado)
  COMMIT
  → CONSUMED_PENDING_ATTESTATION_LOCAL

dispatch(testemunha.submit)
  BEGIN IMMEDIATE
  verificar fonte + pedido pendente
  enviar exatamente o envelope persistido
  verificar assinatura e vínculo do recibo
  UPDATE outbox(ACK)
  COMMIT
  → LOCAL_ATTESTATION_ACKNOWLEDGED

consulta A6 com novo desafio → comparação local do estado atestado
```

Inicialização: fornecer caminho novo, store_id, tupla de escopo, chave privada
do cliente e chave pública fixada da testemunha, com `create=True`. Ela cria
fonte e fila juntas na geração zero. Para reabrir, omita `create` e mantenha a
identidade esperada. Bancos existentes não são sobrescritos; ausentes não são
recriados na retomada. Não há migração automática de A7 ou de bancos avançados.

`consume()` recebe os argumentos de cadeia do escritor original:
`segments`, `expected_state_digest`, `expected_digest`, `context`, `purpose`,
`run_id`, `batches` e `base_registry` opcional. `state()` expõe geração,
sequência, head, digest e pedido pendente verificados. `prepare()` não grava
nada: informa que a preparação integra o consumo atômico.

## Validação e evidências

Suíte nova: `test_f3_int121_a8_atomic_store.py`.
Logs: `VALIDACAO_A8_ATOMIC_STORE.txt` e `VALIDACAO_A8_PYTHON_O.txt`.
Regressão direcionada A5/A6/A7: `REGRESSAO_A5_A7_PARA_A8.txt`.
O resumo executado é registrado em `RESULTADOS_A8.json` no pacote.

Execução normal A8: **26/26 aprovados em 258,422 segundos**.
Execução A8 com Python `-O`: **26/26 aprovados em 145,220 segundos**,
incluindo subprocessos iniciados com a mesma otimização.
Regressão A5/A6/A7: **74/74 aprovados em 270,111 segundos**.
Os **68 hashes** da entrega anterior A7 foram reconferidos sem alterações.

Cobertura:

- Consumo e envelope coerentes; confirmação A5 e consulta A6 com desafio novo.
- Bloqueio de nova geração enquanto pendente e liberação somente após ACK.
- Reabertura preservando o mesmo pedido e nonce.
- Falhas na escrita do estado, inserção do pedido, conexão read-only e ACK.
- Commit recusado por leitor concorrente: resultado incerto, seguido de
  reabertura comprovando ausência dos dois registros nesse cenário específico.
- Encerramento real de subprocesso com `os._exit(73)` depois do UPDATE,
  depois do INSERT, antes do commit, depois do commit do consumo, depois do
  ACK da testemunha e depois do commit do ACK local.
- Dois subprocessos concorrentes: só um admite a geração; o outro encontra
  o atestado pendente.
- Recibo inválido ou resposta perdida não desbloqueiam novo consumo.
- Lock de escrita durante o envio exclui outro escritor SQLite ordinário.
- Recusa de replay, âncora/escopo/digest inválidos e WAL incompatível.
- Fronteira 4095 → 4096 e recusa da 4097ª entrada sem alterar os bytes do banco
  nem acrescentar envelope.

O teste de fronteira usa um ledger sintético com assinaturas válidas e um
histórico de consumo sintético para alcançar 4095; não executa nem comprova
4095 consumos anteriores reais. As transições testadas em 4096/4097 usam o
escritor A8. As chaves determinísticas são fixtures públicas de teste.
Os testes de morte de processo propagam `-O` aos filhos quando a suíte é
iniciada com essa opção.

## Executar

Extraia preservando scripts, testes, fixtures e a pasta `a6_vendor`. Requer
Python e `cryptography`. No ambiente utilizado nesta máquina:

```powershell
& 'C:\COPILOTO_PRICE_ACTION_AI\ambiente\Scripts\python.exe' -B '.\test_f3_int121_a8_atomic_store.py' -v
& 'C:\COPILOTO_PRICE_ACTION_AI\ambiente\Scripts\python.exe' -B -O '.\test_f3_int121_a8_atomic_store.py' -v
```

## Limites e próximo passo

1. Esta é uma variante isolada para teste offline. O runtime principal, os
   módulos históricos e os marcos oficiais não foram alterados.
2. O bloqueio de pendências pertence à API cooperante A8. O escritor legado
   ou SQL direto ainda consegue alterar `state` sem manter `outbox`. Há teste
   explícito: o legado admite a alteração, e o A8 detecta a divergência e
   recusa abertura/novo consumo. Não se trata de fencing contra bypass.
3. A atomicidade local não abrange o banco A5. ACK perdido é reconciliado por
   replay do pedido persistido; não há certificação de exactly-once operacional.
4. Fonte e testemunha continuam locais. Rollback conjunto válido, custódia
   independente, checkpoint monotônico externo e transporte autenticado
   permanecem pendentes.
5. O callback síncrono de testemunha deve impor seu próprio timeout. Enquanto
   bloqueado, mantém o lock de escrita; prazo estrito não é garantido.
6. Sem teste físico de perda de energia ou falha real de fsync. As falhas de
   escrita são controladas; morte de processo não comprova durabilidade física.
7. A verificação percorre todo o ledger; não houve ensaio de desempenho ou
   regressão integral de todas as etapas históricas do projeto.

Próxima etapa: auditar o contrato do escritor A8 e preparar uma rota de
integração que faça todos os consumidores do projeto utilizarem a mesma API,
com bootstrap/migração explícitos e sem fallback para o escritor legado.

F3: OPEN. OPERACOES REAIS: BLOQUEADAS. PROMOCAO A FINAL: BLOQUEADA.
