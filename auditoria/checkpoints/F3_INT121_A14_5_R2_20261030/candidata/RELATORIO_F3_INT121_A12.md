# F3-INT-121 A12 — morte do supervisor nas fronteiras de consumo e ACK

Data: 29/10/2026. Classificação: NATIVE_OWNER_DEATH_TRANSACTION_BOUNDARIES_LOCAL_EXPERIMENT.

## Escopo e implementação

A12 testa a contenção A11 em conjunto com o consumo/atestado A8–A10. O dono
efetivo do Job interno é encerrado em oito pontos controlados. Um observador
fora desse Job mantém handles dos processos e verifica sua saída antes de
permitir a limpeza do Job de segurança externo.

`f3_int121_a12_boundaries.py` é um adaptador de experimento offline, não uma
rota instalada no runtime. Ele reutiliza o gate, Job e identidade congelados
em `a11_native`, o wire tipado A11 e o chamador A10. Os patches de `_worker`,
`OfflineConsumptionRoute._open` e `SQLiteWitness.__init__` existem apenas na
memória dos processos de teste para instalar as pausas nos pontos `_fault`
já existentes. Nenhum fonte A5–A11 ou supervisor histórico é editado.

Os pins before/after e o digest da cadeia são calculados e retidos antes de
qualquer mutação/falha, nas fixtures conhecidas. O marcador capturado dentro da
transação é evidência do ponto alcançado, não uma nova âncora de confiança.

## Fronteiras e resultados esperados/observados na execução normal

| Ponto da morte do dono | Estado após abertura validada | Testemunha antes da retomada | Após retomada explícita |
|---|---|---:|---:|
| Após UPDATE da fonte | Não consumido | 0 | 0; somente consulta |
| Após INSERT do pedido pendente | Não consumido | 0 | 0; somente consulta |
| Antes do commit de consumo | Não consumido | 0 | 0; somente consulta |
| Após commit de consumo | Consumido, pendente | 0 | 1 |
| Antes do commit da testemunha | Consumido, pendente | 0 | 1 |
| Após commit da testemunha | Consumido, pendente | 1 | 1 |
| Antes do commit do ACK local | Consumido, pendente | 1 | 1 |
| Após commit do ACK local | Consumido com ACK | 1 | 1; já confirmado |

As mortes anteriores ao commit não levam a um novo consumo automático.
Quando há pendência confirmada, a retomada normal A11 → A10 → A9 reenvia o
envelope persistido; o fingerprint é conferido contra o pedido anterior.
Quando o ACK local já está confirmado, a retomada informa isso sem avançar a
testemunha. Pins after divergentes produzem resultado não resolvido sem escrita.

Há um controle positivo adicional: a pausa antes do commit é liberada com o
supervisor vivo. A operação então confirma o consumo normalmente, demonstrando
que alcançar a pausa não desfaz o trabalho por si só. O décimo teste verifica
que pins de recuperação inválidos não inicializam um banco ausente.

## Como o experimento evita uma confirmação falsa de limpeza

1. O worker publica o ponto alcançado e sua otimização real; o controlador
   publica o PID do processo Python dono do Job e o gate associado.
2. O observador abre handles do dono, gate, ponte e worker e confere sua
   associação ao Job externo de segurança.
3. O handle usado para encerrar o dono tem PID e tempo de criação comparados
   com a identidade já retida. Não é usado um kill posterior baseado só em PID.
4. O observador aguarda o sinal de saída dos quatro handles e confirma a saída
   de todos os processos acompanhados pelo JobTracker, incluindo redirecionadores
   do ambiente virtual. A contagem de processos ativos deve ser zero.
5. Somente depois é iniciado o encerramento do Job de segurança externo.

As evidências registram os tempos dessas observações. O empacotamento verifica
que os sinais precedem a limpeza de segurança, de modo que essa limpeza não
possa ser confundida com o efeito do Job interno que se está avaliando.

O observador é outro processo/contexto de teste na mesma máquina, não uma
entidade de auditoria independente. As chaves usadas são fixtures públicas.

## Abertura explícita após a morte

`recover_for_inquiry()` abre a fonte pelo A9/A8, confere fonte/ledger e compara
o digest observado com os pins previamente retidos. Não executa consumo nem
envio de ACK. Essa abertura permite que o próprio SQLite faça a recuperação
normal que for necessária antes da consulta; ela não é uma inspeção forense
puramente de leitura.

Antes dessa abertura, o teste registra tamanho e hash da fonte, testemunha e
eventuais arquivos `-journal`, mantendo-os no lugar. Não remove, troca ou renomeia
journals. A existência de um journal por si só não comprova que ele estava hot
ou que houve escrita parcial de páginas no arquivo principal.

O SQLite pode precisar realizar rollback de um hot journal antes de ler a base.
Por isso, uma consulta somente de leitura não deve ser tratada como um reparador
universal de crash. [SQLite: File Locking and Concurrency](https://www.sqlite.org/lockingv3.html)

O banco e seus journals devem permanecer corretamente associados para que a
recuperação automática possa funcionar. [SQLite: How To Corrupt a Database File](https://www.sqlite.org/howtocorrupt.html)

## Evidências e validação

- `VALIDACAO_A12_BOUNDARIES.txt`: 10/10 testes, 85,070 segundos.
- `VALIDACAO_A12_PYTHON_O.txt`: 10/10 com `-O`, 113,854 segundos.
- `REGRESSAO_A11_PARA_A12.txt`: 11/11 testes Windows A11, 53,729 segundos.
- `EVIDENCIAS_A12_NORMAL.json` e `EVIDENCIAS_A12_PYTHON_O.json`: nove registros
  por modo, correspondentes às oito mortes e ao controle com liberação.
- `RESULTADOS_A12.json`: contagens, tempos e integridade conferida.

Cada registro inclui a fase alcançada, pins retidos, geração transitória vista
na transação, fingerprint do pedido quando já existe, provas dos handles,
arquivos presentes antes da abertura e resultados da reconciliação/retomada.
O teste de pins inválidos não cria processos e não precisa de registro de árvore.

Requer Windows real, Python e `cryptography`. Extraia mantendo todos os módulos,
fixtures, `a6_vendor` e `a11_native` juntos:

```powershell
& 'C:\COPILOTO_PRICE_ACTION_AI\ambiente\Scripts\python.exe' -B '.\test_f3_int121_a12_boundaries.py' -v
& 'C:\COPILOTO_PRICE_ACTION_AI\ambiente\Scripts\python.exe' -B -O '.\test_f3_int121_a12_boundaries.py' -v
```

Os intermediários são gravados em `../work/`. Os índices de evidências apontam
para uma pasta própria de cada execução; o pacote de entrega consolida apenas
os registros das execuções finais validadas. O worker medido e a ponte precisam
reportar a otimização esperada no modo `-O`.

## Limites e próximo passo

- Os pontos são pausas antes/depois de chamadas conhecidas. Não foi induzida
  morte em todas as instruções internas de `sqlite3.commit`, no fsync real,
  controlador de disco ou perda física de energia.
- As fixtures são pequenas; não foi comprovado spill de cache, journal hot em
  todos os casos ou resistência a falta de espaço física. Os metadados de journal
  são evidência observada, sem inferência de durabilidade de hardware.
- O experimento não avalia atacante hostil removendo associação, escapando do
  Job ou duplicando seu handle. Tampouco comprova prazo estrito de startup/limpeza.
- O backup anterior e todos os fontes/checkpoints A5–A11 permanecem preservados.
  Não há instalação no runtime, migração de histórico ou regressão integral das
  demais etapas do projeto.
- Custódia independente, referência monotônica externa, serviço remoto
  autenticado e proteção contra rollback conjunto continuam pendentes.
- As sete flags operacionais e `safe_to_promote()` permanecem False, inclusive
  após recuperação e correspondência de pins locais.

Próximo passo técnico: contraprovas isoladas que retirem o efeito
KILL_ON_JOB_CLOSE, mantendo o Job externo de segurança, para verificar que as
provas de A11/A12 detectam a perda de contenção e não apenas o término incidental
de processos. Preservar os pacotes anteriores sem promoção automática.

F3: OPEN. OPERACOES REAIS: BLOQUEADAS. PROMOCAO A FINAL: BLOQUEADA.
