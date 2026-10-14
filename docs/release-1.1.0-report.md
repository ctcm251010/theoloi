# AudioTP1.1.0 — Offline Downloads & Startup Updates

Ngày15/10/2026, Asia/Bangkok. **READY FOR REVIEW — source và artifact local, chưa phát hành/live acceptance.** Người dùng yêu cầu làm tới EXE/setup chuẩn bị đưa GitHub rồi dừng. Không push/tag/Release, upload installer/audio, deploy Worker, đổi serving/auth/credential hay public bucket trong lượt này.

## Artifact cuối để review

Thư mục `release/windows/1.1.0-20261014T193441266227Z/` (build stamp UTC, ngày local15/10). Đây là bản cuối có pacing/backoff; không chọn bản intermediate191653 hoặc TEST để phân phối.

| File | Bytes | SHA-256 |
|---|---:|---|
| `AudioTP.exe` |5,006,848 |`84331a82b5c247421253618ef3fcc5ea8784b3be18b8247194280520a48c9510` |
| `AudioTP_1.1.0_x64-setup.exe` |1,948,420 |`052705592ed7c7928398d9f2fcd01f6c2b362e9614a2f5acc14bd1992790faeb` |
| `AudioTP_1.1.0_x64-setup.exe.sig` |436 |`3877b4082a080b1b1997c314671f0c36253e81203bd7c9b7b9344e2c8a6ccdc0` |

EXE/NSIS build exit0, file PE/hash/allowlist checks PASS, HUONG-DAN khớp guide source, không M4A/WAV/HLS/private key. `.sig` thật qua official updater verify bằng public key hiện hành và signed version1.1.0, byte tải loopback khớp installer, không gọi install. Publisher **dry-run** PASS, không tạo update metadata hoặc request Cloudflare. Windows Authenticode vẫn **NotSigned**, khác với chữ ký updater.

## Phạm vi đã triển khai

- Native Rust quản lý cache `app_local_data_dir/offline-v1`, manifest riêng, queue riêng; không trộn state vào catalog nguồn. Một worker, tải theo assetId, giữ `.part`, size/SHA-256, Range/If-Range/ETag và atomic rename. Có disk preflight +64MiB dự phòng, pause/resume/cancel/retry, giữ phần hoàn tất khi mất mạng/mở lại, xóa riêng/chọn/nhóm/toàn bộ local. Không nhận path/objectKey/URL tùy ý qua IPC.
- Protocol offline phục vụ đúng file đã xác minh qua handle chống reparse/hardlink/write races, GET/HEAD/Range, tối đa4MiB mỗi response và4 request đồng thời; kiểm tra SHA khi mở để phát. Startup hash chạy nền, không yêu cầu đăng nhập. Poll dùng metadata để tránh hash983 file mỗi giây; playback và lệnh download-skip xác minh nội dung lại.
- UI Settings bánh răng riêng Bộ lọc, Nghe offline/online, icon tải/check/lỗi cạnh tim, popover tải có số bài/bytes, tiến độ và xác nhận xóa. Full manifest ẩn tải chung; xóa hiện lại. Search/favourites/history/queue và cả ba tab chỉ lấy file khả dụng khi offline. Không có player thứ hai hoặc audio thay thế.
- API source mới: authenticated `/v1/offline-manifest` chỉ trả core tracks/assetId/bytes/SHA/contentType, không objectKey/sourceURL/credential, không probe R2. `/v1/release-info/windows-x86_64/:version` công khai duy nhất số phiên bản mới hơn; installer/catalog/audio vẫn xác thực. Worker giữ gates/rate-limit/no-store.
- Startup updater im lặng khi latest/offline/timeout; modal giữa cửa sổ, Để sau và kiểm tra thủ công; progress scoped. Bấm install luôn kiểm tra signed metadata đã xác thực mới, official Tauri updater2.13.3 +Minisign +signed version, Windows restart flag. Không tải/chạy EXE tùy ý, không Authenticode/UAC/SmartScreen bypass.

Hai prayer bổ sung vẫn online, ngoài phạm vi tải983 core. Không thay assetId/objectKey/983 media/catalog/manifest gốc. File `.env.example` có thay đổi của người dùng từ trước được giữ ngoài staging, không đọc nội dung.

## Lỗi đã tìm và sửa

1. Logout phải hủy cả bearer native và sync/download đang chờ. Hủy có generation phía Rust/JS; frontend bypass hàng đợi để không phải đợi một request mạng mới hủy được.
2. Full cache cũ không được coi là đầy đủ khi bundle mới có revision khác; giữ file đã tải nhưng yêu cầu làm mới manifest hiện hành. Không hardcode983 làm điều kiện full.
3. Để sau trong signed pre-install check phải hủy intent install, không chỉ đóng modal. Late callback bị loại; event listener được dọn.
4. Windows có thể giữ cùng size/mtime/ctime sau ghi nhanh; kiểm chứng66/200 lần với nanosecond stat. Bỏ cache fingerprint ở adapter preview, native hash lại trước phát/skip. Test lỗi cũ tái hiện RED→GREEN.
5. Server fixture Winsock kế thừa socket nonblocking có thể đóng HTTP header chưa đủ, gây10053 ngẫu nhiên. Accepted stream chuyển blocking; native HTTP failure/resume tests chạy ổn, không nới bảo vệ mạng production.
6. Resume ngay sau pause có thể bị callback cũ đưa item lại paused. Worker tôn trọng trạng thái resume mới. ETag thay đổi liên tục có giới hạn restart, không lặp tải vô hạn.
7. Giới hạn180 request/phút/IP cần pacing500ms và backoff429/Retry-After tối đa hai lần. Hủy trong lúc chờ được; delay quá300s hoặc mạng/API không khả dụng giữ completed, dừng phần queue còn lại để thử sau, không fail hàng trăm bài liên tiếp. Không tăng limiter live.

## Bằng chứng kiểm thử

| Phạm vi | Kết quả |
|---|---|
| Frontend Node |92 PASS,0 FAIL,0 SKIP |
| Worker Node/workerd + local adapters |40 PASS,0 FAIL,0 SKIP; typecheck PASS |
| Python full regression |229 total:225 PASS,4 symlink SKIP,0 FAIL |
| Native Rust |41 PASS,0 FAIL,2 explicit helper/artifact checks ignored by default; helper lock chạy riêng trong parent test |
| Chữ ký artifact thật |1 explicit PASS trên final installer; official updater download từ loopback, verify public key/signed version, so byte; không gọi install |
| Data integrity |983 files/2,506,137,889 bytes size/SHA PASS;18 original metadata/state unchanged; `offline-integrity.json` |
| Browser Chrome Bang |Tự mở localhost; real preview guide1 currentTime22s/readyState4/duration125.016s. UI TEST partial/full/search/favourite/pause/resume/skip/count/delete/ẩn-hiện tải, startup update/defer/manual/progress; không giả lập filesystem playback trong browser |
| Responsive |Desktop và viewport nhỏ; measured innerWidth355px/documentWidth341px, không tràn ngang. Fixture TEST có banner riêng |
| Installer TEST |0.2.0→1.1.0 tại tmp riêng: cả hai exit0; manifest+WAV fixture SHA giữ nguyên. TEST WebView2/Responding/cache lock PASS; gỡ exit0 giữ cache, installed EXE không còn |
| Production native |Final portable TEMP/PATH chỉWindows, một EXE, quan sát10s, Responding=true/WebView2 child1/titleAudioTP; tương tác player Windows và native updater install end-to-end chưa nghiệm thu |

Hai entry Rust ignored có chủ đích: child helper do parent chạy hai subprocess; kiểm tra chữ ký build thật cần chỉ định thư mục release và chạy riêng. Không bỏ qua test hỏng để làm xanh. Python ResourceWarning từ fixture font benchmark là cảnh báo ở suite có sẵn, không phát hiện lỗi test.

## Giới hạn và điểm dừng

Computer Use Windows báo native pipe unavailable (`os error2`), đã thử lại API được tài liệu hỗ trợ; không tự chạy helper ngoài tài liệu hoặc điều khiển UI bằng shell/CDP. Chrome kiểm thử được bình thường. Vì vậy không gọi native playback/pause/seek/offline GUI hoặc updater tự cài thực tế là PASS. TEST installer filesystem preservation không thay cho nghiệm thu nâng cấp production với favourites/history/credential thực trên máy khác.

Một lần smoke intermediate không còn process khi kiểm tra lại, nguyên nhân chưa xác định; lần thử lại ổn. Final artifact được quan sát trực tiếp10s và dừng đúng process do agent tạo sau kiểm tra. Không dùng smoke process để thay cho native E2E hoặc clean-machine acceptance.

**API mới chưa deploy**: bản build dùng endpoint HTTPS thật nhưng server live vẫn source cũ. Online hiện có giữ nguyên; tải offline từ R2 cần deploy route mới sau review. Không công bố1.1.0 như đã dùng đầy đủ qua production và không thay update metadata1.0.3 trong lượt này. Các bản cũ chưa được thông báo1.1.0.

GitHub repo private đã xác minh từ remote: `ctcm251010/theoloi`. Branch làm việc `feature/offline-downloads-updates`, nềnb361659. Chưa publish/push/tag. Tài liệu học và command thực tế: [Nghe offline/build/release](offline-updates-guide.vi.md), [hướng dẫn người dùng](windows-user-guide.vi.md). Git/secret audit ghi sau checkpoint local; không thay đổi remote theo điểm dừng người dùng.

Audit staged44 source/docs paths:0 forbidden paths, không stage `.env.example`, media, operational/generated datasets, artifact hoặc secret. Gitleaks staged0 leak; diff-check sạch. Lưu checkpoint local trên feature branch, giữ remote/main/tag/Release nguyên trạng. Bằng chứng local `logs/repository-audit/offline-*` không commit.

## Sau khi review

1. Duyệt source/artifact; nghiệm thu thao tác Windows offline với fixture hợp lệ, updater và nâng cấp dữ liệu thực trên máy đích.
2. Phê duyệt riêng deploy route API mới, giữ private bucket/serving/epoch/secrets và chưa quảng bá update trước khi native/live test đạt.
3. Live QA phạm vi nhỏ: tải một bài, ngắt mạng, mở lại/phát/tua/xóa/retry; xác minh request/rate behavior. Không Codex bulk983 bài để test.
4. Sau nghiệm thu mới push/PR/merge/tag/GitHub Release, publish một installer private và deploy update metadata1.1.0; kiểm tra app1.0.3 nhận cập nhật và clean-machine install. Không tự mở Phase03/04 đầy đủ.

## File thay đổi

- `apps/windows/src-tauri/src/offline.rs`, `offline_fs.rs`, `offline_tests.rs`; `main.rs`, `updater.rs`, `updater_tests.rs`, Cargo/config/version.
- `apps/windows/web/offline.mjs`, `app.mjs`, `app-updates.mjs`, `api-client.mjs`, HTML/CSS/version/connection; npm metadata đồng bộ1.1.0.
- `apps/windows/tests/`: offline/UI/harness/startup updater/API/mock tests; `native-mock.mjs` chỉ fixture tự tạo.
- `workers/media-api/src/service.mjs`, service/source-runtime/local-integration tests và static/verification adapter `local-preview.mjs`.
- `scripts/build-windows.py`, Windows builder/packaging tests; docs CURRENT_PHASE/TASKS/ROADMAP/CHANGELOG, design/plan, user guide, learning guide và báo cáo này.

Operational source/catalog/manifest/state/media không thay. Build output/log/projection vẫn local-only, không đưa vào Git.
