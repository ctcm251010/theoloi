# THEOLOI / AudioTP

THEOLOI là hệ sinh thái đa nền tảng dành cho người theo Kinh Thánh. AudioTP là ứng dụng đầu tiên: tìm theo số/tên, guide/instrumental hoặc silent riêng, một player, yêu thích/lịch sử local. PDF/ảnh chỉ nhập từ nguồn có quyền sử dụng phù hợp.

Stack hiện có: Windows Tauri 2/WebView2 + JavaScript, Cloudflare Worker/private R2, pipeline Python. Chưa chọn mobile stack hoặc có code shared thực tế.

Phạm vi hiện tại: chuẩn hóa monorepo, audit, test, GitHub. Không đổi UI/framework, media, assetId/objectKey, quyền tài liệu hoặc Cloudflare live. Native EXE, deployment và phân phối là milestone riêng.

Definition of done: source an toàn, local data được bảo toàn bằng hash, test chạy thật, commit/push được xác minh hoặc blocker được ghi rõ. README/SETUP và docs/ROADMAP.md, docs/TASKS.md là điểm vào.
