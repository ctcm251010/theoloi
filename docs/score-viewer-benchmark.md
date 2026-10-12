# AudioTP — Benchmark hiển thị bản nhạc A/B/C

Ngày 12/10/2026. Prototype thực nghiệm, chưa phải ứng dụng production hoặc quyết định chốt công nghệ. Chỉ dùng fixture tự soạn, không truy cập/tải/chụp BookVN, không dùng audio hay R2.

## Fixture và tính công bằng

Một nguồn `benchmarks/score-viewer/fixtures/score.json`: 4 trang, 6 khuông/trang, 4 ô nhịp 4/4/khuông, 20 nốt/khuông, **480 nốt** tổng cộng. Có cao độ C4–A4, trường độ nốt đen/móc đơn, ô nhịp và từng âm tiết lời Việt. Giai điệu/lời tự soạn, không chép tác phẩm bên ngoài. Đây là mẫu đơn âm có chủ đích, không đại diện hợp xướng nhiều bè, dấu luyến phức tạp hoặc cả kho bản nhạc.

Cùng một display list tạo PDF vector và SVG geometry/HTML text. PNG/WebP/AVIF được rasterize từ chính PDF ở **1520×2120**, tương đương 2 pixel/đơn vị bố cục 760×1060. C không có `<image>` hoặc raster nhúng; khuông/nốt là line/ellipse vector, lời là HTML span. Không phải đưa một PNG vào SVG rồi gọi là vector. Ký hiệu khóa nhạc ở mẫu là nét hình học tự dựng, chưa đạt mức khắc bản chuyên nghiệp.

Font Noto Sans SIL OFL được kèm license; PDF nhúng subset. C cũng dùng subset **22.120 bytes**, cùng glyph outlines, để không so PDF subset với font web đầy đủ 569.208 bytes. PDF.js **6.4.299** Apache 2.0, module **860.818 bytes**, worker **2.229.713 bytes**; đây là chi phí runtime riêng, không cộng lặp vào mỗi bài. Có provenance URL/size/SHA-256 từng file vendor. Không tải script CDN lúc chạy.

## Dung lượng thực đo trên đĩa

| Phương án | Trang đầu / dữ liệu cần cho trang đầu | Cả 4 trang | Thiết lập |
|---|---:|---:|---|
| A PDF vector | 65.566 B (file 4 trang) | 65.566 B | PDF trực tiếp từ vector/text, có font subset |
| B PNG | 206.685 B | 830.648 B | RGB lossless |
| B WebP | 43.800 B | 175.200 B | lossless, quality=100, method=6 |
| B AVIF | 104.052 B | 419.229 B | quality=90, 4:4:4, speed=6; lossy |
| C SVG + HTML Text | 44.678 B + font 22.120 B = 66.798 B | 178.720 B + font = 200.840 B | JSON gồm geometry SVG + vị trí/text HTML |

Bytes chính xác, không phải KiB. JSON source/manifest chỉ phục vụ fixture/provenance, không cần tải để xem từng trang (UI tải manifest nhỏ để export bằng chứng). Server không gzip/Brotli; C có thể hưởng text compression trong triển khai tương lai, chưa đo. PNG/WebP cùng pixel nên so dung lượng trực tiếp; AVIF cấu hình này có tổn hao và không phải tối ưu rate-distortion cho mọi codec. Không suy ra AVIF luôn lớn hơn WebP từ một fixture.

## Môi trường và phương pháp

Windows 11 build 26200; Python 3.13.15; ReportLab 5.0.1, PyMuPDF 1.28.2, Pillow 12.3.0, fonttools 4.66.1. OS báo Intel64 Family 6 Model 79 Stepping 1, 36 logical processors; sandbox từ chối WMI nên không suy đoán tên thương mại CPU/RAM hệ thống. Browser UA/DPR/viewport/visibility và thời điểm chạy lấy trực tiếp trong raw JSON.

Trình duyệt Chrome qua extension profile Bang. Server `127.0.0.1:8765`, chỉ phục vụ folder prototype, không nén, không mạng WAN/Cloudflare. Chưa build Tauri, chưa đo WebView2/EXE trên máy sạch.

- Cold tài nguyên: renderer tài liệu mới, media fetch `cache:reload`. Không phải cold process/OS/JIT; PDF.js module được import trước vòng đo và ghi thời gian riêng.
- Warm: renderer mới, fetch `cache:default` cùng URL ngay sau cold; phải thấy resource transferSize=0 để xác nhận HTTP hit. Worker/module runtime dùng cache riêng. Revisit: trang 1 sau trang 2 trong cùng renderer, là cache phiên riêng.
- Mỗi trial đo mở trang 1, chuyển trang 2, quay lại trang 1, zoom 100%. Thời gian `ms` từ trước fetch đến render/decode xong và 2 animation frame; `workMs` dừng trước chờ frame, `frameWaitMs` ghi riêng. Không gọi thời điểm này là đo photon/screen hay LCP của toàn app.
- PDF tải toàn bộ file nhỏ bằng fetch rồi đưa bytes cho PDF.js; chưa kiểm thử Range streaming. B/C tải đúng trang được chọn, giữ tối đa 2 encoded buffer/JSON pages; một image/canvas đang hiển thị. Không prefetch trang 3–4.
- Resource timing theo request same-origin, không dùng time giả hoặc kích thước ước lượng thay cho transferSize. `performance.memory` chỉ là JS heap thô, có thể thiếu worker/GPU/image decode. [MDN memory](https://developer.mozilla.org/en-US/docs/Web/API/Performance/memory), [MDN transferSize](https://developer.mozilla.org/en-US/docs/Web/API/PerformanceResourceTiming/transferSize).

## Thời gian và bộ nhớ

Đã lưu **90 quan sát**, 3 vòng × 5 định dạng × cold/warm × first/next/revisit. Mỗi ô dưới là median của 3 mẫu, đơn vị ms; min/max chỉ cho trang đầu. Raw: [chrome-raw.json](../benchmarks/score-viewer/evidence/chrome-raw.json), thống kê độc lập: [chrome-summary.json](../benchmarks/score-viewer/evidence/chrome-summary.json). Chrome **155.0.0.0**, viewport **1745×968 CSS px**, DPR **1,1000000238**. Chạy xong `2026-10-11T22:04:25.780Z` (05:04 ngày 12/10, Bangkok). PDF.js module init riêng **70,2 ms**.

| Định dạng | Cache | Trang đầu tổng | Trang 2 tổng | Quay lại tổng | Trang đầu work | Trang đầu chờ frame | Trang đầu min–max |
|---|---|---:|---:|---:|---:|---:|---:|
| A PDF | cold | 2100,0 | 1101,8 | 1068,1 | 2041,2 | 56,3 | 300,9–2100,3 |
| A PDF | warm | 2159,5 | 1085,2 | 1068,3 | 2093,3 | 74,3 | 2147,6–2178,1 |
| B PNG | cold | 1111,0 | 1085,1 | 66,5 | 70,5 | 1031,8 | 138,7–1114,3 |
| B PNG | warm | 1082,8 | 1085,0 | 82,9 | 52,4 | 1030,4 | 1080,9–1083,6 |
| B WebP | cold | 1082,9 | 1084,8 | 66,2 | 50,8 | 1031,2 | 1064,6–1084,0 |
| B WebP | warm | 1082,5 | 1085,0 | 82,8 | 52,9 | 1030,8 | 1081,0–1083,7 |
| B AVIF | cold | 1083,5 | 1085,1 | 1068,0 | 85,4 | 1004,4 | 1083,1–1098,0 |
| B AVIF | warm | 1083,3 | 1084,7 | 1085,2 | 60,6 | 1021,3 | 1081,9–1083,3 |
| C SVG/HTML | cold | 1047,5 | 65,9 | 66,6 | 31,4 | 1009,9 | 1032,9–1049,6 |
| C SVG/HTML | warm | 1031,3 | 65,5 | 66,3 | 19,4 | 1011,9 | 1031,2–1031,4 |

**Không dùng bảng này để khẳng định tốc độ UX/WebView2.** Nhiều lượt chờ frame khoảng 1 giây dù visibility start/end đều `visible`; chưa xác định nguyên nhân scheduling/occlusion trong môi trường extension. PDF có khoảng biến thiên cold lớn và warm không nhanh hơn cold. Giữ nguyên quan sát bất thường, không lọc bỏ mẫu xấu hoặc gán chắc do background. Median work và median frame được tính độc lập nên không nhất thiết cộng thành median tổng. Thứ tự format cố định, mẫu ít, không randomize/GC/hardware isolation; có hoạt động desktop/công cụ đồng thời. Cần chạy foreground trên máy mục tiêu trước quyết định tốc độ cuối cùng.

Kiểm tra cache từ raw: mọi first cold có transfer >0; mọi resource trong warm có transferSize=0. Median first transfer A **65.866 B**, PNG **206.985 B**, WebP **44.100 B**, AVIF **104.352 B**, C **67.398 B**, gồm overhead mà Resource Timing báo. Không có request page-3/page-4 trong benchmark trang 1→2→1: lazy loading hoạt động. Revisit app cache tách riêng, không gọi là HTTP cold.

Median JS heap theo nhóm khoảng **20,6–22,4 MiB**, trong một context chạy tuần tự: không so thành RAM của từng phương án. Pixel backing-store arithmetic tại 100%, DPR đo được: canvas PDF **3.907.116 B**; một ảnh decoded RGB→RGBA **12.889.600 B**; C không có image/canvas buffer do code cấp phát (không có nghĩa RAM=0). Canvas/GPU/worker overhead, peak native memory, cache nội bộ decoder và thu hồi GC chưa đo. Giới hạn encoded cache 2 trang đã triển khai; không hứa browser giải phóng vật lý ngay khi bỏ reference.

## Chất lượng và zoom

Kiểm tra pixel so với raster RGB gốc: PNG và WebP **max error 0, MAE 0** cả 4 trang. AVIF max error **14–15/255**, MAE **0,0881–0,0892/255** trên cả trang; nền trắng chiếm nhiều diện tích nên MAE nhỏ không chứng minh nét chữ/nốt hoàn toàn như nhau. File manifest ghi từng trang và thời gian encode; cấu hình WebP method=6 mất khoảng 5,8–6,1 giây/trang, PNG khoảng 82–104 ms/trang và AVIF khoảng 1,5–1,6 giây/trang trên lần tạo fixture này. Đây là encode offline một lần, không phải thời gian mở trang.

Ảnh 2× có giới hạn độ phân giải: ở 400%, một pixel nguồn phủ 2 CSS pixel. PDF được render lại theo zoom×DPR; SVG/HTML dùng hình học/chữ vector. Canvas PDF ở 400% có thể cần bộ đệm xấp xỉ 16 lần 100%; ảnh không tăng thông tin khi phóng. C giữ chữ HTML để tìm kiếm trong DOM, nhưng prototype hiện tắt pointer events trên text layer nên chưa hỗ trợ chọn chữ trực tiếp bằng chuột. PDF prototype hiện chỉ canvas (chưa thêm text layer), B chỉ có alt của trang.

Đã kiểm tra trực tiếp A/WebP/C tại 50%, 100%, 200%, 400% và vừa trang; chuyển qua đủ 4 trang. PNG/AVIF decode thành công trong benchmark, chưa làm bộ screenshot zoom riêng cho hai codec này. Ở 400%, ảnh WebP thấy nét mềm hơn trong khi PDF render lại và SVG/HTML giữ nét; dấu Việt không có ô glyph thiếu sau sửa font. C có lệch baseline/anti-alias nhẹ với PDF, chưa đạt pixel-identical. Bằng chứng UI cuối có [chrome-smoke.json](../benchmarks/score-viewer/evidence/chrome-smoke.json); console không có warn/error trong lượt smoke.

Ảnh thật từ prototype (JPEG screenshot, không phải hình minh họa dựng):

Có thêm [ảnh prototype và phần bảng smoke](../benchmarks/score-viewer/evidence/prototype-results.jpg), từ lượt smoke riêng **1 vòng / 30 quan sát** của code bàn giao, không phải bảng median 3 vòng ở trên. [Raw smoke benchmark](../benchmarks/score-viewer/evidence/chrome-final-smoke-benchmark.json) lưu riêng; chạy PASS, console không warn/error. Một số cạnh ảnh full-page bị giới hạn bởi capture của công cụ; sáu ảnh viewport bên dưới là bằng chứng zoom chính.

![A PDF vừa trang](../benchmarks/score-viewer/evidence/a-pdf-fit.jpg)
![B WebP vừa trang](../benchmarks/score-viewer/evidence/b-webp-fit.jpg)
![C SVG/HTML vừa trang](../benchmarks/score-viewer/evidence/c-svg-html-fit.jpg)
![A PDF zoom 400%](../benchmarks/score-viewer/evidence/a-pdf-400.jpg)
![B WebP zoom 400%](../benchmarks/score-viewer/evidence/b-webp-400.jpg)
![C SVG/HTML zoom 400%](../benchmarks/score-viewer/evidence/c-svg-html-400.jpg)

## Tích hợp, cache và phân phối

| Tiêu chí | A PDF | B ảnh | C SVG + HTML |
|---|---|---|---|
| Độ phức tạp prototype | Trung bình: viewer/worker/font, lifecycle và canvas zoom | Thấp nhất: decode, lazy page, fallback codec, cache | Cao nhất ở khâu tạo nhạc: layout, glyph, lyric alignment; viewer đơn giản hơn |
| Tài liệu có sẵn | Giữ PDF gốc/ấn bản/in ấn | Hợp nguồn ảnh được phép, có thể tạo derivative từ PDF được phép | Cần vector/nhạc cấu trúc có sẵn hoặc công biên soạn; không tự phục hồi chính xác từ PNG |
| Tauri 2/WebView2 | Bundle PDF.js/worker, CSP/worker/font, test actual runtime | img/decode đơn giản; kiểm tra AVIF trên runtime mục tiêu, fallback WebP/PNG | SVG/HTML web chuẩn, cần sanitize nguồn ngoài/CSP/font/a11y |
| Private R2 | Một object PDF, GET/HEAD/Range khi API đã kiểm thử | Object từng trang/codec; manifest xác định trang/hash/size | Object JSON/vector từng trang + font hash dùng chung; không cho SVG/script tùy ý |
| Cache | File hash + quyền user, document lifecycle; bounded canvas | Lazy LRU encoded/decode có giới hạn, không tải cả thư viện | Hash cho geometry/text/font; bounded DOM/pages, edition/version rõ ràng |

Tauri asset protocol cần scope/CSP hẹp nếu dùng file local; không mở `$HOME/**`. Đây là phân tích tích hợp, không phải kết quả WebView2 đã chạy. [Tauri asset protocol](https://tauri.app/security/asset-protocol). Worker R2 có range/conditional read APIs, nhưng authentication/authorization/cache user phải được triển khai riêng. Không public bucket hoặc đưa R2 credential vào client. [Cloudflare R2 Workers API](https://developers.cloudflare.com/r2/api/workers/workers-api-reference/).

## Kiểm thử, lỗi và giới hạn

Đã thấy và sửa khi chạy thử: API PDF.js mới không có `PDFDocumentProxy.destroy`, dùng loading task destroy; lời dài bị va chạm ở khoảng cách nốt cố định, chuyển sang căn giữa theo glyph width và có regression test; font không có ký hiệu tempo ♩, thay bằng chữ Tempo và test cmap; UI zoom ban đầu lệch với scale thực, sửa selected/fit; module viewer cũ bị HTTP cache giữ lại, code/HTML dùng no-cache còn fixture giữ cache để đo.

Review độc lập phát hiện resource timing buffer mặc định có thể đầy ở lượt dài/lặp lại, gây transfer=0 giả. Đã clear buffer trước mỗi render tuần tự và bắt buộc có timing entry cho mọi fetch thực hiện; thiếu bằng chứng thì FAIL. Thêm regression test cho missing entries/cache-hit hợp lệ và xóa timestamp kết thúc cũ khi bắt đầu lượt mới. Chỉ gán font vào session sau load thành công để không dùng fallback font sau lỗi. Lượt 90 quan sát được chạy sau các sửa logic này; sau đó tách hai helper cùng logic để có Node unit test và smoke bản cuối.

Browser Use wait-for-download bị timeout; lưu raw trực tiếp từ nội dung JSON hiển thị trong DOM bằng filesystem writer, không suy đoán kết quả download. Nút export vẫn có trong prototype, nhưng chưa xác minh download end-to-end qua API của công cụ. Không dùng kết quả chạy thử trước sửa trong bảng chính.

**Kiểm thử cuối:** Python toàn project **133 tests / 132 PASS / 0 FAIL / 1 SKIP**, 107,721 giây; log `tmp/score-benchmark-final-tests.log`. SKIP có sẵn: `test_delivery.DeliveryTests.test_redirected_file_is_rejected`, do tài khoản Windows không tạo được file symlink; không nâng quyền máy. Bốn test mới kiểm tra cùng nguồn/vector/PDF tiếng Việt/hashes/codec lossless, font coverage, không va chạm lời và loopback server traversal/hidden paths/POST/cache headers (symlink nhánh bổ sung chạy khi hệ điều hành cho phép). Node metrics tests PASS: median/null/grouping, thiếu timing không được thành cache hit, reset timestamp/error; `node --check viewer.js` PASS. Review cuối có một Important đã sửa; font failure và stale timestamp được xử lý luôn vì ảnh hưởng kết quả PASS. Minor pointer-events được giữ và ghi rõ giới hạn chọn chữ.

Danh sách chính: tạo folder `benchmarks/score-viewer/` gồm generator, vendor/provenance/licenses, fixture/manifest/hash, viewer HTML/CSS/JS, metrics/tests, loopback server, analyzer, README và evidence; tạo `tests/test_score_benchmark.py`, báo cáo này và `docs/superpowers/plans/2026-10-12-score-benchmark.md`. Dependency mới chỉ cho fixture: ReportLab/Pillow/fonttools, có pin riêng trong prototype; không thay requirements/pipeline audio. Đối chiếu SHA-256 audio catalog, audio manifest, sheet catalog, BookVN snapshot và config R2 với baseline đều không đổi. Không đọc/sửa credential, không mở upload/download state thật, không chạy B10 hoặc FFmpeg.

Sửa `docs/windows-app-architecture.md` để liên kết kết quả thực nghiệm, không chốt Tauri/native runtime. Các pin bảo toàn có trong [protected-hashes.json](../benchmarks/score-viewer/evidence/protected-hashes.json). Sau kiểm thử đã dừng server Codex; người dùng chạy lệnh README để mở prototype bằng process PowerShell riêng.

Chưa có remote/cloud latency, tổng RAM process, GPU profiling, installer startup/size, native WebView2, accessibility toàn diện, full score engraver, harmony/ties/beams nhiều bè, long PDF Range hoặc kho tài liệu thật. Bằng chứng không cấp quyền tải/chuyển đổi BookVN. Các định dạng dùng cùng nội dung/bố cục, nhưng rasterizer PDF.js/PyMuPDF và HTML text layout có thể anti-alias/baseline khác nhau; không hứa pixel-identical giữa A và C.

## Hướng dùng và roadmap

Đề xuất **hybrid theo nguồn** từ bằng chứng dung lượng/chất lượng và mức độ triển khai: giữ PDF gốc khi có nguồn được phép (nhỏ nhất cả bộ fixture, zoom tốt); WebP lossless làm trang xem nhanh/thumbnail khi nguồn là ảnh hoặc derivative được phép (nhỏ hơn PNG khoảng 79%, pixel không đổi); C cho nội dung có source nhạc/vector thật, cần lời có cấu trúc hoặc tương tác (work thấp trong thử nghiệm nhưng chưa chứng minh UX/native RAM). AVIF quality=90 hiện không có lợi thế cho fixture này, chưa loại codec khỏi các kiểu tài liệu khác. Không coi C là đường chuyển tự động từ BookVN PNG sang bản khắc vector. Chưa chốt công nghệ desktop từ benchmark Chrome có nhiễu scheduling.

Tiếp theo: người dùng thử cùng prototype khi Chrome/Edge foreground, rồi chạy bản WebView2/Tauri thử riêng với fixture này trên máy mục tiêu; đo tổng RAM native/process, cold launch, scrolling nhiều trang, DPI khác nhau và mạng mô phỏng. Chỉ sau đó chốt viewer/cache/codec, thiết kế API private và xem xét nguồn/quyền file thật. Không deploy trong bước này.

Lệnh Windows và toàn bộ thao tác ở [README prototype](../benchmarks/score-viewer/README.md). Source/tooling/test mới nằm dưới `benchmarks/score-viewer/` và `tests/test_score_benchmark.py`; không sửa pipeline audio, catalog/manifest/state hoặc credential.
