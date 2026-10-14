# THEOLOI — Development changelog

## 2026-10-15 — Phản hồi Nghe online khi mất mạng

User xác nhận EXE offline cơ bản ổn, góp ý thiếu thông báo khi chuyển online lúc mất mạng. Sửa sr-only/hidden notice bằng inline network guidance, pending button, clear trên reconnect;3 regression RED→GREEN/frontend95/browser TEST PASS. Final EXE/setup rebuild1.1.0 có chữ ký, đang thực hiện GitHub/update publication theo phê duyệt mới, không đổi983/media/credential.

## 2026-10-15 — API offline1.1 live, dừng trước Release

Sau phê duyệt deploy Worker đúng ctcm251010, giữ private R2/secrets/epoch3/update1.0.3. Review độc lập không Critical/Important;18livechecks PASS, native Rust tải guide1 hai lần với SHA/restart không auth/Range/skip/xóa/tải lại. Thêm ignored explicit live acceptance test, không network trong suite mặc định; preview version lấy package1.1.0 có regression. Native GUI acceptance còn chờ vì Computer Use pipe unavailable; chưa push/tag/GitHub Release hoặc publish update1.1.0. [Báo cáo](release-1.1.0-report.md#nghiệm-thu-live-sau-phê-duyệt1510).

## 2026-10-15 — AudioTP1.1.0 local build, chưa phát hành

Native offline downloads/cache/Range/SHA/delete/resume, UI Nghe offline và startup signed updater modal/progress. Giữ ba tab/player và983 media. Thêm authenticated offline manifest/public version-only API source; pacing/backoff tôn trọng limiter, generation chống logout/defer races. Frontend92/Worker40/typecheck/Python225 PASS4SKIP/Rust41 PASS2 deliberate helpers ignored +real artifact signature PASS. TEST upgrade cache giữ SHA, final production portable startup PASS. EXE/NSIS1.1.0 local READY FOR REVIEW; chưa push/tag/GitHub/Cloudflare theo điểm dừng người dùng. Native E2E/máy sạch/API mới live pending. [Báo cáo](release-1.1.0-report.md), [hướng dẫn học](offline-updates-guide.vi.md).

## 2026-10-14 — Sửa Browser Use mở localhost

Preview từ chối nhầm cross-site top-level navigation dẫn tới HTTP403/Chrome ERR_BLOCKED_BY_CLIENT. Cho phép đúng HTML entry GET/HEAD, giữ API/media protections và thêm frame denial. Codex tự mở tab mới và kiểm thử playback thành công. Worker37/frontend69/typecheck PASS; Windows Python64 PASS2 SKIP. [Báo cáo](local-browser-troubleshooting.md).

## 2026-10-14 — AudioTP1.0.3 thống thanh/Mật khẩu chung

Thêm file thống thanh người dùng cấp5:11 vào supplementaryR2/private và playerchung, không đổi983/our-wish. Ô kết nối đổi nhãn **Mật khẩu chung**, không đổi hoặc nhúng giátrị. Frontend69/Worker36/typecheck/Python225PASS4SKIP/Rust16PASS,12livechecksPASS,review/secret/indexsạch. PR#4merge/tag/Release có5file/hashkhớp;userxácnhậnupdate1.0.1→1.0.3 và thửổn. [Báo cáo](release-1.0.3-report.md) phân biệt nativeuseracceptance với máysạch và ghi lỗi BrowserUse mởlocalhost chưa rõ rootcause.

## 2026-10-13 — AudioTP1.0.1 prayer và updater có chữ ký

Thêm một prayer asset riêng qua supplementary API, giữ nguyên983 audio. Nghe nhanh phát đúng “Cầu nguyện chúng con mong muốn”; updater xác thực và kiểm tra chữ ký/phiên bản trước cài đặt. EXE/NSIS build PASS; live API12checks PASS;223Python/67frontend/35Worker/16Rust PASS (SKIP có lý do). PR#3 merge/tagv1.0.1/Release có đủ5file,5SHA GitHub khớp local; người dùng xác nhận prayer EXE ổn. [Báo cáo](release-1.0.1-report.md) ghi native upgrade/máy khác còn pending, không đánh dấu toàn bộ Closed Beta DONE.

## 2026-10-13 — AudioTP1.0.0 Windows nội bộ

Người dùng duyệt review/hợp nhất/phát hành GitHub1.0.0; nâng metadata đồng bộ và build EXE/NSIS HTTPS thật. Hai review độc lập không Critical/Important; regression190 Python PASS3 SKIP/frontend60/Worker25/Rust6 PASS,983media/18metadata nguyên vẹn. Xem [báo cáo](release-1.0.0-report.md) cho bằng chứng merge/publish và phần máy khác/signing/updater còn chờ.

## 2026-10-13 — Mã chung ngắn cho nhóm nội bộ

- Theo lựa chọn rõ ràng của người dùng: API/UI/DPAPI/helper nhận mã4–256 ký tự; không nhúng mã thật. Giữ rate limit, exact match và R2 private. Helper `--code-only` giữ signing key; sau đổi hash tăng epoch3 thu hồi phiên/vé cũ.
- ONLINE EXE/NSIS mới042837062795Z; live login/catalog983 smoke PASS. Frontend60, Worker25/typecheck, Python190 PASS3 SKIP, Rust6 PASS; review không Important/Critical.983 media và18 metadata/state nguyên vẹn. Native/máy đích trên artifact mới còn chờ nghiệm thu.

## 2026-10-13 — ONLINE Beta và Nhớ đăng nhập

- Worker đã deploy theo phê duyệt vào account đích, bucket giữ private; live health/auth/CORS5 checks PASS. Không tải/upload thêm audio hoặc đổi credential R2.
- Windows Nhớ đăng nhập dùng DPAPI current-user/exact-origin; không localStorage credential, logout và OS lock/crash recovery. Review finding staging bị kẹt đã sửa và re-review sạch.
- ONLINE EXE/NSIS với983 IDs/0 media, HTTPS thực, portable TEMP/PATH tối thiểu startup PASS. Python188 PASS/3 SKIP, frontend58, Worker24/typecheck, Rust5 + subprocess lock checks.983 media/18 metadata không đổi.
- Native Play/seek/mã thật/remember restart, authenticated R2 và máy đích vẫn pending; không DONE, merge hoặc Phase03. Giữ riêng thay đổi `.env.example` của người dùng.

## 2026-10-13 — Phase02 correction: thư viện Bài ca mới thật

- LOCAL EXE/NSIS dùng public projection983 audio thật; không TEST catalog hoặc chép media vào app. `Mo-AudioTP.cmd` khởi động backend chỉ đọc+EXE và tự kết nối.
- Native CORS opt-in exact origins, media anonymous Origin; fix launcher mở trùng bằng Windows byte lock, chỉ dừng backend tự tạo; không proxy/redirect readiness.
- Native session/catalog200; Python185 PASS/3 SKIP, frontend53, Worker24/typecheck. Native Play/seek/máy sạch/live chưa được claim PASS. Không sửa media/credential/Cloudflare hoặc bắt đầu Phase03.

## 2026-10-13 — Phase02 READY FOR REVIEW

- Phase01 PR#1 OPEN sau khi người dùng cấp quyền repo; không merge, live gate giữ nguyên.
- Stage/override/metadata allowlist, HTTPS production origin, locked Cargo và artifact PE/freshness/hash. Npm build đi qua builder; mặc định CSP đóng.
- Native navigation/popup policy, EXE debug/release và NSIS currentUser TEST; cài/gỡ exit0, WebView2 startup và portable TEMP/PATH tối thiểu.
- App TEST identifier riêng, banner và catalog tự tạo; mock WAV12s có session/ticket/Range. Không phát âm mẫu dưới tên WATV.
- Python177 PASS/3 SKIP, frontend52, Worker23/typecheck, Rust1, metrics1;983 media/18 metadata nguyên vẹn. Browser mock playback/network/reconnect/UI PASS; native UI/máy sạch/live/signing chưa nghiệm thu. Không deploy/credential/media changes hoặc Phase03.

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
