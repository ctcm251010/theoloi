# THEOLOI — Current phase

Ngày cập nhật: 12/10/2026, Asia/Bangkok.

- Current: **PHASE 00 — Repository Foundation**.
- Status: **DONE**; đã hoàn thành acceptance kỹ thuật Phase 00, đang chờ người dùng giao phase tiếp theo.
- Authorized scope: hoàn thiện và nghiệm thu Phase 00 theo MASTER_ROADMAP; không bắt đầu Phase 01.
- Baseline: `748d180404c44a2cd35b9c40fb44e81e7bac09cc` trên main và origin/main; audit/tests trước trong repository-audit.md.
- Owner `.git`: user-run đổi thành Sunny đã được kiểm tra; Git thường chạy được, working tree sạch trước task này.
- Evidence: clone setup PASS; Python source-only92 PASS/2 SKIP, frontend37, Worker service12, metrics1; full Python workspace168 PASS/2 SKIP. Integrity983 media/18 metadata không đổi. Clone full Worker typecheck FAIL do chưa prepare private inputs; xem báo cáo phạm vi.
- Git: source commit11543ed8071d150b2d0a01871dd95906ba13b6ac đã push; local/remote/clone khớp SHA, clone sạch; Python92 PASS/2 SKIP được chạy lại từ published source. Review độc lập, exact-index audit và Gitleaks PASS. Docs kết thúc phase được commit theo sau.
- Remaining in Phase 00: không còn acceptance task; giới hạn native/live/private inputs được ghi rõ. Không có task Phase 01 đang chạy.
- Plan / acceptance / evidence: [Phase 00](phases/phase-00.md).
- Next proposed after acceptance: **PHASE 01 — Cloudflare R2 & Online Audio**; chờ xác nhận của người dùng.

Ưu tiên Phase 01: (1) đọc kết quả B10 user-run nếu có và kiểm tra asset mapping/config hiện có; (2) audit/reuse API auth/ticket/Range, bổ sung test mạng/lỗi; (3) cấu hình client online không cần media local; (4) chuẩn bị deploy/chi phí/rủi ro/rollback để người dùng duyệt rồi mới live E2E. Không yêu cầu gửi credential qua chat. Thiếu kết quả live không chặn phần code/mock độc lập.

“Tiếp tục” khi phase chưa xong nghĩa là hoàn thiện phase này. Sau khi phase DONE, “Tiếp tục” cho phép bắt đầu phase đã đề xuất; không tự cho phép deploy production hoặc thay R2.
