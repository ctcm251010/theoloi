# AudioTP — Khảo sát UI/player WATV

Ngày 12/10/2026, Chrome extension profile **Bang** (Profile 4 đã được người dùng xác nhận). Nguồn: [trang WATV đang mở](https://worship1.watv.org/vi/sermon/102232), DOM, tương tác UI và inventory tài nguyên đã được trình duyệt quan sát. Không đọc cookie/token, không gọi API thành viên, không tải audio thành file. Đây là phát bình thường trên website theo yêu cầu người dùng, không phải kiểm thử R2.

## Kết quả quan trọng về hai mục ghim

| Mục | Quan sát trực tiếp | Giới hạn kết luận |
|---|---|---|
| Nhạc ngẫm nghĩ | UI ghi **00:56**; hai lần chọn trong cùng lần mở trang yêu cầu cùng playlist `WATV_NEWSONG/2022_03_03_171629_972.m4a/playlist.m3u8`. URL khớp chính xác snapshot `silentSongList`, audio ID **19976**, title **Thánh Thay! Thánh Thay!**, số nguồn 474 | Chứng minh nguồn đã phát trong phiên đó. Chưa chứng minh lựa chọn cố định giữa ngày/lần mở trang; không gán cả mục ghim thành một silent cố định trong catalog |
| Cầu nguyện chúng con mong muốn & Nhạc ngẫm nghĩ | UI ghi **01:08**; chọn mục này phát sinh playlist `WATV_PRAYER/pray/our_wish.m4a/playlist.m3u8`. Khi kết thúc trong lần quan sát, player reset về “Vui lòng chọn nhạc.”, không thấy chuyển sang nguồn khác | Một nguồn HLS được quan sát trong lượt phát, **không có bằng chứng chuỗi nhiều file**. Không xác minh cấu trúc lời/nhạc bên trong recording bằng nghe hoặc phân tích bytes |

Các URL trên là bằng chứng quan sát request phát khi bấm UI, không phải ghép bằng tên hoặc thời lượng. Inventory không phải Network trace đầy đủ; không có API Network/handler nội bộ hoặc media detached để đọc duration chính xác. **00:56/01:08 là thời lượng UI/metadata, chưa phải số giây đo từ media của website.** Không khẳng định đã nghe và phân biệt nội dung bằng tai.

Manifest local có `watv:vi:silent:19976`, với duration đo từ file B7, tách khỏi duration nhãn của website. Nguồn `our_wish` không có trong manifest 983. Cùng URL HLS chứng minh sự tương ứng với record nguồn, không tự xác nhận recording ngoài catalog/quyền phân phối.

## Quan hệ với 14 URL PRAYER

Báo cáo cũ ghi 14 URL PRAYER ngoài 983. Lần khảo sát này chỉ đọc whitelist URL PRAYER từ script nhúng trong DOM: thấy **13 literal** `pray_01`–`pray_13`; inventory sau bấm mục kết hợp thấy **our_wish**. Snapshot audio lưu trên đĩa chỉ chứa ba danh sách 983 record, không chứa metadata đầy đủ của 14 PRAYER.

- Có bằng chứng trực tiếp `our_wish` liên quan tới nút thứ hai trong lượt thử.
- **Không quan sát request `pray_01`–`pray_13`** trong các lượt thử hai mục ghim; chưa biết chúng được dùng ở đâu/có phải lựa chọn theo ngữ cảnh khác không.
- Nút ghim thứ nhất đã yêu cầu một URL NEWSONG thuộc silent; không được suy từ nhãn “ngẫm nghĩ” rằng nó dùng PRAYER.
- Không cộng 14 URL vào catalog và không suy ra cần tải đủ 14 để triển khai hai nút.

## Hành vi player đã thử

1. Bấm ghim thứ nhất: tên/thời lượng xuất hiện ở **cùng `.player`** phía dưới; hàng được chọn đổi từ pin sang animation `nowPlaying`, icon `ico-pause-mini`.
2. Bấm pause ở thanh player: icon thành `ico-play`, animation có class `paused`. Bấm lại mục khác thay thế tên/tiến trình; hàng cũ hết trạng thái playing.
3. Bấm giữa `.progress-bar`: progress chuyển tới khoảng **47–49%** ở cả hai mục ghim; thanh tiếp tục tiến khi đang phát. Đây là bằng chứng tua bằng UI, không đo độ chính xác của seek HLS hoặc byte Range.
4. Chuyển sang tab Nhạc đệm trong khi ghim đang chạy: ghim vẫn là mục trong player; **chuyển tab không tự chọn bài**.
5. Chọn bài 1 Nhạc đệm: player ghi “Ngày Thật Tôn Quý Phước Lành!”/02:04; hàng ghim không còn pause. Mở tab silent: có **13 hàng**, player vẫn giữ bài đệm cho tới khi chọn hàng khác.
6. Chọn silent đầu danh sách: số nguồn **472**, title “Tâm Linh Tha Thiết Cầu Nguyện”, 00:49. Không đánh số lại thành 1 và không ghép với guide số 472 trong ứng dụng.
7. Chọn bài 1 Hướng dẫn: cùng player đổi sang 02:06. Mục kết hợp kết thúc/reset trong một lượt theo dõi; chưa xác minh end/loop/autonext của tất cả nhóm.

DOM chính không có `audio`/`video` cho player này trong thời điểm đọc (iframe YouTube sermon là player riêng, không tương tác). Vì vậy chỉ kết luận có **một thanh điều khiển audio chung trên UI**; chưa chứng minh website chỉ có đúng một đối tượng audio nội bộ. AudioTP tự dùng một HTMLAudioElement để bảo đảm không chồng âm.

## Layout, tìm kiếm và responsive

- Bố cục rộng ban đầu: panel Bài Ca Mới bên phải rộng khoảng **400 CSS px**, hai hàng ghim ở trên; ba tab dạng pill; ô tìm kiếm; danh sách cuộn; thanh player cố định dưới panel. Header/tài khoản được loại khỏi ảnh minh họa.
- Hàng hiển thị số nguồn, title, category, MM:SS và icon; title dài bị ellipsis. Màu active xanh tím, divider nhạt, nền trắng. Phụ lục hiện nhãn riêng.
- Search `100` + Enter trả một hàng bài 100; search “Tình Yêu Thương Lớn Lao” cũng trả bài 100. Xóa query + Enter khôi phục danh sách. Không suy rộng thành tìm không dấu trên WATV: chưa thử quy tắc đó.
- Trong viewport hẹp được quan sát, panel desktop ẩn; mở từ footer “Bài Ca Mới”, rồi liên kết “Nhạc đêm Bài Ca Mới” để hiện panel mobile. Player dưới toàn chiều ngang, tabs trên danh sách. Có nút đóng riêng.
- Capability viewport có lúc không phản ánh kích thước set/reset ngay qua DOM; số đo thực tế sau cùng là khoảng **685×900 CSS client**. Không dùng giá trị override yêu cầu làm bằng chứng đo. Đã gọi reset; không sửa cài đặt/profile Chrome.
- Sau reload, bố cục mobile và trạng thái panel thay đổi; không lấy được bằng chứng desktop mới để xác minh quy tắc chọn ghim qua nhiều lần mở trang. Hai lượt phát nguồn thứ nhất bên trên thuộc cùng phiên trang trước reload.

![Hai mục ghim và player paused](../apps/windows/evidence/watv-quick-paused.jpg)

[Bài hướng dẫn đang chọn](../apps/windows/evidence/watv-guide-player.jpg), [panel hẹp quan sát được](../apps/windows/evidence/watv-narrow-player.jpg). Chỉ lưu UI nghiên cứu, không đưa logo/icon/tài nguyên WATV vào app.

## Thiết kế AudioTP áp dụng

Cập nhật implementation 0.2: đã bỏ âm mẫu khỏi luồng nghe catalog, source được lấy qua MediaAPI theo assetId. Audio thật đã phát local; Worker/live EXE vẫn cần deploy/toolchain. Các mô tả demo dưới đây là thiết kế/thử nghiệm 0.1 được giữ làm lịch sử, không phải fallback hiện hành. [Báo cáo P0–P4](autonomous-implementation-report.md).

Giữ Phát nhanh ở trên thư viện, đúng hai tên, ba tab đầy đủ, dấu đang phát và player cố định. Cải tiến: sidebar, bộ lọc chủ đề/nhóm, tìm tiếng Việt không dấu, nút điều khiển có nhãn, trạng thái loading/error, yêu thích/gần đây, phím tắt, giao diện sáng/tối.

Tách **tab đang xem**, **bài đang phát** và **queue đã chọn**. Chuyển tab không cắt audio; bấm bài mới thay nguồn trên một media element. Thời lượng player lấy từ media thật đang phát, không lấy duration catalog khi đang dùng âm demo 12 giây.

Hai quick cards tồn tại độc lập với ba tab; hiện **unavailable**. Không gắn alias cố định 19976 từ một phiên trang và không dùng URL our_wish trực tiếp trong ứng dụng. Chỉ bật khi source rule, quyền sử dụng và asset/API được review riêng; thiếu điều kiện nào vẫn không phát. Không có URL giả.

## R2 và bước bổ sung nguồn sau review

Status local B9 chỉ đọc: **983 uploaded / 983 verified / 0 failed / 0 remaining**, gồm guide485/instrumental485/silent13. Không gọi R2 để kiểm tra lại; B10 vẫn user-run và metadata audit khác full remote-content SHA.

| Nội dung | Trong manifest/R2 theo B9 | Sẵn sàng phát production từ MVP |
|---|---|---|
| 485 guide + 485 instrumental + 13 silent | Có đủ 983 theo state local | Chưa — thiếu authenticated API/policy phân phối |
| Nguồn 19976 quan sát ở ghim đầu | Đã nằm trong 13 silent; không cần tải trùng nếu sau này review chốt alias đó | Chưa — quy tắc lựa chọn ghim chưa chốt |
| `our_wish` | Không có trong delivery manifest | Chưa — quyền/nhập nguồn/verification riêng |
| `pray_01`–`pray_13` | Không có trong delivery manifest | Chưa — chưa xác minh chúng liên quan UI nào |

Quy trình tiếp: review bằng chứng nguồn/chuỗi và scope quyền → tạo catalog quick riêng versioned → nhập đúng asset được duyệt, state/hash riêng → user-run download subset → review manifest mới → user-run upload. Không thay baseline 983. Chưa có downloader/importer cho PRAYER, nên **không đưa command tải/upload PRAYER giả**. Command audit B10 hiện có nằm trong `r2-verification.md` và không được chạy ở bước này.
