# Phase02 — AudioTP Windows Beta

Ngày: 13/10/2026, Asia/Bangkok. Status: **READY FOR REVIEW** — source và TEST artifacts đã kiểm tra; native playback/máy sạch/live chưa nghiệm thu, chưa DONE.

Phase02 bắt đầu trên `phase/02-windows-installer`, parent `637fbd182f5cceef431b079ac131d577edfef1bb` của Phase01. [PR Phase01 #1](https://github.com/ctcm251010/theoloi/pull/1) OPEN, chưa merge. Phase01 vẫn READY FOR REVIEW: source/offline hoàn tất, live R2/API chưa nghiệm thu. Không deploy, thay Cloudflare, đọc credential hoặc phân phối thư viện thật.

## Bổ sung sau review người dùng — Bài ca mới thật trên máy

Bàn giao trước chỉ có TEST catalog4 track, không đáp ứng việc nghe Bài ca mới thật trong EXE. Đã sửa bằng chế độ build `--local-library`: dùng projection983 track hiện có (485 guide/485 instrumental/13 silent), assetId thật, không lấy âm mẫu hoặc thay catalog/manifest/media gốc. Identifier `org.audiotp.local` tách TEST và production. Production giữ HTTPS; LOCAL cần explicit127.0.0.1 origin, chưa phải online/R2 live.

**Mở bằng `Mo-AudioTP.cmd` tại root workspace**, không mở bản TEST cũ. Launcher kiểm tra hash artifact, tự mở Node backend read-only rồi EXE và app tự kết nối, không cần mã. Windows byte lock giữ xuyên suốt backend+EXE để không mở trùng; chỉ dừng backend do chính launcher tạo. Backend có sẵn/cổng chương trình khác được bảo toàn. Readiness gọi thẳng loopback, không proxy hoặc redirect. Native CORS chỉ opt-in `--desktop` với exact origins; media gửi anonymous Origin. Log chỉ có fixed route/method/status, không token/query/header/body.

Artifact LOCAL: `release/windows/LOCAL-0.2.0-20261013T021343012529Z/`. EXE3,122,176 bytes, SHA256 `297f62c04d6ff1c7404f1ae00e1d9c4fde6dcffa8b075e82608a7f97e4d9c591`; NSIS1,142,635 bytes, SHA256 `b70c5f28917dc24c52cd64ec76327435c2fdbdfd42d3286c0f506c505345298d`. Build exit0, stage không có M4A/WAV, catalog không có test:*; config nguồn không bị builder sửa. Không phân phối bản LOCAL cho máy khác vì launcher/backend cần workspace/Node/Python/media. Mở trực tiếp EXE hoặc shortcut installer cần backend đã chạy.

Validation follow-up: Python188 total/185 PASS/3 symlink SKIP; frontend53 PASS; Worker24 PASS/typecheck PASS, gồm native-origin preflight/session/catalog983/real media206 và full-byte SHA cho guide/instrumental/silent. Launcher7 PASS, cross-process lock đã được reviewer kiểm tra trên Windows. Review lỗi hai launcher dùng chung backend đã được sửa, targeted re-review không còn blocking finding. Integrity983/983 media SHA/size,18 metadata/state không đổi.

EXE LOCAL đã thực sự chạy/WebView2, `Responding=true`. Log native-origin sau startup ghi OPTIONS204, POST `/v1/local-session`200, GET `/v1/catalog`200. Chứng minh EXE đã kết nối backend/catalog thật; **chưa chứng minh thao tác Play/seek native**. CUA vẫn apps=[]; Chrome tự mở cổng8872 bị ERR_BLOCKED_BY_CLIENT. Tab người dùng mở sẵn8766 đang phát bài148 thật được giữ nguyên, không thao tác/gián đoạn. Không dùng browser hoặc process startup thay native playback acceptance. Log local `logs/repository-audit/phase02-real-*`, backend `logs/windows-local/`.

Theo dõi: native Play/seek trên cửa sổ LOCAL hiện có, máy sạch và online HTTPS/R2 live vẫn pending. Không deploy hoặc Phase03. Bằng chứng TEST lịch sử bên dưới được giữ riêng.

## Phần đã triển khai

- Giữ frontend/player hiện có. Endpoint trong connection.json được cấu hình khi build, khóa trường địa chỉ theo origin/CSP bản cài. Mã truy cập/session/ticket chỉ trong RAM; R2 credential không vào app. Chưa có endpoint production đã nghiệm thu.
- Builder dùng stage allowlist và config override, không sửa config tracked dù build lỗi; kiểm tra public metadata, bỏ provenance nội bộ của quick cards. Không chép media, WAV hoặc thư mục thừa vào frontendDist. PE/freshness/marker scan và SHA-256 trước tạo release folder. Không thay catalog/manifest/audio gốc.
- Cargo.lock từ build thật; CLI2.12.2 và npm lock hiện có. Cargo build dùng --locked. Native window chỉ điều hướng origin frontend nội bộ, chặn popup, không shell/fs/network plugin hoặc capability mới. CSP mặc định đóng; build chỉ thêm API origin đã chọn. NSIS currentUser, WebView2 downloadBootstrapper.
- Debug không endpoint là catalog-only và không thể kết nối/phát. `--test-fixtures` tạo application identifier riêng `org.audiotp.acceptance`, banner TEST và catalog4 track `test:*`. Ba WAV tự tạo sẵn có, mỗi file12 giây, phục vụ qua mock loopback; track silent2 dùng lại WAV silent để thử queue. Không phải 13 bài silent thật hoặc 983 bài WATV. Hai mục cầu nguyện vẫn chưa khả dụng.
- Native mock chỉ phục vụ fixture allowlist với session/ticket ngắn hạn, CORS origin kiểm thử, body/table bounds và GET/HEAD/Range audio/wav. Không import production generated JSON, không R2/network ngoài loopback. Đây là mock hợp đồng client, không thay workerd integration đã có.
- Npm build/installer đi qua builder được kiểm soát; `npm run tauri` dành cho phát triển, không dùng để tạo release phân phối.

## Bằng chứng kiểm thử

| Nhóm | Kết quả / phạm vi |
|---|---|
| Preflight | READY: Rust/Cargo1.99.0, MSVC x64, Windows SDK/UCRT, WebView2; Node24.18.0/npm11.16.0, Tauri CLI2.12.2. Rust crate khóa2.12.3. Người dùng cài công cụ hệ thống. |
| Python full | 180 test:177 PASS /3 SKIP symlink privilege; không live B10. |
| Frontend | 52 PASS gồm API/player/connection races, catalog/storage/quick và mock HTTP. |
| Worker | 23 PASS, typecheck PASS; chỉ mock/workerd/local integration, config live không đổi. |
| Viewer metrics | 1 PASS regression. |
| Rust navigation | 1 PASS; URL ngoài app, file/data/javascript/credential/port bất thường bị từ chối. |
| Clone source-only | Commit7da2d00: Python101 PASS/3 SKIP (1 private manifest,2 quyền symlink); frontend52 PASS, Worker21 PASS/2 private integration SKIP, typecheck/metrics PASS. TEST prepare chạy được khi không có private catalog/manifest. Đây là nhóm Python source-only, không phải full discover. |
| Native debug | EXE build thật, khởi chạy từ working directory tmp; process Responding và WebView2 child. |
| Release/NSIS TEST | Build thật x64; không ký; chỉ acceptance artifact. EXE3,099,648 bytes; NSIS1,120,502 bytes. |
| Cài/gỡ TEST | NSIS /S current-user vào thư mục tmp mới, exit0; EXE installed khởi chạy với WebView2; uninstaller exit0 và EXE installed không còn. |
| Chrome Bang | Fixture WAV12s readyState4/error=null, chỉ1 audio; guide/instrumental/silent/quick, next/pause/seek, search/clear/manual-collapse/highlight, favourite/history qua reload, dark/light. Reload không tự phát/giữ session. |
| Lỗi mạng/reconnect | Dừng đúng mock, chọn bài báo lỗi có retry và audio paused; restart mock làm session mất, app yêu cầu kết nối lại; đăng nhập lại phát được. Không fallback âm khác. |
| Responsive | Requested390×844 và620×600; Chrome có zoom/DPI nên actual innerWidth355/564. Không tràn ngang nội dung; player nằm trong visualViewport (sai số làm tròn <1px). Không coi đây là native window test. |

Log/ảnh local: `logs/repository-audit/phase02-*`, không commit raw evidence. Ảnh browser-desktop/mobile/light/minimum-window và network-error chỉ chứa fixture tự tạo. Các test RED ban đầu thiếu helper/policy đã được tái hiện rồi sửa; không có FAIL còn lại ở các suite trên. Hash EXE installed khác portable đúng3 byte marker Tauri `UNK`→`NSS`; đã so sánh toàn file và xác minh không khác byte nào khác. [Source Tauri bundler](https://github.com/tauri-apps/tauri/blob/dev/crates/tauri-bundler/src/bundle.rs).

## Giới hạn nghiệm thu

- Native UI interaction/audio/seek không được tự động kiểm chứng: công cụ CUA hiện chỉ expose Chrome, apps rỗng. Process/window title/WebView2 startup không chứng minh native playback. Không dùng công cụ ngoài CUA để vượt giới hạn điều khiển UI.
- Chưa có máy Windows sạch/VM không workspace, Rust, Node/Python hoặc media local. Thử portable từ thư mục ngoài workspace và PATH tối thiểu trên máy này chỉ là kiểm tra dependency sơ bộ, không thay máy sạch.
- Chưa thử WebView2 bootstrap trên máy thiếu runtime, ARM64, SmartScreen ngoài máy phát triển, Authenticode, cập nhật hoặc rollback production. Không cài/gỡ runtime hệ thống để giả lập.
- API production chưa deploy/nghiệm thu. TEST backend cần Node/repo để phục vụ fixture; EXE chỉ cần WebView2 để mở. Đây không phải kết nối R2 thật hoặc bản online beta được phép phân phối.

## Bàn giao / bước kế tiếp

Lệnh thực tế ở [Windows README](../../apps/windows/README.md). Artifact TEST cuối: `release/windows/TEST-0.2.0-20261013T014110189461Z/`, có guide TEST, SHA256SUMS và build-report; không push EXE/media vào Git. Để nghe Bài ca mới thật trên máy, dùng LOCAL/launcher ở phần bổ sung trên.

| Artifact | SHA-256 |
|---|---|
| AudioTP.exe | dd013b7263e597c79bb33288c42bf31e23ce929d1fa821f59af7d485a4c41272 |
| AudioTP Test_0.2.0_x64-setup.exe | b354d4705df19f6b4f33e89e20dab38ef38c31bbcd98a2232876a934bf46f084 |

Integrity cuối:983/983 media,2,506,137,889 bytes; SHA/size khớp và18 metadata/state gốc không đổi. Không đọc credential. Portable cuối đã chạy riêng từ TEMP ngoài workspace với PATH chỉ Windows/System32, title AudioTP/Responding=true và child msedgewebview2.exe; không dùng Node/Python làm runtime EXE. Máy sạch vẫn chưa có.

Source implementation commit: `7da2d00`. Review độc lập và targeted re-review không còn blocking finding; exact-index audit201 files không có private path/content finding, Gitleaks staged/history không phát hiện leak. Log Python clone có ResourceWarning từ HTTPError trong test viewer cũ; không có test FAIL. Không đổi PowerShell execution policy: dùng `npm.cmd` theo hướng dẫn Windows.

Branch `phase/02-windows-installer` đã push; remote source SHA7da2d00266adee264472d531eaa1121990e68db8 khớp. Main ef7f50d và Phase01 637fbd1 giữ nguyên. Commit ledger tiếp theo chỉ cập nhật bằng chứng bàn giao; không merge/deploy. Hai server TEST8870/8871 được dừng sau kiểm thử; preview8766 có sẵn của người dùng được giữ.

Trước Closed Beta: nghiệm thu PR Phase01, phê duyệt riêng quyền phục vụ/chi phí/deploy, user-run live API/Range và nghe đúng asset trên máy không media local; rồi build production với HTTPS endpoint thật. Kiểm thử native UI trên máy đích và máy sạch, WebView2 bootstrap/cài-gỡ, ký mã/chính sách phân phối. Chưa bắt đầu Phase03 hoặc triển khai updater.
