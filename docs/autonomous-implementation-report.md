# AudioTP 0.2 — Kết quả P0–P4

**Nghe nhanh 12/10/2026:** triển khai hàng ba mục dưới tabs, ẩn theo tìm kiếm và lưu thu gọn thủ công; silent bắt đầu đúng asset 19977, cầu nguyện chưa nhập nên khóa. Frontend 37 PASS; Python 167 PASS / 2 SKIP; Chrome desktop/mobile, shared playback và full SHA-256 của 983 media PASS. [Chi tiết và bằng chứng](quick-listening-report.md). Chưa build EXE hoặc chạy live R2 trong bước này.

**Cập nhật UI 12/10/2026:** đã thay sidebar bằng Minimal Music Player; Chrome Bang phát audio thật, có ảnh desktop/mobile. Frontend 34 PASS, Python 165 PASS / 2 SKIP. Các kết quả bên dưới là ledger P0–P4 trước redesign; xem [báo cáo UI hiện hành](minimal-player-redesign.md). Native build/live deployment vẫn bị chặn.

Ngày 12/10/2026. **Chưa hoàn thành sản phẩm EXE online E2E.** Đã sửa lỗi phát WAV dưới tên bài thật, triển khai backend/API và thử audio M4A thật local. Worker live và binary Windows vẫn cần thao tác người dùng.

## P0 — Chuỗi phát

**DONE code/local integration; BLOCKED live deployment.**

Browser tái hiện lỗi cũ: bài 1 → `fixtures/guide.wav`. Frontend hiện không còn demo resolver hoặc fallback theo mode. Mỗi lựa chọn yêu cầu vé theo assetId; Worker lấy objectKey chính xác từ allowlist manifest 983 đã pin.

Đã có API catalog, từng logical song, login nhóm, vé HMAC gắn asset/revision/epoch, streaming GET/HEAD/Range, metadata/ETag checks, CORS, rate limiting và các error code. Thẻ audio dùng signed URL ngắn hạn, không giả định có thể gắn Bearer vào request media. Session chỉ ở RAM; code không lưu credentials và không có R2 key trong frontend.

Local adapter dùng cùng handler Worker, thay R2 bằng bộ đọc file chỉ đọc từ manifest. Size/SHA của file được chọn được kiểm tra; không remux/transcode hoặc sửa media. Kiểm thử HTTP full SHA ba đại diện và browser playback xác nhận đúng nguồn. Đây là **local integration với audio thật**, chưa phải Cloudflare live.

Runtime workerd chạy bundle Worker và R2 mô phỏng cô lập đã PASS. Không có Cloudflare deployment, public bucket hoặc upload thật. B10 chưa thấy báo cáo trong `logs/r2-verification`; không tự chạy live audit. B9 983 verified từ state/tài liệu không thay thế B10 độc lập hoặc full remote-content hash.

## P1 — Hai mục nhanh

**DONE UI/gating; BLOCKED nguồn/quyền chưa chốt.** Giữ đúng hai nút riêng, cùng player với ba tab. Không trộn vào 13 silent hoặc sửa catalog audio đã pin. Ghim đầu đã quan sát silent 19976 trong cùng phiên WATV, chưa chốt quy tắc qua phiên/ngày; `our_wish` ngoài manifest. `pray_01–pray_13` chưa xác minh liên hệ UI. Cả hai vẫn unavailable, không dùng âm thay thế.

## P2 — Windows

**DONE source/build tooling; BLOCKED native toolchain.** Tauri 2/WebView2 shell 0.2.0, UI tiếng Việt, 485/485/13, sidebar, tìm không dấu, theme, yêu thích/history, keyboard, pause/seek/volume/queue/repeat/continuous, buffering/timeout/retry.

Đã kiểm tra máy: Node 24.18.0, npm shell 12.2.0 (builder gọi npm đi cùng Node: 11.16.0), Tauri CLI 2.12.2 có sẵn; WebView2 có file runtime. Thiếu Cargo, Rust, MSVC x64 C++ Build Tools và Windows SDK/UCRT. Không tự cài toolchain/admin hoặc thay hệ thống. Chưa có debug/release EXE, NSIS installer, Cargo.lock hay test native WebView2/clean machine.

`scripts/build-windows.py` mặc định chỉ preflight, `--build` cần API HTTPS thật và đủ dependency. Nó stage đúng web assets, **loại WAV fixtures**, cấu hình API/CSP riêng, chạy test/build, kiểm tra binary marker/đường developer và chỉ đóng gói EXE/installer + hướng dẫn + SHA khi thực sự có artifact. Khôi phục Tauri config trong finally kể cả build fail. Test mock xác nhận không tạo release khi thiếu toolchain và không để lại config sai sau thất bại.

## P3 — Bằng chứng kiểm thử

| Lớp | Kết quả đã quan sát |
|---|---|
| Python toàn project | **167 tổng / 165 PASS / 2 SKIP**, 103,011 giây; symlink privilege SKIP, junction PASS |
| Frontend/API/player Node | **33 PASS** sau sửa native fetch receiver, source matching, auth, timeout, retry position, buffering, local restart bootstrap và history migration |
| Backend | **15 PASS**, gồm mock + HTTP integration + workerd runtime; log trong evidence v0.2 |
| Typecheck | Worker JS/JSDoc với Env generated bởi Wrangler: PASS |
| Wrangler | dry-run bundle PASS, chỉ chuẩn bị bundle local; không deploy |
| Browser | IAB phát M4A thật: guide 4177 **125,016236s**, instrumental 17407 **125,248435s**, silent 19977 **50,085442s**, silent 19976 **56,958549s**; readyState 4, tiến trình chạy, seek 60/20/30, pause và giữ nguồn khi đổi tab |
| Repeat/continuous | Browser seek gần cuối rồi lặp đúng guide 1; bật continuous chuyển qua queue thực đến bài 4; không phát đồng thời hai audio element |
| Network | Đã dừng riêng helper local để tạo lỗi request thật, UI error/retry; xác nhận phục hồi ở evidence cuối. Không vô hiệu hóa browser/network sandbox |
| Chrome | Lượt hiện tại chặn localhost `ERR_BLOCKED_BY_CLIENT`; không sửa Chrome protection. Dùng IAB cho kiểm thử app local; khảo sát WATV trước vẫn thuộc Chrome Bang |
| Screenshot 0.2 | Hai API screenshot đều timeout khi capture dù browser visible. **Chưa có ảnh mới**, không dùng ảnh demo cũ làm bằng chứng bản 0.2. Tab actual-audio được giữ mở |
| Native/clean Windows/live R2 E2E | **NOT VERIFIED / BLOCKED**, không thay bằng kết quả mock/browser |

Audio thật được xác minh bằng bytes/hash, decode-ready media state và thời gian chạy. Công cụ không xác nhận bằng tai; người dùng cần nghe nghiệm thu, không suy từ trạng thái player rằng đã đo chất lượng âm thanh.

Các test ghi log/evidence đã loại signed query/session. Không thu raw console/network log chứa ticket. Lịch sử demo v1 không còn được trình bày như nghe nhạc thật; favourites/theme được giữ, history v2 chỉ ghi khi actual media phát.

Bằng chứng cuối: [verification JSON](../apps/windows/evidence/verification-v0.2.json), [30 bước browser với audio thật](../apps/windows/evidence/real-playback-v0.2.json), [Python 167](../apps/windows/evidence/python-tests-final-v0.2.txt), [frontend 33](../apps/windows/evidence/node-tests-final-v0.2.txt), [backend 15 + typecheck](../apps/windows/evidence/worker-tests-latest-v0.2.txt), [native preflight](../apps/windows/evidence/native-preflight-v0.2.json). Status B9 local vừa kiểm tra lại: **983 uploaded/verified, 0 failed/remaining**; vẫn không phải remote audit B10.

## P4 — Phân phối

**DONE công cụ/tài liệu; BLOCKED artifact/deploy.** Chưa có gói EXE để gửi bạn bè. Build thành công mới tạo `release/windows/0.2.0-<timestamp>/`, gồm binary/installer, hướng dẫn và SHA. Không đóng gói source workspace, log, credential, manifest server hoặc audio local.

Portable EXE vẫn cần WebView2. NSIS cấu hình bootstrapper runtime khi thiếu. Chưa ký Authenticode, chưa có updater tự động hoặc xác minh máy sạch. Không gọi bản chưa build là standalone/release. [Tauri Windows installer](https://tauri.app/distribute/windows-installer/)

Audio disk cache mặc định **tắt**, response private/no-store; không bulk prefetch. Browser/WebView2 có bộ đệm đang phát do engine quản lý, chưa đo native RAM. Không tuyên bố đã triển khai LRU/offline-download.

## Lệnh và các bước cần người dùng

Nghe thử đúng file hiện có:

```powershell
cd D:\Workspace\AudioTP
node workers/media-api/local-preview.mjs
```

Mở `http://127.0.0.1:8766/`; nếu helper đang chạy thì mở trang, không chạy thêm process cùng cổng. Command Python cũ vẫn dùng được và nay gọi backend local thật. Preview này cần workspace/media; điều đó **không phải** yêu cầu đối với app được build kết nối Worker sau này.

Build preflight an toàn:

```powershell
cd D:\Workspace\AudioTP
.\.venv\Scripts\python.exe -X utf8 scripts/build-windows.py --check
```

Exit 2 nghĩa thiếu dependency. Cài C++ Build Tools với workload **Desktop development with C++** và Windows SDK theo [Tauri prerequisites](https://tauri.app/start/prerequisites/); đây là cài hệ thống do bạn thực hiện. Rust có lệnh chính thức `winget install --id Rustlang.Rustup`; sau đó mở PowerShell mới, `rustup default stable-msvc`.

Worker/B10/secrets/deploy theo [Worker README](../workers/media-api/README.md). Chỉ người dùng tự deploy và bật serving sau review; chưa có URL production để điền giả.

Sau khi có Worker thật và toolchain:

```powershell
cd D:\Workspace\AudioTP
.\.venv\Scripts\python.exe -X utf8 scripts/build-windows.py --build --api-base (Read-Host 'HTTPS URL Worker đã deploy') --installer
```

Script là công cụ đã kiểm tra offline và đường lỗi, **chưa chứng minh native build thành công trên máy này**. Sau khi có artifact, chạy app/installer trên máy khác không có workspace/Node/Python/M4A, đăng nhập bằng quyền hợp lệ, nghe/tua/đổi guide-instrumental, test logout/hết hạn/mất mạng, rồi mới phân phối nhóm.

Builder dùng lock `apps/windows/build.lock` để chặn build đồng thời và lưu cấu hình gốc vào `apps/windows/build-backups/` trước thay đổi. Nếu terminal bị đóng cưỡng bức, không tự xóa lock: kiểm tra process đã dừng và đối chiếu/khôi phục backup đúng build trước khi bỏ lock. Không ảnh hưởng download/upload lock hoặc state. Artifact được kiểm tra trước khi tạo thư mục phân phối; không tạo gói khi binary chứa marker cấm. Rust dùng [path remapping](https://doc.rust-lang.org/rustc/command-line-arguments.html#--remap-path-prefix-remap-source-names-in-output), nhưng kiểm tra binary thật vẫn chưa thể chạy khi chưa compile.

## Files thay đổi và review

- `workers/media-api/`: Worker, generated allowlist/catalog, config, locked dependencies, Env/types, mock/HTTP/runtime tests và local adapter.
- `apps/windows/web/`: MediaAPI client, login/kết nối, source resolver thật, status/buffering, retry giữ vị trí, history migration; không sửa source audio.
- `apps/windows/tests/`, `tests/test_windows_build.py`: regression và build safeguards.
- `scripts/prepare-worker.py`, `scripts/build-windows.py`, `scripts/configure-worker-secrets.py`: chuẩn bị backend/release và thao tác auth user-run. Secrets script chỉ chạy dry-run trong Codex.
- `apps/windows/serve.py`: command cũ gọi backend thật; `--static` hoặc root tùy chọn vẫn chỉ catalog, không có tone fallback.
- Tauri/package version 0.2.0, CSP/API configuration, `.gitignore`, tài liệu/plan/evidence.

Review phát hiện và sửa: mock fetch không bắt được receiver của native Window.fetch (IAB phát hiện); Node fetch không chuyển Host tùy chỉnh (HTTP test dùng node:http thật); Miniflare installed API 5 yêu cầu converter public thay vì signature docs V4; rootPath mặc định làm runtime fail khi chạy từ folder Worker thay vì project root, đã khai báo rootPath rõ ràng và chạy npm test từ đúng folder PASS; retry/ticket refresh cần giữ vị trí và phân biệt local bootstrap với auth production. Lần runtime FAIL được giữ riêng, không đổi thành SKIP. Không có fresh independent reviewer trong lượt này; đây là self-review + tests, chưa phải audit bảo mật bên ngoài.

Source snapshot, audio catalog, delivery manifest, sheet catalog và R2 config phải giữ nguyên hash baseline; kết quả cuối ghi trong evidence v0.2. Media/state/download/upload không bị reset hoặc ghi lại. Không tải/chụp BookVN, không FFmpeg, không live R2 upload/audit/deploy.
