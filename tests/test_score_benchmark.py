"""Real self-authored score artifacts and loopback server boundary tests."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'benchmarks/score-viewer'))


class ScoreBenchmarkTests(unittest.TestCase):
    def test_lyrics_do_not_overlap_neighbor_syllables(self):
        # Break caught: Vietnamese words longer than the note spacing collide.
        import fixture
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        pdfmetrics.registerFont(TTFont('LayoutCheck', str(ROOT/'benchmarks/score-viewer/vendor/NotoSans-Regular.ttf')))
        pdfmetrics.registerFont(TTFont('BenchmarkNoto', str(ROOT/'benchmarks/score-viewer/vendor/NotoSans-Regular.ttf')))
        score=fixture.structured_score()
        for page in score['pages']:
            display=fixture.layout(score,page)
            for system in range(6):
                row=[t for t in display['texts'] if t['y']==227+system*140]
                for a,b in zip(row,row[1:]):
                    end=a['x']+pdfmetrics.stringWidth(a['text'],'LayoutCheck',a['size'])
                    self.assertLessEqual(end+1,b['x'], (a['text'],b['text']))

    def test_fixture_font_covers_all_vietnamese_and_symbols(self):
        # Break caught: unsupported glyphs silently turn into missing-glyph boxes.
        import fixture
        from fontTools.ttLib import TTFont
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont as PDFTTFont
        font=ROOT/'benchmarks/score-viewer/vendor/NotoSans-Regular.ttf'
        pdfmetrics.registerFont(PDFTTFont('BenchmarkNoto',str(font)))
        with TTFont(font) as source:
            cmap=source.getBestCmap()
            for page in fixture.structured_score()['pages']:
                for text in fixture.layout(fixture.structured_score(),page)['texts']:
                    self.assertFalse([c for c in text['text'] if ord(c) not in cmap],text['text'])

    def test_same_structured_content_exports_real_vectors_and_vietnamese_pdf(self):
        # Break caught: raster-wrapped SVG/PDF or lost pitch/lyric/page content.
        import fixture
        import pymupdf
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            result = fixture.generate(out, ROOT / 'benchmarks/score-viewer/vendor/NotoSans-Regular.ttf')
            self.assertEqual(result['pages'], 4)
            score = json.loads((out / 'score.json').read_text('utf-8'))
            self.assertEqual(sum(len(s['notes']) for p in score['pages'] for s in p['systems']), 480)
            for p in score['pages']:
                for system in p['systems']:
                    self.assertEqual(sum(n['beats'] for n in system['notes']), 16)
            with pymupdf.open(out / 'original.pdf') as pdf:
                self.assertEqual(len(pdf), 4)
                self.assertIn('Bình minh', pdf[0].get_text())
                self.assertFalse(pdf[0].get_images())
            page = json.loads((out / 'page-1.vector.json').read_text('utf-8'))
            self.assertNotIn('<image', page['svg'])
            self.assertNotIn('<text', page['svg'])
            self.assertGreater(page['svg'].count('<ellipse'), 100)
            self.assertIn('Bình', [x['text'] for x in page['texts']])
            self.assertEqual(len(result['assets']), 17)
            self.assertLess(result['font']['bytes'], 569208)
            self.assertTrue(all(x['bytes'] > 0 and len(x['sha256']) == 64 for x in result['assets']))
            self.assertTrue(all(x['maxPixelError'] == 0 for x in result['quality'] if x['codec'] in ('png', 'webp')))

    def test_static_handler_blocks_escape_and_writes(self):
        # Break caught: serving workspace secrets via traversal/symlink, POST writes.
        import serve
        import threading
        import urllib.request
        import urllib.error
        from http.server import ThreadingHTTPServer
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'public'; root.mkdir()
            (root / 'index.html').write_text('own fixture', encoding='utf-8')
            (root / 'page.png').write_bytes(b'fixture asset')
            secret = Path(temp) / 'secret.txt'; secret.write_text('outside')
            server = ThreadingHTTPServer(('127.0.0.1', 0), serve.handler_for(root))
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            base = f'http://127.0.0.1:{server.server_port}'
            try:
                with urllib.request.urlopen(base + '/') as response:
                    self.assertEqual(response.read(), b'own fixture')
                    self.assertIn('no-cache', response.headers['Cache-Control'])
                with urllib.request.urlopen(base + '/page.png') as response:
                    self.assertIn('max-age', response.headers['Cache-Control'])
                for path in ('/%2e%2e/secret.txt', '/.secrets/r2.env', '/missing', '/sub/'):
                    with self.assertRaises(urllib.error.HTTPError) as error:
                        urllib.request.urlopen(base + path)
                    self.assertIn(error.exception.code, (403, 404))
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(urllib.request.Request(base + '/', data=b'x'))
                self.assertEqual(error.exception.code, 501)
                try:
                    (root / 'link.txt').symlink_to(secret)
                except OSError:
                    pass  # Other Windows path boundary checks still execute.
                else:
                    with self.assertRaises(urllib.error.HTTPError):
                        urllib.request.urlopen(base + '/link.txt')
            finally:
                server.shutdown(); server.server_close(); thread.join()


if __name__ == '__main__':
    unittest.main()
