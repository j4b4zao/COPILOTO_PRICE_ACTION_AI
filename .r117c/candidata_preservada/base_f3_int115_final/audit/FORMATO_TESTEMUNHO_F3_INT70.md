# Formato JSON fechado de testemunho de crash

EXEMPLO_TESTEMUNHO_F3_INT70.json e uma fixture sintetica minima em uma remocao
de evento, gerada pelo marco 69. Nao contem dados de mercado ou ordens.

schema=1; requests contem round_id e argumentos em pares sem duplicatas. Os
unicos tipos compostos decodificados sao tuple, Membership e EpochEvidence,
com campos fechados. Nao ha pickle, importacao dinamica ou classe fornecida no
JSON. left_events e right_events contem operacao, ator e geracao; os traces
completos sao reconstruidos pelo simulador 66, partindo de snapshot vazio.
left_sha256 e right_sha256 comparam os traces completos reconstruidos.

Limites do formato: 131072 bytes, 8192 nos JSON, profundidade 32, arrays com ate
256 elementos, objetos com ate 64 campos, strings com ate 4096 caracteres e
inteiros de 64 bits. No maximo 3 requests e 16 eventos por lado. Limites do
modelo de recuperacao tambem se aplicam. Objetos JSON com chaves duplicadas,
numeros nao finitos ou tipos/tags desconhecidos sao rejeitados.

encode_witness valida o replay antes de serializar. decode_witness valida o
formato, reexecuta os eventos e compara digests antes de devolver o testemunho.
assess_encoded devolve um resultado com F3 OPEN e os sete flags false.

Digests sao controlados pelo chamador: isto e integridade interna reproduzivel,
nao assinatura, autenticacao, consenso, persistencia confiavel ou certificacao.
