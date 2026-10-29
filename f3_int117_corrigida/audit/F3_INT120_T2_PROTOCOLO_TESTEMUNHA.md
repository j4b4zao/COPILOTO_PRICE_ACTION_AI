# F3-INT-120 T2 ? Protocolo de testemunha externa

## Estado
ESPECIFICACAO EXPERIMENTAL ? NAO IMPLEMENTADA.

## 1. Identidade
- A chave privada Ed25519 permanece sob custodia externa.
- A chave publica e fixada por configuracao confiavel.
- A origem da chave publica nao pode ser definida pelo recibo.
- Rotacao de chaves exige procedimento autenticado e auditavel.

## 2. Registro externo
Cada registro contem:
- schema
- store_id
- sequence
- generation
- state_digest
- key_id
- previous_receipt_digest

## 3. Confirmacao
- A testemunha valida o registro recebido.
- Rejeita sequencias antigas ou repetidas indevidamente.
- Vincula cada atualizacao ao registro anterior.
- Persiste o novo estado antes de confirmar.
- Assina somente registros aceitos.

## 4. Consulta
- O cliente consulta diretamente a testemunha autenticada.
- A resposta informa o ultimo estado confirmado.
- A resposta e vinculada a um desafio unico do cliente.
- Uma resposta antiga nao pode ser aceita como atual.
- A indisponibilidade da testemunha resulta em bloqueio.

## 5. Protecao contra rollback
- O SQLite observado deve corresponder ao estado externo.
- Recibos antigos nao substituem a referencia externa atual.
- Divergencia de sequence, generation ou digest causa rejeicao.
- Rollback conjunto local deve ser detectado.
- Rollback da propria testemunha exige protecao independente.

## 6. Persistencia
- Confirmacao somente apos persistencia duravel.
- Falha durante gravacao nao pode produzir confirmacao falsa.
- Recuperacao deve preservar a ultima sequencia confirmada.
- Testes de perda fisica de energia continuam obrigatorios.

## 7. Limites
- Nenhuma testemunha externa foi implementada nesta etapa.
- Nenhuma custodia independente foi demonstrada.
- Nenhuma garantia de durabilidade fisica foi comprovada.
- Nenhuma operacao real esta autorizada.

## 8. Decisao
F3-INT-120 permanece CANDIDATO EXPERIMENTAL.
F3 permanece OPEN.
Checkpoint oficial: F3-INT-117 R2 FINAL.
Todas as sete travas operacionais permanecem False.
Promocao a FINAL: BLOQUEADA.
