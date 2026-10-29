# Limites da evidencia offline

Os checkpoints, e nao a presenca de um arquivo de codigo, indicam quais marcos
foram concluidos com regressao integral. A suite e somente a auditoria isolada.

## Snapshots e geracoes controlados pelo chamador

Manter versao e conteudo do snapshot permite ao modelo rejeitar propostas
obsoletas. Restaurar ambos integralmente permite reapresentar a mesma proposta
como se a primeira execucao nao tivesse ocorrido. O marco 63 reproduz essa
limitacao. Redefinir somente versao ou somente estado foi rejeitado nas fixtures.
Isto nao fornece armazenamento confiavel nem fencing de sistemas reais.

Contadores de geracao de atores e registros de digests tambem sao memoria local
substituivel. Crash de um ator no modelo descarta sua proposta pendente; nao
simula persistencia de disco, falha de processo real, rede, hardware ou broker.

## Invariantes e replay

O monitor 64 verifica condicoes necessarias, como incremento de versao e
preservacao de prefixos. Ha adulteracoes que preservam essas condicoes. O marco
65 compara o monitor com replay completo e reproduz essa diferenca. Mesmo o
replay completo somente reexecuta fixtures do chamador; nao autentica pessoas,
testemunhas, pins, votos, digests ou origem de dados.

## Exploracao e minimizacao

As familias finitas de agendas preservam a ordem local definida para cada ator.
Nao cobrem todos os programas concorrentes, falhas, intercalacoes, escalonadores
ou sistemas de memoria. Cobertura incompleta possui status explicito. Resultados
de simetria nao demonstram fairness ou ausencia de starvation em sistemas reais.

Um par reduzido de traces e minimo apenas quanto a remocao de um evento isolado,
sob o predicado definido: divergencia terminal, crash seguido de commit de
geracao reiniciada em ambos os lados e ao menos um commit de geracao obsoleta.
Nao se afirma minimo global ou causalidade fora desse predicado/modelo.

## Pacotes e formato JSON

Manifestos SHA256, digests de traces, logs e ancoras sao fornecidos ou produzidos
no mesmo fluxo local. Conferencia interna de hashes e consistencia nao e
assinatura nem atestacao independente. Logs sinteticos coerentes podem ser
forjados por quem controla todo o pacote. O formato fechado rejeita tipos
desconhecidos e exige replay, mas nao autentica a fixture que foi reexecutada.

Limites de bytes, profundidade, nos e contagens reduzem o trabalho percorrido
pelo modelo; nao estabelecem prazo estrito nem limitam alocacao feita previamente
pelo chamador. Entradas legadas sem fachada limitada continuam disponiveis.

## Fronteira operacional

F3 permanece OPEN. Os sete flags operacionais permanecem false. Sem Profit,
Excel, RTD/DDE, ordens, adaptadores ou sistemas reais. Sem certificacao.
