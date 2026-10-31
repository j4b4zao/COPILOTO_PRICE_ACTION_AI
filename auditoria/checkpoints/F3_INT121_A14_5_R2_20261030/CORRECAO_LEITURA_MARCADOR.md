# Candidata de correção — leitura do marcador Windows

F3 OPEN; offline; simulation_only; operações reais bloqueadas.

## Resultado da origem R2

- Normal: 180 testes, OK, 900,334 s.
- Otimizado: 180 testes, 179 aprovações e 1 erro, 966,618 s.
- Erro: `PermissionError: [Errno 13]` em `BoundaryTests.wait_json`, ao ler `boundary.json` em `test_repeat_before_source_commit` da A14.1.
- As seis repetições A14.5-R2 emitiram evidências válidas em ambos os modos, mas a regressão integral original **não foi aprovada**.

## Diagnóstico e alteração

O leitor já repete a observação enquanto o arquivo está ausente ou contém JSON incompleto, com prazo de 20 segundos. Uma negação de abertura `PermissionError` encerrava a observação imediatamente.

Na cópia candidata, `wait_json` também repete a leitura após `PermissionError`, dentro do mesmo prazo existente. Se a última falha ao esgotar o prazo continuar sendo uma negação de acesso, a exceção é relançada. Não há aumento do timeout, fabricação de marcador ou alteração nas asserções de contenção, recuperação SQLite e limpeza.

Foi reproduzido um `PermissionError` real usando `CreateFileW` com compartilhamento zero. O teste libera o handle depois de 150 ms e exige que a leitura retorne o JSON correto. Outro teste mantém o bloqueio e exige falha. Os demais cobrem arquivo ausente e JSON malformado. Isso sustenta o tratamento de acesso transiente, mas **não identifica conclusivamente a causa da negação original**: o log original não contém o código Win32 e a fixture já foi limpa.

## Verificação

- Quatro testes de acesso Windows: aprovados.
- Conjunto com os quatro testes novos e os dois A14.1: 6/6 normal em 23,807 s; 6/6 otimizado em 43,880 s.
- Ambiente da candidata: Python 3.13.5 do projeto, `cryptography` 50.0.2.
- Regressão integral candidata: 184 testes por modo; consultar o checkpoint específico da correção para o resultado consolidado.
- O manifesto R2 herdado documenta a origem. A candidata possui manifesto próprio; não deve ser apresentada como ZIP R2 original intacto.

Nenhum arquivo operacional foi substituído. A14.6 permanece uma proposta separada de experimento offline. Os resultados da candidata não apagam o erro da execução original nem estabelecem ausência de intermitência em todos os escalonamentos.

## Resultado final da candidata

CORRECAO_VALIDADA_LOCALMENTE

- Normal: 184 testes em 729,515 s; auditoria aprovada.
- Otimizado (-O): 184 testes em 826,754 s; auditoria aprovada.
- Fronteiras: 24 registros; auditoria aceita=True.
