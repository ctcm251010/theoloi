# AudioTP score viewer laboratory

Retained experimental prototype, not AudioTP.exe or a production score engraver. Uses only a self-authored melody/lyrics and openly licensed font/viewer tooling. No BookVN/WATV score material, audio catalog access, credentials, R2 calls or upload code.

## Run on Windows

From PowerShell:

```powershell
cd D:\Workspace\AudioTP
.\.venv\Scripts\python.exe -X utf8 benchmarks\score-viewer\serve.py
```

Open **http://127.0.0.1:8765/** in Chrome or Edge. Keep the tab visible throughout measurement. `Ctrl+C` stops this loopback-only read server. If port 8765 is occupied, use the implemented `--port 8766` option and open that port. Never serve the workspace root with another server.

Existing environment is prepared. To recreate dependencies in a suitable Python environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r benchmarks\score-viewer\requirements.txt
```

Vendor files and fixtures are already included; runtime has no CDN dependency. `vendor/provenance.json` pins actual downloaded versions, sizes, SHA-256 and source URLs. PDF.js Apache 2.0 and Noto SIL OFL licenses accompany them. `prepare-vendor.py` is the one-time tooling fetcher, refuses replacement when pinned; it is not needed to open the prototype. Do not fetch a new version for a comparison without recording it.

## Manual checks

1. Select PDF/PNG/WebP/AVIF/SVG+HTML and press **Mở bản nhạc**. Changing the selector alone does not replace an open document.
2. Check all four pages using arrows; try 50%, 100%, 200%, 400% and **Vừa màn hình**. Large zoom scrolls inside the paper viewport.
3. PDF renders a fresh resolution at each zoom. Image versions all start at 1520×2120 pixels. SVG geometry and HTML text remain vector at every scale.
4. Image/vector pages load on selection only; no hidden-page prefetch. At most two encoded image buffers/vector JSON pages are retained in the session, with one displayed image/canvas. Navigating releases prior object URL/canvas; switching documents destroys PDF loading task/removes font. PDF itself is loaded whole (65 KB fixture); this prototype does not benchmark HTTP Range PDF streaming.
5. Press **Chạy benchmark 5 định dạng**, default five rounds (150 observations). Controls are disabled until complete, preventing stale page/zoom writes. Keep the browser foreground, do not resize/zoom the browser during the run. **Xuất kết quả JSON** saves a local observation file. Nothing is sent to a server.

## Measurement contract

- Cold: each document has a fresh renderer and media `fetch(cache: 'reload')`, bypassing HTTP cache but not OS disk cache, warmed JIT, PDF.js module cache or browser process state.
- Warm: fresh document renderer, same resource URL and `fetch(cache: 'default')`. Verify `transferSize=0` per resource before calling it a hit. A warm label alone is not evidence. Revisit: page 1 after page 2, within the same document, separately labeled app cache.
- Timer: before first selected-page fetch through parse/decode, DOM/canvas render completion and two requestAnimationFrame callbacks. `workMs` ends before those callbacks, `frameWaitMs` is the remaining wait. This is a presentation proxy, not a physical screen measurement. Visibility start/end is recorded; hidden/occluded tabs can throttle frames. Do not rank real UX from such timings.
- PDF.js module initialization is recorded separately; worker initialization may appear in the first PDF sample. Shared viewer HTML/CSS/JS startup is outside these media timers. This is not a cold launch/EXE benchmark. Total runtime dependency bytes must be considered separately.
- Resource timings record transfer/body sizes. The server does not gzip fixtures; disk bytes are raw, not predicted Cloudflare wire costs.
- `performance.memory` is an optional coarse JS heap observation, not renderer/GPU/worker/total RAM. No GC is forced, trials share one browser context. `estimatedActivePixelBytes` is known image/canvas pixel-buffer arithmetic, not actual process RAM. Null metrics mean unsupported; no substitution with guessed numbers.

## Regenerate/test

Only if you intentionally change the self-authored fixture:

```powershell
.\.venv\Scripts\python.exe -X utf8 benchmarks\score-viewer\fixture.py
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_score_benchmark.py -v
node benchmarks\score-viewer\metrics.test.mjs
```

Regeneration replaces only files in `benchmarks/score-viewer/fixtures`, takes approximately half a minute on this environment, and invalidates old benchmark evidence. PDF uses the common vector display list directly (not images). Raster pages are rendered from that PDF; SVG music uses the same display list, with visible texts represented by HTML spans. A Unicode font subset uses the same glyph outlines and is shared by C's pages. Score data is in `fixtures/score.json` (pitch, diatonic step, quarter/eighth beats, bar, lyric).

See [benchmark report](../../docs/score-viewer-benchmark.md) for actual observations, screenshots, limitations and recommendation. Do not apply this prototype's trusted-generator SVG handling to arbitrary external SVG/HTML without a separate sanitizer/security design.
