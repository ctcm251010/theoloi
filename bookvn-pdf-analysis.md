# AudioTP — Khảo sát Bài ca mới BookVN

Ngày khảo sát: 12/10/2026, Asia/Bangkok. Phạm vi: đọc danh mục và 7 trang bài mẫu bằng Chrome local; không tải tài liệu, không triển khai downloader, không thay đổi audio/R2.

**Kết luận:** đã kết nối Chrome profile Bang, được người dùng xác nhận là Profile 4. Các bài mẫu hiển thị bằng ảnh PNG nền, không thấy PDF hoặc nút tải PDF. Website ghi “Cấm tải về, chụp, phân phát mọi tài liệu.” Vì yêu cầu chỉ cho tải thử khi website cho phép, không thực hiện tải mẫu.

## 1. Khả năng kết nối Chrome Profile 4

Browser Use đã hoạt động trong lần kiểm tra mới nhất. Công cụ trả Chrome qua extension, browser ID `1`, profileName `Bang`. Người dùng xác nhận “Đúng, dùng profile Bang”. Đã mở và đọc được [danh mục Bài ca mới](https://bookvn.net/category/newsong/) trong profile này; trang có trạng thái đăng nhập và nội dung bài.

Các lần trước runtime lỗi sandbox, có log `os error 32` tại `node_repl.exe`. Lỗi đó không tái hiện trong lần kiểm kê và duyệt trang này; không xác định được chính xác thay đổi nào đã khắc phục. Không sửa ACL, credential, Chrome profile hoặc extension.

Khảo sát web công khai trước đó: [trang chủ](https://bookvn.net/) chuyển tới [Login](https://bookvn.net/login/); công cụ web không đọc được danh mục/bài 1. Browser Use hiện dùng phiên Chrome sẵn có; không xuất cookie, token, mật khẩu và không tự đăng nhập.

## 2. Cấu trúc BookVN và số lượng đã quan sát

Danh mục có ID bài viết dạng `post-76163`, title, URL bài và liên kết phân trang. Không coi thứ tự DOM hoặc array là số bài.

| Phạm vi | Số mục quan sát | Phân loại |
|---|---:|---|
| Danh mục mặc định trang 1 | 100 | Bài chính |
| Trang 2 | 100 | Bài chính |
| Trang 3 | 100 | Bài chính |
| Trang 4 | 100 | Bài chính |
| Trang 5 | 85 | 80 bài chính + 5 mục appx |
| Tổng danh mục mặc định | 485 | 480 bài chính + 5 mục appx |
| Bộ lọc Phụ lục | 57 | Nhóm đánh số riêng 1–57 |
| Hợp hai danh mục | **542** | 542 URL và 542 post ID khác nhau |

Nguồn: [danh mục mặc định](https://bookvn.net/category/newsong/), [trang 2](https://bookvn.net/category/newsong/page/2/), [trang 3](https://bookvn.net/category/newsong/page/3/), [trang 4](https://bookvn.net/category/newsong/page/4/), [trang 5](https://bookvn.net/category/newsong/page/5/), [bộ lọc Phụ lục](https://bookvn.net/category/newsong/?newsong_category=newsong-appendix).

Bài chính có số 1–485, thiếu **34, 242, 300, 306, 367** trong danh sách quan sát. Không thấy URL hoặc post ID trùng trong hợp danh mục. Nhóm phụ lục đánh số có đủ 1–57.

Có ba namespace nguồn cần giữ riêng:

- `main`: đường dẫn `/newsong/newsong1/`, …, `/newsong/newsong485/`.
- `appx`: 5 bài `/newsong/newsong-appx001/` đến `newsong-appx005/`, không có số tiền tố trên title.
- `numbered-appendix`: 57 bài `/newsong/newsong-appendix1/` đến `newsong-appendix57/`, title có số tiền tố.

Có **537 title khác nhau sau chuẩn hóa**: bỏ số tiền tố, chuẩn hóa Unicode NFC, gộp khoảng trắng và không phân biệt hoa/thường. Năm title xuất hiện ở cả appx và numbered-appendix. Đây là thống kê title, không phải chứng minh có 537 tác phẩm/ấn bản độc lập.

Anomaly: title HTML các trang 2–5 ghi “Page … of 6”, trong khi điều hướng quan sát được kết thúc ở trang 5 của danh mục mặc định. Không đoán URL trang 6 để kết luận có thêm tài liệu. Cần lưu kết quả như phạm vi danh mục đã quan sát; chưa chứng minh toàn bộ kho website.

**542 là số trang bài viết, không phải số PDF hoặc số ảnh.** Chỉ kiểm tra nội dung 7 bài mẫu; không mở toàn bộ 542 bài.

## 3. Cơ chế hiển thị và tải

Trong cả 7 bài mẫu:

- Không thấy `iframe`, `embed`, `object` hoặc `canvas`.
- Không thấy link PDF hoặc nút/link download trong DOM đã đọc.
- Bản nhạc nằm trong `div.newsong-bg` với CSS `background-image: url(...png)`.
- Bên trong có ảnh `transIMG.png` làm phần tử phụ; đây không phải file bản nhạc gốc cần thu thập.

Ví dụ bài 1:

```html
<div class="newsong-bg"
     style="background-image:url('/wp-content/uploads/2023/02/nsv-001-1.png')">
  <!-- Có ảnh transIMG.png bên trong -->
</div>
```

Do đó, **nội dung render của các mẫu là ảnh PNG, chưa có bằng chứng về PDF gốc**. Không kết luận rằng website hoặc chủ sở hữu hoàn toàn không có PDF ở nơi khác. Không đoán URL bằng cách đổi đuôi PNG sang PDF.

Công cụ tab chỉ quảng bá thêm capability `pageAssets`; không cung cấp API Network tổng quát trong tài liệu đã đọc. Kết luận ở đây dựa trên DOM và CSS của trang đang hiển thị, không dựa trên việc bắt toàn bộ request hoặc trích xuất dữ liệu phiên.

Điều kiện sử dụng xuất hiện ở footer danh mục và bài mẫu:

> Cấm tải về, chụp, phân phát mọi tài liệu.

Footer cũng ghi bản quyền World Mission Society Church of God. Không tải ảnh/PDF, không chụp tài liệu và không chuyển ảnh sang PDF. Chưa thấy giới hạn tốc độ tải cụ thể; không coi việc không có rate limit hiển thị là cho phép tải.

## 4. URL mẫu và kết quả kiểm tra

Các URL dưới đây được đọc trực tiếp từ CSS của trang, **chưa tải thành file local**. Đường dẫn asset chỉ là bằng chứng định dạng render, không phải URL PDF hoặc sự cho phép tải.

| Trang bài | Số trang ảnh quan sát | Đường dẫn ảnh nền |
|---|---:|---|
| [Bài 1](https://bookvn.net/newsong/newsong1/) | 1 | `/wp-content/uploads/2023/02/nsv-001-1.png` |
| [Bài 2](https://bookvn.net/newsong/newsong2/) | 1 | `/wp-content/uploads/2023/02/nsv-002-1.png` |
| [Bài 100](https://bookvn.net/newsong/newsong100/) | 2 | `/wp-content/uploads/2023/03/nsv-100-1.png`; `nsv-100-2.png` cùng thư mục |
| [Bài 485](https://bookvn.net/newsong/newsong485/) | 1 | `/wp-content/uploads/2023/03/nsv-485-1.png` |
| [appx001](https://bookvn.net/newsong/newsong-appx001/) | 1 | `/wp-content/uploads/2024/10/nsav-001-1.png` |
| [Phụ lục 1](https://bookvn.net/newsong/newsong-appendix1/) | 2 | `/wp-content/uploads/2018/11/nsav-001-2-1.png`; `nsav-001-2-2.png` cùng thư mục |
| [Phụ lục 51](https://bookvn.net/newsong/newsong-appendix51/) | 1 | `/wp-content/uploads/2018/11/nsav-051-1.png` |

Tổng trong 7 mẫu: **9 phần tử ảnh nền**. Không suy ra số trang của các bài chưa mở.

Đường dẫn mẫu không có query chữ ký/thời hạn nhìn thấy. Chưa kiểm tra truy cập asset khi không đăng nhập, header HTTP, validator hoặc thời hạn thực tế; không khẳng định URL vĩnh viễn/công khai. Không đo kích thước pixel, bytes, chất lượng hoặc hash file vì chưa tải bản nguồn.

## 5. Quy luật đánh số và ghép với audio

Bài chính: số trên title và slug nhất quán trong các mẫu; các bài 1, 2, 100, 485 có title khớp catalog audio sau chuẩn hóa Unicode/khoảng trắng. Danh sách số thiếu cũng khớp catalog audio hiện tại. Đây là bằng chứng tốt để dùng `(sourceGroup, sourceNumber)` làm định danh trong nguồn BookVN, nhưng chưa đối chiếu title từng bài trong toàn bộ 480 bài chính.

**Không dùng số phụ lục BookVN để ghép trực tiếp với số phụ lục audio.** Catalog audio `appendix:1` là “Bây giờ Nước Thiên Đàng sắp kíp!”, khác title BookVN `newsong-appendix1`.

Đối chiếu cả 5 title audio phụ lục với title trong hai danh mục BookVN cho các ứng viên sau:

| Audio catalog | BookVN appx | BookVN numbered-appendix | Title |
|---|---:|---:|---|
| `appendix:1` | 005 | 51 | Bây giờ Nước Thiên Đàng sắp kíp! |
| `appendix:2` | 001 | 56 | Nước Thiên Đàng đầy vinh hiển rực rỡ nay đã đến thật gần! |
| `appendix:3` | 002 | 57 | Ngày Vào Thành Nước Thiên Đàng đang được gần kề! |
| `appendix:4` | 003 | 50 | Buổi Sáng của Nước Thiên Đàng Vĩnh Cửu được sáng rực lên! |
| `appendix:5` | 004 | 52 | Hãy hoàn thành Tin Lành Nước Thiên Đàng |

Mapping này là **ứng viên theo title**, chưa kiểm tra đầy đủ nội dung nhạc, lời hoặc ấn bản giữa các trang cùng tên và audio. Không gộp/xóa nguồn trùng tên trước review. Với 52 phụ lục còn lại chưa có liên kết audio được xác minh; không coi thiếu liên kết là thiếu file.

Khóa nguồn tốt nhất: `bookvn:vi:post:<postId>`, kèm URL, sourceGroup, sourceNumber và rawTitle. Quan hệ tới audio là mapping riêng, có trạng thái/evidence. Không dùng array index hoặc coi `appendix:1` của hai nhà cung cấp là cùng một bài. Nhạc ngẫm nghĩ tiếp tục độc lập.

## 6. Kết quả tải thử

- PDF tải về: **0/3**.
- Ảnh tải thành file local: **0**.
- Không có sample để kiểm tra magic `%PDF-`, bytes, pageCount, SHA-256 hoặc khả năng mở PDF.
- Lý do: chưa tìm thấy PDF/nút tải trong mẫu và website cấm tải/chụp/phân phát.

Không tạo PDF từ ảnh để thay cho “PDF gốc”. Chưa cài dependency hoặc chạy công cụ PDF.

## 7. Khả năng tải hàng loạt

**LIMITED — chưa đủ cơ sở triển khai downloader PDF theo nguồn hiện tại.**

Đã xác minh được cách liệt kê metadata bài và đọc định dạng render của các mẫu. Chưa xác minh được nguồn PDF hợp lệ hay phương thức tải được website cho phép. Vì vậy không viết/chạy công cụ tải tài liệu trong bước này.

Để tiếp tục theo mục tiêu PDF gốc, cần nguồn PDF hoặc phương thức xuất/tải được chủ sở hữu cho phép, cùng phạm vi tài liệu và quy tắc truy cập. Nếu sau này phạm vi đổi sang tạo PDF từ ảnh, phải coi đó là sản phẩm phái sinh với chất lượng raster và quyền sử dụng riêng; chưa được thực hiện hoặc mặc định là phương án đã chọn.

## 8. Data model và kiến trúc downloader đề xuất — chưa triển khai

Catalog nên mô tả **nguồn bản nhạc**, cho phép ghi nhận định dạng thực tế thay vì mặc định mọi bài có PDF:

- `id`, `provider`, `locale`, `sourcePostId`, `sourcePageUrl`.
- `sourceGroup`, `sourceNumber`, `rawTitle`, `title`, `edition` (null nếu chưa biết).
- `observedContent`: định dạng và các trang ảnh được quan sát; danh sách này không có nghĩa được phép tải.
- `originalPdf`: null khi chưa tìm thấy; không có nghĩa PDF không tồn tại.
- `audioLinks`: liên kết ứng viên/đã review với song ID của AudioTP, lưu evidence.
- Download/upload state, retry count, local verification và lỗi giữ ở SQLite riêng.

Ví dụ metadata thực tế để review, chưa tạo catalog mới:

```json
{
  "id": "bookvn:vi:post:76163",
  "provider": "bookvn",
  "locale": "vi",
  "sourcePostId": 76163,
  "sourcePageUrl": "https://bookvn.net/newsong/newsong1/",
  "sourceGroup": "main",
  "sourceNumber": 1,
  "rawTitle": "1. Ngày Thật Tôn Quý Phước Lành!",
  "title": "Ngày Thật Tôn Quý Phước Lành!",
  "edition": null,
  "observedContent": {
    "format": "image-pages",
    "pages": [
      {
        "pageNumber": 1,
        "sourceUrl": "https://bookvn.net/wp-content/uploads/2023/02/nsv-001-1.png"
      }
    ]
  },
  "originalPdf": null,
  "audioLinks": [
    {
      "songId": "watv:vi:newsong:main:1",
      "status": "candidate",
      "evidence": "number-and-normalized-title"
    }
  ]
}
```

```json
{
  "id": "bookvn:vi:post:100854",
  "provider": "bookvn",
  "locale": "vi",
  "sourcePostId": 100854,
  "sourcePageUrl": "https://bookvn.net/newsong/newsong-appendix51/",
  "sourceGroup": "numbered-appendix",
  "sourceNumber": 51,
  "rawTitle": "51. Bây giờ Nước Thiên Đàng sắp kíp!",
  "title": "Bây giờ Nước Thiên Đàng sắp kíp!",
  "edition": null,
  "observedContent": {
    "format": "image-pages",
    "pages": [
      {
        "pageNumber": 1,
        "sourceUrl": "https://bookvn.net/wp-content/uploads/2018/11/nsav-051-1.png"
      }
    ]
  },
  "originalPdf": null,
  "audioLinks": [
    {
      "songId": "watv:vi:newsong:appendix:1",
      "status": "candidate",
      "evidence": "normalized-title"
    }
  ]
}
```

Tên rawTitle bài 1 trong ví dụ biểu diễn ở Unicode NFC; nội dung chữ giữ nguyên. Source ID/number không phụ thuộc cách mã hóa title.

Cấu trúc folder dự kiến, chỉ tạo khi chốt nguồn và implementation:

```text
catalog/sheet-sources.vi.json
schemas/sheet-catalog.schema.json
state/sheet-transfers.sqlite
tmp/sheet-downloads/
media/sheets/bookvn/vi/post-76163/original.pdf
delivery/sheet-manifest.vi.json
scripts/                       # CLI/BAT sau khi có thiết kế được duyệt
bookvn-pdf-analysis.md
```

Đặt storage theo source ID tránh va chạm giữa ba namespace và giữ nhiều nguồn/ấn bản cho cùng bài audio. Frontend/bot vẫn tìm bằng số bài AudioTP rồi đi qua mapping đã review.

Khi có nguồn tải được phép: một worker với khoảng nghỉ cấu hình được; bounded retry và Retry-After; ghi .part, atomic rename; chỉ resume HTTP Range khi validator chứng minh cùng phiên bản; skip file hoàn tất sau kiểm tra size/hash; xác minh định dạng thật để loại HTML login giả PDF, parse pageCount, SHA-256; xuất manifest và log an toàn. CLI full/resume/status/retry-failed + BAT gọi environment sẽ được thiết kế sau. Không đưa command hoặc flag giả khi chưa implement.

Không lưu credential vào catalog/source/log. Nếu cần đăng nhập thì dùng phương thức được website hỗ trợ; không tự xuất cookie. Không upload R2 trong giai đoạn này.

## 9. Những thông tin còn thiếu và bàn giao

1. Nguồn PDF gốc hoặc phương thức tải được chủ sở hữu cho phép; hiện chưa tìm thấy trong mẫu.
2. Phạm vi truy cập/tải hợp lệ và giới hạn tốc độ; trang hiện có thông báo cấm.
3. PDF/ảnh có cần auth trực tiếp không; URL có ổn định, validator/Range ra sao.
4. Số trang/asset, bài lỗi hoặc thiếu tài liệu trong 535 trang bài chưa mở. Không coi chưa kiểm tra là thiếu.
5. Ấn bản và nội dung thực tế giữa appx với numbered-appendix; review mapping audio trước khi sử dụng.
6. Đối chiếu title của toàn bộ bài chính; mới kiểm tra 4 mẫu với catalog audio.
7. Giải thích sự khác nhau giữa title HTML “of 6” và điều hướng mặc định kết thúc ở 5.

Chỉ sửa `bookvn-pdf-analysis.md`. Không sửa source/catalog/state/media, không đọc `.secrets/r2.env`, không tạo downloader, không chạy FFmpeg/B10 hoặc upload R2.

```text
Chrome Profile 4: CONNECTED — profile Bang được người dùng xác nhận; đã đọc BookVN
PDF source: NOT FOUND — trong 7 bài mẫu; nội dung quan sát là PNG
Authentication: REQUIRED — đường vào trang chủ chuyển Login; Chrome dùng phiên sẵn có; asset trực tiếp UNKNOWN
Bulk download: LIMITED — chưa có nguồn PDF được phép tải
Ready for Codex implementation: NO — chưa đủ cơ sở viết downloader PDF
```

## 10. Bước triển khai catalog và file local — 12/10/2026

Đã triển khai phần độc lập với nguồn tải: snapshot metadata 542 mục, catalog/schema riêng, mapping audio có review và pipeline xử lý PDF/ảnh local được phép bằng dữ liệu tự tạo. Xem [báo cáo triển khai](docs/sheet-implementation-report.md), [mapping chi tiết](docs/sheet-mapping-report.md) và [hướng dẫn Windows](docs/sheets-windows.md).

Kết luận khảo sát PDF gốc/nguồn tải BookVN ở trên vẫn giữ nguyên: chưa có cơ sở triển khai downloader BookVN. Không tải hoặc chuyển ảnh BookVN; catalog quyền restricted, manifest BookVN 0 assets/542 no-file. Công cụ local mới không phải downloader cho website này.

