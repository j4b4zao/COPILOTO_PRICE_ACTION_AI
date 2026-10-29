"""Pre-fix reproductions and handle-pinned diagnosis; no candidate edits."""
from pathlib import Path
import ctypes
from ctypes import wintypes as W
import hashlib
import json
import sys
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from tools import f3_int115_process_control as c
import test_f3_int115_process_control as old

K=c.K
K.GetProcessTimes.argtypes=[W.HANDLE,ctypes.POINTER(W.FILETIME),ctypes.POINTER(W.FILETIME),ctypes.POINTER(W.FILETIME),ctypes.POINTER(W.FILETIME)]
K.GetProcessTimes.restype=W.BOOL

def identity(handle,pid,ppid=None):
    times=[W.FILETIME() for _ in range(4)]
    c.wincheck(K.GetProcessTimes(handle,*[ctypes.byref(t) for t in times]))
    return dict(pid=pid,ppid=ppid,creation_100ns=(times[0].dwHighDateTime<<32)|times[0].dwLowDateTime)


def main():
    out=ROOT/'F3_INT115_INVESTIGACAO_IDENTIDADE_20261023'
    out.mkdir()
    full=(ROOT/'F3_INT115_REVALIDACAO_FINAL_20261023/REGRESSAO_COMPLETA.log').read_bytes()
    lines=full.decode('utf8',errors='replace').splitlines()
    (out/'LEITURA_LOG_COMPLETO.json').write_text(json.dumps(dict(bytes=len(full),lines=len(lines),
        sha256=hashlib.sha256(full).hexdigest(),lines_examined=len(lines),
        failure_lines=[dict(line=i+1,text=t) for i,t in enumerate(lines) if 'FAIL' in t or 'AssertionError' in t],
        ignored_lines=[dict(line=i+1,text=t) for i,t in enumerate(lines) if "skipped '" in t]),indent=2)+'\n')
    name='test_root_exit_still_cleans_living_descendant'
    runs=[]
    with (out/'REPETICAO_TESTE_ORIGINAL.log').open('x',encoding='utf8') as stream:
        for n in range(50):
            stream.write('ITERATION '+str(n)+'\n');stream.flush()
            result=unittest.TextTestRunner(stream=stream,verbosity=2).run(old.ProcessControlTests(name))
            row=dict(iteration=n,passed=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors))
            runs.append(row)
            print(json.dumps(row),flush=True)
    (out/'REPETICAO_TESTE_ORIGINAL.json').write_text(json.dumps(runs,indent=2)+'\n')
    evidence=[]
    for n in range(100):
        child=c.Peer([sys.executable,'-B','-c',
            "import subprocess,sys,json,os; p=subprocess.Popen([sys.executable,'-B','-c',"+repr(old.STALL)+"]); "
            "print(json.dumps({'pid':p.pid,'ppid':os.getpid()}),flush=True); sys.stdin.readline()"],cwd=ROOT,timeout=15)
        h=None
        try:
            record=child.recv()
            h=c.wincheck(K.OpenProcess(0x100000|0x1000,False,record['pid']))
            pinned=identity(h,record['pid'],record['ppid'])
            alive_before=K.WaitForSingleObject(h,0)==258
            child.send('EXIT')
            exit_code=child.wait()
            alive_after_parent=K.WaitForSingleObject(h,0)==258
            started=time.perf_counter_ns()
            child.close()
            after_close_ns=time.perf_counter_ns()
            wait_immediate=K.WaitForSingleObject(h,0)
            generic_pid_alive=c.process_running(record['pid'])
            same=None
            current=K.OpenProcess(0x100000|0x1000,False,record['pid'])
            if current:
                try:
                    observed=identity(current,record['pid'])
                    same=observed['creation_100ns']==pinned['creation_100ns']
                finally:K.CloseHandle(current)
            wait_final=K.WaitForSingleObject(h,5000)
            row=dict(iteration=n,root_pid=child.pid,root_exit=exit_code,descendant=pinned,
                alive_before_parent_exit=alive_before,alive_after_parent_exit=alive_after_parent,
                old_cleanup=child.cleanup,wait_immediately_after_close=wait_immediate,
                generic_pid_running=generic_pid_alive,same_creation_identity=same,
                wait_final=wait_final,cleanup_ns=after_close_ns-started,
                final_confirmation_ns=time.perf_counter_ns()-after_close_ns)
            evidence.append(row)
            with (out/'IDENTIDADE_PINADA.jsonl').open('a',encoding='utf8') as stream:
                stream.write(json.dumps(row)+'\n')
            if wait_final!=0:raise RuntimeError('Pinned descendant termination not confirmed')
        finally:
            child.close()
            if h:K.CloseHandle(h)
    summary=dict(original_runs=len(runs),original_failures=sum(x['failures'] for x in runs),
        original_errors=sum(x['errors'] for x in runs),pinned_runs=len(evidence),
        termination_race_same_handle=sum(x['wait_immediately_after_close']==258 for x in evidence),
        generic_pid_running=sum(x['generic_pid_running'] for x in evidence),
        pid_reuse_observed=sum(x['same_creation_identity'] is False for x in evidence),
        all_pinned_handles_eventually_signaled=all(x['wait_final']==0 for x in evidence))
    (out/'RESUMO_ANTES_DA_CORRECAO.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary),flush=True)


if __name__=='__main__':main()
