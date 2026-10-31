# F3-INT-121 A9 — rota offline explícita e cópia de base vazia

Data: 28/10/2026. Classificação: OFFLINE_EXPLICIT_ROUTE_AND_EMPTY_BOOTSTRAP_PROTOTYPE.

## Entrega

`f3_int121_a9_route.py` acrescenta uma rota experimental única para o A8.
`OfflineConsumptionRoute` abre o escritor atômico em cada operação, fecha a
conexão ao terminar e nunca usa `legacy.consume_chain` como fallback.
Inicialização é uma operação separada e explícita; abrir um arquivo ausente,
legado, corrompido ou com identidade divergente não provoca reset ou upgrade.

`RouteConfig` fixa store_id, escopo, chave pública do cliente e chave pública da
testemunha. A chave privada fornecida para escrita precisa corresponder à
identidade do cliente. Nenhuma chave é gerada ou salva pela rota.

Também foram implementadas observação e reconciliação **somente de leitura**,
usando chaves públicas e SQLite `mode=ro`, `query_only=ON`, `trusted_schema=OFF`.
Essas funções validam fonte e ledger A8 no mesmo snapshot, com a mesma regra
de assinaturas do A7/A8. Não exigem a chave privada para consultar evidências.

## Contrato de resultados

| Operação | Comportamento |
|---|---|
| `create_new()` | Inicializa explicitamente um novo A8; retorna `INITIALIZED_LOCAL` e digest para retenção pelo chamador. |
| `consume_chain()` | Usa somente A8; o commit local retorna `CONSUMED_PENDING_ATTESTATION_LOCAL`, sem autorização operacional. |
| `dispatch()` | Reenvia o pedido persistido; só recibo válido pode registrar ACK e liberar a próxima geração local. |
| `observe()` | Compara o snapshot com uma âncora fornecida; não substitui âncora divergente pela observada. |
| `reconcile()` | Classifica antes/depois com pins independentes: não consumido, consumido pendente, consumido com ACK ou não resolvido. |
| `copy_empty_legacy()` | Copia somente fonte legada vazia e conferida para um destino A8 novo. Não faz cutover. |

Os status históricos não são um contrato de substituição transparente.
`CONSUMED_FIXTURE_UNAUTHENTICATED` do legado não é devolvido pela rota nova.
Os chamadores precisam tratar pendência, resultado incerto e falha fechada
explicitamente, sem continuar por outro escritor.

## Bootstrap e migração

A cópia explícita exige:

1. Fonte SQLite DELETE, somente com a tabela legada `state`, sem objetos extras.
2. Escopo esperado e digest iguais ao pin fornecido pelo chamador.
3. Geração zero, histórico vazio e revisão inicial válida.
4. Caminho de destino diferente e ainda inexistente.

A fonte permanece em transação de leitura durante a inicialização do destino.
Seu payload não é alterado; a revisão inicial e o digest são preservados na
nova base A8. O original continua existindo e **não é aposentado automaticamente**.
O corte de todos os escritores antigos exige um procedimento separado.

Bases com histórico retornam `MIGRATION_HISTORY_REQUIRES_SEPARATE_PROCEDURE`.
Não são criados recibos retroativos nem inferida uma cadeia de atestados ausente.
Bases já A8, schemas desconhecidos e destinos existentes não são migrados.

## Auditoria local do A8 e revisão do A9

Os testes adicionais desafiaram o contrato A8 com triggers que ignoram UPDATE
da fonte, INSERT do pedido ou UPDATE do ACK. A verificação de coerência recusou
esses resultados; não houve falsa confirmação nem liberação da geração seguinte.
Uma interrupção injetada após commit foi devolvida como resultado incerto e
depois classificada como consumo pendente pelos pins de reconciliação.
Nenhum fonte A8 foi modificado.

Na revisão do A9, uma contraprova encontrou um erro no filtro de schema: o
padrão SQL `LIKE 'sqlite_%'` tratava `_` como curinga e ocultava a tabela de
usuário `sqlitex_extra`, permitindo indevidamente a cópia daquela base.
Foi alterado para `GLOB 'sqlite_*'`, que mantém o sublinhado literal.
O novo teste reproduziu a falha antes da correção e integra as suítes finais.
As execuções de desenvolvimento com 22 testes não representam a versão final.

Isso constitui auditoria local de propriedades específicas, não revisão
independente, certificação ou aceitação de todos os critérios externos.

## Mapeamento do projeto

`INVENTARIO_ROTAS_A9.json` registra 513 arquivos examinados, nove arquivos com
referências e nenhuma falha de leitura/parse. Foram examinados apenas:

- `C:\COPILOTO_PRICE_ACTION_AI\app` — 21 arquivos.
- `C:\COPILOTO_PRICE_ACTION_AI\core` — 34.
- `C:\COPILOTO_PRICE_ACTION_AI\execution` — 3.
- `C:\COPILOTO_PRICE_ACTION_AI\tools` — 247.
- `C:\COPILOTO_PRICE_ACTION_AI\audit\tools` — 101.
- `C:\COPILOTO_PRICE_ACTION_AI\f3_int117_corrigida\audit\tools` — 107.

As referências encontradas estão nas árvores de auditoria. Nos quatro primeiros
diretórios não foram encontrados imports/referências textuais ao F3-INT-109 ou
chamadas diretas `consume_chain`. Essa é uma conclusão limitada a esses arquivos;
não prova ausência de chamadas dinâmicas, plugins, testes ou outras árvores.

| Componente examinado | Tratamento de integração |
|---|---|
| F3-INT-109 | Novo chamador cooperante deve usar a rota A9 e os status A8. Fonte histórico é preservado. |
| F3-INT-110 | Nova consulta de resultado usa `reconcile()` com pins anteriores à consulta e coerência do ledger. |
| F3-INT-115 | Importa tipo de resultado; integração multiprocesso precisa tratar os novos status explicitamente. |
| F3-INT-116 | A sonda faz patch no `_connect` legado. Isso não injeta falhas no A8; é necessária sonda própria. |
| F3-INT-117 | Sondas e replays legados são históricos; não devem ser apresentados como consumidores A8 migrados. |
| F3-INT-120 | O adaptador antigo usa outro recibo. Consulta do protocolo A5 continua sendo feita pelo A6. |

## Validação e execução

Suíte final: `test_f3_int121_a9_route.py`, 23 testes, em modo normal e `-O`.
Evidências: `VALIDACAO_A9_ROUTE.txt`, `VALIDACAO_A9_PYTHON_O.txt` e
`REGRESSAO_A8_PARA_A9.txt`. Contagens, tempos e hashes anteriores conferidos
constam de `RESULTADOS_A9.json`.

- Normal A9: **23/23 aprovados**, 46,992 segundos.
- A9 com `-O`: **23/23 aprovados**, 47,559 segundos.
- Regressão A8: **26/26 aprovados**, 130,721 segundos.
- **77 hashes** da entrega anterior A8 conferidos sem alterações.
- `CONTRAPROVA_SCHEMA_A9_ANTES.txt` conserva a falha esperada observada antes
  da correção do filtro. Não é uma falha das suítes finais.

Além da auditoria de triggers, há cobertura de fluxo em duas gerações, ACK
perdido, observação sem escrita, pins inválidos, falta/corrupção de banco sem
fallback, identidade errada e todos os caminhos de cópia aceitos/recusados.
Os pins de depois usados na consulta de resultado são calculados antes do
consumo, a partir da fixture conhecida, não do banco observado após a falha.

Requer Python e `cryptography`. Extraia mantendo os módulos e `a6_vendor` juntos:

```powershell
& 'C:\COPILOTO_PRICE_ACTION_AI\ambiente\Scripts\python.exe' -B '.\test_f3_int121_a9_route.py' -v
& 'C:\COPILOTO_PRICE_ACTION_AI\ambiente\Scripts\python.exe' -B -O '.\test_f3_int121_a9_route.py' -v
```

## Limites e próxima etapa

- A9 não foi instalado como rota do runtime principal. Nenhum consumidor
  histórico, marco oficial ou configuração operacional foi alterado.
- A cópia vazia não encerra escritores antigos nem muda referências de caminho.
  Usar fonte antiga e destino simultaneamente cria bases distintas; a ativação
  precisa escolher um dono e aposentar a rota antiga explicitamente.
- Não há migração de histórico avançado, custódia independente, checkpoint
  monotônico externo, transporte remoto configurado ou prova de perda de energia.
- `observe()` e `reconcile()` não provam frescor externo. Os pins devem ser
  retidos independentemente antes da consulta; rollback conjunto continua possível.
- `dispatch()` mantém o callback síncrono herdado e seu requisito de timeout
  externo. Não existe garantia de prazo estrito nem fencing contra SQL direto.
- Todas as sete travas e `safe_to_promote()` permanecem False em toda resposta.
  Não foi repetida a regressão integral de todas as etapas históricas.

Próxima etapa: preparar um chamador offline multiprocesso que utilize apenas
a rota A9, com contrato de retomada e encerramento, para validar uma integração
concreta antes de qualquer instalação no runtime ou migração com histórico.

F3: OPEN. OPERACOES REAIS: BLOQUEADAS. PROMOCAO A FINAL: BLOQUEADA.
