# Economic Calendar RC9 — seleção de fonte real

Data da avaliação: 24/08/2026  
Escopo: Brasil e Estados Unidos, uso observacional e somente leitura.

## Decisão

**Trading Economics foi selecionada como candidata principal para ensaio controlado da RC10.**

A seleção não autoriza conexão em produção, uso de credencial, alteração de Score/Risk/Decision nem bloqueio operacional. A fonte somente poderá ser promovida após ensaio real, registro multi-pregão e aprovação dos critérios abaixo.

## Comparação

| Critério | Trading Economics | EODHD Economic Events | FMP Economic Calendar |
|---|---|---|---|
| Cobertura internacional documentada | Sim | Sim | Calendário global anunciado, cobertura BR não comprovada na documentação avaliada |
| Filtro por país | País e múltiplos países | ISO-3166 de 2 letras | Não comprovado na documentação avaliada |
| Brasil + EUA | Compatível com a API por país | Compatível por códigos BR/US | Pendente de evidência |
| Data/hora | Campo `Date` | Campo `date` | Data documentada |
| Impacto/severidade | `Importance` 1–3 | Não consta no payload documentado | Não comprovado |
| Actual/Previous/Forecast | Sim | Actual/Previous/Estimate | Não comprovado integralmente |
| Atualização | Quase em tempo real, 24h/dia | Passado e futuro desde 2020 | Ciclo informado de 10 minutos |
| Formato | JSON/CSV | JSON | JSON |
| Autenticação | Chave de API | Token de API | Chave de API |
| Adequação ao núcleo atual | Alta, após mapper de chaves PascalCase | Média; exige regra própria de impacto | Indeterminada |
| Resultado RC9 | **Selecionada para ensaio** | Reserva comparativa | Não selecionada |

## Motivos da seleção

1. Cobertura conjunta de eventos brasileiros e norte-americanos.
2. Impacto explícito 1=LOW, 2=MEDIUM e 3=HIGH, compatível com o modelo atual.
3. Horário, país, moeda, evento, anterior, consenso e realizado no mesmo payload.
4. Filtros por país, intervalo e importância reduzem volume e ruído.
5. Estrutura adequada ao recorder e comparador multi-sessão já implementados.

## Restrições identificadas

- O exemplo JSON usa chaves PascalCase (`Event`, `Date`, `Importance`, `Country`, `Currency`); o normalizador RC4 é case-sensitive. A RC10 deve introduzir mapper explícito, sem ampliar aliases de forma ambígua.
- A documentação mostra autenticação por query string. Antes de qualquer chamada, a URL precisa ser sanitizada nos diagnósticos para nunca registrar a chave.
- Datas sem offset devem ser verificadas contra a semântica de fuso da resposta. Nenhuma suposição UTC será promovida sem amostra real.
- Cobertura nominal não prova pontualidade para Copom, IPCA, Payroll, CPI e FOMC; isso será medido.
- Termos comerciais, limite do plano e licença de uso precisam ser confirmados antes de operação contínua.

## Critérios obrigatórios para RC10/RC11

- Zero segredo em logs, exceções, relatórios ou `repr`.
- Allowlist restrita a `api.tradingeconomics.com`.
- Somente HTTPS GET, sem redirects, com timeout e limite de resposta.
- Filtro exclusivo Brasil/Estados Unidos e janela temporal limitada.
- Mapper PascalCase testado offline.
- Conversão de impacto 1–3 sem inferência textual.
- Validação explícita de timezone e horário de verão.
- Fail-safe: indisponibilidade gera estado `UNAVAILABLE` ou cache stale, nunca sinal.
- Pelo menos 5 pregões registrados antes de avaliar promoção.
- Conferência manual dos eventos críticos: Copom, IPCA, IGP-M, Payroll, CPI, PPI, GDP, FOMC e Jobless Claims.
- Cobertura, rejeição, duplicação, atraso e mudanças de horário comparados por sessão.
- Psicologia do Trader poderá consumir apenas razões contextuais futuras; não altera o ScoreEngine.

## Fontes oficiais consultadas

- Trading Economics — Economic Calendar Snapshot: https://docs.tradingeconomics.com/economic_calendar/snapshot/
- Trading Economics — Economic Calendar Streaming: https://docs.tradingeconomics.com/economic_calendar/streaming/
- EODHD — Economic Events Data API: https://eodhd.com/financial-apis/economic-events-data-api
- Financial Modeling Prep — Economic Data Releases Calendar: https://site.financialmodelingprep.com/developer/docs/stable/economics-calendar

## Próximo passo

RC10: endurecer a sanitização de URL, criar o mapper Trading Economics e validar amostras sintéticas/offline. Somente depois disso solicitar/configurar uma credencial para um ensaio manual e observacional.
