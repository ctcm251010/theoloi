# THEOLOI — Phase 01: R2 & Online Audio

**Status: READY FOR REVIEW.** Ngày nghiệm thu source: 13/10/2026, Asia/Bangkok. Source/offline/local hoàn tất; **chưa DONE**, chưa deploy và chưa có live API/Windows user acceptance. Phạm vi theo [MASTER_ROADMAP](../MASTER_ROADMAP.md); Phase00 DONE baseline `ef7f50d0dd3ff2e867cccd2505d8056a98830636`.

## Kết quả triển khai

Giữ monorepo, Worker R2 binding private, signed session/ticket và một HTML audio player. Không thay original catalog/manifest/983 assets/object keys hoặc config Cloudflare.

- **Contracts:** `contracts.d.ts` và ambient generated-data declaration cho typecheck source-only; validation runtime kiểm tra exact fields, ID, enum, size/SHA, duplicate/unsafe key, duration. Không dùng `any`, không giảm checkJs, không tạo fake production JSON. Bundle thật vẫn FAIL nếu thiếu private inputs.
- **API:** readiness không probe R2; auth trước HEAD/GET; full/range/conditional requests; HEAD bỏ qua Range; exact returned offset/length và ETag chặn object đổi giữa HEAD/GET. Stream trực tiếp, cancellation tới nguồn, không buffer toàn file. Lỗi upstream/limiter 503 an toàn/Retry-After, diagnostics chỉ fixed event/code.
- **Cache/request:** response private/no-store và CDN no-store; không Cache API/disk audio cache/prefetch. Ticket reuse/coalescing tối đa16 trong RAM; operation-count tests xác nhận media GET hợp lệ1 HEAD+1 GET, auth/metadata routes0 R2.
- **Client:** timeout/network/401/403/404/409/429/503; expired ticket seek giữ vị trí và ý định pause/play. Logout/new login/preview renewal/pending reconnect không khôi phục phiên hoặc publish stale UI. Giữ search/favorites/history/quick controls/ba nhóm485/485/13.
- **Vận hành:** [quy trình deploy/bootstrap required secrets, chi phí, quyền truy cập, live checklist và rollback](../phase01-operations.md). Không tự deploy, đọc credential hoặc sửa Cloudflare live.

## Bằng chứng kiểm thử

Không cộng các nhóm trùng nhau thành tổng test giả. Các kết quả sau là test đã chạy, không suy từ đọc code.

| Phạm vi | PASS / FAIL / SKIP | Phương pháp |
|---|---|---|
| Python full workspace | 168 / 0 / 2, tổng170;104.217s | unittest discover, dataset thật local và mocks network; hai symlink tests thiếu quyền Windows |
| Frontend/player final | 49 / 0 / 0 | Node tests, expiry/seek, queue, quick panel, search/storage và session cancellation races |
| Worker full workspace final | 23 / 0 / 0 | Service19 + source workerd1 + local adapter1 + private HTTP1 + production workerd1 |
| Worker typecheck + dry-run | PASS / 0 / 0 | tsc noEmit/checkJs; Wrangler4.149.0 dry-run542.79KiB/gzip97.95KiB, serving=false |
| Clean-source clone Worker | 21 / 0 / 2, tổng23; typecheck PASS | Không manifest/generated JSON; private HTTP và production bundle runtime SKIP rõ lý do; synthetic workerd/adapter chạy thật |
| Clean-source clone frontend | 49 / 0 / 0 | Cùng source patch, không private inputs |
| Benchmark metrics regression | 1 test-file PASS | medians/missing values/format/cache/phase separation |
| B10 offline regression | 12 / 0 / 0 | LIST/HEAD/metadata/errors mock, không R2 thật; thuộc nhóm Python full ở trên |
| Missing-input production bundle | EXPECTED FAIL exit1 | Clone dry-run thiếu cả generated JSON; negative test PASS vì không fallback/publish fake catalog |
| Browser local guide smoke | PARTIAL | Chrome Bang, actual guide4177, duration125.016236s, play/pause/seek; một audio element |
| Windows native / live Cloudflare / user acceptance | NOT RUN | Không toolchain/native build/deploy approval trong phase này |

Private HTTP test đọc đúng ba M4A local đại diện, đối chiếu full SHA; production workerd test seed M4A local vào R2 emulator cô lập, không bucket thật. Source workerd test dùng opaque bytes tự tạo để kiểm tra HTTP/client, không fake audio trong sản phẩm. Lệnh tái lập source-only trong [SETUP](../../SETUP.md); full workspace cần inputs riêng đã được phép.

Clone kiểm thử: `tmp/phase00-clean-clone-20261012`; copy chỉ source thay đổi, không private data. Published-commit verification được ghi tại mục Git sau khi push. Python source-only92 PASS/2 SKIP thuộc nghiệm thu Phase00, không nhận là run mới Phase01; Python implementation không đổi trong phase này.

### Review / lỗi đã sửa

Review độc lập phát hiện session renewal hợp lệ bị coi stale, local bootstrap adoption sau logout, pending connection publish sau disconnect và microtask continuation có thể dùng phiên mới/return URL sau logout. Đã viết test tái hiện RED trước fix, bổ sung cancellation epoch và connection gate, rồi chạy lại GREEN. Focused re-review không còn important finding; reviewer xác minh riêng34 tests liên quan PASS. Review cuối operations/README cũng không có important finding. Không còn FAIL trong final automated suites.

Browser smoke dùng tab người dùng mở thủ công và helper8766 đã chạy từ trước; frontend mới nhưng backend helper đang giữ service cũ trong RAM. Backend mới được xác minh độc lập bằng HTTP/workerd tests. Tự mở helper mới ở port49596 bị ERR_BLOCKED_BY_CLIENT; không đổi bảo vệ/profile. Tab người dùng có thao tác ngoài agent trong lúc kiểm thử nên dừng tương tác, không ghi nhận full browser regression hoặc native/live PASS. Không có screenshot mới của phase này.

## Bảo toàn dữ liệu / B10

Fresh local integrity: **983/983**, **2,506,137,889 bytes**, size/SHA đúng manifest; **18/18** original catalog/manifest/snapshot/config/state metadata hashes không đổi. Evidence local ignored: `logs/repository-audit/phase01-integrity.json`. Không tải audio, chạy FFmpeg, upload, đọc `.secrets` hoặc đổi credential. R2 emulator writes chỉ trong test cô lập disposable, không production.

Đọc báo cáo B10 user-run sẵn có `logs/r2-verification/20261011T213835954595Z-148d5382/report.json`: PASS ngày11/10/2026 UTC, expected/actual/checked/matched983, inventoryComplete=true, listPages1, missing/extra/errors/mismatch0. Manifest SHA đúng pin. Mode LIST/HEAD metadata, `contentSha256Verified=false`, không dựa upload state. **Đây là lịch sử user-run, không audit live mới, không hash remote bytes hoặc bằng chứng online API hoạt động.**

## Security / giới hạn còn lại

Client không nhận R2 keys/HLS/private source/object key/local path. Group code nhập runtime; session/tickets chỉ RAM, credentials omit, redirects error, no-referrer. Private projection không vào Git; strict validation ngăn field riêng tư lọt public catalog. Bucket binding có capability ghi platform nhưng handler chỉ head/get; không gọi read-only IAM nếu không có.

Mã nhóm chưa quản lý/thu hồi từng người. Ticket là bearer URL trong hạn, client logout không server-revoke; epoch/signing rotation thu hồi toàn nhóm. No-store ưu tiên auth, tăng R2 HEAD/GET; limiter phân tán không hard billing cap. Worker CPU/live request count/plan/account total usage chưa đo. Stream lỗi sau headers không đổi sang JSON; browser báo lỗi, user retry. Chi phí giả định có nhãn, không cam kết miễn phí. Xem operations cho số liệu/nguồn chính thức.

## Git / file thay đổi

Branch **phase/01-online-audio**, không merge main. [Source commit4fc4d8dcc9fcb7e7cf07454d6def8e26411dafb4](https://github.com/ctcm251010/theoloi/commit/4fc4d8dcc9fcb7e7cf07454d6def8e26411dafb4) đã push, `ls-remote` khớp SHA. Exact-index audit193 files/8,561,287 bytes:0 forbidden paths/0 content findings; staged scan và Gitleaks6-commit history:0 leak. Scanner ban đầu flag synthetic signing-key literal trong test; thay bằng key ngẫu nhiên mỗi test, re-test PASS và scan lại sạch, không thêm allowlist hoặc sửa credential thật.

Clone source-only đã fetch đúng published commit4fc4d8d, working tree sạch, không manifest/generated JSON: typecheck PASS, Worker21 PASS/2 SKIP, frontend49 PASS được chạy lại từ commit này. Overlay trước commit giữ nguyên trong clone stash, không reset/xóa. Helper49596 do agent tạo đã dừng; helper8766/tab người dùng giữ nguyên. Commit docs ledger nghiệm thu theo sau không đổi runtime/data; SHA cuối bàn giao sau verify remote.

- Worker: `src/{contracts.d.ts,generated-data.d.ts,validate-data.mjs,index.mjs,service.mjs}`, `tsconfig.json`, `package.json`, `local-preview.mjs`, `tests/{service,source-runtime,local-integration,runtime}.test.mjs`, README.
- Windows: `web/{api-client,app,player}.mjs`, `tests/{api-client,connection-gate,player}.test.mjs`.
- Docs: SETUP/README, CURRENT_PHASE/ROADMAP/TASKS/CHANGELOG/DECISIONS/BACKLOG, báo cáo này, operations và plan `docs/superpowers/plans/2026-10-12-phase01-online-audio.md`.
- Không đổi package-lock/dependency, wrangler production config, original data, pipeline uploader/downloader hoặc credentials. Logs/audit helpers chỉ local ignored, không commit.

## Nghiệm thu còn chờ / đề xuất Phase02

1. Người quản lý review phạm vi phục vụ nhóm/chi phí/config rồi mới cho phép bootstrap secrets/deploy. Required secrets trước first deploy; secret put có thể tạo draft/deploy ngay. Không gửi code/key qua chat.
2. User-run live checklist auth/health/Range/cache/errors và playback đúng bài trên máy không media local; recording chỉ status/assetId/version không ticket. Sau đầy đủ acceptance mới đổi Phase01 DONE.
3. **Đề xuất Phase02 — Windows Application & Installer**: preflight/cài Rust-MSVC-SDK hợp lệ; build Tauri/NSIS; cấu hình API URL không secret; test WebView2/máy sạch; artifact/hash/hướng dẫn cài và gỡ. Không bắt đầu trong phiên Phase01, không gọi preview là EXE.

Dừng chờ người dùng tại ranh giới phase; đề xuất Phase02 không thay phê duyệt production hoặc quyền phân phối.
