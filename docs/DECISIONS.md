# THEOLOI — Decisions

- **2026-10-13 / Phase02 build:** config override + stage allowlist thay sửa tracked config; exact HTTPS origin production, Cargo.lock/--locked và artifact freshness trước export. Không dùng raw Tauri build để phân phối.
- **2026-10-13 / Acceptance:** app TEST có identifier riêng, title TEST và âm tự tạo; mock loopback không thay API/R2 thật. Native startup/install khác native UI/playback/máy sạch. CUA không expose native apps nên giữ gate manual review.
- **2026-10-13 / Security:** native navigation chỉ bundled origin, popup deny; không shell/fs/network plugin. Mã/session/ticket trong RAM; không nhúng credential R2. NSIS currentUser, chưa signing/updater.

- **2026-10-13 / Contracts:** public .d.ts + runtime boundary validation thay typeof private JSON; giữ checkJs, không fake production catalog. Bundle thiếu inputs vẫn fail.
- **2026-10-13 / Streaming:** auth trước R2, allowlist, HEAD metadata rồi conditional GET, exact returned range/cancel propagation; HEAD bỏ qua Range. Metadata SHA không thay hash remote bytes.
- **2026-10-13 / Cache/cost:** mọi response private/no-store + CDN no-store; tối đa16 ticket RAM/coalescing, không disk audio cache/prefetch. GET hợp lệ tốn1 HEAD+1 GET; limiter phân tán không phải billing cap.
- **2026-10-13 / Lifecycle:** explicit logout cancellation epoch tách khỏi renewal; pending reconnect không khôi phục session/UI sau disconnect. Giữ một player và original IDs.
- **2026-10-13 / Deployment:** required secrets trước first deploy; secret put có thể tạo draft/deploy ngay. Phase01 READY FOR REVIEW, native/live chưa kiểm thử, không đổi wrangler config/live.

- **2026-10-12 / Workflow:** master roadmap lưu nguyên văn tại MASTER_ROADMAP.md; sử dụng ROADMAP/TASKS hiện có cùng CURRENT_PHASE, CHANGELOG, BACKLOG và báo cáo phases. Không tạo docs/roadmap trùng.
- **2026-10-12 / Phạm vi:** tự chủ hoàn thành phase được giao; sau đó đề xuất và dừng. “Làm hết” chỉ mở rộng phạm vi được giao, không miễn phê duyệt production/chi phí/quyền nội dung.
- **2026-10-12 / Phase 00:** giữ module/path hiện tại; clean-clone source-only tests tách full regression cần private inputs. Không publish datasets hoặc dùng âm thanh giả để che thiếu media.
- **2026-10-12 / Git ownership:** người dùng đổi riêng `.git` sang Sunny, kiểm tra bằng Get-Acl + Git thường thành công. Owner Windows và owner GitHub độc lập; không cần global safe.directory.
- Mobile framework, updater và live authentication deployment chưa có quyết định mới trong phase này.
