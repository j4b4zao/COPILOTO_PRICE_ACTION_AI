"""Offline Windows evidence runner for F3-INT-115 CANDIDATA.

Run from audit with Python -B. Never finalizes or changes ULTIMO_MARCO.
Logs and evidence are local self-recorded observations, not attestation.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PREFIXES = ('f3_int115_', 'test_f3_int115_', 'RESULTADO_F3_INT115_',
            'RELATORIO_F3_INT115_', 'CHECKPOINT_F3_INT115_', 'MANIFESTO_F3_INT115_')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory():
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in ROOT.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts
            and not p.name.startswith(PREFIXES)}


def main():
    before = inventory()
    evidence = dict(stage='F3-INT-115', checkpoint_type='CANDIDATA', f3='OPEN',
                    previous_definitive='F3-INT-114 FINAL', offline=True,
                    simulation_only=True, certification=False,
                    independent_custody_demonstrated=False,
                    physical_durability_demonstrated=False,
                    cross_host_safety_demonstrated=False, runs=[])
    from tools.f3_int114_custody_recovery import LOCKS
    evidence['locks'] = dict.fromkeys(LOCKS, False)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    for label, pattern in [('ESPECIFICOS_VALIDACAO', 'test_f3_int115_multiprocess_recovery.py'),
                           ('REGRESSAO_WINDOWS_VALIDACAO', 'test_*.py')]:
        log = ROOT / ('RESULTADO_F3_INT115_' + label + '.txt')
        started = time.monotonic()
        command = [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-p', pattern, '-v']
        print('RUNNING ' + label, flush=True)
        with log.open('xb') as output:
            result = subprocess.run(command, cwd=ROOT, env=env, stdout=output,
                                    stderr=subprocess.STDOUT, timeout=2400)
        text = log.read_text(encoding='utf8', errors='replace')
        match = re.search(r'Ran (\d+) tests? in ([\d.]+)s', text)
        counts = {key: int(re.search(key + r'=(\d+)', text).group(1))
                  if re.search(key + r'=(\d+)', text) else 0
                  for key in ('failures', 'errors', 'skipped', 'expected failures', 'unexpected successes')}
        total = int(match.group(1)) if match else None
        run = dict(label=label, command=command, exit_code=result.returncode,
                   total=total, passed=(total-counts['failures']-counts['errors']-counts['skipped']
                                       -counts['expected failures']-counts['unexpected successes']) if total is not None else None,
                   seconds=round(time.monotonic()-started, 3), log=log.name, **counts)
        evidence['runs'].append(run)
        print(json.dumps(run), flush=True)
    after = inventory()
    evidence['historical_inventory_before_runner'] = before
    evidence['historical_files_changed_during_runner'] = sorted(k for k in set(before)|set(after)
                                                              if before.get(k) != after.get(k))
    checkpoint = ROOT / 'CHECKPOINT_F3_INT115_CANDIDATA.json'
    checkpoint.write_text(json.dumps(evidence, indent=2, ensure_ascii=True)+'\n', encoding='utf8')
    new = sorted(p for p in ROOT.rglob('*') if p.is_file() and p.name.startswith(PREFIXES)
                 and '__pycache__' not in p.parts)
    report = ROOT / 'RELATORIO_F3_INT115_CANDIDATA.md'
    lines = ['# F3-INT-115 CANDIDATA', '',
             'Base validada: C:/COPILOTO_F3_INT114_FINAL; ultimo marco definitivo F3-INT-114 FINAL.',
             'F3 OPEN; sete flags false; somente fixtures offline locais; sem ordens, adaptadores ou rede.',
             'ULTIMO_MARCO e arquivos historicos preservados. Sem promocao para FINAL ou INT-116.', '',
             '## Tentativas preservadas', '',
             'Ensaio inicial: 10 testes, 8 aprovados, 2 falhas por fixtures regeneradas divergentes.',
             'Segunda tentativa: 10 erros por importacao base64 ausente; regressao interrompida pelo operador.',
             'Ambos os problemas do harness foram corrigidos antes da validacao abaixo; logs preservados.', '',
             '## Implementacao', '',
             'Reutiliza admissao SQLite 109 e reconciliacao 110. Processos Python independentes,',
             'cada um com sua conexao SQLite; barreiras por stdin/stdout e timeout, sem sleeps de sincronizacao.',
             'Threads existem apenas para leitura limitada das saidas dos processos.',
             'Disputa simultanea: exatamente um vencedor; perdedor BUSY ou ancora antiga.',
             'Disputa controlada: transacao IMMEDIATE retida, concorrente BUSY e retry antigo rejeitado.',
             'Interrupcoes reais: processo terminado pelo pai antes da escrita, apos escrita e apos commit.',
             'Nova observacao em outro processo distingue COMMITTED, NOT_COMMITTED e UNRESOLVED.',
             'ACK perdido permanece LOST; nenhum resultado autoriza retry ou operacao real.', '',
             '## Execucao Windows', '']
    for run in evidence['runs']:
        lines.append(f"- {run['label']}: {run['total']} testes; {run['passed']} aprovados; "
                     f"{run['failures']} falhas; {run['errors']} erros; {run['skipped']} skips; "
                     f"exit code {run['exit_code']}; {run['seconds']} s. Log: {run['log']}.")
    lines += ['', 'Inventario historico comparado antes/depois do runner: ' +
              str(len(before)) + ' arquivos; alteracoes: ' +
              str(evidence['historical_files_changed_during_runner']) + '.', '',
              '## Limites', '',
              '- Evidencia local em uma maquina e filesystem; nenhuma seguranca entre computadores demonstrada.',
              '- Kill de processo nao equivale a queda de energia, falha de SO, disco ou durabilidade fisica.',
              '- Pins precomputados antes dos escritores ficam em pasta irma da pasta SQLite e sao comparados byte a byte.',
              '  Mesmo usuario e permissoes: separacao de caminhos nao demonstra custodia independente.',
              '- Manifestos ficam fora das pastas temporarias do banco, mas no mesmo dominio de usuario.',
              '- Hashes e executavel informados pelo runner nao autenticam identidade ou origem independentemente.',
              '- Ausencia de ACK nao comprova ausencia de commit; pins invalidos, banco ausente/corrompido ou estado divergente falham fechados.',
              '- Nenhuma entrega exatamente uma vez, deadline estrito ou resistencia a rollback conjunto e certificada.',
              '- Ensaios limitados aos interleavings exercitados, nao prova exaustiva.', '',
              '## Arquivos novos e SHA-256', '',
              'Nenhum arquivo historico modificado. Hashes abaixo excluem este relatorio e o manifesto para evitar autorreferencia.', '']
    lines += [f'- `{p.relative_to(ROOT).as_posix()}`: `{sha(p)}`' for p in new if p != report]
    report.write_text('\n'.join(lines)+'\n', encoding='utf8')
    manifest = {p.relative_to(ROOT).as_posix(): sha(p) for p in ROOT.rglob('*')
                if p.is_file() and p.name.startswith(PREFIXES) and '__pycache__' not in p.parts
                and not p.name.startswith('MANIFESTO_F3_INT115_')}
    (ROOT / 'MANIFESTO_F3_INT115_CANDIDATA.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf8')
    if any(r['exit_code'] != 0 or r['total'] is None for r in evidence['runs']) or evidence['historical_files_changed_during_runner']:
        raise SystemExit(1)


if __name__ == '__main__':
    sys.path.insert(0, str(ROOT))
    main()

