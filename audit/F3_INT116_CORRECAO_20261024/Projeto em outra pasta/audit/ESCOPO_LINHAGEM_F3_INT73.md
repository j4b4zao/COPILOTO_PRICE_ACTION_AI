# Escopo da verificacao de linhagem

O marco 73 verifica uma sequencia finita de ate 32 pacotes e 32 MiB de bytes ZIP,
ancorada por etapa e contagem de testes fornecidas pelo chamador. Nesta
continuacao, a ancora e F3-INT-52 com 526 testes. A cada etapa, a contagem da
regressao deve ser a anterior mais os testes novos, sem falhas, erros ou skips.

Cada pacote passa pelos verificadores de integridade, portabilidade e evidencia
estrita dos marcos 60 a 62. Fontes .py anteriores em tests/ e tools/ devem existir
e manter seus hashes na etapa seguinte. Arquivos novos sao permitidos.

Essa politica descreve esta continuacao com adicoes de modulos. Nao implica que
fontes nunca possam ser corrigidos: uma extensao futura para correcoes precisara
representar e verificar deltas declarados, em vez de ignorar uma divergencia.

VERIFICACAO_LINHAGEM_ATE_INT72.json registra os 20 pacotes anteriores disponiveis
antes de gerar o ZIP 73. A verificacao final externa ao ZIP pode incluir o proprio
pacote 73; ela fica em outputs/VERIFICACAO_LINHAGEM.json. Evita-se colocar dentro
de um ZIP um arquivo que precisaria conter o hash desse mesmo ZIP.

REVISAO_ESTATICA_CONTINUACAO.json cobre apenas imports, chamadas selecionadas,
guardas safe_to_promote e hashes dos fontes no escopo indicado. Nao e analise
formal nem prova de ausencia de todos os efeitos. O hash do ZIP original e o
nucleo de flags herdado tambem foram comparados com os registros de origem.

Ancoras, digests, programas e logs sao controlados pelo chamador. Passar nessas
verificacoes nao autentica origem, nao certifica veracidade independente de
testes e nao autoriza qualquer operacao. F3 OPEN e sete flags false.
