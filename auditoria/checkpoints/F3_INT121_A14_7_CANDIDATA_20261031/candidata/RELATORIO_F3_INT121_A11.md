# F3-INT-121 A11 — contenção Windows e morte do supervisor

Data: 29/10/2026. Classificação: WINDOWS_JOB_CONTAINMENT_LOCAL_PROTOTYPE.

## Resultado e escopo

`f3_int121_a11_native.py` acrescenta uma fronteira Windows Job Object em torno
do chamador A10, que continua utilizando a rota A9. Não altera o runtime
principal, os módulos A5–A10 nem qualquer marco FINAL.

O supervisor histórico F3-INT-115 já associa um processo de gate a um Job com
KILL_ON_JOB_CLOSE antes de liberar o código de trabalho. A11 reutiliza uma
cópia isolada desse supervisor e do módulo de identidade, em `a11_native/`.
O manifesto `VENDOR_A11_MANIFEST.json` registra hashes de origem e de entrega.

Adaptações das cópias históricas: namespace `tools` → `a11_native.tools`,
normalização UTF-8/LF e explicitação de `close_fds=True` e `CREATE_NO_WINDOW`
na criação do gate. Nenhum arquivo histórico foi editado na origem.

## Fluxo da camada nova

1. A11 valida configuração e pedido tipado local e prepara uma única mensagem.
2. O gate é iniciado, associado ao Job e liberado pelo supervisor histórico.
3. Um launcher fixo inicia a ponte Python atual, com otimização explícita e
   stdin/stdout/stderr redirecionados. Não há shell nem escolha de executável
   arbitrário pelo pedido.
4. A ponte reconstrói somente tipos permitidos e chama `run_worker` do A10.
5. Os workers e descendentes normais permanecem na árvore do Job.
6. O supervisor confere resposta, job_id, otimização da ponte e flags antes
   de aceitar o retorno. A limpeza exige zero processos ativos, ausência de
   threads de IO vivas e prova de saída para cada processo registrado.

A mensagem usa JSON tipado com whitelist de dataclasses conhecidas, tuplas,
listas, dicionários e bytes em base64. Não usa pickle nem import dinâmico de
classes determinadas pelo payload. Há limite de 2 MiB por frame e profundidade
máxima de 64. Esse é um canal stdin privado entre processos locais confiáveis,
não um endpoint remoto autenticado.

Chaves de teste passam em memória pelo canal local; não são colocadas em argv,
arquivos de tarefa ou logs. Isso não comprova custódia independente ou apagamento
seguro da memória. As chaves utilizadas nesta validação são fixtures públicas.

## Resultado nativo não é autorização de consumo

`CONTAINED_WORKER_RETURNED` indica resposta do A10 aceita dentro da camada
nativa. O resultado do processo A10 está em `worker_result.status`, e o da
operação em `worker_result.operation_status`. São três níveis diferentes.

`NATIVE_OUTCOME_UNKNOWN` não permite concluir que o consumo falhou. A consulta
e retomada por pins independentes continuam sendo as do A9/A10, sem repetir
consumo automaticamente.

Na falha de inicialização/associação em que o construtor histórico não devolve
seu objeto, A11 não tem prova estruturada de limpeza para publicar: retorna
`NATIVE_CLEANUP_NOT_CONFIRMED`. O teste de falha de associação captura o processo
criado e verifica sua saída e ausência de alteração da fonte, sem transformar
isso em uma confirmação genérica que a API não dispõe.

Todas as sete flags operacionais e `safe_to_promote()` continuam False,
inclusive quando a árvore foi encerrada com provas válidas.

## Provas de morte e encerramento

Os testes Windows executam processos reais e cobrem:

- Fluxo de consumo A10 → A9/A8, morte do worker após commit e retomada explícita.
- Confirmação do mesmo envelope pela testemunha A5, sem nova sequência indevida.
- Timeout com ponte e descendente vivos, seguido de encerramento da árvore.
- Saída normal da raiz deixando descendente vivo, encerrado na limpeza do Job.
- Morte do processo Python que efetivamente possui o Job interno. O observador
  retém handles do gate, ponte, descendente e dono; confere identidade e tempo
  de criação no handle de término; depois verifica os sinais de saída.
- Morte antes da associação/liberação: o gate vê EOF e termina sem executar
  o alvo. A fonte permanece inalterada.
- Falha de associação sem liberação do código de trabalho.
- Preservação explícita da otimização da ponte no modo normal e `-O`.
- Wire tipado recusando classes arbitrárias e preservação das travas.

O observador mantém um Job de segurança externo separado para recolher processos
se o teste falhar. Na prova de morte do dono interno, os handles precisam
sinalizar **antes** do encerramento desse Job de segurança. A prova não se
baseia em uma busca posterior por PID, que poderia observar identidade diferente.
O observador é externo ao Job interno, mas continua na mesma máquina e domínio
de confiança; isso não é auditoria organizacional independente.

## Diagnóstico preservado

A primeira integração bloqueou esperando resposta: stdin/stdout/stderr não
eram repassados explicitamente ao processo da ponte. As árvores foram encerradas,
mas cinco testes falharam e dois tiveram erro, em 11 executados. Foi corrigido
o redirecionamento dos três streams; o canal de entrada é fechado após seu
único frame. A suíte foi reexecutada integralmente.

`DESENVOLVIMENTO_A11_STDIO_ANTES.txt` preserva essa execução anterior como
diagnóstico de desenvolvimento; não é uma falha das suítes finais. A prova de
morte do dono também foi reforçada para atingir o processo Python real, sem
depender do papel de um redirecionador de ambiente virtual.

## Validação e execução

- `VALIDACAO_A11_NATIVE.txt`: **11/11 aprovados**, 54,062 segundos.
- `VALIDACAO_A11_PYTHON_O.txt`: **11/11 aprovados**, 64,699 segundos.
- `REGRESSAO_A10_PARA_A11.txt`: **23/23 aprovados**, 98,019 segundos.
- `SHA256_A11.json`: manifesto dos membros, sem autorreferência.

Não há substituto permissivo para Job Objects em outro sistema operacional.
Os testes requerem Windows real; fora dele, são ignorados e não podem ser
declarados aprovados. O empacotamento desta entrega exige os 11 testes aprovados
sem skips na execução registrada.

Extraia mantendo módulos, fixtures, `a6_vendor/` e `a11_native/` juntos:

```powershell
& 'C:\COPILOTO_PRICE_ACTION_AI\ambiente\Scripts\python.exe' -B '.\test_f3_int121_a11_native.py' -v
& 'C:\COPILOTO_PRICE_ACTION_AI\ambiente\Scripts\python.exe' -B -O '.\test_f3_int121_a11_native.py' -v
```

## Referências técnicas

O contrato documentado de Jobs prevê término dos processos associados quando
o último handle é fechado com KILL_ON_JOB_CLOSE e herança dos filhos conforme
as regras de associação/breakaway. As provas desta entrega são limitadas às
árvores cooperantes e condições efetivamente testadas. [Microsoft: Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)

O launcher explicita os streams e `close_fds=True`, conforme as regras de
herança de handles de subprocessos no Windows. [Python 3.13: subprocess](https://docs.python.org/3.13/library/subprocess.html)

## Limites e próxima etapa

1. A11 é uma candidata offline isolada. Não instala rota no projeto, migra
   histórico, promove checkpoint ou autoriza operações reais.
2. O bootstrap do gate executa código confiável antes da associação. A morte
   pré-associação é tratada por EOF nos caminhos testados; não equivale à criação
   atômica kernel do processo já associado nem a um prazo estrito de startup.
3. A contenção testada abrange descendentes normais da árvore. Não foi avaliada
   uma tentativa hostil de escapar, duplicar o handle do Job ou interferir no SO.
4. A morte do dono foi testada com uma árvore de controle. Não foram induzidas
   todas as posições possíveis de morte do supervisor durante o commit SQLite
   ou gravação do ACK. Isso é uma próxima etapa de integração de falhas.
5. Não há custódia independente, checkpoint monotônico externo, serviço remoto
   autenticado, proteção contra rollback conjunto ou prova de perda de energia.
6. Não houve regressão integral de todas as etapas históricas do projeto. O
   backup A10 anterior foi preservado e continua representando aquele marco.

Próximo passo: testar a morte do supervisor nativo em fronteiras controladas de
consumo e ACK, com observador externo e reconciliação por pins retidos antes
da falha. Preservar A10/A11 como evidências locais, sem promoção automática.

F3: OPEN. OPERACOES REAIS: BLOQUEADAS. PROMOCAO A FINAL: BLOQUEADA.
