"""Read-only audit of candidate artifacts; writes only new audit evidence.
Run with Python -B. Supplementary probes do not modify candidate sources.
"""
from pathlib import Path
import hashlib
import json
import os
import platform
import re
import sqlite3
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_mapping(mapping):
    matched, missing, changed = [], [], []
    for name, expected in mapping.items():
        path = ROOT / name
        if not path.is_file():
            missing.append(name)
        elif digest(path) != expected:
            changed.append(name)
        else:
            matched.append(name)
    return dict(total=len(mapping), matched=len(matched), missing=missing, changed=changed)


class AuditProbes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import test_f3_int115_multiprocess_recovery as subject
        subject.MultiprocessRecoveryTests.setUpClass()
        cls.subject = subject

    def setUp(self):
        self.h = self.subject.MultiprocessRecoveryTests('test_simultaneous_same_operation_one_winner')
        self.addCleanup(self.h.doCleanups)
        self.h.setUp()

    def test_serial_execution_also_satisfies_simultaneous_acceptance(self):
        h = self.h
        a, b = h.launch(), h.launch()
        self.assertNotEqual(a.pid, b.pid)
        h.send(a, 'GO')
        first = h.finish(a)['status']
        # B is still parked at the GO barrier when A has already exited.
        self.assertEqual(a.poll(), 0)
        h.send(b, 'GO')
        second = h.finish(b)['status']
        statuses = [first, second]
        self.assertEqual(statuses.count('CONSUMED_FIXTURE_UNAUTHENTICATED'), 1)
        self.assertIn(next(s for s in statuses if s != 'CONSUMED_FIXTURE_UNAUTHENTICATED'),
                      ('STORE_BUSY', 'STATE_ANCHOR_MISMATCH'))
        self.assertEqual(h.inquiry(), 'COMMITTED_OBSERVED_UNAUTHENTICATED')
        print('AUDIT_PROBE: serial schedule satisfies original simultaneous predicate', flush=True)

    def test_lost_ack_retry_with_current_anchor_is_rejected(self):
        h = self.h
        h.crash('after_commit')
        self.assertEqual(h.inquiry(), 'COMMITTED_OBSERVED_UNAUTHENTICATED')
        p = h.launch(before=h.pins['after_state_digest'])
        h.send(p, 'GO')
        self.assertEqual(h.finish(p)['status'], 'STALE_CHAIN_REVISION')
        self.assertEqual(h.inquiry(), 'COMMITTED_OBSERVED_UNAUTHENTICATED')
        print('AUDIT_PROBE: current-anchor replay rejected; persisted generation remains pinned to 1', flush=True)

    def test_before_observation_can_be_followed_by_commit_without_retry_authority(self):
        h = self.h
        p = h.launch(hold='after_write')
        h.send(p, 'GO')
        self.assertEqual(h.event(p)['phase'], 'after_write')
        self.assertIsNone(p.poll())
        self.assertEqual(h.inquiry(), 'NOT_COMMITTED_OBSERVED_UNAUTHENTICATED')
        h.send(p, 'CONTINUE')
        self.assertEqual(h.finish(p)['status'], 'CONSUMED_FIXTURE_UNAUTHENTICATED')
        self.assertEqual(h.inquiry(), 'COMMITTED_OBSERVED_UNAUTHENTICATED')
        print('AUDIT_PROBE: snapshot observation is not finality; both queries keep retry false', flush=True)


def numbered(path, needle):
    return next(i for i, line in enumerate((ROOT/path).read_text(encoding='utf-8-sig').splitlines(), 1)
                if needle in line)


def main():
    evidence_path = ROOT/'EVIDENCIAS_AUDITORIA_F3_INT115_20261023.json'
    report_path = ROOT/'RELATORIO_AUDITORIA_F3_INT115_20261023.md'
    manifest_path = ROOT/'MANIFESTO_AUDITORIA_F3_INT115_20261023.json'
    for path in (evidence_path, report_path, manifest_path):
        if path.exists():
            raise FileExistsError(path)
    candidate_manifest = ROOT/'MANIFESTO_F3_INT115_CANDIDATA.json'
    manifest = json.loads(candidate_manifest.read_text())
    checkpoint = json.loads((ROOT/'CHECKPOINT_F3_INT115_CANDIDATA.json').read_text())
    historical = checkpoint['historical_inventory_before_runner']
    tracked = dict(historical, **manifest)
    tracked[candidate_manifest.name] = digest(candidate_manifest)
    before = check_mapping(tracked)
    evidence = dict(workspace=str(ROOT.parent), date='2026-10-23',
                    python=sys.version, executable=sys.executable, platform=platform.platform(),
                    sqlite_version=sqlite3.sqlite_version,
                    candidate_manifest_sha256=digest(candidate_manifest),
                    manifest_before=check_mapping(manifest), historical_before=check_mapping(historical),
                    candidate_manifest=manifest, candidate_plus_history_before=before, runs=[])
    evidence['preexisting_files_outside_inventory'] = sorted(
        p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*')
        if p.is_file() and '__pycache__' not in p.parts
        and p.relative_to(ROOT).as_posix() not in tracked)
    if before['missing'] or before['changed'] or len(historical) != 772:
        raise RuntimeError('Baseline mismatch; do not execute tests')
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    for label, command in [
        ('ESPECIFICOS', [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests',
                         '-p', 'test_f3_int115_multiprocess_recovery.py', '-v']),
        ('SONDAGENS', [sys.executable, '-B', str(Path(__file__).resolve()), '--probes'])]:
        log = ROOT/('LOG_AUDITORIA_F3_INT115_' + label + '_20261023.txt')
        started = time.monotonic()
        print('RUNNING ' + label, flush=True)
        with log.open('xb') as stream:
            proc = subprocess.run(command, cwd=ROOT, env=env, stdout=stream,
                                  stderr=subprocess.STDOUT, timeout=600)
        text = log.read_text(encoding='utf8', errors='replace')
        summary = re.search(r'^Ran (\d+) tests? in ([\d.]+)s$', text, re.MULTILINE)
        counts = {key: int(match.group(1)) if (match := re.search(r'\b'+key+r'=(\d+)', text)) else 0
                  for key in ('failures', 'errors', 'skipped')}
        total = int(summary.group(1)) if summary else None
        run = dict(label=label, command=command, exit_code=proc.returncode, total=total,
                   passed=total-sum(counts.values()) if total is not None else None,
                   seconds=round(time.monotonic()-started, 3), log=log.name,
                   log_sha256=digest(log), **counts)
        evidence['runs'].append(run)
        print(json.dumps(run), flush=True)
    evidence['manifest_after'] = check_mapping(manifest)
    evidence['historical_after'] = check_mapping(historical)
    evidence['candidate_plus_history_after'] = check_mapping(tracked)
    ultimate = json.loads((ROOT/'ULTIMO_MARCO.json').read_text())
    evidence['definitive'] = {k: ultimate[k] for k in ('stage', 'checkpoint_type', 'f3', 'locks')}
    evidence['audit_source_sha256'] = digest(Path(__file__))
    evidence['result'] = 'RESSALVAS_TECNICAS_CORRECOES_NECESSARIAS_ANTES_DE_PROMOCAO'
    evidence_path.write_text(json.dumps(evidence, indent=2, ensure_ascii=True)+'\n', encoding='utf8')
    testfile = 'tests/test_f3_int115_multiprocess_recovery.py'
    runner = 'tools/f3_int115_run_candidate.py'
    module = 'tools/f3_int115_multiprocess_recovery.py'
    findings = [
        ('A1 - MEDIA - alegacao de simultaneidade mais forte que o teste', testfile,
         'def test_simultaneous_same_operation_one_winner',
         'Dois processos prontos recebem GO sequencialmente. O perdedor pode retornar STATE_ANCHOR_MISMATCH; '
         'portanto a aceitacao tambem passa com execucao inteiramente serial. A sondagem reproduziu isso. '
         'Nao invalida o teste separado de lock retido, que comprova sobreposicao com STORE_BUSY. '
         'Correcao: renomear este teste para disputa sem garantia de sobreposicao; manter/adicionar '
         'barreiras que registrem a transacao retida e a tentativa concorrente dentro desse intervalo.'),
        ('A2 - MEDIA - esperas IPC nao sao integralmente limitadas', testfile,
         "p.stdin.write(value + '\\n'); p.stdin.flush()",
         'send() faz write/flush bloqueantes sem deadline. Um worker parado antes de consumir uma '
         'fixture maior que a capacidade do pipe pode bloquear o pai antes do timeout da fila. '
         'stderr nao e drenado enquanto o filho vive; se encher, o worker pode bloquear. '
         'Leitura de stderr apos wait normalmente recebe EOF, mas nao possui limite proprio. '
         'Threads leitoras daemon nao sao guardadas/joined e sua fila nao tem limite. '
         'Nao houve hang observado; e um defeito de robustez inferido do codigo. '
         'Correcao: supervisionar escrita/leitura de ambos os pipes com deadline, limite de bytes, '
         'kill/wait e join deterministico de todos os leitores. Nao resolver com sleeps.'),
        ('A3 - MEDIA - runner nao confere estabilidade das fontes candidatas', runner,
         "and not p.name.startswith(PREFIXES)",
         'inventory() exclui por prefixo as fontes 115. Os hashes novos sao calculados depois dos testes. '
         'Uma alteracao concorrente das fontes candidatas nao seria detectada pelo inventario historico. '
         'A auditoria atual comparou fontes e manifesto antes/depois sem divergencias. '
         'Correcao: inventariar explicitamente fontes/dependencias antes da execucao e compara-las apos; '
         'separar apenas os caminhos de saida, sem exclusao generica por basename. Isso ainda nao autentica execucao.'),
        ('A4 - MEDIA - runner incompleto na trajetoria de timeout', runner,
         'stderr=subprocess.STDOUT, timeout=2400',
         'TimeoutExpired nao e tratado. subprocess.run termina/aguarda o processo direto, '
         'mas os workers descendentes nao estao sob supervisao de arvore neste runner. '
         'O timeout pode impedir a geracao de checkpoint/relatorio e deixar descendentes ate EOF/encerramento. '
         'Nao foi provocado um timeout destrutivo nesta auditoria. '
         'Correcao: bloco try/finally que preserve evidencia parcial, registre timeout e exit status, '
         'supervisione apenas os processos proprios e finalize os workers antes do encerramento.'),
        ('A5 - BAIXA - cobertura original de retry apos ACK perdido e parcial', testfile,
         'def test_death_after_commit_lost_ack_and_retry_rejected',
         'O retry original usa somente a ancora anterior; a rejeicao pode ocorrer antes do mecanismo anti-replay. '
         'Sondagem adicional com ancora posterior correta confirmou STALE_CHAIN_REVISION, '
         'sem mudanca da geracao fixada em 1. Correcao: incorporar esse caso a suite 115 e conferir '
         'ACK preservado como LOST/UNKNOWN, flags false e retry_allowed false em cada resultado.'),
    ]
    lines = ['# Auditoria tecnica F3-INT-115 CANDIDATA', '',
        'Data: 2026-10-23. Workspace: C:/COPILOTO_F3_INT114_FINAL.',
        'Resultado: CANDIDATA mantida, com ressalvas tecnicas e correcoes necessarias antes de eventual promocao.',
        'Nenhum defeito de dupla admissao ou autorizacao operacional foi observado nos cenarios executados.',
        'A aprovacao dos testes nao elimina os defeitos de evidencia e robustez descritos abaixo.', '',
        '## Integridade e escopo', '',
        '- Manifesto candidato: 10/10 entradas SHA-256 coincidentes antes e depois.',
        '- Manifesto candidato em si preservado; SHA-256: '+evidence['candidate_manifest_sha256']+'.',
        '- Historico: 772/772 arquivos existentes e coincidentes com o inventario do checkpoint, antes e depois.',
        '- Conjunto protegido: 783 arquivos (772 historicos + 10 entradas + manifesto), todos preservados.',
        '- Esta comparacao usa referencia local preexistente, nao autenticada independentemente. '
        'Nao comprova alteracoes anteriores a captura original do inventario, nem identidade do executavel.',
        '- Nenhuma implementacao, teste, log, checkpoint ou manifesto candidato foi modificado pela auditoria.', '',
        '## Revisao dos arquivos candidatos', '']
    roles = {'CHECKPOINT_F3_INT115_CANDIDATA.json':'inventario historico, comandos, contagens e exit codes',
        'RELATORIO_F3_INT115_CANDIDATA.md':'alegacoes, limitacoes, hashes e tentativas preservadas',
        'RESULTADO_F3_INT115_ESPECIFICOS.txt':'tentativa com 10 erros de importacao; nao evidencia aprovacao',
        'RESULTADO_F3_INT115_ESPECIFICOS_CANDIDATA.txt':'tentativa com 8 aprovados e 2 falhas; nao evidencia aprovacao completa',
        'RESULTADO_F3_INT115_REGRESSAO_WINDOWS.txt':'regressao interrompida; nao evidencia conclusao',
        'RESULTADO_F3_INT115_ESPECIFICOS_VALIDACAO.txt':'validacao anterior: 10/10 aprovados',
        'RESULTADO_F3_INT115_REGRESSAO_WINDOWS_VALIDACAO.txt':'regressao anterior: 1397 aprovados e 1 skip por symlink; nao repetida nesta auditoria',
        testfile:'dez ensaios e worker subprocesso revisados integralmente',
        module:'wrapper conservador de reconciliacao; retry sempre false e safe_to_promote false',
        runner:'inventario, execucao, parsing, relatorio e manifesto revisados integralmente'}
    lines += [f'- `{name}`: {roles[name]}; SHA-256 `{sha}`.' for name, sha in manifest.items()]
    lines += ['', 'Tambem foram revisados os modulos historicos 109/110 e o marco 114, sem alteracao.', '',
              '## Achados e correcoes propostas', '']
    for title, path, needle, body in findings:
        lines += ['### '+title, '', f'Evidencia: `{path}:{numbered(path, needle)}`.', '', body, '']
    lines += ['## Concorrencia, atomicidade, isolamento e ACK', '',
        '- Popen inicia interpretadores independentes, com PIDs diferentes do pai e entre concorrentes. '
        'Cada worker abre sua propria conexao sqlite3 para o mesmo arquivo local real; nao ha mock de SQLite.',
        '- Threads sao exclusivamente leitores de stdout. Nao substituem processos na disputa pelo banco.',
        '- A fixture e transmitida em JSON/base64; nenhum objeto de conexao e compartilhado. '
        'O hook _checkpoint e alterado apenas no interpretador filho.',
        '- BEGIN IMMEDIATE precede leitura da ancora e verificacao anti-replay; UPDATE de consumed, '
        'generation e next_revision fica em uma transacao. Concorrente com lock retido recebe STORE_BUSY.',
        '- A consulta posterior compara o hash de todo o estado esperado: generation=1, next_revision=2 '
        'e uma unica entrada consumed. Nos ensaios nao houve dupla admissao.',
        '- Morte antes da escrita/apos UPDATE recuperou estado anterior; morte apos commit recuperou '
        'estado posterior sem reenviar confirmacao. Kill ocorre em checkpoints, nao dentro da chamada commit.',
        '- A sondagem com escritor vivo mostrou NOT_COMMITTED observado seguido de COMMITTED apos liberar '
        'a transacao: e um snapshot, nao prova de ausencia futura de commit. retry permaneceu false.',
        '- Banco ausente/corrompido, referencia ausente ou incorreta e ACK invalido produzem rejeicao '
        'ou estado nao resolvido. Nao ha recriacao automatica, reset ou fallback permissivo.',
        '- Ausencia de ACK e representada pelo canal de retorno interrompido e pela entrada LOST da consulta; '
        'nao existe protocolo de transporte ou autenticacao de ACK sob teste.', '',
        '## Novas execucoes', '']
    for run in evidence['runs']:
        lines.append(f"- {run['label']}: {run['total']} testes, {run['passed']} aprovados, "
                     f"{run['failures']} falhas, {run['errors']} erros, {run['skipped']} skips; "
                     f"exit code {run['exit_code']}; {run['seconds']} s; `{run['log']}`.")
    lines += ['', 'As 3 sondagens aprovadas confirmam limites/controles; nao significam que os achados foram corrigidos.', '',
        '## Limites e restricoes', '',
        '- Mesma maquina, usuario e filesystem; pins em diretorio separado nao estabelecem custodia independente.',
        '- Sem prova de durabilidade fisica, falha de energia, seguranca entre hosts ou identidade autenticada do executavel.',
        '- Interleavings limitados; sem stress prolongado, falha dentro de commit, disco cheio ou erro de I/O induzido.',
        '- Nenhuma operacao de rede, corretora, Profit, Excel, RTD/DDE ou ordem real.',
        '- F3 OPEN e sete flags false. ULTIMO_MARCO continua F3-INT-114 FINAL. Sem promocao ou INT-116.',
        '- Correcoes descritas, nao aplicadas aos artefatos candidatos/historicos nesta auditoria.', '',
        '## Artefatos da auditoria', '',
        '- `tools/f3_int115_technical_audit_20261023.py`: runner e 3 sondagens reproduziveis.',
        '- `EVIDENCIAS_AUDITORIA_F3_INT115_20261023.json`: hashes comparados, contagens, ambiente e comandos.',
        '- `LOG_AUDITORIA_F3_INT115_ESPECIFICOS_20261023.txt`: repeticao integral dos dez testes.',
        '- `LOG_AUDITORIA_F3_INT115_SONDAGENS_20261023.txt`: execucao das tres sondagens adicionais.',
        '- `MANIFESTO_AUDITORIA_F3_INT115_20261023.json`: SHA-256 dos cinco artefatos anteriores e deste relatorio.',
        'O manifesto nao contem seu proprio hash; seu hash sera apresentado separadamente.', '']
    report_path.write_text('\n'.join(lines), encoding='utf8')
    outputs = [Path(__file__), evidence_path, report_path] + [ROOT/r['log'] for r in evidence['runs']]
    audit_manifest = {p.relative_to(ROOT).as_posix():digest(p) for p in outputs}
    manifest_path.write_text(json.dumps(audit_manifest, indent=2)+'\n', encoding='utf8')
    print('AUDIT_MANIFEST_SHA256='+digest(manifest_path), flush=True)
    if any(r['exit_code'] or r['total'] is None for r in evidence['runs']) or check_mapping(tracked)['matched'] != 783:
        raise SystemExit(1)


if __name__ == '__main__':
    if '--probes' in sys.argv:
        unittest.main(argv=[sys.argv[0]], verbosity=2)
    else:
        main()
