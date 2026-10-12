# Score viewer benchmark implementation plan

Goal: compare a self-authored four-page score as vector PDF, PNG/WebP/AVIF and genuine SVG with HTML text. Retain an isolated prototype, not production app code. User explicitly authorizes implementation and small local benchmark; no approval pauses or technology commitment.

Architecture: one structured pitch/duration/lyric source and common display list generate all representations. Bundled PDF.js renders PDF; page-based image and SVG viewers load only selected pages. Loopback-only static server serves only prototype files. Instrument actual fetch/decode/render plus two animation frames; export raw observations. Cold means cache-bypass fetch, warm means HTTP-cache eligible same URL with new renderer; repeated page is a separate in-memory case. No fake timings or total-RAM claims from JS heap.

Constraints: no BookVN, secrets, audio/source/manifest mutations, real cloud requests or production app. Only openly licensed tooling/fonts and self-authored fixtures. No Git repository; retain this ledger. User requested all feasible work, superseding skill approval gates. Use PDF, Cloudflare and Context7 skills for relevant domains.

Review focus: mismatched content across formats; stale async page/zoom results; cache labels unsupported by evidence; unbounded decoded image/canvas resources; local server path/symlink escape.

- [x] Fixture: failing tests then structured music/display list, PDF and image/vector generation, hashes, codec quality evidence and licenses.
- [x] Viewer/server: bounded page lifecycle, fit/zoom/navigation, explicit cache conditions, raw export and loopback server safety tests.
- [x] Browser: actual Chrome run, repeated cold/warm observations, own-fixture screenshots and zoom inspection; explicitly record unsupported metrics.
- [x] Final: offline suite, independent read-only review, fixes, protected hashes, report and tested Windows commands.

Ledger:
- Context read: no local/parent AGENTS.md or SETUP.md found; user AGENTS/Context7 instructions apply. Existing Windows architecture and sheet demo read. Protected baseline hashes recorded from current files.
- Ruling: this is an isolated retained experimental subsystem, not a production technology decision. Use local HTTP intentionally for ES modules/worker instrumentation, not the previous review UI blocked file URL.
- pip default sandbox cannot access PyPI; bounded dependency install retried through approved escalation. No credential access.
- Fixture/server: missing-module RED then 4 new tests GREEN. Visual/font checks found overlap and absent tempo glyph; explicit regression FAIL then width-center layout / Tempo text PASS. Same-source 4 pages/480 notes, vector PDF with no images, real SVG lines/ellipses, full PNG/WebP pixel identity validated. Open font subset removes disproportionate full font cost.
- Browser preflight found actual PDF.js6.4.299 lifecycle change; task.destroy used. Cache retained stale JS; code no-cache + versioned module URL corrected, header regression FAIL then PASS. Zoom selected/fit synchronized. Do not use failed/provisional measurements.
- One fresh independent final review: Important timing buffer exhaustion corrected by clearing each serialized render and requiring per-fetch resource evidence. Missing-evidence/cache-hit and reset-run helper tests RED then GREEN. Ruling: stale finish timestamp/font failure are Important to honest PASS, so fix in same pass. Minor pointer-events prevents mouse selection; document limitation rather than broadening prototype.
- Final retained benchmark: 90 actual rows (3 rounds) from DOM, complete cold/warm/request checks; all warm resource transfers 0, all first cold transfers positive, no page3/4 fetch in 1-2-1 trials. All visibility states visible but many frame waits ~1s; timing conclusions explicitly limited, no claimed cause or final native technology choice. Shared context / fixed trial ordering / background desktop activity not controlled.
- Six real Chrome screenshots: A/WebP/C fit and 400%. Smoke all 4 pages, 50/100/200/400% and fit, no console warn/error. Download-event tool timed out/reset; current browser ID re-inventoried, existing prototype tab debugger unavailable, new tab in same browser used. Persisted raw DOM and screenshot buffers locally via Node filesystem, no policy bypass or alternate browser control.
- Final tests: Python 133 total, 132 PASS / 0 FAIL / 1 SKIP in107.721s (existing Windows file-symlink privilege skip). Node metrics and JS syntax PASS. Log tmp/score-benchmark-final-tests.log. One interrupted redundant Python run not used as completion evidence. Protected catalog/manifest/snapshot/R2-config hashes match baseline.
- Ruling: total process/GPU memory and WebView2/EXE performance remain unmeasured; report JS heap plus explicit pixel arithmetic only — cost if wrong: need native instrumentation before resource budgets.
- Ruling: original fixture is a limited monophonic geometric study, not a professional score engraver or proof for complex real scores — cost if wrong: additional authorized complex fixtures needed.
- Ruling: no power/cache/runtime/cloud distribution claims beyond actual local fixtures — future private API/R2 integration remains separate, credentials untouched. Retain ledger because workspace has no Git repository.
- Final code smoke benchmark: 1 additional round / 30 rows PASS, persisted separately in chrome-final-smoke-benchmark.json; console clean. Overview results screenshot separate from six zoom screenshots. Main report uses only the 90-row run; no mixing repetitions. File pins exported to evidence/protected-hashes.json. Architecture doc links benchmark without declaring native technology winner. Stop only own loopback server after handoff artifacts saved.
