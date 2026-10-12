# Báo cáo B3 — Catalog audio tiếng Việt

**Trạng thái:** PASS. Đã tạo catalog thật từ snapshot audio; dừng tại B3.

## Kết quả

| Thành phần | Số lượng |
|---|---:|
| Bài ca logic | 485 |
| Main | 480 |
| Appendix | 5 |
| Guide | 485 |
| Instrumental | 485 |
| Meditations độc lập | 13 |
| Audio asset nguồn | 983 |
| Audio ID / URL HLS duy nhất | 983 / 983 |

Catalog: `catalog/catalog.vi.json`, UTF-8, xuống dòng LF, 491.888 byte.

SHA-256 catalog:

```text
e449b3a25ed49c6879bf06c72219863857632491f4a2ca424c2bc692e45ca8d4
```

## File tạo trong B3

- `catalog/catalog.vi.json`: toàn bộ catalog chuẩn hóa.
- `schemas/catalog.schema.json`: JSON Schema Draft 2020-12.
- `scripts/catalog_lib.py`: đọc JSON nghiêm ngặt, kiểm tra nguồn, ghép bài và validate.
- `scripts/build-catalog.py`: tái tạo catalog offline, chỉ ghi output sau khi validate thành công.
- `scripts/validate-catalog.py`: CLI kiểm tra schema, quy tắc B3 và đối chiếu từng field với nguồn.
- `source/snapshots/watv-vi-2026-10-10.audio.json`: metadata audio nguồn và provenance an toàn.
- `tests/test_catalog.py`: kiểm thử dữ liệu thật, dữ liệu sai và CLI.
- `requirements.txt`: dependency `jsonschema==4.25.1`.
- `.gitignore`: loại `.venv`, Python cache khỏi quản lý source.
- `docs/superpowers/plans/2026-10-10-catalog-b3.md`: kế hoạch và nhật ký thực hiện.
- `docs/catalog-build-report.md`: báo cáo này.

Môi trường `.venv` và cache Python chỉ phục vụ chạy công cụ, không phải catalog/media output. Không sửa `docs/audio-data-analysis.md`.

## Nguồn và khả năng tái tạo

Nguồn quan sát: [trang WATV tiếng Việt](https://worship1.watv.org/vi/sermon/102232), ngày 2026-10-10, múi giờ Asia/Bangkok. Snapshot lưu **dữ liệu đã parse từ inline `window.__NUXT__` đọc qua browser DOM**, không phải HTTP Response nguyên byte. B3 dùng lại dữ liệu quan sát đã giữ từ B1/B2, không gọi lại endpoint thành viên.

Snapshot chỉ lưu 8 field của mỗi record thuộc `guideSongList`, `instrumentalSongList`, `silentSongList`: `title`, `newsongDispNo`, `playTime`, `categoryNm`, `jsonKey`, `songUrl`, `appendixYn`, `newsongAudioId`. Không lưu HTML đầy đủ, cookie, token hoặc thông tin tài khoản/thành viên. Provenance ghi nhận lần kiểm tra DOM trước đó: 485/485/13 dòng, không có sai lệch title/duration.

SHA-256 snapshot đã lưu:

```text
febb88a7aa08ada4bac3abb78176112ce3a35c42673f100771dfb15ecfe8ac97
```

SHA-256 inline script đã quan sát (chỉ lưu hash, không lưu script đầy đủ):

```text
994f6d2fb603e4e8d9a0443766472f02e20800b472b0e626a88e4b398d0e460f
```

Build chỉ đọc snapshot, không đọc DOM hoặc tải URL. Đảo thứ tự cả ba array vẫn tạo catalog có cùng bytes. Hash giúp đối chiếu artifact; không chứng minh dữ liệu WATV hiện tại chưa thay đổi.

## Ghép bài và quyết định schema

- Ghép duy nhất bằng `(appendixYn, newsongDispNo)`; kiểm tra không trùng khóa, hai tập khóa guide/instrumental bằng nhau và title/category giống nhau trước khi merge. Không dùng array index.
- Song key là `main:N` hoặc `appendix:N`; ID là `watv:vi:newsong:<section>:N`. `main:1` và `appendix:1` là hai bài khác nhau.
- `source.audioId` và `source.jsonKey` lưu dạng chuỗi để dùng như identifier. Trong snapshot hiện tại chúng bằng nhau; validator kiểm tra điều này.
- `assetId` chứa loại phiên bản và audio ID, ví dụ `watv:vi:guide:4177`. Duration thuộc từng asset; `durationSeconds` được chuyển từ metadata `sourceDuration`, chưa đo file media.
- Meditation key/ID là `watv:vi:silent:<audioId>`, không ghép với songs. `sourceDisplayNumber` chỉ giữ số hiển thị nguồn.
- Schema yêu cầu đầy đủ field, đúng kiểu, số dương, text không rỗng, duration `HH:MM:SS`, số giây không âm và URL HTTPS thuộc mẫu HLS nguồn đã quan sát. `additionalProperties: false` ở mọi object nội dung loại cả field transfer state lẫn field chưa khai báo.
- Schema cho phép song có ít nhất một trong hai variant để model dùng được về sau. Validator B3 bắt buộc **cả guide và instrumental**, đúng số lượng và đúng tập số của snapshot này.
- So khớp key ↔ ID ↔ section/number, uniqueness toàn catalog, duration chuyển đổi và nguồn ghép là quy tắc semantic của CLI; JSON Schema tiêu chuẩn không tự so sánh các giá trị này.
- Validator đối chiếu từng field với catalog được xây lại từ nguồn: tráo hai asset dù vẫn đủ số lượng và không trùng ID/URL cũng bị phát hiện.

## Anomaly bảo toàn

- Main giữ nguyên dải 1–485, thiếu **34, 242, 300, 306, 367**; không tạo record giả, không đánh lại số.
- Appendix có đúng 1–5, tách riêng số trùng main.
- 267 cặp có duration khác nhau; 218 cặp bằng nhau. Các chênh lệch lớn giữ nguyên: main:335 guide 03:07 / instrumental 03:25; main:343 02:04 / 02:24; main:452 03:35 / 03:24.
- Silent giữ 13 số nguồn: 472 và 474–485; không suy diễn 471/473 là bài bị thiếu, không tạo ID từ số này.
- Không tìm thấy guide thiếu instrumental hoặc ngược lại, title/category khác nhau, trùng khóa ghép, trùng audio ID, trùng URL, record null hoặc thiếu field trong snapshot.

## Kiểm tra đại diện

| Key | Guide audio ID | Instrumental audio ID | Duration guide / instrumental |
|---|---|---|---|
| main:1 | 4177 | 17407 | 00:02:06 / 00:02:04 |
| main:33 | 3889 | 17439 | 00:04:04 / 00:04:05 |
| main:35 | 4094 | 17441 | 00:03:51 / 00:03:49 |
| appendix:1 | 25495 | 25464 | 00:02:00 / 00:01:59 |
| appendix:5 | 25499 | 25468 | 00:01:57 / 00:01:57 |

Hai meditation kiểm tra: `watv:vi:silent:19977` có số nguồn 472, duration 49 giây; `watv:vi:silent:19976` có số nguồn 474, duration 56 giây. `main:34` không tồn tại. Source audio ID guide/instrumental khác nhau ở cả 485 cặp.

Kiểm thử bao gồm: nguồn đảo thứ tự, collision main/appendix, JSON trùng key, NaN/Infinity, null/field thiếu, bool giả integer, title rỗng, duration/URL sai, field transfer state, count/key/ID sai, số main giả, thiếu variant, title/category sai nguồn, tráo asset, meditation lọt vào songs và exit code của CLI. Kết quả chạy cuối: **11 tests PASS**; validator **PASS** với 983 asset.

Rà soát độc lập không tìm thấy lỗi count/ghép bài. Một lỗi biên của regex `$` cho phép newline ở cuối chuỗi đã được sửa bằng điều kiện kết thúc chuỗi tuyệt đối tương thích regex JSON Schema. Kiểm thử hồi quy tái hiện 9 trường hợp FAIL trước sửa, PASS sau sửa; schema và validator đều từ chối chúng. Catalog và hash không thay đổi. Không còn lỗi review được hoãn lại.

## Lệnh chạy lại từ thư mục project

Thiết lập một lần nếu chưa có môi trường:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Kiểm tra catalog hiện tại (offline):

```powershell
.\.venv\Scripts\python.exe scripts/validate-catalog.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tái tạo catalog từ snapshot đã lưu (offline):

```powershell
.\.venv\Scripts\python.exe scripts/build-catalog.py
```

Hai CLI hỗ trợ `--snapshot` và `--schema`; builder hỗ trợ `--output`, validator hỗ trợ `--catalog`. Validator trả exit code 0 khi PASS, nonzero nếu sai.

## Khác biệt và giới hạn

Không thay đổi model hay kết luận dữ liệu của `audio-data-analysis.md`. B3 bổ sung artifact thật, snapshot an toàn, builder offline và validator đối chiếu nguồn. Quy tắc số lượng/dải số của CLI cố ý cố định cho B3; khi WATV thêm bài cần review snapshot mới và cập nhật quy tắc/kiểm thử, không nới lỏng tự động.

Chưa xác minh URL còn phát được, codec, bitrate, duration đo thực tế hoặc quyền truy cập media. B3 không tải `.m3u8`, segment/audio, không gọi FFmpeg/FFprobe, không tạo media output, không upload/cấu hình R2 và không sửa API/web/bot. **Chưa bắt đầu B4.**
