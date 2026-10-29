"""Package every candidate byte and independent review evidence without promotion."""
import hashlib
import json
from pathlib import Path
import zipfile

WORK=Path(__file__).resolve().parent
OUT=WORK/'audit/F3_INT116_REVISAO_20261024'
ROOT=WORK/'f3_int116_work'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    data=json.loads((OUT/'RESULTADO.json').read_bytes())
    assert len(data['runs'])==2
    assert not data['base_changed_after'] and not data['candidate_changed_after']
    assert all(r['exit_code']==0 and r['failures']==r['errors']==0 and
               r['cleanup']['confirmed'] and r['cleanup']['active_processes']==0 and
               not r['cleanup']['live_io_threads'] for r in data['runs'])
    counts='\n'.join(f"- {r['label']}: {r['total']} testes, {r['passed']} aprovados, {r['skipped']} skipped, {r['failures']} falhas, {r['errors']} erros; {r['seconds']} s; exit code {r['exit_code']}." for r in data['runs'])
    report='''# Auditoria tecnica F3-INT-116 CANDIDATA — 24/10/2026

Parecer: evidencias favoraveis no escopo offline ensaiado; revisao humana pendente. Sem promocao automatica. F3 OPEN, sete flags false, offline e simulation_only; certification false. ULTIMO_MARCO continua F3-INT-115 FINAL.

## Integridade e alteracoes

874/874 entradas do manifesto da base FINAL verificadas. Todos os 875 arquivos da arvore extraida foram preservados byte a byte antes e depois dos testes, na base e na candidata. Zero arquivos herdados modificados ou removidos. Manifesto da candidata: 12/12 entradas corretas; sidecar SHA-256 correto. Sao 14 adicoes, listadas em ALTERACOES.json; tres sao fontes: audit/tools/f3_int116_commit_recovery.py, audit/tools/f3_int116_run_audit.py e audit/tests/test_f3_int116_commit_recovery.py. As outras 11 sao relatorio, manifestos e evidencias.

## Testes reexecutados

'''+counts+'''

Sem enfraquecimento ou alteracao de testes. Supervisao Windows com Job Object e identidades de processo: cleanup confirmado nas duas execucoes, zero processos ativos no Job e zero threads de IPC remanescentes. Essa evidencia cobre os descendentes supervisionados, nao uma afirmacao sobre todos os processos do computador.

## Recuperacao, atomicidade e replay

Controle normal confirma gravacao. Erro antes do commit, recusa COMMIT pelo authorizer SQLite e SQLITE_BUSY real provocado por leitor mantiveram o estado anterior integral apos fechamento e reabertura. Erro apos commit retornou STORE_ERROR, mas a reconciliacao observou o estado novo integral. Ambos os estados passam PRAGMA integrity_check e comparacao integral do payload. Replay com ancora antiga: STATE_ANCHOR_MISMATCH; com ancora atual: STALE_CHAIN_REVISION, sem mudar o estado. Ancora after divergente: RECONCILIATION_UNRESOLVED. Banco ausente nao e recriado. Retry permanece false; sete flags false e F3 OPEN sao conferidos nos resultados exercitados.

## Achados e limitacoes

- Nenhuma falha funcional ou regressao detectada no escopo executado; nenhuma correcao foi aplicada a candidata.
- Runner usa assert para invariantes e aprovacao de execucao. python -O remove essas verificacoes. A execucao desta auditoria foi sem -O; recomenda-se substituir por verificacoes explicitas numa futura revisao, sem alterar a candidata auditada.
- Runner depende do caminho absoluto C:/COPILOTO_F3_INT115_FINAL e recusa sobrescrever EVIDENCIAS_F3_INT116. Reexecucao exige pasta nova ou harness separado; esta auditoria usou harness separado preservado no pacote.
- Patch de _connect e global no processo: uso apenas em testes isolados sem concorrencia de threads.
- As falhas controladas na fronteira da chamada nao demonstram morte dentro do motor SQLite. O caso de leitor demonstra erro real de commit, sem comprovar resistencia a perda de energia ou durabilidade fisica.
- STORE_ERROR nao determina sozinho se houve commit. Reconciliacao exige ancoras retidas previamente; nao autoriza retry. Restaurar banco e ancoras juntos pode derrotar deteccao de rollback.
- Hashes locais e ancoras do mesmo usuario nao constituem custodia autenticada, procedencia independente, entrega exatamente uma vez ou garantia entre computadores.
- Um teste de symlink permanece skipped por falta de permissao no Windows; nao foi contornado.
- A base disponivel e a arvore extraida: nenhum ZIP original FINAL foi fornecido para verificar sua origem/CRC/hash.

## Pacote

ZIP inclui toda a arvore f3_int116_work (889 arquivos), todas as novas evidencias desta revisao e os dois scripts desta auditoria. Nao inclui arquivos alheios da raiz do projeto. MANIFESTO_PACOTE.json fixa cada arquivo do payload; o ZIP e reaberto, testado por CRC e cada membro comparado por SHA-256. O hash do ZIP fica em sidecar externo, evitando autorreferencia.

Status: CANDIDATA; aguardar revisao antes de qualquer promocao para FINAL. Nenhuma operacao real autorizada.
'''
    (OUT/'RELATORIO_AUDITORIA.md').write_text(report,encoding='utf8')
    (OUT/'ALTERACOES.json').write_text(json.dumps({k:data[k] for k in ('added','modified','removed')},indent=2),encoding='utf8')
    files={f'f3_int116_work/{p.relative_to(ROOT).as_posix()}':p for p in ROOT.rglob('*') if p.is_file()}
    files.update({f'revisao_20261024/{p.relative_to(OUT).as_posix()}':p for p in OUT.rglob('*') if p.is_file()})
    for n in ('audit_f3_int116_review_20261024.py','package_f3_int116_review_20261024.py'):
        files['revisao_20261024/'+n]=WORK/n
    pins={n:sha(p) for n,p in sorted(files.items())}
    package_manifest=json.dumps(dict(stage='F3-INT-116',status='CANDIDATA',promoted=False,f3='OPEN',files_sha256=pins),indent=2).encode('utf8')
    target=WORK/'audit/F3_INT116_CANDIDATA_COMPLETA_REVISAO_20261024.zip'
    with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for n,p in sorted(files.items()):z.write(p,n)
        z.writestr('MANIFESTO_PACOTE.json',package_manifest)
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        assert len(z.namelist())==len(pins)+1
        for n,h in pins.items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
    digest=sha(target)
    Path(str(target)+'.sha256').write_text(digest+'  '+target.name+'\n',encoding='ascii')
    (WORK/'audit/F3_INT116_VERIFICACAO_PACOTE_20261024.json').write_text(json.dumps(dict(zip=str(target),sha256=digest,payload_files=len(pins),candidate_files=sum(n.startswith('f3_int116_work/') for n in pins),crc_ok=True,all_member_hashes_ok=True),indent=2),encoding='utf8')
    print(str(target));print(digest)

if __name__=='__main__':main()
