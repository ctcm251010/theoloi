# THEOLOI roadmap

Task riêng15/10 **AudioTP1.1.0 Offline Downloads & Startup Updates — READY FOR REVIEW**: code/tests và EXE/NSIS có chữ ký updater chuẩn bị local;983media/18metadata nguyên vẹn. Dừng trước GitHub/Cloudflare theo yêu cầu mới. Native/live acceptance chưa hoàn tất; không đánh dấu toànPhase03 DONE. [Bàn giao](release-1.1.0-report.md).

Task riêng14/10 sửa Browser Use local **DONE**: root cause preview cross-site navigation; tự mở tab/phát nhạc và regression PASS. [Báo cáo](local-browser-troubleshooting.md). Không thay nghiệm thu native/live hoặc mở phase mới.

[Yêu cầu master do người dùng cung cấp](MASTER_ROADMAP.md) là đặc tả dài hạn; [CURRENT_PHASE](CURRENT_PHASE.md) là trạng thái thực thi, [TASKS](TASKS.md) là checklist hiện tại. Tận dụng hệ thống docs hiện có, không thêm docs/roadmap song song.

| Phase | Mục tiêu | Trạng thái |
|---|---|---|
| 00 — Repository Foundation | Source audit, GitHub, setup và clean-clone validation | DONE |
| 01 — Cloudflare R2 & Online Audio | API private đã deploy/user xác nhận online; PR#1 đã merge, formal Range/R2 metadata còn pending | READY FOR REVIEW |
| 02 — Windows Application & Installer | PR#2 đã merge, EXE/NSIS1.0.0/DPAPI; user thử bản trước ổn, bản1.0/máy khác/installer còn chờ nghiệm thu; [Release task](release-1.0.0-report.md) | READY FOR REVIEW |
| 03 — Closed Beta & Automatic Updates | Beta/máy khác, release artifacts/hash, updater có ký và recovery | NOT STARTED |
| 04 — Android & iOS | ADR React Native/Tauri Mobile; Android/background audio; iOS theo môi trường thực tế | NOT STARTED |
| 05 — THEOLOI Ecosystem | Ưu tiên từng MVP: bản nhạc/lời, sách, kế hoạch đọc, công cụ thờ phượng | NOT STARTED |

Source của các module Phase 01/02 đã có một phần; NOT STARTED ở đây chỉ đợt nghiệm thu theo master mới, không có nghĩa viết lại từ đầu. Sheets/mapping hiện có tiếp tục được giữ; nguồn/quyền còn thiếu nằm trong [BACKLOG](BACKLOG.md).

Task riêng1.0.0 được người dùng duyệt đã DONE: review/merge/tag/build và [GitHub Release](https://github.com/ctcm251010/theoloi/releases/tag/v1.0.0) có đủ installer/portable/hướng dẫn/hash, digestGitHub khớp local. Không đồng nghĩa bắt đầu toàn bộ Phase03/updater/Closed Beta hoặc đã nghiệm thu máy đích.

Task riêng1.0.1 do người dùng giao: prayer bổ sung và signed updater đang hoàn tất phát hành, [nghiệm thu](release-1.0.1-report.md). Đây là phần updater của Phase03, không tự mở rộng sang toàn bộ Closed Beta; máy khác/nâng cấp native vẫn cần acceptance riêng.

Taskriêng1.0.3DONE:thốngthanh+Mật khẩu chung,Releaseđủfile,người dùng xácnhậnnativeupdate1.0.1→1.0.3/phátổn. [Nghiệm thu](release-1.0.3-report.md). Đây chưa phải xácnhận toànClosedBeta/máyWindowskhác/mạngyếu hoặc đãfixrootcauseBrowserUselocalhost; không tựbắtđầu phasekhác.

Hoàn thành một phase thì test, đối chiếu acceptance, cập nhật tài liệu/Git, đề xuất phase tiếp theo và chờ người dùng. Production Cloudflare, chi phí mới và quyền phân phối phải được phê duyệt riêng. Mock/local không chứng minh live. Chỉ triển khai nhiều phase khi người dùng giao rõ phạm vi đó.
