# Registro tipado de evidencias

EvidenceRegistry registra pares de IDs de referencia e de observacoes finitas.
Nao e o Registry de testemunhos consumidos, e esses tipos nao sao intercambiaveis.
O namespace IMPORT_DIVERGENCE_V1 participa dos hashes, sem fornecer autenticacao.

O ID de referencia cobre o JSON canonico, incluindo referencias exatas aos
pacotes. O ID de observacoes cobre o snapshot inicial, pins por ator/lote e os
dois traces completos, ordenados pelo digest para desconsiderar a orientacao do
par. Reempacotar transporte pode mudar referencias sem mudar essas observacoes.
Isso nao demonstra equivalencia geral de programas, independencia ou consenso.

Registro de lote e atomico no modelo: qualquer falha devolve a mesma instancia
do registro anterior, sem recibos parciais. Reposicao integral do registro pelo
chamador permite replay novamente; nao existe persistencia confiavel ou fencing.
