# Microstructure Architecture Audit RC11

## Escopo

Auditoria da cadeia observacional Price Action × Order Flow/Delta × BookDepth antes de qualquer novo A/B de impacto no Score oficial.

## Resultado

A arquitetura permanece adequada para coleta passiva, mas foram encontrados dois defeitos de dependência que precisavam ser corrigidos antes de continuar.

### 1. Order Flow consultava o atributo estrutural incorreto

`OrderFlow._qualify_structure()` consultava `context.market_structure`, porém o contrato real `AnalysisContext` expõe o resultado estrutural em `context.structure`.

Efeito anterior: absorção/exaustão podia permanecer com `structure_alignment=UNAVAILABLE` no contexto real mesmo com estrutura válida.

Correção RC11:
- usa `context.structure`;
- normaliza `Trend` enum por `.value`;
- preserva compatibilidade com strings de adaptadores/testes;
- `UNKNOWN` fica explicitamente `UNAVAILABLE`;
- `SIDEWAYS` permanece `NEUTRAL`.

### 2. BookDepth executava antes do Price Action que ele consumia

`BookDepthAnalysis.PRIORITY` era 47, enquanto `PriceAction.PRIORITY` é 50. Mesmo assim, BookDepth lia `context.price_action.bias` para calcular alinhamento e ajustar confiança.

Efeito anterior: a análise do Book podia consumir o Price Action ainda limpo no ciclo atual.

Correção RC11:
- `BookDepthAnalysis.PRIORITY = 55`;
- ordem garantida: `OrderFlow (45) -> PriceAction (50) -> BookDepthAnalysis (55) -> ContextEngine (70)`.

## Independência de evidência

A auditoria de microestrutura mantém três famílias máximas de evidência independente:
1. Price Action;
2. Order Flow/Delta;
3. BookDepth independente.

Pressure, momentum e pattern_direction do Order Flow pertencem à mesma família e não multiplicam a contagem independente. BookDepth marcado como correlacionado com Delta também não aumenta a contagem independente.

## Isolamento operacional

A camada continua passiva. Os módulos de confluência, elegibilidade, recorder, persistência, relatórios e comparadores multi-sessão não escrevem em:
- Score oficial;
- Strategy;
- Risk;
- Decision;
- execução.

## Limitação de dados reais

O contrato e a análise de BookDepth estão prontos para uma fonte real, mas a validade dos resultados depende de snapshots reais de profundidade. Enquanto a fonte de Book não estiver alimentando o serviço em produção, métricas de Book devem ser tratadas como indisponíveis e nunca inferidas.

## Gate para próximo estágio

Antes de considerar A/B hipotético da confluência no Score:
1. manter RC11 verde em testes;
2. coletar sessões reais com Order Flow e, quando disponível, BookDepth real;
3. exigir estabilidade multi-pregão nos comparadores passivos;
4. verificar que `STRONG_CANDIDATE` não depende majoritariamente de evidência correlacionada;
5. qualquer A/B futuro deve continuar pós-Decision e sem alterar o Score oficial.

## Decisão

**APROVADO PARA OBSERVAÇÃO PASSIVA.**

**NÃO APROVADO AINDA PARA PESO OPERACIONAL.**
