# Limites da fachada de ingestao

Os pontos de entrada legados de prepare/commit aceitam arvores de tuples sem
limite global de profundidade. O marco 56 adiciona bounded_prepare e
bounded_commit: percorrem apenas tipos exatos conhecidos e rejeitam entradas
mutaveis/desconhecidas, excesso de profundidade, nos ou tamanho de strings antes
da avaliacao de recuperacao. Geradores nao sao consumidos e objetos arbitrarios
nao sao inspecionados. Limites nao constituem garantia de prazo.

Esta protecao depende de usar a fachada. Os pontos de entrada legados e a
exploracao 54 nao foram alterados retroativamente. Memoria, snapshots e propostas
continuam sob controle do chamador. Rejeicao nao restaura confianca nem autoriza
operacao. A cota de nos limita o percurso, nao o custo de alocar uma entrada que
ja chegou pronta do chamador.
