# Monorepo THEOLOI

Giữ runtime paths AudioTP đang hoạt động. **Không di chuyển file/thư mục trong đợt này**, không sửa import/assetId/objectKey/production URL. Chuẩn hóa ranh giới source/dữ liệu, tài liệu và Git.

```text
THEOLOI/                      # checkout vẫn D:\Workspace\AudioTP
  apps/windows/               # UI + src-tauri + tests
  workers/media-api/           # service + local adapter + tests + lockfile
  scripts/ tests/ schemas/     # pipeline, tests và JSON schemas
  benchmarks/score-viewer/     # fixture tự tạo + licensed vendor
  docs/                       # architecture/reports/roadmap/tasks
  config/r2.example.json       # placeholder
  .env.example                # template tài liệu
  README.md PROJECT.md AGENTS.md SETUP.md
  catalog/ delivery/ source/   # operational inputs local
  reviews/ state/ media/       # local decisions/SQLite/media
  .secrets/ .venv/ logs/ tmp/  # local-only
```

Trước/sau: các thư mục ứng dụng/pipeline giữ nguyên; bổ sung Git, root README/PROJECT/roadmap/audit/setup hướng dẫn. Folder chỉ chứa ignored files có thể không xuất hiện khi clone; người quản lý cung cấp inputs, các script tự tạo output dirs khi cần.

Mobile/web/shared chỉ tạo khi có source/nhiệm vụ thật. Không đổi tên runtime AudioTP; THEOLOI là tên hệ sinh thái/repository.

## Dữ liệu và tài liệu

- Commit source, schema, lockfiles và audited fixtures.
- Production catalog/manifest/generated projections/snapshots/account config/review decisions giữ local; không mặc định chúng được phép công khai.
- Không ignore toàn bộ source/config/state/reviews; áp dụng nhóm file cụ thể, SQLite/lock/session và secret patterns.
- Media copy bị ignore ở mọi nơi, ngoại trừ ba WAV tự tạo làm fixture. Chúng không được dùng thay audio thật.
- Benchmark score là tự tạo; PDF.js/Noto giữ license/provenance. Browser evidence raw bị ignore; ba ảnh UI Nghe nhanh tự tạo được giữ.
- Không xóa/di chuyển báo cáo cũ hoặc bookvn-pdf-analysis.md để tránh phá links. Báo cáo cũ là ledger lịch sử, có thể chứa trạng thái đã được cập nhật ở báo cáo mới.
