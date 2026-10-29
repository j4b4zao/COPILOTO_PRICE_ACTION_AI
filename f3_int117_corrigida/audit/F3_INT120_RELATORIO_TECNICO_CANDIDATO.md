# F3-INT-120 ? Relatorio tecnico candidato

Gerado em UTC: 2026-10-28T18:58:12.581568+00:00

## Classificacao

- Status: CANDIDATO EXPERIMENTAL
- Promocao a FINAL: BLOQUEADA
- Checkpoint oficial preservado: F3-INT-117 R2 FINAL
- Estado F3: OPEN
- Operacoes reais: NAO AUTORIZADAS

## Modulos verificados

| Modulo | SHA256 |
|---|---|
| f3_int120_authenticated_witness.py | 9E4E04D54E108984EAFCED3489F5038957F3B99C8962E27CD93271DD4A2CF564 |
| f3_int120_sqlite_witness_adapter.py | 86B3A2E0A99351D428B71695DC1F80A5C8A789BE71678C8727569AE2B782C396 |

## Resultados informados das etapas

- E1: 4/4
- E2: 5/5
- E3: 9/9
- G: 12/12
- H: 12/12
- I: 4/4
- L2: 4/4
- M: 5/5
- P: 7/7
- Q: 6/6
- R: 2/2

Total: 70/70 verificacoes informadas como aprovadas.

A contagem representa verificacoes locais e nao certificacao operacional.

## Limites identificados

1. A chave publica e fornecida pelo chamador.
2. A referencia confiavel tambem e fornecida pelo chamador.
3. Nao ha comprovacao de custodia externa independente.
4. Uma assinatura local nao impede rollback conjunto de banco e referencia.
5. Durabilidade diante de perda fisica de energia permanece nao demonstrada.
6. A integracao ainda nao constitui uma certificacao de producao.

## Decisao

NAO PROMOVER A FINAL.

Manter todas as sete travas operacionais em False.
Nao habilitar ordens reais, execucao automatica ou certificacao live.

## Proximo trabalho

Definir e auditar a origem independente da chave publica,
a custodia monot?nica externa e o vinculo entre a referencia
externa e o estado SQLite observado.
