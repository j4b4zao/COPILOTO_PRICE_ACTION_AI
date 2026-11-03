from pathlib import Path
import hashlib
import runpy
import subprocess
import sys

clone = Path(sys.argv[1])
auditor = clone / "auditoria_consolidada_a14_18.py"

original = auditor.read_bytes()
original_sha = hashlib.sha256(original).hexdigest()

target_commit = "f20f0b2e90772b9919dcd9c9d00ac1e0f16d1d68"

# Instrumentação limitada ao processo de teste.
# O arquivo do auditor e o histórico Git não são modificados.
real_check_output = subprocess.check_output

def intercepted_check_output(command, *args, **kwargs):
    if (
        isinstance(command, (list, tuple))
        and len(command) >= 5
        and command[0] == "git"
        and command[1] == "-C"
        and command[3] == "rev-parse"
        and command[4] == target_commit + "^"
    ):
        print("T05_INJECAO_PARENT_INCORRETO: ATIVADA", flush=True)
        return (
            b"0000000000000000000000000000000000000000\n"
        )

    return real_check_output(command, *args, **kwargs)

subprocess.check_output = intercepted_check_output

try:
    sys.argv = [str(auditor), str(clone)]
    runpy.run_path(str(auditor), run_name="__main__")

except RuntimeError as exc:
    message = str(exc)
    print("T05_ERRO_DETECTADO:", message)

    if "CADEIA" not in message.upper() and "PARENT" not in message.upper():
        raise RuntimeError(
            "T05_REJEICAO_POR_MOTIVO_INESPERADO"
        ) from exc

    print("T05_CADEIA_INCONSISTENTE_REJEITADA: PASS")

else:
    raise RuntimeError(
        "T05_AUDITOR_ACEITOU_CADEIA_INCONSISTENTE"
    )

finally:
    subprocess.check_output = real_check_output

    if hashlib.sha256(auditor.read_bytes()).hexdigest() != original_sha:
        raise RuntimeError("T05_AUDITOR_MODIFICADO")

    print("T05_AUDITOR_ORIGINAL_PRESERVADO: PASS")

print("A14_19_T05_APROVADO")