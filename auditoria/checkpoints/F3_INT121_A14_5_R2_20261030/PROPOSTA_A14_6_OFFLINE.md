# Proposta para A14.6 — evidências de encerramento verificáveis

Proposta de continuidade, sem atribuir critérios históricos inexistentes nos arquivos examinados.

F3 OPEN; offline; simulation_only; operações reais bloqueadas.

## Problema observado

A14.5-R2 distingue sobrevivência observada de término espontâneo e mantém a limpeza externa obrigatória. A14.4 conserva asserções estritas sobre sobreviventes, embora worker-first e encerramentos em rápida sucessão possam drenar os descendentes antes da observação. Aprovação de uma execução não elimina essa possível intermitência.

## Experimento proposto

Criar um espécime negativo adicional, exclusivamente de teste, que confirme por handshake que um descendente permanece retido em uma barreira antes de encerrar worker/supervisor. A barreira precisa ser independente dos pipes que o worker fecha. O Job externo de segurança deve conter o espécime desde o início e ser encerrado em finally, inclusive se o handshake ou uma asserção falhar.

Usar handles retidos e vínculo ao Job para observar a identidade, sem inferir identidade apenas pelo PID. Separar três observações: estado antes da solicitação de encerramento, estado confirmado após a morte dos alvos e estado após a limpeza externa. O instante de uma solicitação não deve ser descrito como instante de morte confirmada.

## Critérios propostos

- Controle negativo retido: sobrevivente efetivamente confirmado antes da limpeza externa.
- Controle positivo: contenção interna confirmada antes da limpeza externa, sem depender da barreira negativa.
- Caminho de falha: expiração do handshake gera falha explícita e limpeza obrigatória; nenhum timeout é convertido em aprovação.
- Todas as saídas: Job sem processos ativos, handles sinalizados, threads de I/O encerradas e flags operacionais falsas.
- Se a coleta de marcador falhar, preservar errno, código Win32 quando disponível, etapa e tempos observados, sem atrasar a limpeza externa obrigatória. A execução de origem desta retomada perdeu o espécime após o cleanup e não permite identificar conclusivamente quem negou a abertura do arquivo.
- Manter intactos os testes e resultados R2. Novos cenários devem ter nomes e contagem próprios.
- Executar específicos e regressão, sequencialmente, em normal e otimizado; publicar logs, hashes e limitações.

## Implementação já disponível nesta retomada

`auditar_regressao.py` confere a integridade semântica dos logs R2: código de saída, 180 testes, ausência de skips, modo Python, seis repetições distintas, nove registros de encerramento A14.4/A14.5 e limpeza final. Também confere os 12 registros de fronteiras por modo, os sete bloqueios operacionais e a observação dos handles antes da limpeza externa. Dezesseis verificações sintéticas exercitam sua aceitação/rejeição, incluindo substituição indevida de inteiros por booleanos; elas não contam como testes do projeto.

## Limites

Um descendente artificialmente retido melhora a contraprova controlada, mas não caracteriza a distribuição de escalonamentos de produção. Não estabelece prazo estrito, resistência a atacante hostil, custódia independente, durabilidade física nem autorização de operação. Esta proposta não é uma implementação nem um aceite A14.6.
