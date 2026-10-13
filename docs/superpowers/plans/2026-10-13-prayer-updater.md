# AudioTP 1.0.1 — bài cầu nguyện và cập nhật ứng dụng

Trạng thái: IN PROGRESS. Người dùng đã xác nhận bản thu `our-wish.m4a` đúng bài và có quyền phục vụ cho nhóm AudioTP ngày 13/10/2026; cho phép hoàn thành upload, API, kiểm thử và phát hành. Yêu cầu bổ sung: thông báo phiên bản mới và cập nhật khi người dùng bấm nút.

## Thiết kế đã chọn

- Giữ nguyên catalog/manifest/state và 983 audio gốc. Bài cầu nguyện có registry, manifest, state upload riêng, ID `watv:vi:prayer:our-wish`.
- `/v1/catalog` giữ tương thích bản 1.0.0: 485 guide, 485 instrumental, 13 silent. Endpoint xác thực `/v1/quick-audio` cung cấp track bổ sung; player chung phát bằng ticket và HTTP Range hiện có.
- Ba tab không thay đổi. Nghe nhanh bật đúng bài cầu nguyện sau khi API xác nhận asset; mục thống thanh tiếp tục chưa khả dụng. Không thêm audio giả.
- Cập nhật bằng Tauri updater có chữ ký. Private R2 giữ installer; Worker xác thực cung cấp metadata và file cập nhật. Không cần GitHub token trên máy người dùng; GitHub repo/bucket giữ private.
- Native IPC giới hạn origin API và URL tải, giữ token trong RAM, kiểm tra chữ ký trước cài đặt. Chỉ cài khi người dùng bấm Cập nhật. Khóa ký private giữ local; chỉ public key vào ứng dụng.
- Bản 1.0.0 chưa có updater, cần cài 1.0.1 thủ công một lần. Từ 1.0.1 trở đi có thông báo và cập nhật trong ứng dụng.

## Các bước và nghiệm thu

1. [x] Đọc ngữ cảnh, xác nhận quyền và bản thu; kiểm tra đăng nhập đúng Cloudflare account.
2. [ ] Registry/preparer/uploader một asset riêng; dry-run, retry, state và SHA-256, test offline.
3. [ ] Worker supplementary API và updater API tương thích cũ; auth/range/metadata/error tests.
4. [ ] UI Nghe nhanh, player chung và thông báo cập nhật; test race/logout/lỗi mạng, ba tab.
5. [ ] Native signed updater, build staging và signature; unit/integration/regression/secret scan/review độc lập.
6. [ ] Upload một prayer audio, signed installer và metadata riêng; xác minh, deploy giữ serving/auth epoch; smoke live có giới hạn.
7. [ ] Build/phát hành 1.0.1, Git/release assets, tài liệu và đối chiếu integrity 983 media.

Native UI, installer trên máy khác và nâng cấp thực tế cần ghi riêng với bằng chứng; không dùng unit/mock để tuyên bố đã nghiệm thu máy sạch. Không bắt đầu phase khác.
