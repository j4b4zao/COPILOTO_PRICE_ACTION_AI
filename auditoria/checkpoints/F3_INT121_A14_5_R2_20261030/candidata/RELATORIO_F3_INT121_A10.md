# F3-INT-121 A10 — chamador offline multiprocesso e retomada explícita

Data de conclusão: 29/10/2026. Classificação: OFFLINE_SPAWN_WORKER_RECOVERY_PROTOTYPE.

## Ponto de retomada

A implementação iniciada em 28/10 ficou salva com 19 testes normais aprovados,
sem pacote final. Esta conclusão acrescenta tratamento de falhas de alocação,
falha antes do início e falha depois do lançamento efetivo do worker. A suíte
final contém 23 testes. O resultado histórico de 19 testes não substitui a
validação da versão final.

## Implementação

`f3_int121_a10_worker.py` fornece `WorkRequest` e `run_worker`. Cada chamada
cria um processo Python pelo contexto `spawn`, com uma das operações fechadas:

| Operação | Efeito |
|---|---|
| `consume` | Chama somente `OfflineConsumptionRoute.consume_chain` do A9. Não confirma atestado automaticamente. |
| `inquire` | Consulta A9 com pins antes/depois e digest da cadeia; exige apenas configuração pública. |
| `resume` | Consulta o resultado e, somente se houver consumo pendente correspondente, tenta registrar o ACK do mesmo pedido. Nunca chama consumo novamente. |

O chamador não inicializa bancos, não migra bases, não seleciona executáveis
arbitrários e não usa shell. Banco principal e testemunha precisam existir.
Não há fallback para o escritor legado nem retry automático de consumo.

Para a fronteira local de teste, `resume` usa a testemunha SQLite A5, aberta
com identidade fixada. Isso não é um transporte externo implantado.

## Resultado do processo versus resultado da operação

`WorkerResult.status == WORKER_RETURNED` significa que o supervisor recebeu um
resumo válido de um processo encerrado com exit code zero. O resultado técnico
do consumo/consulta/ACK está em `operation_status`, que pode indicar recusa,
pendência ou falha. Encerrar normalmente não equivale a consumir com sucesso.

Timeout, término abrupto ou resposta inválida produzem `WORKER_OUTCOME_UNKNOWN`.
O chamador deve fazer outra consulta explícita com os pins previamente retidos;
o supervisor não presume que a transação falhou nem repete o consumo.

A resposta entre processos é um resumo JSON de até 4096 bytes. Contém job_id,
operação, status, digests e geração quando disponíveis. Não carrega o envelope
completo, payload da cadeia, texto de exceções ou material de chave privada.
O supervisor verifica schema, identidade do job, tipos, digests, geração e
sete flags estritamente False antes de aceitar o resumo. `job_id` é apenas
correlação local da resposta; não é uma credencial nem uma fila persistente de jobs.

## Retomada sem atingir outro pedido

`resume_pending` primeiro reconcilia o estado contra os pins antes/depois.
Se o consumo não foi observado, retorna a observação sem consumir. Se já foi
atestado, retorna `ALREADY_ACKNOWLEDGED_LOCAL` sem avançar a testemunha.

Para uma pendência, observa o envelope associado ao after-state esperado e
retém seu fingerprint. O callback executado dentro do lock A8 confere novamente
o fingerprint do envelope efetivamente enviado. Se outro pedido tiver ocupado
essa posição entre consulta e envio, retorna `RESUME_TARGET_CHANGED` e não o
encaminha à testemunha. A troca de alvo é testada com um callback adversarial;
os fluxos de concorrência entre workers também usam processos reais.

## Encerramento e falhas de início

O supervisor acompanha somente o processo que criou. Ao expirar a espera,
solicita término, aguarda até 1 segundo e, se necessário, solicita kill e
aguarda mais 1 segundo. Depois registra PID, exit code, `process_stopped`,
`process_reaped` e `cleanup_confirmed`. Se não confirmar o encerramento,
devolve `CLEANUP_INCONCLUSIVE` e descarta a resposta.

Canais são fechados mesmo se a construção do objeto Process falhar. Se
`start()` falhar após já ter criado um processo, o supervisor recupera a
identidade pelo handle e executa a mesma limpeza. Há testes separados para
alocação, falha antes do lançamento e falha depois de lançamento real. A recusa
de terminate/kill pelo SO foi simulada com um processo de teste falso: ela
produz limpeza inconclusiva, sem criar um processo real que não possa ser parado.
Quando nenhum filho chegou a ser criado, `cleanup_confirmed` apenas indica
que não há worker conhecido a recolher; `process_started` permanece False.

Não há Job Object ou contenção nativa de árvore nesta etapa. Morte abrupta do
próprio supervisor e descendentes criados por código adicional não são cobertos.

## Validação

Arquivos de evidência final:

- `VALIDACAO_A10_WORKER.txt` — 23 testes normais.
- `VALIDACAO_A10_PYTHON_O.txt` — mesma suíte iniciada com Python -O.
- `REGRESSAO_A9_PARA_A10.txt` — 23 testes da rota A9.
- `RESULTADOS_A10.json` — contagens, tempos e integridade conferida.

Resultados finais: **23/23 normais** em 91,244 segundos; **23/23 com -O**
em 164,871 segundos; **23/23 da regressão A9** em 96,655 segundos.
Os **88 hashes** da entrega anterior A9 foram conferidos sem alterações.

Os testes cobrem consumo, consulta e retomada em processos diferentes; morte
do worker após commit do consumo; morte após commit da testemunha; ACK perdido;
timeout com recolhimento do worker; resposta inválida; chamadas concorrentes;
pendência impedindo a próxima geração; banco ausente sem recriação; validação
das identidades e ausência de liberação operacional em qualquer resultado.

Uma chamada de retomada pode ser recusada por contenção concorrente. O chamador
recebe a recusa e precisa solicitar outra consulta/retomada explicitamente.
Não há loop automático que ignore erros até encontrar sucesso.

Todos os dados de teste são fixtures sintéticas herdadas das etapas anteriores.
As chaves determinísticas nos testes são públicas e exclusivas dessas fixtures.
Nenhuma chave operacional do projeto foi usada ou salva.

## Executar e integrar como teste

Requer Python, `cryptography` e os módulos/fixtures do pacote. O script que
chama `run_worker` deve usar a proteção usual de entrada para `spawn`:

```python
if __name__ == '__main__':
    multiprocessing.freeze_support()
    # run_worker(...): fornecer configuração, pedido e capacidades necessárias.
```

`consume` recebe os argumentos completos de cadeia A9 no dicionário do pedido.
`inquire` e `resume` recebem `before_state_digest`, `after_state_digest` e
`expected_chain_digest`, retidos antes da consulta. Para escrever, a chave
privada do cliente precisa corresponder à configuração pública. `resume`
também exige banco e chave da testemunha local de teste.

```powershell
& 'C:\COPILOTO_PRICE_ACTION_AI\ambiente\Scripts\python.exe' -B '.\test_f3_int121_a10_worker.py' -v
& 'C:\COPILOTO_PRICE_ACTION_AI\ambiente\Scripts\python.exe' -B -O '.\test_f3_int121_a10_worker.py' -v
```

## Limites e próxima etapa

1. Esta é uma integração offline isolada. Runtime principal, consumidores
   históricos e marcos oficiais permanecem sem alteração.
2. Chaves privadas são passadas em memória ao worker via IPC local de spawn.
   Isso não constitui custódia independente, isolamento seguro de chave ou
   garantia de apagamento da memória.
3. A validação do resumo IPC não autentica origem externa. Os processos e o
   código local continuam no mesmo domínio de confiança.
4. Há orçamento de espera e limpeza, mas início de processo e escalonamento
   do sistema operacional não possuem prazo estrito comprovado.
5. A limpeza cobre o worker diretamente supervisionado nos caminhos testados;
   não toda a máquina, uma árvore arbitrária ou morte abrupta do pai.
6. Rollback conjunto válido, referência monotônica externa, transporte remoto
   autenticado e durabilidade após perda física de energia continuam pendentes.
7. Não houve migração de bases avançadas nem regressão integral de todas as
   etapas históricas. As sete flags e `safe_to_promote` permanecem False.

Próximo passo técnico: avaliar contenção nativa do worker e sua árvore no Windows,
incluindo falha/morte do supervisor, reaproveitando o contrato dos supervisores
históricos sem alterar as evidências ou os FINAL anteriores.

F3: OPEN. OPERACOES REAIS: BLOQUEADAS. PROMOCAO A FINAL: BLOQUEADA.
