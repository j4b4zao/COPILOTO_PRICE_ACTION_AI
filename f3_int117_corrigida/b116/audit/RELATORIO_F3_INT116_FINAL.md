# Promocao F3-INT-116 FINAL — 24/10/2026

Promocao expressamente autorizada pelo usuario apos parecer APROVADO (51/51 verificacoes de consistencia). FINAL identifica o marco offline aprovado; F3 continua OPEN, sete flags false, offline/simulation_only true, certification false. Nenhuma operacao real autorizada.

## Base aprovada e testes

Base: F3_INT116_CANDIDATA_CORRIGIDA_COMPLETA_20261024.zip, SHA-256 4af6d6d84195532a6fd013a3ba894b2e1684f5368526266c7c580d9526c42b0f. Os 898 pins da candidata, 225 fontes executados e conteudo do ZIP foram reconferidos antes da promocao. Nenhum codigo ou teste da candidata foi alterado.

Resultados reutilizados da execucao aprovada, sem nova execucao das suites nesta promocao de metadados: especificos 17/17; regressao 1438 testes, 1437 aprovados, 1 skipped, zero falhas/erros, exit code 0. Runner principal com -O em pasta relocalizada; supervisor herdado executou suites sem -O; nove testes novos exercitam subprocessos -O. Limpeza dos Jobs confirmada, zero processos ativos e threads IPC remanescentes no escopo supervisionado.

## Publicacao e preservacao

Projeto FINAL: f3_int116_final. audit/ULTIMO_MARCO.json e audit/CHECKPOINT_F3_INT116_FINAL.json possuem bytes identicos. Manifesto oficial: audit/MANIFESTO_F3_INT116_FINAL.json. Todos os 225 fontes e logs aprovados permanecem identicos.

Os checkpoints FINAL anteriores nao foram modificados. O antigo audit/ULTIMO_MARCO (F3-INT-115 FINAL) foi preservado byte a byte em audit/HISTORICO_ULTIMO_MARCO_F3_INT115_FINAL_20261024.json. O projeto candidato original permanece intacto e tambem esta integralmente em candidata_preservada/, onde seus manifestos continuam validos e seu runner pode ser reexecutado com nome novo de output. A base F3-INT-115 FINAL permanece integral em base_f3_int115_final/.

Na arvore ativa FINAL, manifestos anteriores que fixam ULTIMO_MARCO sao historicos: o manifesto candidato se aplica ao snapshot candidata_preservada/audit; o manifesto F3-INT-115 FINAL se aplica a base_f3_int115_final. O manifesto novo fixa o estado FINAL atual e inclui esses snapshots. Esse mapeamento evita confundir o marcador autorizado novo com alteracao de checkpoint anterior.

Os antigos marcadores do workspace (raiz F3-INT-98 e audit F3-INT-114) foram preservados em promotion_artifacts/HISTORICO_ULTIMO_MARCO_RAIZ_PRE_F3_INT116.json e HISTORICO_ULTIMO_MARCO_AUDIT_PRE_F3_INT116.json. Apos validar o ZIP, os dois aliases do workspace e seus novos checkpoints serao publicados com os mesmos bytes do checkpoint FINAL, e a publicacao sera conferida em registro externo.

O ZIP e preparado antes da publicacao: CRC, nomes unicos seguros, hash de cada membro, manifesto, fontes, evidencias, historicos e checkpoint sao verificados. Validacao pos-publicacao e hash do ZIP ficam fora do pacote para evitar autorreferencia. O manifesto exclui somente ele proprio e seu sidecar; o hash externo do ZIP cobre ambos.

## Limites

Sem custodia autenticada, procedencia independente ou resistencia comprovada a perda de energia. Permanece o skip de symlink do Windows. Nao ha garantia de durabilidade fisica, entrega exatamente uma vez ou entre computadores. Comparacoes locais antes/depois nao detectam alteracao transitoria restaurada. O runner 116 e preservado como auditor da candidata sobre a base 115; sua reexecucao deve usar o snapshot candidato, pois a arvore FINAL tem ULTIMO_MARCO legitimamente atualizado.

F3-INT-117: somente inspecao e proposta apos verificacao desta promocao; implementacao nao autorizada.
