"""Testa compartilhamento de arquivo Win32 com um journal sintético e offline."""
import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


BASE = "9572242085122cbd0833830576d7b2b4aa8b3b5f"
LOCKER = """
import ctypes
from ctypes import wintypes
import sys

kernel = ctypes.WinDLL("kernel32", use_last_error=True)
create = kernel.CreateFileW
create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                   wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
create.restype = wintypes.HANDLE
close = kernel.CloseHandle
close.argtypes = [wintypes.HANDLE]
close.restype = wintypes.BOOL
handle = create(sys.argv[1], 0x80000000, 0, None, 3, 0x80, None)
if handle == ctypes.c_void_p(-1).value:
    raise ctypes.WinError(ctypes.get_last_error())
try:
    print("LOCKED", flush=True)
    sys.stdin.readline()
finally:
    if not close(handle):
        raise ctypes.WinError(ctypes.get_last_error())
"""
READER = """
import json
from pathlib import Path
import subprocess
import sys

import f3_int121_a14_11_budget as budget

locker_code, path, mode, payload = sys.argv[1:]
locker = subprocess.Popen(
    [sys.executable, "-B", "-E", "-s", "-c", locker_code, path],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
)
now = 0
denials = []

def release():
    if locker.poll() is None:
        locker.stdin.write("\\n")
        locker.stdin.flush()
    if locker.wait(timeout=5) != 0:
        raise RuntimeError("Falha no processo bloqueador")

def on_denial(error):
    global now
    denials.append((error["type"], error["errno"], error["winerror"]))
    if mode == "liberado":
        release()
    else:
        now = 500_000_000

try:
    if locker.stdout.readline().strip() != "LOCKED":
        raise RuntimeError("Bloqueio exclusivo indisponível")
    result = budget.read(Path(path), json.loads(payload), after_denial=on_denial,
                         clock_ns=lambda: now)
    release()
finally:
    if locker.poll() is None:
        locker.kill()
        locker.wait(timeout=5)
    locker.stdin.close()
    locker.stdout.close()

verification = result["verification"]
print(json.dumps({
    "status": result["status"], "denials": denials,
    "attempts": len(result["attempts"]),
    "sha256": verification["sha256"] if verification else None,
    "production_api_changed": result["production_api_changed"],
}))
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("Este teste requer Windows")
    scenario_path = "checkpoints/F3_INT121_A14_30_20261104/testar_interrupcao_journal_a14_30.py"
    repo = args.repo.resolve()
    runner_blob = subprocess.check_output(
        ["git", "-C", str(repo), "cat-file", "blob", f"{BASE}:{scenario_path}"], timeout=60,
    )
    with tempfile.TemporaryDirectory(prefix="a14_31_") as temp:
        root = Path(temp)
        (root / "cenario.py").write_bytes(runner_blob)
        # O cenário anterior fornece o registro sintético usado pelos dois testes.
        fixture = subprocess.check_output(
            [sys.executable, "-B", "-E", "-s", "-c",
             "import cenario; print(cenario.encode(cenario.RECORD))"],
            cwd=root, timeout=15,
        ).strip()
        path = root / "journal.json"
        path.write_bytes(fixture)
        hashes = {}
        for name in ("f3_int121_a14_8_journal.py", "f3_int121_a14_11_budget.py"):
            data = subprocess.check_output(
                ["git", "-C", str(repo), "cat-file", "blob", f"{BASE}:{name}"], timeout=60,
            )
            (root / name).write_bytes(data)
            hashes[name] = hashlib.sha256(data).hexdigest()

        evidence = []
        digest = hashlib.sha256(fixture).hexdigest()
        for optimized in (False, True):
            flags = ["-O"] if optimized else []
            for mode, status, attempts, sha in (
                ("mantido", "JOURNAL_READ_DENIED", 1, None),
                ("liberado", "CONTENT_MATCH", 2, digest),
            ):
                output = subprocess.check_output(
                    [sys.executable, *flags, "-B", "-E", "-s", "-c", READER,
                     LOCKER, str(path), mode, fixture.decode("utf-8")],
                    cwd=root, timeout=30,
                )
                result = json.loads(output)
                denials = result.pop("denials")
                if len(denials) != 1 or denials[0][:2] != ["PermissionError", errno.EACCES] or denials[0][2] not in (None, 32):
                    raise RuntimeError(f"Erro de compartilhamento inesperado: {denials}")
                if result != {
                    "status": status,
                    "attempts": attempts, "sha256": sha, "production_api_changed": False,
                }:
                    raise RuntimeError(f"{mode}: {result}")
                evidence.append({"modo": "otimizado" if optimized else "normal",
                                 "bloqueio": mode, "denials": denials, **result})
        if path.read_bytes() != fixture:
            raise RuntimeError("Journal alterado durante a leitura")
    print(json.dumps({
        "etapa": "F3-INT-121 A14.31",
        "commit_base": BASE,
        "python": sys.version.split()[0],
        "sha256_script": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "sha256_modulos": hashes,
        "relogio": "Injetado para expirar o orcamento de forma deterministica.",
        "estado_operacional": {
            "f3": "OPEN", "offline": True, "simulation_only": True,
            "certification": False, "real_operations_authorized": False,
            "production_api_changed": False,
        },
        "execucoes": evidence,
    }, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
