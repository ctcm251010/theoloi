# THEOLOI — Backlog

Theo thứ tự phụ thuộc; chỉ triển khai khi phase tương ứng được giao:

1. Phase 01: nhận/đánh giá kết quả B10 user-run; kiểm tra online Worker/client có sẵn, Range/auth/error; chuẩn bị cấu hình, chi phí/rủi ro và rollback trước xin duyệt live.
2. Phase 02: cài Rust/MSVC/SDK bằng thao tác hệ thống hợp lệ, native EXE/NSIS và kiểm thử máy khác; không gọi browser preview là Windows runtime PASS.
3. Phase 03: closed beta, release artifacts/hash, updater signing/recovery; phân biệt workflow test và release published.
4. Phase 04: ADR mobile/background audio, prototype Android, thiết bị thật; iOS khi có môi trường Apple phù hợp.
5. Phase 05: chọn từng MVP nội dung được phép; không tự xây account/database/microservices cho các ý tưởng tương lai.

Nguồn bản nhạc: BookVN đang restricted, PDF gốc chưa được quan sát; mapping 464/phụ lục và rights review tách riêng. Không tải/chụp/chuyển PNG BookVN. Nhạc cầu nguyện/quick items còn thiếu nguồn hợp lệ không gán nhầm asset khác.

Giới hạn vận hành còn theo dõi: Browser Use tự điều hướng local bị ERR_BLOCKED_BY_CLIENT nhưng tab thủ công hoạt động; 8 whitespace warnings trong source/docs/types cũ được giữ nguyên; clean clone thiếu operational datasets theo thiết kế.

Phase 01 có thể tách type contract Worker khỏi typeof generated production JSON nếu cần source-only typecheck toàn bộ; hiện full typecheck cần prepare authorized inputs. Clone nghiệm thu cũng có npm allowScripts warnings với esbuild/workerd; xác minh native bundle/runtime trong phạm vi phase phù hợp, không tự nới policy toàn hệ thống.
