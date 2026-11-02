"""Audita logs A14.5-R2 sem importar ou executar o projeto operacional.

Uso: python auditar_regressao.py normal.log otimizado.log [testes_por_modo]
Os arquivos .exit.txt devem acompanhar cada .log.
"""
import hashlib
import json
from pathlib import Path
import re
import sys


def audit_boundaries(root, modes=(0, 1)):
    """Confere os registros A12 produzidos por esta execucao isolada."""
    expected = {
        'a14_1_after_ack_repeat', 'a14_1_before_commit_repeat',
        'a14_2_positive_inner_kill_on_close',
        'test_death_after_local_ack_commit', 'test_death_after_pending_insert',
        'test_death_after_source_commit', 'test_death_after_source_update',
        'test_death_after_witness_commit', 'test_death_before_local_ack_commit',
        'test_death_before_source_commit', 'test_death_before_witness_commit',
        'test_releasing_boundary_without_death_commits_normally',
    }
    locks = {'authenticated_witness_verified', 'f3_resolved', 'flow_complete',
             'live_certified', 'native_prototype_authorized', 'orders_allowed',
             'strict_deadline_guaranteed'}
    failures, files = [], []
    for mode in modes:
        paths = sorted(Path(root).glob(f'a12_evidence_O{mode}_*/*.json'))
        names = []
        for path in paths:
            data = json.loads(path.read_bytes())
            name = data.get('test')
            names.append(name)
            errors = []
            operational = data.get('operational_locks', {})
            if set(operational) != locks or any(v is not False for v in operational.values()):
                errors.append('Bloqueios operacionais incompletos ou liberados')
            if (type(data.get('optimization')) is not int or data.get('optimization') != mode or
                    type(data.get('reached_boundary', {}).get('optimization')) is not int or
                    data.get('reached_boundary', {}).get('optimization') != mode):
                errors.append('Modo de otimizacao divergente')
            if data.get('runtime_modified') is not False or data.get('safety_cleanup_confirmed') is not True:
                errors.append('Runtime modificado ou limpeza nao confirmada')
            proofs = data.get('process_proofs', [])
            if not proofs or any(p.get('exit_confirmed') is not True for p in proofs):
                errors.append('Provas de encerramento ausentes ou incompletas')
            if data.get('release_control') is False:
                if (type(data.get('active_processes_before_safety')) is not int or
                        data.get('active_processes_before_safety') != 0):
                    errors.append('Contencao anterior a limpeza externa nao confirmada')
                if {p.get('role') for p in proofs} != {'owner','gate','bridge','worker'}:
                    errors.append('Papeis de processo incompletos')
                if any(p.get('observed_ns', float('inf')) >= data.get('safety_cleanup_started_ns', 0)
                       for p in proofs):
                    errors.append('Prova nao e anterior a limpeza externa')
                owned = data.get('all_owned_exit_proofs_before_safety', [])
                if not owned or any(p.get('exit_confirmed') is not True for p in owned):
                    errors.append('Provas do Job externo incompletas')
            elif name != 'test_releasing_boundary_without_death_commits_normally':
                errors.append('Controle de liberacao inesperado')
            failures.extend(f'{path}: {error}' for error in errors)
            files.append({'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                          'optimization': mode, 'test': name})
        if len(paths) != 12 or set(names) != expected:
            failures.append(f'Modo {mode}: esperados 12 registros distintos de fronteira')
    return {'accepted': not failures, 'failures': failures, 'files': files}


def audit(path, optimization, expected_tests=180):
    path = Path(path)
    text = path.read_text(encoding='utf-8-sig', errors='strict')
    failures = []
    def require(condition, message):
        if not condition:
            failures.append(message)
    exit_path = path.with_suffix('.exit.txt')
    require(exit_path.is_file() and exit_path.read_text(encoding='utf-8-sig').strip() == '0',
            'Codigo de saida ausente ou diferente de zero')
    summaries = re.findall(r'^Ran (\d+) tests? in ([\d.]+)s\s*$', text, re.M)
    require(len(summaries) == 1 and summaries[0][0] == str(expected_tests),
            f'Esperado um resumo com exatamente {expected_tests} testes')
    require(bool(re.search(r'^OK\s*\Z', text, re.M)), 'Resumo final nao e OK sem skips')
    require(not re.search(r'^(FAILED|ERROR:|FAIL:|Traceback)', text, re.M),
            'Log contem falha ou traceback')
    evidence = {}
    for line in text.splitlines():
        if '_EVIDENCE=' not in line:
            continue
        marker = re.search(r'([A-Z][A-Z0-9_]*_EVIDENCE)=', line)
        if marker is None:
            failures.append('Marcador de evidencia invalido')
            continue
        prefix, raw = marker.group(1), line[marker.end():]
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            failures.append('JSON invalido: ' + prefix)
            continue
        evidence.setdefault(prefix, []).append(row)
        require(type(row.get('optimization')) is int and row.get('optimization') == optimization,
                'Otimizacao divergente: ' + prefix)
        require(row.get('real_operations_authorized') is False,
                'Bloqueio de operacoes nao confirmado: ' + prefix)
    repeats = evidence.get('A14_5_REPEAT_EVIDENCE', [])
    exits = evidence.get('A14_4_EXIT_ORDER_EVIDENCE', [])
    expected = {f'a14_5_{order}_repeat_{i}'
                for order in ('worker_first', 'near_simultaneous')
                for i in (1, 2, 3)}
    require(len(repeats) == 6 and {r.get('label') for r in repeats} == expected,
            'As seis repeticoes A14.5 nao estao completas e unicas')
    require(len(exits) == 9, 'Esperadas nove evidencias A14.4/A14.5')
    by_label = {row.get('label'): row for row in exits}
    require(len(by_label) == 9, 'Rotulos de evidencia duplicados')
    strict_labels = {'a14_4_owner_first', 'a14_4_worker_first', 'a14_4_close_succession'}
    require(set(by_label) == expected | strict_labels, 'Rotulos inesperados ou ausentes')
    for row in exits:
        label = row.get('label')
        require(row.get('outer_cleanup_confirmed') is True and
                type(row.get('active_processes_after_cleanup')) is int and
                row.get('active_processes_after_cleanup') == 0,
                'Limpeza nao confirmada: ' + str(label))
        after = row.get('handles_after_outer_cleanup', {})
        require(set(after) == {'owner', 'gate', 'bridge', 'worker'} and
                all(v is True for v in after.values()),
                'Handles finais incompletos ou ativos: ' + str(label))
        require(row.get('runtime_modified') is False,
                'Runtime modificado: ' + str(label))
        before = row.get('handles_before_outer_cleanup', {})
        require(set(before) == {'owner', 'gate', 'bridge', 'worker'},
                'Handles anteriores incompletos: ' + str(label))
        observed = any(before.get(role) is False for role in ('gate', 'bridge'))
        require(row.get('survivor_observed_before_cleanup') is observed,
                'Classificacao de sobrevivencia inconsistente: ' + str(label))
        if label in expected:
            require(row.get('observational') is True,
                    'Repeticao deve ser observacional: ' + str(label))
            require(before.get('owner') is True and before.get('worker') is True,
                    'Encerramento dos alvos nao confirmado: ' + str(label))
        elif label in strict_labels:
            require(row.get('observational') is False,
                    'Controle A14.4 deve permanecer estrito: ' + str(label))
            if label == 'a14_4_owner_first':
                require(row.get('negative_control') is False and
                        all(v is True for v in before.values()),
                        'Contencao positiva nao confirmada')
            else:
                require(row.get('negative_control') is True and observed,
                        'Contraprova estrita sem sobrevivente: ' + str(label))
    for row in repeats:
        label = row.get('label')
        proof = by_label.get(label, {})
        require(row.get('observational') is True and
                row.get('survivor_not_assumed') is True and
                row.get('negative_control') is True and
                row.get('runtime_modified') is False,
                'Semantica observacional ausente: ' + str(label))
        require(proof.get('order') == row.get('order') and
                proof.get('negative_control') is True,
                'Repeticao sem evidencia correspondente: ' + str(label))
    return {
        'log': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'optimization': optimization, 'summary': summaries,
        'evidence_counts': {k: len(v) for k, v in evidence.items()},
        'survivors_observed_in_repeats': sum(
            by_label.get(label, {}).get('survivor_observed_before_cleanup') is True
            for label in expected),
        'accepted': not failures, 'failures': failures,
    }


if __name__ == '__main__':
    if len(sys.argv) not in (3, 4):
        raise SystemExit(__doc__)
    expected_tests = int(sys.argv[3]) if len(sys.argv) == 4 else 180
    result = {'f3': 'OPEN', 'offline': True, 'simulation_only': True,
              'real_operations_authorized': False,
              'scope': 'Auditoria dos logs locais; nao certifica producao',
              'modes': [audit(sys.argv[1], 0, expected_tests),
                        audit(sys.argv[2], 1, expected_tests)]}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(0 if all(m['accepted'] for m in result['modes']) else 1)
