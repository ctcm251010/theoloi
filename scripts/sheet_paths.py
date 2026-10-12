"""Paths and atomic writes restricted to the new sheet subsystem."""
import hashlib
import os
from pathlib import Path
import re
import tempfile

from catalog_lib import json_text


def sha256_file(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''): h.update(block)
    return h.hexdigest()


def project_root(root):
    root=Path(os.path.abspath(root))
    if root.resolve()!=root or root.is_symlink() or root.is_junction():
        raise ValueError('Project root may not redirect through a symlink/junction')
    return root


def plain_path(path,root):
    root=project_root(root)
    p=Path(path)
    if not p.is_absolute(): p=root/p
    p=Path(os.path.abspath(p))
    if not p.is_relative_to(root): raise ValueError('Path escapes project root')
    current=root
    for part in p.relative_to(root).parts:
        if part in ('.','..') or part.endswith((' ','.')) or ':' in part or re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?',part,re.I):
            raise ValueError('Unsafe Windows path component')
        current=current/part
        if current.is_symlink() or current.is_junction(): raise ValueError('Symlink/junction is not allowed')
    return p


def relative_input(value,root):
    if not isinstance(value,str) or not value or '\\' in value or ':' in value or value.startswith('/') or any(x in ('','..','.') for x in value.split('/')):
        raise ValueError('Input must be a plain project-relative POSIX path')
    if not any(value.startswith(prefix) for prefix in ('source/local-sheets/','tmp/sheets-demo/','tests/fixtures/sheets/')):
        raise ValueError('Inputs belong under source/local-sheets, tmp/sheets-demo or tests/fixtures/sheets')
    return plain_path(value,root)


def output_path(value,root,area,extension):
    p=plain_path(value,root)
    relative=p.relative_to(project_root(root)).as_posix()
    if area in ('catalog','delivery','docs','state'):
        if not relative.startswith(area+'/sheet-') or p.suffix != extension or len(p.relative_to(project_root(root)).parts)!=2:
            raise ValueError(f'Output must be {area}/sheet-*{extension}')
    elif not relative.startswith(area+'/') or (extension and p.suffix!=extension):
        raise ValueError('Output is outside the sheet area')
    return p


def atomic_write(path,content,root):
    path=plain_path(path,root)
    path.parent.mkdir(parents=True,exist_ok=True)
    plain_path(path,root)
    handle,temp=tempfile.mkstemp(prefix='.sheet-',suffix='.part',dir=path.parent)
    try:
        with os.fdopen(handle,'wb') as stream:
            stream.write(content); stream.flush(); os.fsync(stream.fileno())
        plain_path(path,root)
        os.replace(temp,path)
    finally:
        if os.path.exists(temp): os.unlink(temp)


def write_json(path,value,root):
    atomic_write(path,json_text(value).encode('utf-8'),root)
