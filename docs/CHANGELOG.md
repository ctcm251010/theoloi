# THEOLOI — Development changelog

## 2026-10-13 — Phase01 READY FOR REVIEW

- Streaming/Range/HEAD/conditional/errors/readiness, CDN no-store, diagnostics không chứa URL/session.
- Public contracts + runtime validation: clean-source typecheck/workerd không private JSON; production bundle vẫn cần inputs riêng.
- Ticket RAM reuse/coalescing, expiry seek và logout/renewal/reconnect race được tái hiện bằng test rồi sửa; review độc lập không còn important finding.
- Workspace Python168 PASS/2 SKIP, frontend49 PASS, Worker23 PASS/typecheck/dry-run, metrics1 PASS. 983 media/18 original metadata hashes không đổi. Xem phases/phase-01.md cho clone/Git và giới hạn.
- Đọc B10 lịch sử PASS983 metadata; chuẩn bị vận hành/chi phí/rollback; không deploy/live R2/credential/config changes. Native/live chưa nghiệm thu, đề xuất Phase02 và dừng.

## 2026-10-12 — Phase 00 DONE

- Ghi nhận master roadmap 00–05 và ranh giới phase theo yêu cầu người dùng; giữ quản lý docs hiện có.
- Xác nhận Git owner đã được người dùng sửa sang Sunny, Git status thường sạch và đồng bộ origin/main.
- Clone riêng từ GitHub baseline748d180; cài dependency mới và nghiệm thu source-only tests theo SETUP.
- Source-only clone Python92 PASS/2 SKIP, frontend37, Worker service12, metrics1; full Python workspace168 PASS/2 SKIP. Hai test portability được sửa; production implementation và pin manifest giữ nguyên. Full Worker typecheck clone thiếu private generated inputs được ghi FAIL/precondition, không gọi PASS.
- Fresh integrity983 media và18 metadata/state hashes không đổi; review độc lập không có finding; source11543ed đã publish, ls-remote/clone SHA khớp, published clone Python92 PASS/2 SKIP. Exact index185 files/0 finding, Gitleaks4 commits/0 leak. Phase00 hoàn tất; Phase01 được đề xuất và chưa bắt đầu.
- Không sửa audio/catalog/manifest/R2/credential hoặc bắt đầu Phase 01.

## 2026-10-12 — Repository foundation trước master roadmap

- Source publish main, 179 tracked files; initial commit 4dd8065, handoff 748d180.
- Scan ba commits ~5.12 MB text không có leak; full media integrity983 và input/state18 hashes không đổi.
- Python167 PASS/2 SKIP, frontend37 PASS, Worker15 PASS/dry-run/typecheck; Chrome manual-tab smoke PASS, native build thiếu toolchain, live E2E chưa chạy. Xem repository-audit.md để phân biệt phạm vi.
