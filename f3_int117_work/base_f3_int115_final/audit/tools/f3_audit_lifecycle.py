"""Local unittest evidence and reproducible package creation. No external I/O."""
import contextlib
import hashlib
import json
from pathlib import Path
import sys
import time
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LOCKS = ('orders_allowed', 'live_certified', 'flow_complete', 'f3_resolved',
         'native_prototype_authorized', 'strict_deadline_guaranteed',
         'authenticated_witness_verified')


def run(pattern, log):
    started = time.monotonic()
    with (ROOT / log).open('w', encoding='utf-8') as stream:
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
            suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'), pattern=pattern)
            result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    summary = dict(tests=result.testsRun, failures=len(result.failures),
                   errors=len(result.errors), skipped=len(result.skipped),
                   seconds=round(time.monotonic()-started, 3), log=log)
    print(json.dumps(summary), flush=True)
    if not result.wasSuccessful() or result.skipped or not result.testsRun:
        raise RuntimeError('Audit incomplete: inspect ' + log)
    return summary


def finish(stage, description, next_step):
    new = run('test_f3_int' + str(stage) + '*.py', f'LOG_F3_INT{stage}_NOVOS.txt')
    full = run('test*.py', f'LOG_F3_INT{stage}_REGRESSAO.txt')
    state = dict(last_completed=f'F3-INT-{stage}', next_step=next_step,
                 f3='OPEN', simulation_only=True, offline=True,
                 certification=False, locks={name: False for name in LOCKS},
                 new_tests=new, regression=full,
                 pending=['Autenticidade, consenso, persistencia e fencing reais nao verificados.'])
    text = (f'# F3-INT-{stage}\n\n{description}\n\n'
            f'Testes novos: {new["tests"]}/{new["tests"]}. '
            f'Regressao integral da auditoria isolada: {full["tests"]}/{full["tests"]}.\n\n'
            'F3=OPEN. Sete bloqueios operacionais permanecem false: '
            + ', '.join(LOCKS) + '.\n\n'
            'Todos os pins, digests, membros e votos sao fixtures do chamador. '
            'Resultados simulados nao certificam autenticidade, consenso, persistencia, '
            'independencia de testemunhas, fencing nativo ou operacao real. '
            'Nenhuma conexao com sistemas reais ou envio de ordens.\n\n'
            'Escopo da regressao: todos os testes do pacote F3 isolado; '
            'a suite operacional do repositorio principal nao foi executada.\n\n'
            f'Proximo: {next_step}.\n')
    (ROOT / f'RELATORIO_F3_INT{stage}.md').write_text(text, encoding='utf-8')
    (ROOT / f'CHECKPOINT_F3_INT{stage}.md').write_text(text, encoding='utf-8')
    encoded = json.dumps(state, ensure_ascii=False, indent=2) + '\n'
    (ROOT / f'CHECKPOINT_F3_INT{stage}.json').write_text(encoded, encoding='utf-8')
    (ROOT / 'ULTIMO_MARCO.json').write_text(encoded, encoding='utf-8')
    manifest_name = f'SHA256_F3_INT{stage}.txt'
    files = sorted(p for p in ROOT.rglob('*') if p.is_file()
                   and '__pycache__' not in p.parts and p.suffix != '.zip'
                   and p.name != manifest_name)
    manifest = ''.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  '
                       + p.relative_to(ROOT).as_posix() + '\n' for p in files)
    (ROOT / manifest_name).write_text(manifest, encoding='utf-8')
    package = ROOT.parent / f'PACOTE_AUDITORIA_F3_INT{stage}_LOCAL.zip'
    with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED) as archive:
        for p in files + [ROOT / manifest_name]:
            archive.write(p, p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(package) as archive:
        if archive.testzip() is not None:
            raise RuntimeError('ZIP integrity failure')
        for line in manifest.splitlines():
            digest, name = line.split('  ', 1)
            if hashlib.sha256(archive.read(name)).hexdigest() != digest:
                raise RuntimeError('Manifest mismatch: ' + name)
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    package.with_suffix('.zip.sha256').write_text(digest + '  ' + package.name + '\n', encoding='ascii')
    print('PACKAGE', package.name, 'SHA256', digest, flush=True)


if __name__ == '__main__':
    sys.path.insert(0, str(ROOT))
    finish(int(sys.argv[1]), sys.argv[2], sys.argv[3])
