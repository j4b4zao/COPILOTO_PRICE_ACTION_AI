# F3-INT-115 CANDIDATA

Base validada: C:/COPILOTO_F3_INT114_FINAL; ultimo marco definitivo F3-INT-114 FINAL.
F3 OPEN; sete flags false; somente fixtures offline locais; sem ordens, adaptadores ou rede.
ULTIMO_MARCO e arquivos historicos preservados. Sem promocao para FINAL ou INT-116.

## Tentativas preservadas

Ensaio inicial: 10 testes, 8 aprovados, 2 falhas por fixtures regeneradas divergentes.
Segunda tentativa: 10 erros por importacao base64 ausente; regressao interrompida pelo operador.
Ambos os problemas do harness foram corrigidos antes da validacao abaixo; logs preservados.

## Implementacao

Reutiliza admissao SQLite 109 e reconciliacao 110. Processos Python independentes,
cada um com sua conexao SQLite; barreiras por stdin/stdout e timeout, sem sleeps de sincronizacao.
Threads existem apenas para leitura limitada das saidas dos processos.
Disputa simultanea: exatamente um vencedor; perdedor BUSY ou ancora antiga.
Disputa controlada: transacao IMMEDIATE retida, concorrente BUSY e retry antigo rejeitado.
Interrupcoes reais: processo terminado pelo pai antes da escrita, apos escrita e apos commit.
Nova observacao em outro processo distingue COMMITTED, NOT_COMMITTED e UNRESOLVED.
ACK perdido permanece LOST; nenhum resultado autoriza retry ou operacao real.

## Execucao Windows

- ESPECIFICOS_VALIDACAO: 10 testes; 10 aprovados; 0 falhas; 0 erros; 0 skips; exit code 0; 50.029 s. Log: RESULTADO_F3_INT115_ESPECIFICOS_VALIDACAO.txt.
- REGRESSAO_WINDOWS_VALIDACAO: 1398 testes; 1397 aprovados; 0 falhas; 0 erros; 1 skips; exit code 0; 818.073 s. Log: RESULTADO_F3_INT115_REGRESSAO_WINDOWS_VALIDACAO.txt.

Inventario historico comparado antes/depois do runner: 772 arquivos; alteracoes: [].

## Limites

- Evidencia local em uma maquina e filesystem; nenhuma seguranca entre computadores demonstrada.
- Kill de processo nao equivale a queda de energia, falha de SO, disco ou durabilidade fisica.
- Pins precomputados antes dos escritores ficam em pasta irma da pasta SQLite e sao comparados byte a byte.
  Mesmo usuario e permissoes: separacao de caminhos nao demonstra custodia independente.
- Manifestos ficam fora das pastas temporarias do banco, mas no mesmo dominio de usuario.
- Hashes e executavel informados pelo runner nao autenticam identidade ou origem independentemente.
- Ausencia de ACK nao comprova ausencia de commit; pins invalidos, banco ausente/corrompido ou estado divergente falham fechados.
- Nenhuma entrega exatamente uma vez, deadline estrito ou resistencia a rollback conjunto e certificada.
- Ensaios limitados aos interleavings exercitados, nao prova exaustiva.

## Arquivos novos e SHA-256

Nenhum arquivo historico modificado. Hashes abaixo excluem este relatorio e o manifesto para evitar autorreferencia.

- `CHECKPOINT_F3_INT115_CANDIDATA.json`: `41aa42d767edd8d294024ed592aa105babf583c961734ba1f3e420430675d836`
- `RESULTADO_F3_INT115_ESPECIFICOS.txt`: `ef864db441a9b4bcc0c97856b7a9ad5a4c07e3808af7c7c9f8d11004b4d44473`
- `RESULTADO_F3_INT115_ESPECIFICOS_CANDIDATA.txt`: `21d7ce77695e87787fac624567eae66555397a0043127ad2402ad817649bb852`
- `RESULTADO_F3_INT115_ESPECIFICOS_VALIDACAO.txt`: `469743be46136754085b2cb8303f3d0acfdbde224827f9ae639e94b3ebaf1954`
- `RESULTADO_F3_INT115_REGRESSAO_WINDOWS.txt`: `4741529bb8be6b4cd0faeb37aa6c8fbd7443388cc30a84040a6832b221dce90c`
- `RESULTADO_F3_INT115_REGRESSAO_WINDOWS_VALIDACAO.txt`: `4bb97bb6ad7e86833d72f5a6f71ad8de04b0033b3bf60ba82950f3736afc4b12`
- `tests/test_f3_int115_multiprocess_recovery.py`: `b76bda86e579883607a4d40981f7cb2e9e65b20e19c87e95e6b4d38978e38366`
- `tools/f3_int115_multiprocess_recovery.py`: `ff92b7a3fa53c63e8c50bc5815a8e07880155eac3340b14e699c62a5cb7afd64`
- `tools/f3_int115_run_candidate.py`: `875f66e5a8aea645b8ad7bf6d41067c2d6f6e134ba9ff4c95a2fe4347d61a3bd`
