# THEOLOI — Backlog

Theo thứ tự phụ thuộc; chỉ triển khai khi phase tương ứng được giao:

1. Phase01 READY FOR REVIEW: source/local hoàn tất, đã đọc B10 lịch sử PASS983 metadata. Còn phê duyệt quyền phục vụ/chi phí/deploy và user-run live API/WebView2 playback không media local; dùng phase01-operations.md, chưa DONE.
2. Phase 02: cài Rust/MSVC/SDK bằng thao tác hệ thống hợp lệ, native EXE/NSIS và kiểm thử máy khác; không gọi browser preview là Windows runtime PASS.
3. Phase 03: closed beta, release artifacts/hash, updater signing/recovery; phân biệt workflow test và release published.
4. Phase 04: ADR mobile/background audio, prototype Android, thiết bị thật; iOS khi có môi trường Apple phù hợp.
5. Phase 05: chọn từng MVP nội dung được phép; không tự xây account/database/microservices cho các ý tưởng tương lai.

Nguồn bản nhạc: BookVN đang restricted, PDF gốc chưa được quan sát; mapping 464/phụ lục và rights review tách riêng. Không tải/chụp/chuyển PNG BookVN. Nhạc cầu nguyện/quick items còn thiếu nguồn hợp lệ không gán nhầm asset khác.

Giới hạn vận hành còn theo dõi: Browser Use tự điều hướng local bị ERR_BLOCKED_BY_CLIENT nhưng tab thủ công hoạt động; 8 whitespace warnings trong source/docs/types cũ được giữ nguyên; clean clone thiếu operational datasets theo thiết kế.

Phase01 đã tách contracts: clone typecheck/workerd PASS không private JSON, không nới npm policy. Production bundle vẫn cần inputs hợp lệ. Theo dõi CPU/request thực tế trước quyết định cache/chi phí mới. Auth mã nhóm chưa thu hồi từng người; ticket còn hạn có thể replay, logout không thu hồi server.
