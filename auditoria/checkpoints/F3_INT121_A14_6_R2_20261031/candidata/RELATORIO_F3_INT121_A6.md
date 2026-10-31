# F3-INT-121 A6 — consulta assinada e adaptador SQLite de leitura

Data: 28/10/2026. Classificação: FRESH_QUERY_SQLITE_ADAPTER_LOCAL_PROTOTYPE.

## Resultado e escopo

O A6 compara o estado SQLite de consumo do projeto com o último recibo do A5,
obtido em uma resposta assinada que inclui um desafio novo do verificador.
É uma integração experimental de leitura, validada com consumo real de
fixtures sintéticas pelas funções originais do projeto. Não é uma integração
de escrita no runtime principal nem uma testemunha externa implantada.

`f3_int121_a6_adapter.py` contém:

- `LocalChallengeResponder`: lê cadeia, head e recibo do A5 na mesma transação
  de leitura e assina a resposta com a identidade já fixada do A5.
- `FreshQuery`: gera um desafio aleatório de 256 bits, aceita uma única
  tentativa de verificação e aplica prazo de 5 segundos pelo relógio monotônico
  local. Uma nova consulta invalida a anterior; reiniciar o cliente descarta
  consultas pendentes. Não há fallback para recibo em cache.
- Leitura SQLite com `mode=ro`, `query_only=ON` e `trusted_schema=OFF`.
  Exige o modo DELETE usado pelo armazenamento examinado.
- Comparação de store_id, identidade da testemunha, escopo do projeto,
  geração, digest do estado, head e assinatura do recibo. Campos e tipos são
  verificados antes da comparação.
- Todas as sete travas de `AdapterResult` permanecem False, inclusive em
  `SQLITE_WITNESS_FRESH_LOCAL_MATCH`. `safe_to_promote` sempre retorna False.

## Base do projeto identificada

Foram lidos, sem alteração:

- `C:\COPILOTO_PRICE_ACTION_AI\f3_int117_corrigida\audit\tools\f3_int120_sqlite_witness_adapter.py`
- `C:\COPILOTO_PRICE_ACTION_AI\f3_int117_corrigida\audit\tools\f3_int109_offline_consumption_store.py`
- Protocolo T2 e encerramento U23 da F3-INT-120 nessa mesma árvore.

O adaptador da F3-INT-120 usa recibos e serialização diferentes do A4/A5.
O A6 mantém o protocolo A4/A5 e reutiliza `_load` e `_digest` do armazenamento
encontrado, evitando uma segunda interpretação do estado do projeto.

Foram congelados 48 módulos de helpers em `a6_vendor/tools/`. A única adaptação
semântica de empacotamento foi trocar o namespace dos imports de `tools` para
`a6_vendor.tools`; também houve normalização para UTF-8/LF. Os hashes de origem
e de entrega estão em `VENDOR_A6_MANIFEST.json`.

`A6_TEST_FIXTURE.json` contém um segmento sintético gerado pelo helper de testes
original. `A6_FIXTURE_PROVENANCE.json` registra os hashes dos módulos originais
carregados nessa geração. Os testes A6 usam `create_store`, `build_typed_chain`
e `consume_chain` dos helpers congelados para produzir gerações reais de teste.
Não há alteração manual do payload nos cenários positivos.

## Validação

- A6: 24/24 testes de integração e de rejeição aprovados, em 122,589 segundos; evidência em
  `VALIDACAO_A6_ADAPTER.txt`.
- Regressão A5: 26/26 testes aprovados; evidência em `REGRESSAO_A5_PARA_A6.txt`.
- Conferidos os hashes dos 48 helpers de origem e das cópias entregues.
  Os seis hashes da entrega A5 anterior permaneceram inalterados.
- Consumo de duas gerações e reabertura da testemunha.
- Resposta repetida, resposta de consulta anterior, consulta expirada ou
  descartada em reinício são rejeitadas.
- Recibo adulterado, assinatura incorreta, chave/store_id/escopo incorretos,
  banco ausente, ocupado, inválido ou em WAL não produzem correspondência.
- Commit do projeto ainda não atestado é rejeitado até reconciliação explícita.
- Rollback só do projeto ou só da testemunha gera divergência de geração.
- Teste positivo verifica que a leitura do adaptador não altera bytes do banco.
- O teste de rollback conjunto demonstra a limitação remanescente, sem
  classificá-la como proteção já obtida.

## Executar e interpretar

Extraia o pacote mantendo a pasta `a6_vendor` junto aos scripts. Requer Python
e `cryptography`. No ambiente existente do projeto:

```powershell
& 'C:\COPILOTO_PRICE_ACTION_AI\ambiente\Scripts\python.exe' -B '.\test_f3_int121_a6_adapter.py' -v
& 'C:\COPILOTO_PRICE_ACTION_AI\ambiente\Scripts\python.exe' -B '.\test_f3_int121_a5_sqlite.py' -v
```

As chaves determinísticas nos testes são fixtures públicas, somente para testes.
Os temporários ficam em `../work/`, fora dos entregáveis.

Fluxo da API: instanciar `FreshQuery` com chave pública fixada, store_id e escopo;
chamar `issue()`; obter resposta de `LocalChallengeResponder.answer(desafio)`;
chamar `check(caminho_do_banco_do_projeto, resposta)`. Uma indisponibilidade
da testemunha deve encerrar a consulta sem aceitação. A API de transporte
remoto, suas credenciais e autenticação de conexão não foram implementadas.

## Limites e próxima etapa

1. A chave, a testemunha e os bancos continuam locais. Não existe comprovação
   de custódia independente nem checkpoint monotônico externo. Rollback conjunto
   para um estado antigo válido pode receber uma assinatura nova e passar.
2. A correspondência vale para os snapshots observados. Não há transação
   distribuída entre commit do projeto, commit A5 e consulta; não é autorização
   para uso posterior do estado nem garantia de ausência de corrida no runtime.
3. O A5 exige sequência e geração consecutivas desde 1. Não há bootstrap
   automático para um banco já avançado, migração ou preenchimento de lacunas.
4. A instância de consulta é destinada ao uso sequencial por um chamador.
   A integração concorrente no runtime exige coordenação explícita.
5. Os helpers congelados pertencem à árvore examinada. Seu `_load` ainda
   contém limite de 4096 entradas; esta etapa não substitui nem reverte a
   correção F3-INT-118 existente em outras entregas. É necessário selecionar
   e reconciliar a base oficial antes de aplicar o adaptador ao runtime.
6. Não foram induzidos desligamento físico, falha de disco ou fsync real,
   nem executada a regressão completa do projeto.

Próxima etapa: reconciliar a base de armazenamento com a candidata F3-INT-118,
definir bootstrap/atestado no fluxo de commit e o contrato de custódia e
checkpoint externo. Implantação externa requer destino e identidade definidos.

O relatório U23 consultado aponta F3-INT-117 R2 FINAL; o ULTIMO_MARCO.json da
raiz consultada ainda declara F3-INT-116. Essa divergência foi preservada e
precisa ser reconciliada antes de qualquer promoção.

F3: OPEN. OPERACOES REAIS: BLOQUEADAS. PROMOCAO A FINAL: BLOQUEADA.
