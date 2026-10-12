"""Inspect local PDF/PNG/JPEG; convert only caller-authorized local images."""
import math
from pathlib import Path

import pymupdf
from pypdf import PdfReader

from sheet_paths import sha256_file

MAX_BYTES=256*1024*1024
MAX_PAGES=500
MAX_PIXELS=100_000_000


def inspect_file(path):
    path=Path(path)
    size=path.stat().st_size
    if not 0<size<=MAX_BYTES: raise ValueError('File is empty or exceeds 256 MiB')
    with path.open('rb') as stream: header=stream.read(16)
    result={'bytes':size,'sha256':sha256_file(path),'pageCount':1,'width':None,'height':None}
    try:
        if header.startswith(b'%PDF-'):
            with path.open('rb') as stream:
                stream.seek(max(0,size-1024))
                if not stream.read().rstrip().endswith(b'%%EOF'): raise ValueError('PDF EOF marker missing/trailing data')
                stream.seek(0); reader=PdfReader(stream,strict=True)
                if reader.is_encrypted: raise ValueError('Encrypted PDF is not supported; no decryption attempted')
                count=len(reader.pages)
                if not 0<count<=MAX_PAGES: raise ValueError('PDF page count out of bounds')
                for page in reader.pages:
                    contents=page.get_contents()
                    if contents is not None: contents.get_data()
            with pymupdf.open(path) as doc:
                if not doc.is_pdf or doc.is_repaired or doc.needs_pass or len(doc)!=count:
                    raise ValueError('PDF requires repair or has inconsistent page structure')
                for page in doc:
                    rect=page.rect
                    if not all(math.isfinite(x) and x>0 for x in (rect.width,rect.height)):
                        raise ValueError('Invalid PDF page dimensions')
                    scale=min(1,2048/max(rect.width,rect.height))
                    page.get_pixmap(matrix=pymupdf.Matrix(scale,scale),alpha=False)
            result.update(mediaType='application/pdf',extension='.pdf',pageCount=count)
        elif header.startswith(b'\x89PNG\r\n\x1a\n') or header.startswith(b'\xff\xd8\xff'):
            png=header.startswith(b'\x89PNG')
            if png:
                with path.open('rb') as stream:
                    stream.seek(16); wh=stream.read(8)
                width,height=int.from_bytes(wh[:4],'big'),int.from_bytes(wh[4:],'big')
                if not 0<width*height<=MAX_PIXELS: raise ValueError('Image pixel dimensions out of bounds')
            pix=pymupdf.Pixmap(path)
            if not 0<pix.width*pix.height<=MAX_PIXELS: raise ValueError('Image pixel dimensions out of bounds')
            result.update(mediaType='image/png' if png else 'image/jpeg',extension='.png' if png else '.jpg',
                          width=pix.width,height=pix.height)
        else:
            raise ValueError('Unsupported signature; expected real PDF/PNG/JPEG, not HTML')
    except (OSError,ValueError): raise
    except Exception as exc:
        raise ValueError(f'Invalid document: {type(exc).__name__}') from exc
    if path.stat().st_size!=size or sha256_file(path)!=result['sha256']:
        raise ValueError('Input changed while inspecting')
    return result


def images_to_pdf(inputs,output):
    """Embed original raster pages; no screenshots, resizing, or image re-encoding step."""
    infos=[inspect_file(p) for p in inputs]
    if not infos or any(not x['mediaType'].startswith('image/') for x in infos):
        raise ValueError('Conversion requires PNG/JPEG inputs')
    with pymupdf.open() as doc:
        for path in inputs:
            with pymupdf.open(path) as image:
                with pymupdf.open('pdf',image.convert_to_pdf()) as single:
                    doc.insert_pdf(single)
        doc.set_metadata({'title':'Authorized image-derived sheet','producer':'AudioTP local sheet pipeline'})
        doc.save(output,garbage=4,deflate=True,no_new_id=True)
    info=inspect_file(output)
    if info['pageCount']!=len(inputs): raise ValueError('Converted page count differs')
    if [inspect_file(p) for p in inputs]!=infos: raise ValueError('Input changed during conversion')
    return info
