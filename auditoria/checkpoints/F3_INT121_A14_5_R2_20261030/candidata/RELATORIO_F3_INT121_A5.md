# F3-INT-121 A5 — persistência SQLite local

Data: 28/10/2026. Classificação: LOCAL_SQLITE_PERSISTENCE_PROTOTYPE.

## Base e entrega

O A4 foi recuperado do bloco Python executado pelo PowerShell, no histórico
PSReadLine. A recuperação removeu apenas o invólucro PowerShell e os caracteres
de continuação de linha. O código original permanece em
`f3_int121_a4_recuperado.py`, separado da implementação A5.

`f3_int121_a5_sqlite.py` fornece `SQLiteWitness`. O formato das solicitações e
recibos assinados do A4 foi preservado. Cada arquivo de banco pertence a um
store_id e a uma chave pública da testemunha, ambos conferidos na reabertura.

Nonce, envelope assinado e recibo são gravados na mesma linha, dentro de uma
transação `BEGIN IMMEDIATE`. Sequência, geração e head são derivados da cadeia
persistida e validada. A confirmação só é retornada após o commit.
O modo é `journal_mode=DELETE`, com `synchronous=FULL`.

Cada abertura e submissão verifica a cadeia inteira: assinatura do cliente,
assinatura da testemunha, serialização canônica, vínculo do recibo à solicitação,
nonce, sequência, geração e head anterior. O acesso transacional serializa
escritores independentes. Banco ausente não é recriado na reabertura;
`create=True` exige um caminho ainda inexistente.

## Validação executada

- A4 recuperado: 16/16 verificações aprovadas novamente.
- A5: 26/26 testes unittest aprovados; saída em `VALIDACAO_A5_SQLITE.txt`.
- Reabertura e recuperação do mesmo recibo após reinício.
- Encerramento real de subprocessos com `os._exit(73)` após INSERT e antes
  do commit: a gravação incompleta não é retida; a repetição é aceita.
- Encerramento após commit e antes do ACK: a repetição retorna o recibo
  persistido, sem avançar a sequência.
- Dois subprocessos liberados por uma barreira: a mesma solicitação gera
  uma confirmação e um replay; solicitações distintas para a mesma sequência
  produzem um vencedor e uma rejeição de sequência antiga.
- Falha de escrita injetada por trigger, contenção do banco e conexão fechada
  não produzem confirmação.
- Rejeição de alterações em recibos, metadados, chave/store_id, histórico sem
  confiança, quebra intermediária da cadeia, campos extras, booleanos em
  campos inteiros, hex inválido e sequência fora da faixa SQLite.

A primeira execução encontrou um erro de limpeza da fixture de snapshot:
o contexto de conexão sqlite3 não fecha a conexão automaticamente. A fixture
foi corrigida para fechá-la explicitamente; a execução final passou integralmente.

## Como executar

Requer Python e `cryptography`. No ambiente já utilizado pelo projeto:

```powershell
& 'C:\COPILOTO_PRICE_ACTION_AI\ambiente\Scripts\python.exe' -B '.\test_f3_int121_a5_sqlite.py' -v
```

Execute na pasta que contém os dois arquivos A5. Os temporários dos testes
ficam em `../work/`, fora dos entregáveis. As chaves fixas no arquivo de testes
são fixtures públicas, exclusivamente de teste.

Uso da API: fornecer caminho, store_id, chave privada Ed25519 da testemunha e
mapa de clientes confiáveis ao construtor. Use `create=True` apenas para criar
um banco novo. Para reabrir, omita esse parâmetro e forneça a mesma identidade
da testemunha. `submit(envelope)` retorna `(status, recibo)`; `state()` retorna
sequência, geração e head verificados; `close()` fecha a conexão.

## Limites e próximo passo

- Esta entrega é isolada: não modifica nem integra o runtime principal do projeto.
  A regressão completa do projeto não foi executada.
- Não há custódia independente, serviço remoto, integração de armazenamento
  seguro das chaves ou âncora externa. As chaves são fornecidas pelo chamador;
  os testes reutilizam a identidade de teste em processos independentes.
- Uma cópia antiga e válida do banco, inclusive com remoção de um sufixo inteiro
  da cadeia, continua válida localmente. Um teste demonstra esse limite.
  Não há garantia de monotonicidade contra rollback de snapshots.
- Encerramento de processo não equivale a desligamento físico ou falha de disco.
  Não foram comprovadas garantias do hardware, filesystem ou controlador.
- O teste de falha de escrita usa injeção lógica; não simula disco fisicamente
  cheio nem falha real de fsync. Erro de commit deve ser tratado como resultado
  incerto e reconciliado repetindo exatamente o mesmo envelope.
- A cadeia é percorrida integralmente a cada submissão. Escala, rotação de
  chaves, retenção e migrações ainda não foram implementadas.

Próximo passo técnico: definir custódia da identidade e checkpoint externo,
vincular a API ao armazenamento do projeto e validar falhas na integração.

OPERACOES REAIS: BLOQUEADAS.
PROMOCAO A FINAL: BLOQUEADA.
