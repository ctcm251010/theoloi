# Phân tích dữ liệu audio WATV và đề xuất catalog

Ngày kiểm tra: 10/10/2026, múi giờ Asia/Bangkok. Trạng thái: đề xuất để review, chưa triển khai.

## 1. Nguồn và phương pháp xác minh

- Trang gốc: https://worship1.watv.org/vi/sermon/102232.
- Workspace ban đầu trống, không có `source/...983-response.txt`. Người dùng đã yêu cầu tự lấy dữ liệu từ trang đang mở thay cho file đó.
- Đọc script `window.__NUXT__` nhúng trong DOM của trang mới mở bằng phiên Chrome hiện có: **544.469 ký tự**, chia thành các đoạn tối đa 80.000 ký tự rồi nối đủ. Đây là nội dung script trong DOM, **không phải bản lưu HTTP Response nguyên byte** và không phải file nguồn cũ.
- Script là JavaScript tuần tự hóa bằng IIFE, không phải JSON thuần: 2.263 tham số tương ứng 2.263 đối số; các record dùng tham chiếu tới bảng đối số. Giải mã literal và assignment bằng parser chỉ đọc, không `eval` hay thực thi script nguồn.
- Ba danh sách có cùng tham chiếu ở `fetch["NewsongPlayer:0"]` và `state.totalData.sermonNewsongs`; không đếm chúng hai lần. Tên biến rút gọn của snapshot này: guide=`cO`, instrumental=`Dj`, silent=`Mn`; không dùng tên rút gọn làm giao ước lâu dài.
- Chuyển giữa ba tab giao diện, đọc toàn bộ hàng trong `#pcSongList`, đối chiếu **bằng số hiển thị có phân biệt Phụ lục**, không ghép bằng index. Số hàng/số bài/title/duration: 485/485/13, không có sai khác với dữ liệu đã giải mã. Không click nút phát hoặc tải bài. Tab được trả về Hướng dẫn.
- Snapshot của tab cũ chỉ có guide rỗng, instrumental=485, silent=13, trong khi DOM đã có guide. Trang mới trong cùng phiên cung cấp đủ cả ba danh sách. Vì vậy một response thiếu guide không đủ để kết luận catalog không có guide; cần kiểm tra tình trạng phiên và tính đầy đủ trước khi đồng bộ.
- Không gọi FFmpeg, không yêu cầu playlist/segment audio, không upload, không sửa website. Chỉ tạo báo cáo này; dữ liệu nguồn trên website không bị thay đổi.

Giới hạn: công cụ duyệt web tìm kiếm không đọc được trang này. Browser Use đọc được script/DOM trong Chrome. Không thu được bản ghi request/response của Network hay mã xử lý nội bộ của player, nên không khẳng định website tự JOIN hai danh sách bằng khóa nào. Khóa bên dưới là khóa ghép do phân tích toàn bộ record và DOM xác minh.

Một yêu cầu đọc trực tiếp endpoint `napi.watv.org/worship/data/member?languageGbSn=vi` đã bị xét duyệt tự động chặn vì endpoint có thể trả thông tin thành viên ngoài phạm vi audio; yêu cầu đó không được thực hiện. Phân tích hoàn tất bằng dữ liệu nhúng trong trang gốc mới mở, không đọc endpoint bị chặn.

## 2. Cấu trúc thực tế

`guideSongList`, `instrumentalSongList`, `silentSongList` đều là array record. **Tất cả 983 record có đúng 8 field dưới đây**, không null, không field thiếu, không string rỗng, không lỗ trong array.

| Field nguồn | Kiểu quan sát | Ý nghĩa và cách dùng |
|---|---|---|
| `title` | string | Tiêu đề; DOM hiển thị ở `.song-tit`. Không dùng làm định danh. |
| `newsongDispNo` | integer dương | Số hiển thị của bài, xác nhận với `.num` trên DOM; không phải index. |
| `playTime` | string `HH:MM:SS` | Thời lượng metadata của **từng bản audio**; DOM hiển thị `MM:SS`. |
| `categoryNm` | string | Nhóm chủ đề; DOM hiển thị ở `.theme`. |
| `jsonKey` | integer dương | Bằng `newsongAudioId` trong 983/983 record; không có định danh bài ca chung khác ở đây. |
| `songUrl` | string URL HTTPS | URL playlist HLS, kết thúc `.m4a/playlist.m3u8`. |
| `appendixYn` | integer 0 hoặc 1 | 0=phần chính, 1=Phụ lục; DOM ghi “Phụ lục N” khi bằng 1. |
| `newsongAudioId` | integer dương | ID bản audio ở nguồn; guide và instrumental của cùng bài có ID khác nhau. |

Không có field `duration`, `songId`, `genreNm`, `songFileNm`, `language`, `edition` trong các record thuộc ba danh sách này. Locale `vi` lấy từ phạm vi trang, không suy ra từ tên file. Các nhóm audio khác của trang có thể có schema khác.

12 giá trị `categoryNm` trong guide/instrumental: Lễ trọng thể, Vinh hiển, Cảm tạ, Đức tin, Sự trông cậy, Tình yêu thương, Sự hy sinh, Hối cải, Truyền đạo, Cầu Nguyện, Nghi thức, Ngẫm nghĩ. Silent chỉ có Ngẫm nghĩ. **Chủ đề “Ngẫm nghĩ” trong phần bài ca không đồng nghĩa với membership của `silentSongList`.**

`songUrl` của 983 record đều có dạng:

```text
https://vod.watv.org/watv_media_newsong/_definst_/mp4:WATV_NEWSONG/<tên-file>.m4a/playlist.m3u8
```

Tên file có nhiều cách đặt, ví dụ `2023_07_07_095737_242.m4a` và `20241216104939827.m4a`. Không parse tên file để đoán số bài, ID, ngôn ngữ hay phiên bản. `.m3u8` là địa chỉ playlist; không đổi phần mở rộng URL để đoán link M4A trực tiếp. Chưa kiểm tra codec, bitrate, thời lượng thực hoặc hiệu lực URL.

## 3. Số lượng được xác minh

| Loại | Record | Phần chính | Phụ lục | URL riêng biệt |
|---|---:|---:|---:|---:|
| Hướng dẫn (`guideSongList`) | 485 | 480 | 5 | 485 |
| Nhạc đệm (`instrumentalSongList`) | 485 | 480 | 5 | 485 |
| Nhạc ngẫm nghĩ (`silentSongList`) | 13 | Không thuộc hệ thống bài ca | 0 | 13 |
| **Tổng** | **983** | | | **983** |

Sau ghép: **485 bài ca logic** (480 bài chính + 5 phụ lục), mỗi bài có 2 bản audio; **13 mục ngẫm nghĩ độc lập**. Tổng 498 mục nội dung, 983 bản audio.

Trong toàn bộ script có **998 literal URL `playlist.m3u8`**, trong đó **983 thuộc `WATV_NEWSONG`**. 15 URL còn lại gồm 14 `WATV_PRAYER` (13 `pray_01`…`pray_13` và `our_wish`) cùng 1 HLS sermon `.smil`. Các mục ghim ở đầu player không được tự cộng vào `silentSongList`. Báo cáo/catalog đề xuất chỉ bao gồm ba danh sách được yêu cầu.

## 4. Khóa ghép guide ↔ instrumental

Khóa ghép trong snapshot:

```text
(appendixYn, newsongDispNo)
```

Khóa đầy đủ cho catalog có nhiều nguồn/ngôn ngữ/bộ bài:

```text
(provider, locale, collectionId, section, number)
section = appendixYn === 1 ? "appendix" : "main"
number  = newsongDispNo
```

Lý do chọn:

1. **485/485 khóa duy nhất trong mỗi danh sách**, giao hai tập bằng 485, không dư/thiếu ở hai chiều.
2. Title và category khớp chính xác ở 485/485 cặp; DOM của hai tab hiển thị cùng số/phụ lục tương ứng.
3. Dùng riêng `newsongDispNo` sẽ trùng số 1–5 giữa phần chính và phụ lục. Dùng `newsongAudioId` hoặc `jsonKey` không JOIN được hai bản vì đó là ID audio khác nhau. Dùng title dễ hỏng khi đổi chính tả/dịch thuật. Thời lượng cũng không phải khóa.
4. Khóa độc lập thứ tự array. Phần chính có khoảng trống, phụ lục khởi động lại từ 1; `index + 1` sẽ sai.

Ví dụ: bài chính 1 gồm guide ID **4177** và instrumental ID **17407**; phụ lục 1 gồm guide **25495** và instrumental **25464**. Hai bài này cùng số 1 nhưng phải có ID logic khác nhau.

Mức an toàn: đã chứng minh duy nhất và nhất quán trong snapshot hiện tại, chưa chứng minh WATV sẽ không đổi hệ thống số/ấn bản. Mỗi lần import phải kiểm tra lại uniqueness, tập khóa và title/category; xung đột phải được ghi nhận để review, không tự ghép theo index hoặc title. Nếu nguồn thêm ấn bản, dùng collectionId riêng cho ấn bản đó.

## 5. Anomaly và các điều cần giữ nguyên

| Kiểm tra | Kết quả |
|---|---|
| Có guide không có instrumental | 0 |
| Có instrumental không có guide | 0 |
| Trùng khóa `(appendixYn, newsongDispNo)` trong từng danh sách | 0 |
| Trùng số nếu bỏ `appendixYn` | 1, 2, 3, 4, 5; mỗi số xuất hiện 2 lần/danh sách |
| Số thiếu trong khoảng 1–485 của phần chính | **34, 242, 300, 306, 367**, giống nhau ở cả hai danh sách |
| Số phụ lục | 1–5 đầy đủ ở cả hai danh sách |
| Cặp khác title/category | 0 / 0 |
| Cặp cùng thời lượng metadata | 218 |
| Cặp khác thời lượng metadata | **267** |
| Trùng URL trên toàn bộ 983 audio | 0 |
| Trùng `newsongAudioId` trên toàn bộ 983 audio | 0 |
| `jsonKey` khác audio ID | 0 |
| Record null/lỗ array/thiếu field/field null/string rỗng | 0 |
| Số bài hoặc ID không phải integer dương | 0 |
| URL sai dạng đã quan sát hoặc duration sai định dạng | 0 |

Không tạo bài giả cho các số thiếu và không đổi lại số bài liên tục. Chưa xác định vì sao WATV không cung cấp các số đó.

Phân bố `guideSeconds - instrumentalSeconds` của 267 cặp khác duration:

| Chênh lệch (giây) | Số cặp |
|---:|---:|
| -20 | 1 |
| -18 | 1 |
| -2 | 2 |
| -1 | 41 |
| +1 | 193 |
| +2 | 18 |
| +3 | 6 |
| +4 | 4 |
| +11 | 1 |

Ba chênh lệch lớn hơn 5 giây cần giữ nguyên metadata và kiểm tra audio thực ở giai đoạn sau:

| Bài chính | Title | Guide | Instrumental | Chênh lệch |
|---:|---|---|---|---:|
| 335 | Sứ Mệnh Vĩ Đại Cứu Rỗi Cả Thế Giới | 03:07 | 03:25 | -18s |
| 343 | Theo Con Đường Cha An Xang Hồng Đã Đi | 02:04 | 02:24 | -20s |
| 452 | Thời Gian Con Dâng Cầu Nguyện Lên Cha | 03:35 | 03:24 | +11s |

Chênh duration không tự chứng minh ghép sai hoặc file lỗi. Khoảng metadata: guide 77–338s, instrumental 77–337s, silent 40–56s.

Silent có các số nguồn **472, 474–485**, không có 473 trong khoảng quan sát; cũng không có 471. Điều này không chứng minh silent phải có đủ dãy 471–485. Cả 13 silent có title và số nguồn tương ứng với một bài ca, nhưng ID, URL và thời lượng riêng; không tự biến chúng thành variant thứ ba của bài ca. Dùng số nguồn làm metadata tham chiếu, không làm khóa bài ca và không suy diễn quan hệ từ trùng số/title.

| Số nguồn silent | Audio ID | Thời lượng |
|---:|---:|---|
| 472 | 19977 | 00:00:49 |
| 474 | 19976 | 00:00:56 |
| 475 | 19975 | 00:00:40 |
| 476 | 19974 | 00:00:44 |
| 477 | 19973 | 00:00:42 |
| 478 | 19972 | 00:00:45 |
| 479 | 19971 | 00:00:51 |
| 480 | 19970 | 00:00:54 |
| 481 | 19969 | 00:00:53 |
| 482 | 19968 | 00:00:45 |
| 483 | 19967 | 00:00:43 |
| 484 | 19966 | 00:00:51 |
| 485 | 19965 | 00:00:42 |

## 6. Data model được đề xuất

Đề xuất **catalog JSON theo bài ca với variants**, cùng collection ngẫm nghĩ riêng. Phương án giữ 3 array nguyên trạng đơn giản khi ingest nhưng buộc mọi client ghép lại. Phương án chỉ có bảng audio phẳng phù hợp lưu trữ nhưng thiếu bản sắc bài ca. Catalog theo bài ca phù hợp nhất cho frontend/API/bot; vẫn giữ bản trích xuất nguồn riêng để đối soát. Chưa cần triển khai database hay API ở giai đoạn này.

Tách bốn trách nhiệm:

| Thành phần dự kiến | Nội dung |
|---|---|
| `catalog/catalog.vi.json` | Bài ca, section, số bài, title/category, guide/instrumental; meditation riêng; ID/URL HLS/thời lượng nguồn. Không có download/upload status, lỗi hoặc local path. |
| `source/snapshots/...` | Snapshot metadata đã kiểm tra đầy đủ và provenance: URL trang, thời điểm lấy, SHA-256, phạm vi nguồn. Không lưu cookie/token/thông tin thành viên vào catalog. |
| `state/transfers.sqlite` | Các job download/upload, retry, lỗi, local path, source fingerprint, output profile, kết quả đo thực. Khóa theo assetId + source fingerprint + output profile. |
| `delivery/manifest.vi.json` | Chỉ artifact đã hoàn thành và xác minh: assetId, objectKey, byte size, SHA-256, MIME, duration đo thực, profile. Không dùng để ghi tiến trình job. |

**Quy tắc schema:**

- `schemaVersion`: integer, bắt đầu 1. `provider="watv"`, `locale="vi"`, `collectionId="newsong"` là phạm vi chuẩn hóa nội bộ, không phải field nguồn.
- `songs` là object keyed bằng `main:N` hoặc `appendix:N`; mỗi entry có ID đầy đủ `watv:vi:newsong:<section>:<number>`.
- `section` enum `main | appendix`, `number` integer dương. Hai field cùng phạm vi tạo unique key. Khóa object phải khớp section/number trong record.
- `variants` có khóa `guide | instrumental`; hiện có cả hai ở 485 bài. Schema tương lai cho phép ít nhất một variant, tránh bỏ cả bài khi nguồn chỉ có một bản. Variant vắng mặt được bỏ khóa, không dựng URL hoặc ID giả.
- Mỗi variant có `assetId`, `source.audioId`, `source.jsonKey`, `source.hlsUrl`, `sourceDuration`, `durationSeconds`. `audioId/jsonKey` chuẩn hóa thành string; bảo toàn số gốc trong snapshot nếu cần. ID asset được scope theo provider, locale và list để không giả định ID duy nhất toàn cầu.
- `sourceDuration` giữ nguyên `playTime`; `durationSeconds = HH*3600 + MM*60 + SS`. Đây là thời lượng **nguồn khai báo**, không phải FFprobe đã xác minh. Duration đo thực nằm ở delivery manifest.
- `title`, `category` dùng chung ở cấp bài vì snapshot khớp 100%; nếu nguồn tương lai lệch giữa variants thì chặn merge tự động và review, giữ hai raw record trong snapshot.
- `meditations` là object keyed bằng ID `watv:vi:silent:<audioId>`; `sourceDisplayNumber` chỉ là metadata nguồn. Có một `asset`, không dùng chung namespace `main:N` của bài ca.
- `newsongAudioId` là định danh nguồn tốt nhất cho silent trong snapshot. Nếu WATV thay ID cho cùng tác phẩm, xem như bản ghi nguồn mới đến khi có quan hệ thay thế được review; không tự nối lịch sử bằng title.
- `jsonKey` hiện dư thừa nhưng giữ trong source metadata để phát hiện thay đổi giao ước nguồn.
- Không ràng buộc số bài phải liên tục; không coi category là enum đóng vì WATV có thể thêm chủ đề.
- URL HLS ở catalog là provenance/đầu vào ingest. Delivery manifest lưu **object key**, không đóng đinh domain R2 hoặc URL ký có thời hạn vào catalog.

**Cập nhật:** lấy snapshot mới → kiểm tra đầy đủ và anomaly → ghép bằng khóa → diff theo ID logic và ID audio → review thay đổi bất thường → công bố catalog revision mới. Thay title không đổi ID bài. Thay URL/ID audio đánh dấu nội dung nguồn cần xử lý lại bằng fingerprint. Không xóa bài vì một lần fetch rỗng/thiếu; record biến mất cần được xác minh, có lịch sử revision/tombstone riêng. Chỉ fingerprint URL/metadata không phát hiện được audio đổi nội dung ở cùng URL; cần chính sách kiểm tra định kỳ ở giai đoạn triển khai.

## 7. Ví dụ JSON thực tế

Đây là **hai bài ca** (bài chính 1 và phụ lục 1, cố ý cùng số để minh họa khóa đúng), cùng **hai bản ngẫm nghĩ**. Title, duration, ID và URL đều lấy từ snapshot đã đọc. ID catalog và tên field chuẩn hóa là phần đề xuất. Không phải toàn bộ catalog 983 audio.

```json
{
  "schemaVersion": 1,
  "provider": "watv",
  "locale": "vi",
  "collectionId": "newsong",
  "songs": {
    "main:1": {
      "id": "watv:vi:newsong:main:1",
      "section": "main",
      "number": 1,
      "title": "Ngày Thật Tôn Quý Phước Lành!",
      "category": "Lễ trọng thể",
      "variants": {
        "guide": {
          "assetId": "watv:vi:guide:4177",
          "sourceDuration": "00:02:06",
          "durationSeconds": 126,
          "source": {
            "audioId": "4177",
            "jsonKey": "4177",
            "hlsUrl": "https://vod.watv.org/watv_media_newsong/_definst_/mp4:WATV_NEWSONG/2023_07_07_095737_242.m4a/playlist.m3u8"
          }
        },
        "instrumental": {
          "assetId": "watv:vi:instrumental:17407",
          "sourceDuration": "00:02:04",
          "durationSeconds": 124,
          "source": {
            "audioId": "17407",
            "jsonKey": "17407",
            "hlsUrl": "https://vod.watv.org/watv_media_newsong/_definst_/mp4:WATV_NEWSONG/2020_05_15_090858_830.m4a/playlist.m3u8"
          }
        }
      }
    },
    "appendix:1": {
      "id": "watv:vi:newsong:appendix:1",
      "section": "appendix",
      "number": 1,
      "title": "Bây giờ Nước Thiên Đàng sắp kíp!",
      "category": "Sự trông cậy",
      "variants": {
        "guide": {
          "assetId": "watv:vi:guide:25495",
          "sourceDuration": "00:02:00",
          "durationSeconds": 120,
          "source": {
            "audioId": "25495",
            "jsonKey": "25495",
            "hlsUrl": "https://vod.watv.org/watv_media_newsong/_definst_/mp4:WATV_NEWSONG/20241216104939827.m4a/playlist.m3u8"
          }
        },
        "instrumental": {
          "assetId": "watv:vi:instrumental:25464",
          "sourceDuration": "00:01:59",
          "durationSeconds": 119,
          "source": {
            "audioId": "25464",
            "jsonKey": "25464",
            "hlsUrl": "https://vod.watv.org/watv_media_newsong/_definst_/mp4:WATV_NEWSONG/20250916092751043.m4a/playlist.m3u8"
          }
        }
      }
    }
  },
  "meditations": {
    "watv:vi:silent:19977": {
      "id": "watv:vi:silent:19977",
      "sourceDisplayNumber": 472,
      "title": "Tâm Linh Tha Thiết Cầu Nguyện",
      "category": "Ngẫm nghĩ",
      "asset": {
        "assetId": "watv:vi:silent:19977",
        "sourceDuration": "00:00:49",
        "durationSeconds": 49,
        "source": {
          "audioId": "19977",
          "jsonKey": "19977",
          "hlsUrl": "https://vod.watv.org/watv_media_newsong/_definst_/mp4:WATV_NEWSONG/2022_03_03_171611_233.m4a/playlist.m3u8"
        }
      }
    },
    "watv:vi:silent:19976": {
      "id": "watv:vi:silent:19976",
      "sourceDisplayNumber": 474,
      "title": "Thánh Thay! Thánh Thay!",
      "category": "Ngẫm nghĩ",
      "asset": {
        "assetId": "watv:vi:silent:19976",
        "sourceDuration": "00:00:56",
        "durationSeconds": 56,
        "source": {
          "audioId": "19976",
          "jsonKey": "19976",
          "hlsUrl": "https://vod.watv.org/watv_media_newsong/_definst_/mp4:WATV_NEWSONG/2022_03_03_171629_972.m4a/playlist.m3u8"
        }
      }
    }
  }
}
```

## 8. Cấu trúc folder và object R2 dự kiến

Các đường dẫn bên dưới là **đề xuất**, chưa tạo thư mục pipeline hay audio:

```text
AudioTP/
  docs/audio-data-analysis.md             # báo cáo này
  source/snapshots/<timestamp>/           # snapshot metadata + provenance
  catalog/catalog.vi.json                 # catalog chuẩn hóa
  catalog/revisions/<revision>/           # lịch sử catalog
  schemas/                               # schema sau khi duyệt model
  scripts/                               # ingest/validate/download/upload sau khi duyệt
  state/transfers.sqlite                 # trạng thái job, gitignore
  delivery/manifest.vi.json               # mapping artifact đã xác minh
  media/audio/v1/...                      # audio local, gitignore
  tmp/                                   # file đang tải, gitignore
```

Đề xuất object key R2, với `<sha256>` là hash bytes output thực tế sau này, không phải ID bịa sẵn:

```text
audio/v1/watv/vi/newsong/main/0001/guide/4177/<sha256>.m4a
audio/v1/watv/vi/newsong/main/0001/instrumental/17407/<sha256>.m4a
audio/v1/watv/vi/newsong/appendix/0001/guide/25495/<sha256>.m4a
audio/v1/watv/vi/meditations/19977/<sha256>.m4a
catalog/v1/vi/<revision>/catalog.json
catalog/v1/vi/<revision>/delivery.json
catalog/v1/vi/current.json
```

Giữ khóa media bất biến theo hash để thay bản audio không ghi đè file cũ đang cache; `current.json` trỏ tới revision catalog + delivery đồng bộ. Padding số `0001` chỉ là cách trình bày key, không là định danh/index và không được cắt số lớn. Local có thể dùng cùng cấu trúc key dưới `media/`; output tạm gắn job ID, đổi sang tên hash sau khi xác minh. `.m4a` là **mục tiêu dự kiến**, chưa cam kết codec/profile; quyết định remux/transcode sau khi kiểm tra media thực, đưa profile vào manifest hoặc thêm prefix profile nếu xuất nhiều định dạng.

R2 lưu object theo key phẳng; dấu `/` chỉ nhóm prefix, không tạo thư mục thật. Có thể dùng HTTP/custom metadata cho file nhưng catalog/delivery manifest vẫn là nguồn tra cứu. Đối chiếu tài liệu chính thức qua Context7: [R2 Objects / Prefixes and folders](https://developers.cloudflare.com/r2/objects/), [Workers API reference](https://developers.cloudflare.com/r2/api/workers/workers-api-reference/). Chưa chọn bucket, domain, public/private access hay cấu hình CORS.

## 9. Website, API và bot chat về sau

Website và bot nên cùng dùng **API của project** đọc catalog + delivery manifest. R2 giữ file; lookup theo số bài do catalog/API giải quyết, không phải suy từ thứ tự object listing. Ví dụ giao ước dự kiến, chưa có endpoint hoạt động:

```text
GET /api/v1/vi/songs/main/1
GET /api/v1/vi/songs/appendix/1
GET /api/v1/vi/songs/main/1/audio?variant=guide
GET /api/v1/vi/meditations/watv%3Avi%3Asilent%3A19977
GET /api/v1/vi/search?q=<tên-hoặc-số-bài>&kind=song
```

Lookup bài không có số (ví dụ main/34) trả not found; variant chưa có artifact trả unavailable, không tự lấy nhầm variant. Request bot “bài 1” mặc định phần chính hoặc hỏi lại nếu ngữ cảnh muốn phụ lục. Search không dấu là index phụ trợ, không đổi title gốc hoặc khóa định danh. Khi chưa có local/R2 artifact thì chưa giả rằng có URL phát của project.

Đã quan sát trang sử dụng endpoint WATV có `/member`, nhưng **chưa xác minh đó là API công khai, ổn định hoặc truy cập được không đăng nhập**. Không thiết kế frontend/bot phụ thuộc trực tiếp endpoint nội bộ và không nhúng cookie/token WATV vào client. Nếu sau này muốn đồng bộ trực tiếp từ WATV, cần xác minh riêng giao ước truy cập, response và phạm vi metadata được phép lấy; API của project giữ giao ước ổn định cho người dùng.

## 10. Những giả định chưa chắc chắn và điểm dừng

- Không có file nguồn cũ để so sánh; kết quả áp dụng cho snapshot trang mới ngày kiểm tra.
- Chưa xác định nguyên nhân snapshot cũ thiếu guide, cơ chế cache/session, hay điều kiện đăng nhập chính xác. Không được coi fetch rỗng là thao tác xóa catalog.
- Chưa đọc code player hoặc Network response: DOM xác nhận ba tab và ánh xạ số/title/duration; không chứng minh website JOIN bằng cùng thuật toán đề xuất.
- Chưa rõ nguyên nhân các số bài thiếu, thứ tự/định danh ấn bản, tính bền vững lâu dài của audio ID và số hiển thị.
- Silent có trùng số/title với bài ca nhưng không suy diễn chung hệ thống định danh; quan hệ tác phẩm nếu cần phải xác minh riêng.
- Duration là metadata; chênh 11–20 giây, codec, chất lượng, hiệu lực URL, header/cookie media cần có hay không đều chưa được kiểm tra bằng tải audio.
- URL HLS hiện không có query token trong snapshot; không vì vậy mà bảo đảm truy cập ẩn danh hoặc vĩnh viễn.
- Storage key, ID catalog, API path, revision và output profile đều là đề xuất cần review; chưa provision hoặc triển khai.

**Dừng sau báo cáo này để người dùng review model. Không bắt đầu download/FFmpeg/upload/API/frontend implementation.**
