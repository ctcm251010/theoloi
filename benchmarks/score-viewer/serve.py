"""Loopback-only, read-only prototype server. Never serve the workspace root."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT=Path(__file__).resolve().parent


def handler_for(root):
    root=Path(root).resolve()
    class Handler(SimpleHTTPRequestHandler):
        extensions_map={**SimpleHTTPRequestHandler.extensions_map,'.mjs':'text/javascript','.avif':'image/avif','.webp':'image/webp'}
        def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(root),**kwargs)
        def do_GET(self):
            path=unquote(urlsplit(self.path).path)
            parts=path.replace('\\','/').split('/')
            if any(part.startswith('.') or ':' in part for part in parts if part):
                self.send_error(403); return
            candidate=root.joinpath(*[p for p in parts if p])
            if candidate.is_dir(): candidate=candidate/'index.html'
            try:
                if not candidate.resolve().is_relative_to(root) or any(p.is_symlink() or p.is_junction() for p in [candidate,*candidate.parents] if p!=root and p.is_relative_to(root)):
                    self.send_error(403); return
                if not candidate.is_file(): self.send_error(404); return
            except OSError:
                self.send_error(403); return
            super().do_GET()
        def do_HEAD(self):
            # Same validation; do not leak files through HEAD.
            self._head_only=True
            self.do_GET()
        def copyfile(self,source,outputfile):
            if not getattr(self,'_head_only',False): super().copyfile(source,outputfile)
        def end_headers(self):
            path=urlsplit(self.path).path
            code=path=='/' or (not path.startswith('/vendor/') and Path(path).suffix in ('.html','.js','.mjs','.css'))
            self.send_header('Cache-Control','no-cache' if code else 'public, max-age=3600')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; worker-src 'self' blob:; img-src 'self' blob:; style-src 'self' 'unsafe-inline'; font-src 'self' blob:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
            super().end_headers()
        def log_message(self,format,*args): pass
    return Handler


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    if not 1024<=args.port<=65535: parser.error('port must be 1024..65535')
    with ThreadingHTTPServer(('127.0.0.1',args.port),handler_for(ROOT)) as server:
        print(f'Prototype: http://127.0.0.1:{args.port} (Ctrl+C to stop)',flush=True)
        try: server.serve_forever()
        except KeyboardInterrupt: pass
