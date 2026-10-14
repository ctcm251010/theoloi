# AudioTP1.1.0 — Offline Downloads & Startup Updates

Ngày15/10/2026, Asia/Bangkok. **DONE phát hành1.1.0 và user native update acceptance; máy sạch READY FOR REVIEW.** Người dùng đã duyệt source/deploy API/test một bài thật, xác nhận offline cơ bản ổn, sau đó duyệt bước4GitHub Release và bước5bật update. Không đổi serving/auth/credential/private bucket hoặc983media. Các đoạn chuẩn bị/chưa publish phía dưới giữ lịch sử; kết quả thực tế cuối nằm ở đây.

## GitHub Release và kênh cập nhật đã hoàn tất

- [PR#5](https://github.com/ctcm251010/theoloi/pull/5) MERGED; merge `f4774dd4cce9b3970320a350bb0306daebd07f28` tree khớp source `c3d76ec0228bcdfc8a71f048bf4ac5b7a56a6d45` đã build. Tagv1.1.0 trỏ merge commit, không thay tag cũ. [Release1.1.0](https://github.com/ctcm251010/theoloi/releases/tag/v1.1.0) Latest có5file setup/portable/.sig/HUONG-DAN/SHA256SUMS và2sourcearchives. API GitHub xác nhận5digest/dung lượng khớp local; không chỉ phát source ZIP. Evidence `logs/repository-audit/v1.1.0-published-assets.json`.
- Publish create-only đúng installer2.0MB vào R2 private, fullGET/hash verified; không PUT audio hoặc thay983originalstate. Metadata1.1.0 chỉ ở ignored delivery/generated; secrets được tool sử dụng qua cơ chế hiện có, không đọc/in nội dung. Worker deployment `521e48b2-f38f-4229-82e2-d3498b47e425`; config hậu kiểm giữ auth epoch3/origins/session43200/limiters10và180/servingtrue/MEDIAaudiotp-media. Không đổi visibility repo (đang Public) hoặc bucket.
- **32livechecks PASS**: public old versions→1.1.0/current204; authenticated1.0.1/1.0.3→signed1.1.0, signature bằng đúng local verified .sig; installer401 khi thiếu auth, fullGET200/1.948.675bytes/SHA `909534f5c1594d84fc8001e9cece1622a26f6b16743418590a34f57180540192`,private no-store; catalog/offline983,corebytes2.506.137.889,prayer2,guide1Range1024bytes/identity. Không chạy installer qua smoke; evidence `v1.1.0-live-smoke.json`, `v1.1.0-update-deploy.txt`, `v1.1.0-update-config.json` local-only.
- Test release: frontend95 PASS,Worker40/typecheck PASS,Python225 PASS4platformSKIP,Rust41 PASS3ignored có chủ đích, explicit final signature1PASS/live engine1PASS. History26commits/index246paths/Gitleaks sạch; `.env.example` người dùng giữ nguyên ngoài commit.983media/18metadata hậu kiểm SHA không đổi. Offline GUI user acceptance là “khá ổn” ở build trước network feedback; sửa feedback được3regression và ChromeTEST xác minh. Không đánh đồng với clean-machine hoặc mọi native control trên final build.
- Người dùng1.0.1/1.0.3: Settings→Kiểm tra cập nhật→Cập nhật; chưa có thông báo tự động trong EXE cũ.1.0.0 cần setup mới một lần.1.1.0 trở đi có startup notification cho phiên bản sau. Native actual updater install/restart giữ favourites/history/DPAPI/cache và máy sạch chưa được nghiệm thu; không ghi PASS cho chúng. Authenticode vẫn NotSigned, chữ ký updater là lớp riêng.

Task phát hành được hoàn thành trong phạm vi đã duyệt. Tiếp theo đề xuất nghiệm thu nâng cấp bản đã cài, máy khác và mạng yếu; không tự bắt đầu phase mới.

**User acceptance sau publication15/10:** người dùng trả lời câu hỏi thử Settings→Kiểm tra cập nhật→Cập nhật từ bản1.0.3: “Đã lên1.1.0, dữ liệu vẫn còn”. Ghi PASS cho cập nhật native/mở lại và giữ dữ liệu theo xác nhận user trên máy hiện tại. Đây bổ sung cho giới hạn native install chưa nghiệm thu trong bản ghi trước đó; không phải agent tự quan sát GUI, kiểm kê từng field hay clean-machine acceptance. Bước tiếp theo còn máy Windows khác, mạng yếu và theo dõi usage sau phân phối; dừng chờ phạm vi mới.

## Cập nhật sau user acceptance và phê duyệt phát hành

Người dùng đã thử EXE và trả lời “khá ổn”, góp ý khi mất mạng bấm Nghe online thiếu phản hồi nhìn thấy. Root cause: `announce` là sr-only, connection notice lại bị hidden khi có cache nghe được. Sửa dùng lại inline notice, thông báo kiểm tra Internet/giữ nghe offline, nút Đang kết nối, clear khi network return/switch thành công/Settings login; không popup, đổi focus hoặc dừng bài cached.3 regression RED→GREEN;frontend95 PASS/browser TEST failure/recovery PASS, Windows Python64 PASS2SKIP. Reviewer không Critical/Important; góp ý stale notice khi Settings reconnect đã có regression và sửa.

Yêu cầu mới cho phép thực hiện bước4push/review/merge/tag/GitHub Release rồi bước5private installer publication/deploy update metadata, giải thích từng mốc. Trạng thái phía dưới trước publication là lịch sử. Repository quan sát qua GitHub đang **Public**; không đổi visibility. Chỉ source/EXE/setup/signature/guide/hash được phát hành, không audio/credential/private operational inputs. User acceptance cơ bản không chứng minh clean machine hoặc toàn bộ updater install matrix.

## Nghiệm thu live sau phê duyệt15/10

- Reviewer độc lập: không Critical/Important chặn deploy; rà manifest core/auth/Range/old updater/native contract. Giữ `generated/updates.json`1.0.3, không công bố1.1.0.
- Wrangler4.149.0 xác nhận member nguyenducbang.uit/account ctcm251010; version trước `4b3c5c16-04b8-4faa-a30c-a0d24ec59b66`, version mới `52e19593-8136-41b7-9961-58fe9078c00d`. Deploy `--strict --keep-vars --var SERVING_ENABLED:true`; đối chiếu hậu kiểm giữ epoch3, SESSION_SECONDS43200, exact origins, limiters10/180 và MEDIA→audiotp-media. Không đọc/rotate secrets hoặc sửa public access.
- **18 live checks PASS**: health200/auth401/origin403, manifest983 exact ID/size/hash/type và no-store/không private key, supplementary2, old1.0.1 update vẫn1.0.3,1.0.3 không nhận thông báo1.1.0. Manifest chỉ metadata, không LIST/probe983objects.
- **Native Rust explicit live test1 PASS** dùng đúng production origin và downloader/protocol source, session qua stdin chỉ trong RAM. Chọn guide main1, asset `watv:vi:guide:4177`,2.027.172bytes, SHA `ff9c2ad0d53e908a1f156561f15c16f00894b8b59f072324ee5aa53151d63393`. Hai lượt tải cùng một bài vào `tmp/live-offline-*/offline-v1`, tổng4.054.344audio bytes; kiểm tra SHA/promote, không lưu session, mở lại không auth, HEAD/first/suffix Range, skip với session sai chứng minh không xin vé/tải lại, xóa local rồi tải lại PASS. Không sửa cache người dùng/983media/R2.
- Test mới `live_single_asset_download_restart_ranges_skip_remove_retry` được `#[ignore]` rõ ràng; suite mặc định không bao giờ tự dùng mạng. Log an toàn: `offline-live-api.json`, `offline-live-native.json`, `offline-live-native-test.txt`, deploy/config/secret/index/integrity trong `logs/repository-audit/` (local-only).
- Frontend92/Worker40/typecheck/Python225PASS4SKIP; Rust suite mặc định41 PASS,3 ignored có chủ đích gồm helper/artifact/live; live test chạy riêng1PASS và final installer signature chạy riêng1PASS. Gitleaks commit range không leak, index245paths không forbidden;983media +18metadata SHA không đổi. Preview version lấy package metadata1.1.0 thay hardcode1.0.3, có regression test. Artifact SHA/bytes vẫn khớp cả ba file; thay đổi Rust mới chỉ ở module test, không sửa production binary.
- Final production EXE khởi động12s Responding/title AudioTP, không báo stderr. Công cụ Windows vẫn `native pipe unavailable (os error2)`; đã mở EXE và nhờ người dùng xác nhận play/pause/seek/restart khi mất mạng. **Chưa ghi GUI playback/clean machine/updater install là PASS.** Native test gọi engine Rust, không đi qua UI/IPC/WebView2.

GitHub push/PR/merge/tag/Release, private installer upload và metadata update1.1.0 **chưa thực hiện**. Bản1.0.3 vẫn là bản thông báo cập nhật hiện hành. Chờ native GUI acceptance trước quyết định phát hành; phần dưới giữ bằng chứng build/test trước deploy.

## Artifact cuối để review

Thư mục `release/windows/1.1.0-20261014T205105238937Z/` (build stamp UTC, ngày local15/10). Đây là bản cuối có pacing/backoff và visible network feedback; không chọn bản intermediate193441/203538 hoặc TEST để phân phối.

| File | Bytes | SHA-256 |
|---|---:|---|
| `AudioTP.exe` |5,006,848 |`25832b9819e5e3a51cb801482d8add42bb4f3a7bcef97f751fd5f17f77e948fc` |
| `AudioTP_1.1.0_x64-setup.exe` |1,948,675 |`909534f5c1594d84fc8001e9cece1622a26f6b16743418590a34f57180540192` |
| `AudioTP_1.1.0_x64-setup.exe.sig` |436 |`626f39f6a113af5c3e7487bb78e47998b79c18254c00a896b592271f874bfe2f` |

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

**Cập nhật API:** trạng thái chưa deploy trong handoff ban đầu đã được thay bằng deployment/test ở đầu báo cáo. Online giữ nguyên; API tải offline đã live. Không công bố1.1.0 như đã nghiệm thu GUI đầy đủ và không thay update metadata1.0.3. Các bản cũ chưa được thông báo1.1.0.

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
