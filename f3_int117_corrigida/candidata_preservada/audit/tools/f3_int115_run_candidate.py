"""F3-INT-115 corrected candidate runner. Offline Windows only; never promotes."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.f3_int115_process_control import run_supervised
from tools.f3_int114_custody_recovery import LOCKS


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_inventory(root=ROOT):
    # All Python sources and dependencies, including 115 and retained revisions.
    # Only Python bytecode cache directories are excluded, never source prefixes.
    return {p.relative_to(root).as_posix(): sha(p) for p in sorted(root.rglob('*.py'))
            if '__pycache__' not in p.parts and p.is_file()}


def compare_inventories(before, after):
    return sorted(k for k in set(before)|set(after) if before.get(k) != after.get(k))


def summarize(text):
    matches = list(re.finditer(r'^Ran (\d+) tests? in [\d.]+s\r?$', text, re.MULTILINE))
    if not matches:
        return dict(total=None, passed=None, failures=0, errors=0, skipped=0)
    footer = text[matches[-1].end():].strip()
    outcome = re.search(r'^(OK|FAILED)(?: \(([^\n]*)\))?\s*$', footer, re.MULTILINE)
    if outcome is None:
        return dict(total=None, passed=None, failures=0, errors=0, skipped=0)
    counts = {key: int(m.group(1)) if (m := re.search(r'\b'+key+r'=(\d+)', outcome.group(2) or '')) else 0
              for key in ('failures','errors','skipped')}
    total = int(matches[-1].group(1))
    return dict(total=total, passed=total-sum(counts.values()), **counts)


def check_pins(pins, root=ROOT):
    return sorted(name for name, expected in pins.items()
                  if not (root/name).is_file() or sha(root/name) != expected)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='F3_INT115_CANDIDATA_CORRIGIDA_20261023')
    parser.add_argument('--control-only', action='store_true')
    args = parser.parse_args()
    # A direct child directory is the only accepted output location.
    if Path(args.output).name != args.output or args.output in ('.','..'):
        raise ValueError('Output must be a new direct directory name')
    out = ROOT/args.output
    out.mkdir()  # No overwriting historical evidence.
    historical = json.loads((ROOT/'CHECKPOINT_F3_INT115_CANDIDATA.json').read_text())['historical_inventory_before_runner']
    archive = ROOT/'PRESERVADO_F3_INT115_PRE_CORRECAO_20261023'
    old_manifest = json.loads((archive/'MANIFESTO_F3_INT115_CANDIDATA.json').read_text())
    if len(historical) != 772 or check_pins(historical) or check_pins(old_manifest, archive):
        raise RuntimeError('Historical/archived candidate integrity failure')
    before = source_inventory()
    previous = {p.relative_to(ROOT).as_posix():sha(p) for p in ROOT.rglob('*')
                if p.is_file() and '__pycache__' not in p.parts and out not in p.parents}
    evidence = dict(stage='F3-INT-115', checkpoint_type='CANDIDATA CORRIGIDA', f3='OPEN',
        simulation_only=True, offline=True, certification=False, previous_definitive='F3-INT-114 FINAL',
        locks=dict.fromkeys(LOCKS,False), sources_before=before, runs=[], exception=None,
        modified_files=[{'path':name, 'before_sha256':old_manifest[name], 'after_sha256':sha(ROOT/name),
                         'preserved_copy':str((archive/name).relative_to(ROOT)).replace('\\','/')}
                        for name in ('tests/test_f3_int115_multiprocess_recovery.py','tools/f3_int115_run_candidate.py')],
        created_code=['tools/f3_int115_process_control.py','tests/test_f3_int115_process_control.py'])
    (out/'FONTES_ANTES.json').write_text(json.dumps(before,indent=2)+'\n',encoding='utf8')
    try:
        cases = [('CONTROLES', 'test_f3_int115_process_control.py')] if args.control_only else [
            ('ESPECIFICOS','test_f3_int115_*.py'), ('REGRESSAO_COMPLETA','test_*.py')]
        for label, pattern in cases:
            command = [sys.executable,'-B','-m','unittest','discover','-s','tests','-p',pattern,'-v']
            print('RUNNING '+label, flush=True)
            result = run_supervised(command,cwd=ROOT,log=out/(label+'.log'),timeout=2400)
            result.update(label=label, **summarize((out/(label+'.log')).read_text(encoding='utf8',errors='replace')))
            result['sources_changed'] = compare_inventories(before, source_inventory())
            evidence['runs'].append(result)
            (out/'EXECUCOES_PARCIAIS.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf8')
            print(json.dumps(result), flush=True)
            if result['timed_out'] or result['exception'] or result['sources_changed'] or result['exit_code'] != 0 or result['total'] is None:
                break
    except BaseException as error:
        evidence['exception'] = repr(error)
    finally:
        evidence['sources_after'] = source_inventory()
        evidence['sources_changed'] = compare_inventories(before,evidence['sources_after'])
        evidence['historical_count'] = len(historical)
        evidence['historical_changed'] = check_pins(historical)
        evidence['archived_candidate_changed'] = check_pins(old_manifest, archive)
        evidence['preexisting_changed_during_execution'] = check_pins(previous)
        evidence['success'] = (evidence['exception'] is None and len(evidence['runs']) == len(cases)
            and not evidence['sources_changed'] and not evidence['historical_changed']
            and not evidence['archived_candidate_changed'] and not evidence['preexisting_changed_during_execution']
            and all(r['exit_code']==0 and not r['timed_out'] and not r['exception']
                    and r['total'] is not None and r['cleanup'] is not None
                    and r['cleanup']['active_processes']==0 for r in evidence['runs']))
        (out/'CHECKPOINT_CANDIDATA_CORRIGIDA.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf8')
        lines = ['# F3-INT-115 CANDIDATA CORRIGIDA', '',
            'Resultado da validacao: '+str(evidence['success'])+'. Apenas revisao; sem promocao para FINAL.',
            'F3 OPEN; sete flags false; offline/simulacao. ULTIMO_MARCO permanece F3-INT-114 FINAL.', '',
            '## Cinco correcoes implementadas', '',
            '1. Concorrencia: escritor retido em BEGIN IMMEDIATE; concorrente deve retornar STORE_BUSY antes de CONTINUE. '
            'STATE_ANCHOR_MISMATCH nao e aceito como prova de sobreposicao.',
            '2. IPC: deadlines absolutos/watchdog por processo, write supervisionado, stdout/stderr drenados em paralelo, '
            'limites de bytes/filas, kill e join dos leitores/escritores. Entrada do worker tambem esta sob watchdog externo.',
            '3. SHA-256: todas as fontes Python, inclusive 115 e dependencias, fixadas antes e comparadas apos cada execucao '
            'e no finally. Alteracao, adicao e exclusao falham fechadas.',
            '4. Timeout: Job Objects Windows com KILL_ON_JOB_CLOSE; gate impede execucao antes da contencao. '
            'Descendentes herdam o Job; timeout preserva log parcial e execution.json; finally encerra a arvore e confere '
            'zero processos ativos/threads de IPC. Falha de contencao nao usa fallback permissivo.',
            '5. ACK/replay: testes com ancora atual e anterior, dois retries concorrentes, ACK UNKNOWN/LOST/RECEIVED, '
            'referencias divergentes, escritor pendente e rollback apos limpeza do supervisor; consultas mantem retry false.', '',
            '## Arquivos alterados', '']
        for item in evidence['modified_files']:
            lines += [f"- `{item['path']}`: `{item['before_sha256']}` -> `{item['after_sha256']}`; "
                      f"copia original: `{item['preserved_copy']}`."]
        lines += ['', 'Novos arquivos de codigo: '+', '.join(evidence['created_code'])+'.',
            'A candidata anterior completa foi preservada byte a byte no diretorio PRESERVADO_F3_INT115_PRE_CORRECAO_20261023.',
            'O manifesto candidato antigo continua descrevendo a revisao anterior; valide-o nesse diretorio preservado.', '',
            '## Testes e evidencias', '']
        for run in evidence['runs']:
            lines += [f"- {run['label']}: {run['total']} testes; {run['passed']} aprovados, {run['failures']} falhas, "
                      f"{run['errors']} erros, {run['skipped']} skips; exit code {run['exit_code']}; "
                      f"timeout={run['timed_out']}; {run['seconds']} s; cleanup={run['cleanup']}; "
                      f"fontes alteradas={run['sources_changed']}."]
        lines += ['', 'Testes de controle provocam bloqueio de stdin, falta de stdout, stderr volumoso, overflow, '
            'timeout de espera, timeout com descendente e saida do pai deixando descendente. '
            'Tambem testam deteccao de mudanca/exclusao/adicao de fonte e footer incompleto.',
            'O skip esperado da regressao e symlink sem permissao; consulte a saida para a ocorrencia real.', '',
            '772 arquivos historicos: divergencias='+repr(evidence['historical_changed'])+'.',
            'Candidata anterior arquivada: divergencias='+repr(evidence['archived_candidate_changed'])+'.',
            'Arquivos preexistentes durante a execucao: divergencias='+repr(evidence['preexisting_changed_during_execution'])+'.',
            'Fontes alteradas durante execucao: '+repr(evidence['sources_changed'])+'.',
            'Excecao do runner: '+repr(evidence['exception'])+'.', '',
            '## Limites', '',
            '- Deadlines sao de supervisao local e podem sofrer atraso do SO; nao ha garantia de tempo real.',
            '- Contencao usa APIs locais Windows; falha de SO/kernel ou processo hostil com privilegio superior nao foi validada.',
            '- Hash antes/depois nao detecta alteracao transitoria restaurada e nao autentica executavel/custodia independentemente.',
            '- Sem prova de durabilidade fisica, seguranca entre computadores ou entrega exatamente uma vez.',
            '- Kill nos checkpoints nao equivale a falha dentro de commit ou queda de energia.',
            '- Sem rede, corretora, Profit, Excel, RTD/DDE, ordens reais ou INT-116.',
            '- Logs e manifesto desta revisao sao novos; relatorios/checkpoints anteriores nao foram substituidos.', '']
        (out/'RELATORIO_CANDIDATA_CORRIGIDA.md').write_text('\n'.join(lines),encoding='utf8')
        paths = set([ROOT/item['path'] for item in evidence['modified_files']] +
                    [ROOT/name for name in evidence['created_code']])
        paths.update(p for p in out.rglob('*') if p.is_file())
        paths.update(p for p in archive.rglob('*') if p.is_file())
        manifest = {p.relative_to(ROOT).as_posix():sha(p) for p in sorted(paths)}
        (out/'MANIFESTO_SHA256.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
        print('RESULT='+str(evidence['success'])+' OUTPUT='+str(out),flush=True)
    if not evidence['success']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
