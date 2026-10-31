# F3-INT-121 A7 — fila persistente de atestados e reconciliação da base

Data: 28/10/2026. Classificação: DURABLE_LOCAL_ATTESTATION_OUTBOX_PROTOTYPE.

## Correção da interpretação anterior

O item 5 dos limites do relatório A6 sugeria uma incompatibilidade entre o
limite de 4096 entradas do armazenamento e a correção anterior. Essa inferência
estava incorreta. A correção R2 da sonda F3-INT-117 acrescentou a recusa da
4097ª entrada **antes da escrita**; não removeu o limite de 4096 do armazenamento.
A F3-INT-118 encontrada em `r11826` trata do executor Python e sua otimização.

Foram comparados os bytes de `f3_int109_offline_consumption_store.py` das árvores
`r11726`, `r11826` e `C:\COPILOTO_PRICE_ACTION_AI\f3_int117_corrigida`.
As três cópias são idênticas, com SHA-256:

`ea990a447ac3cbb31ee63dd4709c830c11088d202ae24703442545fb245c83cf`

O A6 já reutiliza essa mesma implementação, com adaptação apenas do namespace
dos imports. Não foi necessário substituir o armazenamento nem alterar sua
capacidade. `RECONCILIACAO_BASE_A7.json` registra os caminhos e hashes.
O relatório A6 histórico foi preservado; esta nota corrige a interpretação.

A divergência documental de marcos (116 na raiz versus 117 R2 reportado no U23)
continua sem resolução de autoridade. Nenhum ULTIMO_MARCO foi editado, e essa
comparação de fontes não constitui promoção ou validação do marco oficial.

## Implementação

`f3_int121_a7_outbox.py` fornece `AttestationOutbox`:

1. Cria uma fila SQLite separada, apenas com bootstrap explícito de uma fonte
   válida na geração zero. Fixa store_id, escopo e chaves públicas esperadas.
2. Após um commit de consumo do projeto, `prepare()` lê o estado e persiste
   envelope assinado, digest, sequência e nonce, antes de permitir o envio.
3. Reabertura e repetição de `prepare()` reutilizam o envelope já persistido.
4. `dispatch(callback)` envia uma cópia do mesmo envelope. O recibo precisa
   ter assinatura da testemunha fixada e corresponder exatamente ao pedido.
5. O ACK é gravado em transação local. Perda de resposta ou morte antes desse
   commit mantém o pedido pendente; sua repetição é idempotente no A5.
6. Após ACK, o A6 pode consultar a testemunha com desafio novo e comparar o
   estado do projeto. As sete travas operacionais continuam False em todo resultado.

Configuração da fila: DELETE/FULL; `BEGIN IMMEDIATE` serializa preparações e
envios de uma mesma fila. Durante o envio e commit local do ACK, uma transação
de leitura mantém o snapshot da fonte aberto. Em DELETE, isso impede o commit
de um escritor SQLite ordinário nessa janela. Não é fencing contra substituição
hostil de arquivos, nem transação distribuída entre bancos.

## Validação

`VALIDACAO_A7_OUTBOX.txt`: 24/24 testes aprovados em 29,195 segundos.
`VALIDACAO_A7_PYTHON_O.txt`: 24/24 aprovados em 41,978 segundos, suíte iniciada com Python -O.
Os subprocessos de crash são iniciados explicitamente com `-B`; não herdam
automaticamente a otimização do processo de testes.
`REGRESSAO_A5_A6_PARA_A7.txt`: regressão conjunta A5/A6, 50/50 testes
aprovados em 156,167 segundos. Os 61 hashes da entrega A6 também foram
reconferidos, sem alterações.

Os testes cobrem:

- Fluxo fonte → prepare → A5 → ACK local → consulta A6.
- Duas gerações, reabertura e preservação exata de nonce/envelope.
- Timeout de transporte depois de commit da testemunha e recuperação do mesmo recibo.
- Morte real de subprocesso antes e depois do commit da preparação, depois
  do ACK da testemunha e depois do commit do ACK local.
- Indisponibilidade, recibo inválido, tentativa do transporte de alterar o
  pedido, fila adulterada, identidade divergente e falha de escrita da fila.
- Recusa de lacuna, rollback e avanço da fonte enquanto há pedido pendente.
- Exclusão de commits ordinários da fonte durante o envio.
- Bootstrap de fonte já avançada recusado, sem criar banco de fila.
- Com fixture de histórico sintético válido, o armazenamento real aceita
  4095 → 4096 e recusa a 4097ª entrada com HISTORY_CAPACITY_EXHAUSTED,
  preservando os bytes do banco. Um estado já inválido com 4097 entradas é
  rejeitado pelo leitor e pela fila.

Os snapshots positivos de gerações 0, 1 e 2 são produzidos uma vez pelas
funções de consumo do projeto, usando a fixture A6, e clonados para cada teste.
Somente os testes adversariais/de fronteira alteram payloads diretamente.
Chaves fixas no código de testes são fixtures públicas, nunca credenciais reais.

## Uso

Extraia o pacote mantendo `a6_vendor` e os scripts/testes juntos. Requer Python
e `cryptography`. No ambiente existente:

```powershell
& 'C:\COPILOTO_PRICE_ACTION_AI\ambiente\Scripts\python.exe' -B '.\test_f3_int121_a7_outbox.py' -v
& 'C:\COPILOTO_PRICE_ACTION_AI\ambiente\Scripts\python.exe' -B -O '.\test_f3_int121_a7_outbox.py' -v
```

A API recebe caminhos da fila e da fonte, store_id, escopo, chave privada do
cliente e chave pública fixada da testemunha. `create=True` só inicializa uma
fila nova para fonte na geração zero. Na retomada, omita `create`.
Use `prepare()` após o commit da fonte e `dispatch(witness.submit)` para envio
local de teste. Consulte o A6 após o ACK. Nenhum resultado autoriza operação real.

## Limites e próxima etapa

- O commit da fonte e a preparação da fila ainda são transações separadas.
  Morte nesse intervalo permite retomar somente se a fonte ainda estiver na
  geração imediatamente seguinte. Se avançar mais, a fila recusa a lacuna.
- O escritor do projeto não foi modificado para consultar a fila; ele ainda
  pode avançar durante indisponibilidade. Cabe ao chamador serializar e bloquear
  novos consumos enquanto o atestado estiver pendente. A7 detecta a divergência;
  não instala essa coordenação no runtime principal.
- Não há migração automática para fontes já avançadas, reconstrução de histórico
  ausente nem criação de recibos retroativos.
- O callback de transporte deve implementar seu próprio timeout. A7 não impõe
  prazo a um callback bloqueado e mantém os locks até ele retornar ou falhar.
- Fila, fonte e testemunha permanecem locais. Rollback conjunto válido pode
  continuar não detectado. Identidade em custódia independente, referência
  monotônica externa e transporte autenticado continuam pendentes.
- Sem prova de resistência a perda física de energia ou falha real de fsync;
  morte de processo e falhas controladas não equivalem a essas condições.
- Não foi executada a regressão integral de todas as etapas do projeto.

Próxima etapa técnica: incorporar o envelope pendente à mesma transação do
consumo, em uma variante isolada do escritor, e bloquear novas gerações antes
do ACK. Isso elimina a janela fonte → fila dentro desse escritor cooperante;
não resolve custódia externa ou rollback conjunto.

F3: OPEN. OPERACOES REAIS: BLOQUEADAS. PROMOCAO A FINAL: BLOQUEADA.
