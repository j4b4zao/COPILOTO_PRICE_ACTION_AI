"""Portable-name preflight after byte integrity verification; never extracts ZIPs."""
from io import BytesIO
import unicodedata
import zipfile
from a6_vendor.tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from a6_vendor.tools.f3_int60_package_integrity_simulator import verify_blob, safe_name

RESERVED={'CON','PRN','AUX','NUL','CONIN$','CONOUT$'}|{
    prefix+str(n) for prefix in ('COM','LPT') for n in range(1,10)}


def portable_name(name):
    if not safe_name(name) or unicodedata.normalize('NFC',name)!=name:
        return False
    for part in name.split('/'):
        if (part[-1] in '. ' or any(ord(c)<32 or c in '<>"|?*' for c in part)
                or part.split('.')[0].upper() in RESERVED):
            return False
    return True


def verify_portable_blob(blob, expected_sha256, stage, **bounds):
    integrity=verify_blob(blob,expected_sha256,stage,**bounds)
    if integrity.status!='PACKAGE_FIXTURE_INTEGRITY_VERIFIED_UNAUTHENTICATED':
        return integrity
    with zipfile.ZipFile(BytesIO(blob)) as archive:
        names=archive.namelist()
    if any(not portable_name(name) for name in names):
        return ConcurrentResult('NONPORTABLE_ARCHIVE_NAME')
    keys=[name.casefold() for name in names]
    if len(set(keys))!=len(keys):
        return ConcurrentResult('PORTABLE_ARCHIVE_NAME_COLLISION')
    # A file cannot also be a directory prefix on extraction.
    files=set(keys)
    if any('/'.join(key.split('/')[:i]) in files for key in keys for i in range(1,len(key.split('/')))):
        return ConcurrentResult('ARCHIVE_FILE_DIRECTORY_COLLISION')
    return ConcurrentResult('PORTABLE_PACKAGE_FIXTURE_UNAUTHENTICATED',integrity.checked)


def safe_to_promote(*args, **kwargs):
    return False
