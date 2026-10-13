# THEOLOI tasks

## AudioTP1.0.1 — IN PROGRESS

- [x] Người dùng xác nhận đúng bản cầu nguyện và quyền phục vụ nhóm AudioTP.
- [x] Registry/manifest/state upload riêng, dry-run/retry/hash/Content-Type test; một object prayer uploaded/verified, không tải lại nguồn.
- [x] Worker supplementary/update API và frontend Nghe nhanh/player chung; 67 frontend,35 Worker/typecheck PASS; Python223 PASS/4 SKIP.
- [x] Native updater ký file và ràng buộc phiên bản; fixture tự tạo kiểm tra signature/tamper/version replay/header. Đang kiểm chứng lại Rust/release build.
- [ ] Build EXE/NSIS1.0.1 ký updater, artifact/hash/secret scan và review cuối.
- [ ] Publish installer private R2, deploy API giữ auth epoch3/serving, smoke live có giới hạn.
- [ ] Git/release1.0.1 và bàn giao; nghiệm thu native cập nhật/cài đặt trên máy khác ghi riêng.

## Tải riêng audio cầu nguyện — DONE local /13-10-2026

- [x] Theo URLour_wish người dùng cung cấp: tải đúng một HLS/7 segment, AAC stream-copy sang `media/prayer/watv/vi/our-wish/our-wish.m4a`;69.427664s,1123614bytes, full decode PASS và SHA-256 lưu trong verification.json cạnh file. Không sửa whitelist pipeline production hoặc gọi fullbatch.
- [x] Catalog/manifest và hai SQLite gốc hash giữ nguyên; không đăng ký assetId, sửa Nghe nhanh, upload R2 hoặc build EXE. Audio/verification/evidence ignored không đưa vào Git. Bước tiếp theo là nghe xác nhận nội dung và chốt phạm vi tích hợp riêng; không tự bắt đầu.

## Task phát hành1.0.0 — DONE

- [x] User duyệt review/merge/GitHub Release; repository private giữ nguyên, không Cloudflare mutation.
- [x] Review độc lập Phase01/02 không Critical/Important; PR#1 merge6158cf9.
- [x] App version1.0.0 đồng bộ, build EXE/NSIS, Python190 PASS3 SKIP/frontend60/Worker25/typecheck/Rust6;983media/18metadata nguyên vẹn, stage secret scan sạch.
- [x] Audit index/history sạch, release branchc783ad9; PR#2 merge0f49c91, tree khớp source đã test/build; main frontend60 PASS.
- [x] Tagv1.0.0 đã push/remoteSHAkhớp; clean-clone frontend60/Worker22 PASS3 private-input SKIP/typecheck PASS.
- [x] Release người dùng đã publish; bổ sung đúng4file bằng Chrome Bang, Assets6 và digestGitHub của cả4file khớp local. Blocker upload đã hết; không đổi tag/quyền hoặc upload media/credential.

## Phase02 online follow-up — READY FOR REVIEW /13-10-2026

- [x] Theo yêu cầu đổi mã chung ngắn: API/UI/DPAPI/helper4–256; code-only giữ signing key; live hash cập nhật và epoch3 thu hồi phiên trước đổi mã; login/catalog983 smoke PASS. Frontend60/Worker25/Python190 PASS3 SKIP/Rust6 PASS; build ONLINE mới tại042837062795Z, không đổi983 media/18 metadata. Chi tiết [nghiệm thu](phase02-online-beta.md).

- [x] Người dùng duyệt bốn bước online; xác minh account/bucket private/member Active bằng Chrome Bang, không mời lại hoặc tăng quyền.
- [x] Chặn helper secrets chạy sai account; sáu test mock PASS và dry-run không network.
- [x] Người dùng Authorize đúng account và bootstrap secret; deploy disabled rồi serving authenticated; health/auth/CORS5 checks PASS, không thay bucket.
- [x] OAuth user-run thành công; CLI thấy đúng login/account. Read-only xác minh Worker chưa tồn tại; không deploy nhầm account.
- [x] Nhớ đăng nhập: DPAPI current-user/origin, native IPC giới hạn, queue/logout/checkbox, OS lock/crash recovery; independent re-review không còn Important/Critical.
- [x] Build ONLINE EXE/NSIS, stage983 real IDs/0 media, portable TEMP/PATH tối thiểu startup; đã mở cho user nhập mã.
- [x] User xác nhận ONLINE hoạt động/tự kết nối lại sau restart; bổ sung auto form lần đầu theo feedback, frontend59 PASS và targeted review sạch; rebuild artifact cuối.
- [ ] User nghiệm thu Play/seek/restart nhớ/xóa/native và installer/máy đích. Không dùng kết quả LOCAL/TEST thay live acceptance.
- [x] Cập nhật nghiệm thu/integrity/secret scan/Git theo [checklist](superpowers/plans/2026-10-13-phase02-live-online.md); source và test fix đã push; không Phase03.

## Phase01 — 13/10/2026 / READY FOR REVIEW

- [x] Đọc Phase00/context/B10 lịch sử; bảo toàn983 media và18 metadata/state hashes.
- [x] Public Worker contracts + boundary validation; clone typecheck không private JSON, bundle thiếu inputs vẫn FAIL đúng thiết kế.
- [x] Streaming/Range/HEAD/conditional/errors/readiness, CDN no-store và operation-count tests.
- [x] Ticket RAM reuse/coalescing, expiry seek, logout/renewal/reconnect cancellation; không credential/disk audio cache ở client.
- [x] TDD findings review độc lập; focused re-review không còn important finding.
- [x] Offline regression, workerd mô phỏng/local HTTP ba M4A thật và clean-source clone/typecheck; báo riêng SKIP/browser/native/live.
- [x] Vận hành/chi phí/request/required-secrets bootstrap/rollback/live checklist; không chạy live.
- [x] Exact-index audit193 files/0 finding, Gitleaks staged/history sạch; source4fc4d8d đã push, remote SHA khớp. Published clone typecheck/Worker21 PASS2 SKIP/frontend49 PASS, working tree sạch; xem Phase01.
- [ ] User review quyền phục vụ/chi phí/deploy, live API/WebView2 playback không có media local trước DONE.
- [x] PR Phase01 #1 OPEN, không merge; Phase02 branch riêng từ637fbd1, không phân kỳ.

## Phase02 — 13/10/2026 / READY FOR REVIEW

- [x] Người dùng cài Rust/MSVC/SDK; preflight READY, WebView2 có sẵn.
- [x] Staging allowlist/config override, HTTPS production origin, source config không bị builder sửa; artifact freshness/PE/hash và tests offline.
- [x] Debug catalog-only/TEST fixture rõ ràng, API origin khóa theo bản cài; không fake audio dưới title thật.
- [x] Native navigation/popup policy và Rust unit test; Cargo.lock tạo từ build thật.
- [x] Build debug và release/NSIS TEST; cài/gỡ current-user trong tmp, startup WebView2 PASS.
- [x] Chrome Bang mock playback/seek/tabs/quick/search/reload/favourite/history/network/reconnect/responsive; một player.
- [x] Final artifact, integrity983/18, source-only verification, secret scan và docs. Source7da2d00; clone Python101 PASS/3 SKIP, frontend52, Worker21 PASS/2 SKIP/typecheck, metrics1.
- [x] Publish Phase02 branch: source7da2d00 remote SHA khớp; main ef7f50d và Phase01 637fbd1 không đổi. Commit ledger bàn giao theo sau; không merge main.
- [ ] Native UI interaction, máy Windows sạch, signing và live API acceptance: cần môi trường/quyền riêng; không coi browser/mock là PASS thay thế.

### Phase02 follow-up — thư viện thật trên máy

- [x] Sửa bàn giao TEST-only: LOCAL build dùng đúng public projection của983 audio, không sample/fake asset hoặc sửa catalog/manifest gốc.
- [x] TDD native local bootstrap/CORS opt-in, anonymous media Origin, tự kết nối/retry không cần mã; production giữ HTTPS.
- [x] Launcher một lần bấm, hash/port/lifecycle/Windows byte lock; review lỗi mở trùng đã sửa và targeted re-review không còn blocking finding.
- [x] EXE/NSIS LOCAL build thật, native session/catalog200; giữ app mở cho người dùng, không claim native Play/seek PASS khi CUA không expose native UI.
- [x] Full Python188 total/185 PASS/3 SKIP, frontend53, Worker24/typecheck; không deploy R2 hoặc Phase03.

## Repository foundation — 12/10/2026

- [x] Đọc context/kiểm kê; giữ runtime paths và local data.
- [x] Init Git main, fetch origin chỉ định; chưa có remote refs.
- [x] Tài liệu THEOLOI, ignore và templates không chứa secret.
- [x] Audit exact index/Gitleaks và independent review; chạy lại scan sau final restage.
- [x] Python 167 PASS/2 SKIP, frontend 37 PASS, Worker 15 PASS + dry-run/typecheck, metrics 1 PASS, validators và full 983 hashes PASS, 18 input/state hashes không đổi.
- [x] Browser UI smoke mới trên tab người dùng mở thủ công (Chrome Bang): 485/485/13, search/clear, silent19977, pause/seek/resume và chuyển tab; một player, không console warn/error. Điều hướng tự động vẫn ERR_BLOCKED_BY_CLIENT, chưa biết thành phần chặn.
- [ ] Native build — BLOCKED preflight: thiếu cargo/rustc/MSVC/Windows SDK; không coi là PASS.
- [x] Commit/push source main thành công: `4dd8065fb6322a0c828fe9e3969db414b0a53d35`; `ls-remote` khớp local HEAD. Commit docs bàn giao sau đó không thay runtime/data.

## Follow-up

- [x] Owner `.git`: người dùng chạy owner correction thành công (424 processed/0 failed); Get-Acl trả Sunny và Git thường chạy sạch, không còn dubious ownership.
- [x] Đọc B10 user-run11/10 PASS983 inventory/HEAD metadata; không phải full SHA remote hoặc audit mới.
- [ ] Source/rights review trước deploy/phân phối.
- [ ] Worker live/client config và live playback.
- [ ] Native toolchain/build/installer/máy sạch/signing.
- [ ] Sheet rights/mapping, mobile research theo roadmap.

## Master roadmap — Phase 00

- [x] Lưu MASTER_ROADMAP nguyên văn; bổ sung ranh giới phase vào AGENTS/README và hệ thống docs hiện có.
- [x] Clone remote main vào tmp/phase00-clean-clone-20261012, tạo venv mới và npm ci cả hai packages; không sửa lockfiles.
- [x] Reproduce thiếu private manifest/generated JSON và test giả định tmp có sẵn. Tách manifest integration khỏi status mock, demo dùng tempfile/audio fixture; không sửa pipeline production.
- [x] Nghiệm thu source-only clone: Python92 PASS/2 SKIP; frontend37, service12, metrics1. Full Python workspace168 PASS/2 SKIP; integrity983/18 không đổi. Clone full Worker typecheck FAIL thiếu private generated JSON, ghi rõ precondition.
- [x] Review độc lập không có finding; audit185 tracked files và Gitleaks không leak; source11543ed đã push và clone/remote SHA khớp. Published clone Python92 PASS/2 SKIP, working tree sạch; cập nhật DONE và đề xuất Phase01, chưa bắt đầu.
