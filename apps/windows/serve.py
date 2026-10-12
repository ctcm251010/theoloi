"""Read-only local Windows MVP preview, served on 127.0.0.1 only.

Run ``python apps/windows/serve.py`` from the repository for port 8766.
Use ``--port 8767`` to choose a port, or ``--port 0`` for an unused port.
The default root is the sibling ``web`` directory regardless of working
directory. ``--root PATH`` explicitly selects a different isolated web root.
No credentials, cloud services, or third-party dependencies are used.
"""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import timezone
from email.utils import formatdate, parsedate_to_datetime
import hashlib
import mimetypes
import os
from pathlib import Path
import re
import stat
import shutil
import subprocess
from urllib.parse import unquote, urlsplit


def _is_link(path: Path) -> bool:
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def _byte_range(value: str, size: int) -> tuple[int, int]:
    match = re.fullmatch(r"bytes=([0-9]*)-([0-9]*)", value.strip(), re.IGNORECASE)
    if match is None or not size or not any(match.groups()):
        raise ValueError("invalid or unsatisfiable range")
    first, last = match.groups()
    if first:
        start = int(first)
        end = min(int(last), size - 1) if last else size - 1
        if start >= size or end < start:
            raise ValueError("unsatisfiable range")
    else:
        suffix = int(last)
        if suffix == 0:
            raise ValueError("unsatisfiable suffix")
        start, end = max(0, size - suffix), size - 1
    return start, end


def _date_is_current(value: str, modified: float) -> bool:
    try:
        date = parsedate_to_datetime(value)
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        return int(modified) <= date.timestamp()
    except (TypeError, ValueError, OverflowError):
        return False


def create_server(root: Path, port: int = 0) -> ThreadingHTTPServer:
    """Create an unstarted loopback HTTP server for one explicit web root."""
    if not isinstance(port, int) or not 0 <= port <= 65535:
        raise ValueError("port must be 0..65535")
    root = Path(root).absolute()
    try:
        valid = root.is_dir() and not any(_is_link(path) for path in (root, *root.parents))
    except OSError:
        valid = False
    if not valid:
        raise ValueError("web root must be an existing directory without links or junctions")
    root = root.resolve()

    class Handler(BaseHTTPRequestHandler):
        def parse_request(self):
            if not super().parse_request():
                return False
            hosts = self.headers.get_all("Host", [])
            match = re.fullmatch(r"(?:127\.0\.0\.1|localhost)(?::([0-9]{1,5}))?", hosts[0], re.IGNORECASE) if len(hosts) == 1 else None
            if match is None or (match.group(1) is not None and int(match.group(1)) != self.server.server_address[1]):
                self.send_error(403, "Loopback Host required")
                return False
            return True

        def do_GET(self):
            self._serve(head=False)

        def do_HEAD(self):
            self._serve(head=True)

        def __getattr__(self, name):
            if name.startswith("do_"):
                return self._method_not_allowed
            raise AttributeError(name)

        def _method_not_allowed(self):
            self.send_response(405)
            self.send_header("Allow", "GET, HEAD")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _path(self):
            try:
                path = unquote(urlsplit(self.path).path, errors="strict")
            except (UnicodeError, ValueError):
                raise PermissionError from None
            parts = [part for part in path.split("/") if part]
            if not path.startswith("/") or any(
                part.startswith(".") or part.endswith((".", " "))
                or any(char in part for char in "\\:%")
                or any(ord(char) < 32 or ord(char) == 127 for char in part)
                for part in parts
            ):
                raise PermissionError
            candidate = root
            for part in parts:
                candidate /= part
                if _is_link(candidate):
                    raise PermissionError
            if candidate.is_dir():
                candidate /= "index.html"
                if _is_link(candidate):
                    raise PermissionError
            if not candidate.resolve().is_relative_to(root):
                raise PermissionError
            return candidate

        def _serve(self, head):
            try:
                candidate = self._path()
                source = candidate.open("rb")
                info = os.fstat(source.fileno())
                if not stat.S_ISREG(info.st_mode):
                    source.close()
                    raise PermissionError
            except PermissionError:
                self.send_error(403)
                return
            except (FileNotFoundError, NotADirectoryError):
                self.send_error(404)
                return
            except OSError:
                self.send_error(403)
                return
            with source:
                content_type = {
                    ".html": "text/html; charset=utf-8",
                    ".js": "text/javascript; charset=utf-8",
                    ".mjs": "text/javascript; charset=utf-8",
                    ".json": "application/json",
                    ".css": "text/css; charset=utf-8",
                    ".wav": "audio/wav",
                }.get(candidate.suffix.lower())
                if content_type is None:
                    content_type = mimetypes.guess_type(str(candidate))[0] or "application/octet-stream"
                self._cache = "public, max-age=3600" if candidate.suffix.lower() == ".wav" else "no-store"
                digest = hashlib.sha256()
                while chunk := source.read(64 * 1024):
                    digest.update(chunk)
                source.seek(0)
                etag = '"' + digest.hexdigest() + '"'
                modified = formatdate(info.st_mtime, usegmt=True)

                def validators():
                    self.send_header("ETag", etag)
                    self.send_header("Last-Modified", modified)
                    self.send_header("Accept-Ranges", "bytes")

                none_match = self.headers.get("If-None-Match")
                if none_match is not None:
                    not_modified = any(
                        tag.strip().removeprefix("W/") in (etag, "*")
                        for tag in none_match.split(",")
                    )
                else:
                    not_modified = _date_is_current(self.headers.get("If-Modified-Since", ""), info.st_mtime)
                if not_modified:
                    self.send_response(304)
                    validators()
                    self.end_headers()
                    return

                ranges = self.headers.get_all("Range", [])
                if_range = self.headers.get("If-Range")
                if if_range is not None and if_range != etag and not _date_is_current(if_range, info.st_mtime):
                    ranges = []
                start, end = 0, info.st_size - 1
                if ranges:
                    try:
                        if len(ranges) != 1:
                            raise ValueError("multiple ranges are unsupported")
                        start, end = _byte_range(ranges[0], info.st_size)
                    except ValueError:
                        self.send_response(416)
                        validators()
                        self.send_header("Content-Range", f"bytes */{info.st_size}")
                        self.send_header("Content-Length", "0")
                        self.end_headers()
                        return
                self.send_response(206 if ranges else 200)
                validators()
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(end - start + 1))
                if ranges:
                    self.send_header("Content-Range", f"bytes {start}-{end}/{info.st_size}")
                self.end_headers()
                if not head:
                    source.seek(start)
                    remaining = end - start + 1
                    try:
                        while remaining > 0:
                            chunk = source.read(min(64 * 1024, remaining))
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                            remaining -= len(chunk)
                    except (BrokenPipeError, ConnectionResetError):
                        pass

        def end_headers(self):
            self.send_header("Cache-Control", getattr(self, "_cache", "no-store"))
            self.send_header("X-Content-Type-Options", "nosniff")
            super().end_headers()

        def log_message(self, format, *args):
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8766, help="loopback port (default: 8766; 0 chooses an unused port)")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent / "web", help="explicit web root (default: sibling web directory)")
    parser.add_argument("--static", action="store_true", help="catalog-only static preview; never substitute demo music")
    args = parser.parse_args(argv)
    default_web = Path(__file__).resolve().parent / 'web'
    if not args.static and args.root.resolve() == default_web:
        node = shutil.which('node')
        if node is None:
            parser.error('Node.js is required for actual local audio preview; --static opens catalog only')
        if not 0 <= args.port <= 65535:
            parser.error('port must be 0..65535')
        adapter = Path(__file__).resolve().parents[2] / 'workers/media-api/local-preview.mjs'
        return subprocess.call([node, str(adapter), '--port', str(args.port)])
    try:
        server = create_server(args.root, args.port)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    with server:
        print(f"Windows preview: http://127.0.0.1:{server.server_address[1]} (Ctrl+C to stop)", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
