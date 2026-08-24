# FinancialJuice — avaliação de provedor

Data da avaliação: 2026-08-24  
Status: **BLOQUEADO — AGUARDANDO AUTORIZAÇÃO ESCRITA OU API OFICIAL LICENCIADA**

## Objetivo

Avaliar o FinancialJuice como fonte secundária de contexto macroeconômico e notícias para o Copiloto Price Action AI, sem substituir a Trading Economics no calendário econômico.

## Dados potencialmente úteis

- calendário econômico internacional;
- manchetes e notícias de mercado;
- classificação de notícias macroeconômicas e market-moving;
- áudio/notícias em tempo real para assinantes;
- widgets públicos de calendário e manchetes;
- feed RSS público divulgado pelo serviço.

## Resultado da avaliação

Não foi encontrada documentação pública de uma API oficial para ingestão programática.

Os Termos de Uso do FinancialJuice restringem coleta, agregação, cópia e uso por data mining, robôs, spiders ou ferramentas semelhantes sem autorização expressa por escrito. Por isso:

- nenhum scraper será criado;
- nenhum login será automatizado;
- o RSS e os widgets não serão ingeridos, armazenados ou transformados pelo projeto sem confirmação de licença;
- nenhuma proteção técnica será contornada;
- nenhuma captura FinancialJuice será habilitada por padrão.

## Papel futuro no projeto

Se houver autorização oficial, o FinancialJuice deverá entrar apenas como fonte secundária e observacional de notícias/contexto macro:

1. Trading Economics continua como fonte primária do calendário.
2. FinancialJuice fornece confirmação narrativa ou alerta de notícia.
3. Os dados não alteram diretamente o ScoreEngine.
4. Os dados não executam ordens.
5. A psicologia do trader permanece no fluxo independente:
   `TraderPsychologyState → TraderPsychologyEngine → CoachingEngine → VoiceAssistant`.
6. A validação começa em replay offline e depois em comparação controlada de cinco sessões.

## Requisitos antes da implementação

É necessário obter do FinancialJuice, por escrito:

- endpoint/API/feed autorizado para uso automatizado;
- método de autenticação;
- limites de requisição;
- direitos de armazenamento e transformação;
- direitos de exibição/redistribuição;
- diferença contratual entre dados atrasados e em tempo real;
- campos, países, eventos e formato de timestamps;
- política de retenção e atribuição.

## Critério de desbloqueio

A integração somente poderá avançar quando houver pelo menos um destes itens:

- contrato/licença escrita que autorize a coleta e o uso no projeto; ou
- documentação oficial de API/feed com termos compatíveis com ingestão, armazenamento e processamento.

Até lá, o provedor permanece fail-closed e fora do runtime.
