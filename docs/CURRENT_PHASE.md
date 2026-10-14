# THEOLOI — Current phase

## Task riêng1.0.3 — IN PROGRESS /14-10-2026

Thống thanh từ file người dùng và nhãn **Mật khẩu chung** theo yêu cầu. Audio mới5038802bytes/311.518912s/decode/hash PASS, uploaded privateR2/GET verified;983media/18metadata nguyên vẹn. Frontend69/Worker36/typecheck/Python225 PASS4SKIP, scopedrecoveryfix review/test. Browserlocal5:11/pause/seek/two-prayer/search PASS; bản cuối signedinstaller/live/release/native đang hoàn tất. [Báo cáo](release-1.0.3-report.md). Không reset source hoặc mở rộng phase.

## Task riêng 1.0.1 — DONE tích hợp/phát hành /13-10-2026

Prayer bổ sung và signed updater đã triển khai; registry/manifest/state riêng,983media/18metadata không đổi. Frontend67,Worker35/typecheck,Python223 PASS/4 symlink SKIP,Rust16 PASS; live API12checks PASS. EXE/NSIS đã ký updater, private R2 installer đã GET/hash verified, Worker deploy giữ epoch3/secrets/serving. Người dùng xác nhận bài cầu nguyện phát ổn trên EXE. PR#3 MERGED/tagv1.0.1/Release có5file+2source archives,5digestGitHub khớp local. [Báo cáo](release-1.0.1-report.md) · [Checklist](superpowers/plans/2026-10-13-prayer-updater.md). Nâng cấp native sang bản sau/máy khác và nút kiểm tra cập nhật native còn READY FOR REVIEW; không triển khai toàn bộ Closed Beta/Phase03. Tiếp theo đề xuất nghiệm thu update/cài đặt máy khác, chưa tự bắt đầu.

## Task phát hành1.0.0 — DONE /13-10-2026

Người dùng xác nhận bản mới thử ổn và yêu cầu merge/phát hành1.0.0. Hai review độc lập không Critical/Important; PR#1/#2 đã MERGED, tagv1.0.0 trỏ0f49c91; main có docs ledger theo sau. Build/regression/integrity/secret scan/clean-clone tests PASS (SKIP ghi riêng). Người dùng đã publish Release khi chưa có binary; nay đã bổ sung đủ bốn file, Assets6, toàn bộ digestGitHub khớp local. [Release](https://github.com/ctcm251010/theoloi/releases/tag/v1.0.0) · [Báo cáo](release-1.0.0-report.md). Không tự bắt đầu updater/Closed Beta hoặc đánh dấu máy khác đã nghiệm thu.

## Hiện hành — Phase02 /13-10-2026

- **READY FOR REVIEW — ONLINE Beta:** API đã deploy đúng account `ctcm251010`, member `nguyenducbang.uit`; bucket giữ private. Health/auth/CORS5 checks PASS; user xác nhận ONLINE hoạt động và tự kết nối lại. Formal authenticated Range/R2 audit, installer và máy đích còn pending.
- Có Nhớ đăng nhập bằng Windows DPAPI current-user, exact HTTPS origin; logout/bỏ chọn xóa mã, không credential localStorage. OS lock/crash recovery và review độc lập PASS.
- Artifact cuối `release/windows/0.2.0-20261013T042837062795Z/`, EXE/NSIS HTTPS thật/983 IDs, form tự hiện nếu chưa đăng nhập. Theo yêu cầu, hỗ trợ mã chung từ4 ký tự; live đã đổi hash và epoch3, login/catalog983 PASS. User cần dùng artifact mới và nhập lại mã một lần; không nhúng mã vào app/source.
- Python190 PASS/3 symlink SKIP, frontend60, Worker25/typecheck, Rust6 PASS và helper subprocess chạy2 lần; review không Important/Critical.983 media/2,506,137,889 bytes +18 metadata/state không đổi.
- [Báo cáo ONLINE](phase02-online-beta.md), [checklist](superpowers/plans/2026-10-13-phase02-live-online.md). Chưa DONE/Closed Beta; không merge Phase01 hoặc bắt đầu Phase03.

## Lịch sử trước triển khai ONLINE — LOCAL/TEST

- **READY FOR REVIEW**, chưa DONE: đã sửa thiếu thư viện thật trong bàn giao TEST; có EXE/NSIS LOCAL với catalog485/485/13, launcher `Mo-AudioTP.cmd`, native session/catalog200. Native UI/playback/máy sạch và live API còn chờ nghiệm thu.
- Branch `phase/02-windows-installer`, parent Phase01 `637fbd1`; [PR Phase01#1 OPEN](https://github.com/ctcm251010/theoloi/pull/1), không merge hoặc deploy Cloudflare.
- Python177 PASS/3 symlink SKIP, frontend52, Worker23/typecheck, Rust1, metrics1.983 media/2,506,137,889 bytes SHA/size và18 metadata/state gốc không đổi.
- TEST artifact: `release/windows/TEST-0.2.0-20261013T014110189461Z/`, chỉ âm tự tạo, không phải thư viện WATV online. Portable đã chạy ngoài workspace với PATH tối thiểu/WebView2.
- Source `7da2d00` được xác minh trong clone không private inputs: Python101 PASS/3 SKIP, frontend52, Worker21 PASS/2 SKIP/typecheck, metrics1; TEST prepare PASS. Gitleaks history/index audit sạch; ledger Git bàn giao tiếp theo không đổi runtime.
- Follow-up LOCAL: Python185 PASS/3 SKIP, frontend53, Worker24/typecheck; review lỗi launcher mở trùng đã sửa. Artifact `release/windows/LOCAL-0.2.0-20261013T021343012529Z/`. Chỉ phát file trên máy, không phải R2 live; giữ bằng chứng TEST lịch sử bên dưới.
- Correction source `de288ee`: clone Python109 PASS/3 SKIP, frontend53, Worker21 PASS/3 private SKIP/typecheck;204-file index/history secret scan sạch. Nguồn đã compile khớp source test; native session/catalog200 và983/18 integrity được xác minh riêng.
- [Báo cáo Phase02](phases/phase-02.md), [lệnh Windows](../apps/windows/README.md). Tiếp theo: review/live acceptance Phase01 và native máy đích trước Closed Beta. **Không bắt đầu Phase03; dừng chờ người dùng.**

## Lịch sử bàn giao Phase01 — giữ nguyên bằng chứng trước khi Phase02 được giao

Ngày cập nhật: 13/10/2026, Asia/Bangkok.

- Current: **PHASE 01 — R2 & Online Audio**.
- Status: **READY FOR REVIEW**: source/offline/local hoàn tất; chưa DONE vì deployment/live playback/user acceptance chưa thực hiện.
- Authorized: API/client/typecheck, bảo mật/chi phí, test, tài liệu và Git; không deploy hoặc thay Cloudflare live.
- Baseline: Phase00 DONE, main ef7f50d0dd3ff2e867cccd2505d8056a98830636; Git owner Sunny, Git thường hoạt động.
- Evidence: workspace Python168 PASS/2 SKIP, frontend49 PASS, Worker23 PASS/typecheck/dry-run, metrics1 PASS. Clone source typecheck/workerd không cần private JSON; private integrations SKIP có lý do. Chi tiết trong báo cáo.
- Integrity: 983 media/2,506,137,889 bytes size/SHA đúng;18 original metadata/state hashes không đổi. B10 user-run11/10 PASS983 metadata là lịch sử, không phải remote content SHA hoặc live API.
- Git: phase/01-online-audio; source4fc4d8d đã push/remote SHA khớp; published clone sạch, typecheck/Worker21 PASS2 SKIP/frontend49 PASS. Audit193 files và Gitleaks sạch; docs ledger commit theo sau. Xem [Phase01](phases/phase-01.md) và final handoff. Không merge main/force-push.
- Remaining: phê duyệt phạm vi phục vụ/chi phí/deploy; user-run live API và playback trên máy không có media local. Browser Phase01 chỉ smoke guide local; helper mới bị ERR_BLOCKED_BY_CLIENT. Native Windows chưa chạy.
- Operations: [deploy/cache/chi phí/rollback/live checklist](phase01-operations.md).

**Đề xuất Phase02 — Windows Application & Installer**, chưa bắt đầu: preflight Rust/MSVC/SDK; build Tauri/NSIS; cấu hình API URL không secret; kiểm thử WebView2/máy sạch; artifact/hash và tài liệu cài đặt. EXE online chưa đủ điều kiện phân phối trước live acceptance/quyền phục vụ phù hợp.

Dừng tại ranh giới phase. “Tiếp tục” cho phép tiếp tục source/phase được đề xuất theo roadmap; không thay phê duyệt production/chi phí hoặc quyền nội dung.
