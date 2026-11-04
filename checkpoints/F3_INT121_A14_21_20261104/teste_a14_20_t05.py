import hashlib
import subprocess
import sys
from pathlib import Path

repo = Path(sys.argv[1])
auditor = Path(sys.argv[2])
commit = sys.argv[3]

local = auditor.read_bytes()

committed = subprocess.check_output(
    [
        "git", "-C", str(repo),
        "show", f"{commit}:auditoria_consolidada_a14_18.py"
    ]
)

def normalize(data):
    if b"\r" in data.replace(b"\r\n", b""):
        raise RuntimeError("CR_ISOLADO")
    return data.replace(b"\r\n", b"\n")

print("SHA256_LOCAL:", hashlib.sha256(local).hexdigest())
print("SHA256_GIT:", hashlib.sha256(committed).hexdigest())

if normalize(local) != normalize(committed):
    raise RuntimeError("AUDITOR_INTERNO_DIVERGENTE")

print("AUDITOR_INTERNO_INTEGRO: PASS")
print("A14_20_T05_APROVADO")