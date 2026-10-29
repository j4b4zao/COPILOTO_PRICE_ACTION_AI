"""Validação somente-leitura da F3-INT-98. Uso: python VALIDAR_F3_INT98.py PACOTE_AUDITORIA_F3_INT98_CANDIDATO.zip"""
import hashlib, json, pathlib, subprocess, sys, tempfile, zipfile, datetime

LOCKS = ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified')

def main():
    if len(sys.argv)!=2: raise SystemExit('Uso: python VALIDAR_F3_INT98.py <pacote.zip>')
    package=pathlib.Path(sys.argv[1]).resolve()
    if not package.is_file(): raise SystemExit('Pacote nao encontrado: '+str(package))
    report=package.with_name('RESULTADO_VALIDACAO_F3_INT98.txt')
    with report.open('w',encoding='utf-8') as out:
        def log(s): print(s,flush=True);out.write(s+'\n');out.flush()
        log('VALIDACAO F3-INT-98 | '+datetime.datetime.now().isoformat())
        log('Pacote: '+str(package));log('SHA256: '+hashlib.sha256(package.read_bytes()).hexdigest())
        with zipfile.ZipFile(package) as z:
            names=z.namelist()
            if z.testzip() is not None: raise ValueError('ZIP com membro corrompido')
            if len(names)!=len(set(names)): raise ValueError('Nomes duplicados no ZIP')
            if any(n.startswith('/') or '\\' in n or '..' in pathlib.PurePosixPath(n).parts for n in names): raise ValueError('Caminho inseguro no ZIP')
            state=json.loads(z.read('audit/ULTIMO_MARCO.json'))
            if state['f3']!='OPEN' or not state['simulation_only'] or not state['offline'] or any(state['locks'].get(k) is not False for k in LOCKS):
                raise ValueError('Flags de seguranca inesperados')
            log('ZIP e flags: OK; ultimo marco oficial no pacote: '+state['last_completed'])
            with tempfile.TemporaryDirectory(prefix='f3_int98_validate_') as tmp:
                z.extractall(tmp)
                root=pathlib.Path(tmp)/'audit'
                for label,pattern in [('NOVOS','test_f3_int98*.py'),('REGRESSAO','test*.py')]:
                    log('INICIO '+label)
                    cmd=[sys.executable,'-m','unittest','discover','-s','tests','-p',pattern,'-q']
                    env=__import__('os').environ.copy();env['PYTHONPATH']=str(root)
                    with tempfile.TemporaryFile(mode='w+t',encoding='utf-8') as captured:
                        proc=subprocess.run(cmd,cwd=root,stdout=captured,stderr=subprocess.STDOUT,env=env)
                        captured.seek(0);output=captured.read()
                    log(output[-12000:]);log('EXIT '+label+': '+str(proc.returncode))
                    if proc.returncode: log('VALIDACAO NAO APROVADA');return 1
                log('TESTES NOVOS E REGRESSAO COMPLETA APROVADOS NESTA EXECUCAO')
    return 0
if __name__=='__main__': sys.exit(main())
