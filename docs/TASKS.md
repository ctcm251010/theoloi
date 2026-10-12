# THEOLOI tasks

## Phase01 — 13/10/2026 / READY FOR REVIEW

- [x] Đọc Phase00/context/B10 lịch sử; bảo toàn983 media và18 metadata/state hashes.
- [x] Public Worker contracts + boundary validation; clone typecheck không private JSON, bundle thiếu inputs vẫn FAIL đúng thiết kế.
- [x] Streaming/Range/HEAD/conditional/errors/readiness, CDN no-store và operation-count tests.
- [x] Ticket RAM reuse/coalescing, expiry seek, logout/renewal/reconnect cancellation; không credential/disk audio cache ở client.
- [x] TDD findings review độc lập; focused re-review không còn important finding.
- [x] Offline regression, workerd mô phỏng/local HTTP ba M4A thật và clean-source clone/typecheck; báo riêng SKIP/browser/native/live.
- [x] Vận hành/chi phí/request/required-secrets bootstrap/rollback/live checklist; không chạy live.
- [ ] Audit/commit/push source branch và xác minh published source — xem báo cáo Phase01 cho kết quả cuối.
- [ ] User review quyền phục vụ/chi phí/deploy, live API/WebView2 playback không có media local trước DONE.
- [ ] Phase02 chưa bắt đầu; đề xuất native toolchain/build/NSIS/máy sạch sau review.

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
