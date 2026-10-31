# COPILOTO_PRICE_ACTION_AI — validação e correção de 30/10/2026

**A correção de leitura do marcador foi validada localmente.** O projeto principal permanece preservado. F3 OPEN, offline, simulation_only, operações reais bloqueadas.

| Pacote / modo | Resultado | Tempo |
|---|---|---|
| R2 original — normal | 180/180, OK | 900,334 s |
| R2 original — otimizado | 179 aprovados, 1 erro | 966,618 s |
| Candidata corrigida — normal | 184/184, OK | 729,515 s |
| Candidata corrigida — otimizado | 184/184, OK | 826,754 s |

O erro original foi um `PermissionError` na leitura de `boundary.json`, na repetição A14.1 anterior ao commit. O leitor corrigido repete a tentativa dentro do mesmo prazo de 20 segundos; negação persistente continua gerando erro. Nenhuma asserção de contenção, recuperação ou limpeza foi removida.

Os quatro testes adicionais exercitam compartilhamento exclusivo real do Windows, liberação do bloqueio, negação persistente, marcador ausente e JSON malformado. Com os dois cenários A14.1, os específicos passaram 6/6 em cada modo. A contraprova controlada reproduz o erro no leitor original e a recuperação no corrigido, mas não identifica conclusivamente a causa da negação ocorrida na primeira regressão.

As duas regressões corrigidas passaram sem skips. Os 24 registros de fronteira e os bloqueios operacionais passaram na auditoria. As 16 verificações sintéticas do auditor são separadas e não entram nos 184 testes do projeto.

## Arquivos principais

- `CANDIDATA_CORRECAO_MARCADOR_20261030.zip`: fontes corrigidas, manifesto próprio, checkpoint, logs e evidências. Extrair em pasta nova fora do projeto operacional. O documento inicial do pacote indica o manifesto vigente; os manifestos herdados descrevem a origem histórica.
- `CHECKPOINT_CORRECAO_MARCADOR_20261030.json`: estado `CORRECAO_VALIDADA_LOCALMENTE`.
- `CHECKPOINT_F3_INT121_A14_5_R2_20261030.json`: resultado da origem R2, mantido como `REGRESSAO_NAO_APROVADA`.
- `CORRECAO_MARCADOR.patch` e `CORRECAO_LEITURA_MARCADOR.md`: alteração revisável e diagnóstico.
- `PROPOSTA_A14_6_OFFLINE.md`: próximo experimento proposto, com barreira e handshake. A14.6 não foi implementada nem aprovada como marco.
- `EVIDENCIAS_WINDOWS_A14_5_R2_20261030.zip`: entrega consolidada, com a candidata, o ZIP original, anexos históricos, ferramentas e resultados.

As regressões originais usaram Python 3.12.14 do runtime local. As corrigidas usaram Python 3.13.5 do ambiente do projeto. Ambos tinham `cryptography` 50.0.2. A contraprova controlada demonstra o efeito da alteração sem depender da comparação de duração entre os ambientes.

## Projeto e GitHub

Nenhum arquivo de `C:\COPILOTO_PRICE_ACTION_AI` foi substituído. Não houve reset, limpeza, merge, commit ou push. As exclusões e arquivos não rastreados apontados inicialmente pelo Git foram preservados; diretórios inacessíveis ao sandbox impedem interpretar todos os caminhos com `D` como exclusões físicas.

O repositório GitHub conectado foi consultado. O commit local `3ca24e4` não foi encontrado pelo conector, e a busca de commits A14.5 não retornou resultados. Portanto, o backup remoto desse checkpoint continua **não confirmado**. A branch local também apresenta divergência nas referências remotas armazenadas, sem fetch nesta sessão.

Esta validação cobre as fixtures locais e os cenários executados. Não autoriza instalação no runtime operacional, operações reais ou certificação de produção; não demonstra todos os escalonamentos, custódia independente ou durabilidade física.
