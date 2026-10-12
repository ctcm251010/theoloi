# THEOLOI tasks

## Repository foundation — 12/10/2026

- [x] Đọc context/kiểm kê; giữ runtime paths và local data.
- [x] Init Git main, fetch origin chỉ định; chưa có remote refs.
- [x] Tài liệu THEOLOI, ignore và templates không chứa secret.
- [x] Audit exact index/Gitleaks và independent review; chạy lại scan sau final restage.
- [x] Python 167 PASS/2 SKIP, frontend 37 PASS, Worker 15 PASS + dry-run/typecheck, metrics 1 PASS, validators và full 983 hashes PASS, 18 input/state hashes không đổi.
- [ ] Browser UI smoke mới — BLOCKED, Browser Use inventory rỗng; HTTP local playback PASS.
- [ ] Native build — BLOCKED preflight: thiếu cargo/rustc/MSVC/Windows SDK; không coi là PASS.
- [ ] Commit/push và xác minh remote SHA.

## Follow-up

- [ ] B10 remote user-run; local hash/B9 không thay remote-content audit.
- [ ] Source/rights review trước deploy/phân phối.
- [ ] Worker live/client config và live playback.
- [ ] Native toolchain/build/installer/máy sạch/signing.
- [ ] Sheet rights/mapping, mobile research theo roadmap.
