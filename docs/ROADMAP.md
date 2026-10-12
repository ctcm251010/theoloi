# THEOLOI roadmap

[Yêu cầu master do người dùng cung cấp](MASTER_ROADMAP.md) là đặc tả dài hạn; [CURRENT_PHASE](CURRENT_PHASE.md) là trạng thái thực thi, [TASKS](TASKS.md) là checklist hiện tại. Tận dụng hệ thống docs hiện có, không thêm docs/roadmap song song.

| Phase | Mục tiêu | Trạng thái |
|---|---|---|
| 00 — Repository Foundation | Source audit, GitHub, setup và clean-clone validation | READY FOR REVIEW |
| 01 — Cloudflare R2 & Online Audio | Audit B10, API private/Range/auth, client online, kế hoạch deploy/rollback và live E2E | NOT STARTED |
| 02 — Windows Application & Installer | Tauri 2/WebView2, native build/EXE/NSIS, máy đích không cần workspace/Python/Node | NOT STARTED |
| 03 — Closed Beta & Automatic Updates | Beta/máy khác, release artifacts/hash, updater có ký và recovery | NOT STARTED |
| 04 — Android & iOS | ADR React Native/Tauri Mobile; Android/background audio; iOS theo môi trường thực tế | NOT STARTED |
| 05 — THEOLOI Ecosystem | Ưu tiên từng MVP: bản nhạc/lời, sách, kế hoạch đọc, công cụ thờ phượng | NOT STARTED |

Source của các module Phase 01/02 đã có một phần; NOT STARTED ở đây chỉ đợt nghiệm thu theo master mới, không có nghĩa viết lại từ đầu. Sheets/mapping hiện có tiếp tục được giữ; nguồn/quyền còn thiếu nằm trong [BACKLOG](BACKLOG.md).

Hoàn thành một phase thì test, đối chiếu acceptance, cập nhật tài liệu/Git, đề xuất phase tiếp theo và chờ người dùng. Production Cloudflare, chi phí mới và quyền phân phối phải được phê duyệt riêng. Mock/local không chứng minh live. Chỉ triển khai nhiều phase khi người dùng giao rõ phạm vi đó.
