# Audio cầu nguyện bổ sung

Từ1.0.3: registry có hai bản thu gồmour-wish vàunison-prayer. Prepare vẫn tạo manifest/projection chung riêng ngoài983. Khi upload phải chọn chính xác một asset, ví dụ `--asset watv:vi:prayer:unison-prayer`; không chọn bị từ chối khi có nhiều entry. Recovery chỉ sửa selected row; không resetour-wish. `--status` không selector xem cả hai, không gọi network. File thống thanh do người dùng cấp local, không đoán URL nguồn. [Báo cáo1.0.3](release-1.0.3-report.md).

```powershell
.venv/Scripts/python.exe -X utf8 scripts/upload-prayer.py --asset watv:vi:prayer:unison-prayer
.venv/Scripts/python.exe -X utf8 scripts/upload-prayer.py --asset watv:vi:prayer:unison-prayer --apply --verify-download
```

Các mục dưới là quy trình1.0.1 trước khi có asset thứ hai; thêm `--asset watv:vi:prayer:our-wish` cho các lệnh upload/dry-run cũ.

Registry `scripts/prayer_assets.py` chỉ chứa `watv:vi:prayer:our-wish`, được người dùng xác nhận danh tính và quyền tích hợp ngày 13/10/2026. Audio đã có tại `media/prayer/watv/vi/our-wish/our-wish.m4a`:1,123,614 bytes,69.427664 giây, SHA-256 `e03022c18f74a5c94a38bb04fb10c5186fa9e8916d43348deb65a3a5402b68f6`.

Pipeline này không tải lại nguồn, không sửa983 assets/catalog/manifest/state gốc. Metadata riêng được tạo trong `delivery/prayer-manifest.vi.json` và `workers/media-api/generated/quick-audio.json`; cả hai là local-only. Manifest giữ provenance/quyền sử dụng; projection Worker chỉ chứa allowlist public track/asset, không đường dẫn local hoặc URL nguồn. Revision là SHA-256 của JSON canonical `{schemaVersion,tracks,assets}` public với UTF-8, sorted keys và separators `,`/`:`; revision không tự tham gia hash.

Chuẩn bị offline:

```powershell
.venv/Scripts/python.exe -X utf8 scripts/prepare-prayer.py
.venv/Scripts/python.exe -X utf8 scripts/prepare-prayer.py --write
```

Mặc định chỉ kiểm tra, không ghi. `--write` xác minh file hiện tại bằng size/SHA-256, đọc báo cáo `verification.json` cạnh audio và yêu cầu PASS/AAC/decodeVerified cùng thông số khớp registry. Đây là kiểm tra lại bytes và báo cáo decode có sẵn; không khẳng định đã chạy decode mới. Xác nhận nội dung/quyền được lưu riêng trong registry/manifest, không sửa báo cáo nguồn lịch sử. Path traversal, symlink/junction và hard-link output bị chặn; lỗi chỉ in mã tĩnh.

Upload dùng đúng target trong `config/r2.json`, credential loader hiện có và một SQLite riêng `state/prayer-r2-transfers.sqlite`; lock riêng `state/upload-prayer.lock`. Không có selector để lẫn983 bài vào batch. Các lệnh có network chỉ được chạy sau khi đã được duyệt phạm vi live:

```powershell
.venv/Scripts/python.exe -X utf8 scripts/upload-prayer.py
.venv/Scripts/python.exe -X utf8 scripts/upload-prayer.py --status
.venv/Scripts/python.exe -X utf8 scripts/upload-prayer.py --apply --verify-download
# Chỉ khi entry đã failed, sau khi xử lý nguyên nhân:
.venv/Scripts/python.exe -X utf8 scripts/upload-prayer.py --apply --retry-failed --verify-download
```

Dry-run/status không đọc credential, không gọi network và không tạo SQLite. `--status` chỉ đọc trạng thái local, không chứng minh remote hiện tại. Apply xác minh manifest khớp registry và audio local trước khi gọi R2. UploadRunner hiện có sử dụng create-only PUT (`IfNoneMatch:*`), HEAD metadata/size, tùy chọn GET toàn file/hash, tối đa3 lần với lỗi transient. Object đã khớp được bỏ qua PUT; object xung đột bị từ chối. Một round thất bại cần `--retry-failed` rõ ràng để thử lại. Không ghi credential hoặc exception message vào stdout/state lỗi.

Kiểm thử offline bằng synthetic bytes trong thư mục tạm, FakeS3 và SQLite thật:

```powershell
.venv/Scripts/python.exe -X utf8 -m unittest discover -s tests -p test_prayer_assets.py -v
```

Các test không upload thật và không dùng audio giả để nghiệm thu bài cầu nguyện thật. Live PUT/GET, deploy, Windows playback và user acceptance phải có bằng chứng riêng.
