# THEOLOI tasks

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

- [ ] Owner `.git`: user đã cho phép sửa riêng `.git`, nhưng Windows Access denied; lệnh Administrator và verification trong repository-audit.md. Commit/push dùng safe.directory giới hạn từng tiến trình.
- [ ] B10 remote user-run; local hash/B9 không thay remote-content audit.
- [ ] Source/rights review trước deploy/phân phối.
- [ ] Worker live/client config và live playback.
- [ ] Native toolchain/build/installer/máy sạch/signing.
- [ ] Sheet rights/mapping, mobile research theo roadmap.
