"""Offline HTTP contract tests for the Windows MVP preview server."""
import http.client
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import unittest


SERVER_PATH = Path(__file__).resolve().parents[1] / "apps/windows/serve.py"


class WindowsPreviewTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SERVER_PATH.is_file(), "Windows preview server is missing")
        spec = importlib.util.spec_from_file_location("windows_preview", SERVER_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.module = module
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "web"
        self.root.mkdir()
        (self.root / "index.html").write_bytes(b"<h1>Local preview</h1>")
        (self.root / "app.mjs").write_bytes(b"export const local = true;")
        (self.root / "catalog.json").write_bytes(b'{"tracks":[]}')
        (self.root / "sample.wav").write_bytes(b"RIFF0123456789")
        self.server = module.create_server(self.root, port=0)
        self.addCleanup(self.server.server_close)
        self.thread = threading.Thread(
            target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
        )
        self.thread.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.server.shutdown()
        self.thread.join(timeout=2)

    def request(self, path="/", method="GET", headers=None):
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=2)
        try:
            connection.request(method, path, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_serves_index_from_explicit_root_on_loopback(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        status, headers, body = self.request()
        self.assertEqual(status, 200)
        self.assertEqual(body, b"<h1>Local preview</h1>")
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertEqual(headers["Content-Length"], "22")
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_host_header_allows_only_loopback_names(self):
        port = self.server.server_address[1]
        for host in ["localhost", f"LOCALHOST:{port}", "127.0.0.1", f"127.0.0.1:{port}"]:
            with self.subTest(host=host):
                self.assertEqual(self.request(headers={"Host": host})[0], 200)
        for host in ["evil.example", "127.0.0.1.evil.example", "localhost.evil.example", "127.0.0.1@evil.example", "[::1]", "127.0.0.1:99999"]:
            for method in ["GET", "HEAD"]:
                with self.subTest(host=host, method=method):
                    status, _, body = self.request(method=method, headers={"Host": host})
                    self.assertEqual(status, 403)
                    self.assertNotIn(b"Local preview", body)

    def test_missing_and_duplicate_host_headers_are_forbidden(self):
        for hosts in [[], ["127.0.0.1", "evil.example"], ["127.0.0.1", "localhost"]]:
            with self.subTest(hosts=hosts):
                connection = http.client.HTTPConnection(*self.server.server_address, timeout=2)
                try:
                    connection.putrequest("GET", "/", skip_host=True)
                    for host in hosts:
                        connection.putheader("Host", host)
                    connection.endheaders()
                    response = connection.getresponse()
                    self.assertEqual(response.status, 403)
                    self.assertNotIn(b"Local preview", response.read())
                finally:
                    connection.close()

    def test_modules_json_and_audio_have_correct_types_and_cache(self):
        for path, content_type, cache, body in [
            ("/app.mjs?v=2", "text/javascript; charset=utf-8", "no-store", b"export const local = true;"),
            ("/catalog.json", "application/json", "no-store", b'{"tracks":[]}'),
            ("/sample.wav", "audio/wav", "public, max-age=3600", b"RIFF0123456789"),
        ]:
            with self.subTest(path=path):
                status, headers, actual = self.request(path)
                self.assertEqual(status, 200)
                self.assertEqual(headers["Content-Type"], content_type)
                self.assertEqual(headers["Cache-Control"], cache)
                self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
                self.assertEqual(actual, body)

    def test_head_returns_get_headers_without_body(self):
        status, headers, body = self.request("/sample.wav", method="HEAD")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Length"], "14")
        self.assertEqual(headers["Content-Type"], "audio/wav")
        self.assertEqual(body, b"")

    def test_single_ranges_include_exact_audio_bytes_and_lengths(self):
        for value, expected_range, expected in [
            ("bytes=0-3", "bytes 0-3/14", b"RIFF"),
            ("bytes=4-", "bytes 4-13/14", b"0123456789"),
            ("bytes=-4", "bytes 10-13/14", b"6789"),
            ("bytes=12-99", "bytes 12-13/14", b"89"),
            ("bytes=-99", "bytes 0-13/14", b"RIFF0123456789"),
            ("bytes=0-0", "bytes 0-0/14", b"R"),
        ]:
            with self.subTest(value=value):
                status, headers, body = self.request("/sample.wav", headers={"Range": value})
                self.assertEqual(status, 206)
                self.assertEqual(headers["Content-Range"], expected_range)
                self.assertEqual(headers["Content-Length"], str(len(expected)))
                self.assertEqual(headers["Accept-Ranges"], "bytes")
                self.assertEqual(body, expected)

    def test_head_range_has_partial_headers_and_no_body(self):
        status, headers, body = self.request("/sample.wav", method="HEAD", headers={"Range": "bytes=4-7"})
        self.assertEqual(status, 206)
        self.assertEqual(headers["Content-Range"], "bytes 4-7/14")
        self.assertEqual(headers["Content-Length"], "4")
        self.assertEqual(body, b"")

    def test_invalid_multiple_and_unsatisfiable_ranges_return_416(self):
        for value in ["bytes=14-", "bytes=8-7", "bytes=-0", "bytes=-", "bytes=", "bytes=0-1,4-5", "items=0-1", "bytes=1.5-2", "bytes=1--2"]:
            for method in ["GET", "HEAD"]:
                with self.subTest(value=value, method=method):
                    status, headers, body = self.request("/sample.wav", method=method, headers={"Range": value})
                    self.assertEqual(status, 416)
                    self.assertEqual(headers["Content-Range"], "bytes */14")
                    self.assertEqual(headers["Content-Length"], "0")
                    self.assertEqual(body, b"")

    def test_duplicate_range_headers_are_rejected(self):
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=2)
        try:
            connection.putrequest("GET", "/sample.wav")
            connection.putheader("Range", "bytes=0-1")
            connection.putheader("Range", "bytes=4-5")
            connection.endheaders()
            response = connection.getresponse()
            self.assertEqual(response.status, 416)
            self.assertEqual(response.getheader("Content-Range"), "bytes */14")
            self.assertEqual(response.read(), b"")
        finally:
            connection.close()

    def test_empty_file_has_no_satisfiable_range(self):
        (self.root / "empty.wav").write_bytes(b"")
        self.assertEqual(self.request("/empty.wav")[0], 200)
        status, headers, body = self.request("/empty.wav", headers={"Range": "bytes=0-"})
        self.assertEqual(status, 416)
        self.assertEqual(headers["Content-Range"], "bytes */0")
        self.assertEqual(body, b"")

    def test_etag_conditional_requests_take_precedence_over_range(self):
        _, headers, _ = self.request("/sample.wav")
        self.assertIn("ETag", headers)
        self.assertIn("Last-Modified", headers)
        self.assertEqual(headers["Accept-Ranges"], "bytes")
        for value in [headers["ETag"], "W/" + headers["ETag"], '"unrelated", ' + headers["ETag"], "*"]:
            with self.subTest(value=value):
                status, current, body = self.request("/sample.wav", headers={"If-None-Match": value, "Range": "bytes=0-3"})
                self.assertEqual(status, 304)
                self.assertEqual(current["ETag"], headers["ETag"])
                self.assertEqual(body, b"")
        (self.root / "sample.wav").write_bytes(b"changed")
        status, updated, body = self.request("/sample.wav", headers={"If-None-Match": headers["ETag"]})
        self.assertEqual(status, 200)
        self.assertNotEqual(updated["ETag"], headers["ETag"])
        self.assertEqual(body, b"changed")

    def test_if_range_accepts_current_strong_etag_or_date(self):
        _, headers, _ = self.request("/sample.wav")
        self.assertIn("ETag", headers)
        for value in [headers["ETag"], headers["Last-Modified"]]:
            with self.subTest(value=value):
                status, _, body = self.request("/sample.wav", headers={"Range": "bytes=0-3", "If-Range": value})
                self.assertEqual(status, 206)
                self.assertEqual(body, b"RIFF")

    def test_if_range_stale_weak_or_invalid_validator_returns_full_file(self):
        _, headers, _ = self.request("/sample.wav")
        self.assertIn("ETag", headers)
        for value in ['"stale"', "W/" + headers["ETag"], "Thu, 01 Jan 1970 00:00:00 GMT", "not-a-validator"]:
            with self.subTest(value=value):
                status, current, body = self.request("/sample.wav", headers={"Range": "bytes=0-3", "If-Range": value})
                self.assertEqual(status, 200)
                self.assertNotIn("Content-Range", current)
                self.assertEqual(body, b"RIFF0123456789")

    def test_if_modified_since_is_used_only_without_if_none_match(self):
        _, headers, _ = self.request("/sample.wav")
        self.assertIn("Last-Modified", headers)
        status, _, body = self.request("/sample.wav", headers={"If-Modified-Since": headers["Last-Modified"]})
        self.assertEqual(status, 304)
        self.assertEqual(body, b"")
        status, _, body = self.request("/sample.wav", headers={"If-Modified-Since": headers["Last-Modified"], "If-None-Match": '"stale"'})
        self.assertEqual(status, 200)
        self.assertEqual(body, b"RIFF0123456789")

    def test_directory_listing_and_missing_paths_return_404(self):
        (self.root / "unlisted").mkdir()
        (self.root / "unlisted/secret.txt").write_bytes(b"not an index")
        for path in ["/unlisted", "/unlisted/", "/missing.json"]:
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)

    def test_nested_directory_index_and_encoded_filename_work(self):
        (self.root / "nested").mkdir()
        (self.root / "nested/index.html").write_bytes(b"nested")
        (self.root / "with space.txt").write_bytes(b"space")
        self.assertEqual(self.request("/nested/")[2], b"nested")
        self.assertEqual(self.request("/with%20space.txt")[2], b"space")

    def test_traversal_backslashes_hidden_files_and_windows_aliases_are_forbidden(self):
        (self.root.parent / "outside.txt").write_bytes(b"private outside")
        (self.root / ".env").write_bytes(b"private hidden")
        for path in [
            "/../outside.txt", "/%2e%2e/outside.txt", "/%2e%2e%2foutside.txt",
            "/%252e%252e/outside.txt", "/..\\outside.txt", "/%5coutside.txt",
            "/.env", "/%2eenv", "/nested/.env", "/app.mjs:secret",
            "/app.mjs.", "/app.mjs%20", "/%00", "/%ff",
        ]:
            for method in ["GET", "HEAD"]:
                with self.subTest(path=path, method=method):
                    status, _, body = self.request(path, method=method)
                    self.assertEqual(status, 403)
                    self.assertNotIn(b"private", body)

    def test_methods_cannot_modify_the_web_root(self):
        for method in ["POST", "PUT", "DELETE", "PATCH", "OPTIONS", "TRACE", "UNSUPPORTED"]:
            with self.subTest(method=method):
                status, headers, _ = self.request("/index.html", method=method)
                self.assertEqual(status, 405)
                self.assertEqual(headers["Allow"], "GET, HEAD")
        self.assertEqual((self.root / "index.html").read_bytes(), b"<h1>Local preview</h1>")

    def test_symbolic_links_cannot_escape_or_alias_the_root(self):
        outside = self.root.parent / "outside.txt"
        outside.write_bytes(b"private outside")
        try:
            (self.root / "outside-link.txt").symlink_to(outside)
            (self.root / "inside-link.txt").symlink_to(self.root / "index.html")
            (self.root / "dir-link").symlink_to(self.root.parent, target_is_directory=True)
        except OSError as error:
            self.skipTest(f"Host does not permit symbolic links: {error}")
        for path in ["/outside-link.txt", "/inside-link.txt", "/dir-link/outside.txt"]:
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 403)

    @unittest.skipUnless(os.name == "nt", "Windows junction contract")
    def test_windows_junctions_cannot_escape_the_root(self):
        outside = self.root.parent / "outside"
        outside.mkdir()
        (outside / "private.txt").write_bytes(b"private junction")
        junction = self.root / "junction"
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(junction), str(outside)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.request("/junction/private.txt")[0], 403)

    def test_create_server_rejects_missing_or_file_roots_and_invalid_ports(self):
        for root in [self.root / "missing", self.root / "index.html"]:
            with self.subTest(root=root):
                with self.assertRaises(ValueError):
                    self.module.create_server(root)
        for port in [-1, 65536]:
            with self.subTest(port=port):
                with self.assertRaises(ValueError):
                    self.module.create_server(self.root, port=port)

    @unittest.skipUnless(os.name == "nt", "Windows junction contract")
    def test_create_server_rejects_junction_root(self):
        junction = self.root.parent / "root-junction"
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(junction), str(self.root)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        with self.assertRaises(ValueError):
            self.module.create_server(junction)

    def test_cli_serves_explicit_root_from_an_unrelated_working_directory(self):
        process = subprocess.Popen(
            [sys.executable, str(SERVER_PATH), "--root", str(self.root), "--port", "0"],
            cwd=self.root.parent, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        def stop_process():
            if process.poll() is None:
                process.terminate()
            process.communicate(timeout=5)
        self.addCleanup(stop_process)
        lines = []
        reader = threading.Thread(target=lambda: lines.append(process.stdout.readline()), daemon=True)
        reader.start()
        reader.join(timeout=5)
        self.assertFalse(reader.is_alive(), "CLI did not announce its loopback URL")
        match = re.search(r"http://127\.0\.0\.1:(\d+)", "".join(lines))
        self.assertIsNotNone(match, "CLI did not start the preview server")
        connection = http.client.HTTPConnection("127.0.0.1", int(match.group(1)), timeout=2)
        try:
            connection.request("GET", "/")
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertEqual(response.read(), b"<h1>Local preview</h1>")
            connection.request("GET", "/../outside.txt")
            response = connection.getresponse()
            self.assertEqual(response.status, 403)
            response.read()
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
