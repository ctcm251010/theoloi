# Báo cáo B4/B5 — Thử nghiệm media HLS

**Trạng thái: PASS — 11/11 sample**, remux stream copy và decode toàn bộ thành công. Dừng trước B6.

Kết luận chính: **chọn AAC nguồn → M4A bằng `-c:a copy` làm default đề xuất**. Không cần transcode trong 11 sample. Các chênh lệch metadata lớn ở main:335, main:343 và main:452 không phản ánh chênh lệch thời lượng media hiện tại.

## Phạm vi và bằng chứng

- Sample cố định: main:1,335,343,452 cả guide/instrumental; appendix:1 cả hai variant; meditation `watv:vi:silent:19977`. Tổng 11 asset, không lấy ngẫu nhiên hoặc tải hàng loạt.
- Lượt xác nhận cuối: 2026-10-10T16:28:56.183830+00:00 → 2026-10-10T16:30:45.157118+00:00; ngày 2026-10-10, khoảng 23:28–23:30 Asia/Bangkok.
- FFmpeg/FFprobe: build `2026-07-20-git-c23123630e-essentials_build-www.gyan.dev`, đã có trên PATH.
- Bằng chứng cuối: `tmp/media-test/20261010T162856181711Z/`; [results.json](../tmp/media-test/20261010T162856181711Z/results.json). Mỗi asset có playlist gốc, `checked-input.m3u8` được dựng local từ segment/duration đã kiểm tra, HTTP status, source/segment/output FFprobe JSON, command/exit code/stdout/stderr, `result.json` và `output.m4a`.
- **11 asset duy nhất**, mỗi lượt có 11 output tổng **26.720.357 byte**. Lượt đầu `20261010T161959576264Z` và lượt xác nhận sau sửa guard đều được giữ lại: 22 file M4A trong cả hai run, tổng 53.440.714 byte; từng hash, byte size và số đo duration giống nhau giữa hai lượt. Có thêm các lần kiểm tra playlist/probe ban đầu của cùng main:1.
- Catalog SHA-256 trước/sau đều `e449b3a25ed49c6879bf06c72219863857632491f4a2ca424c2bc692e45ca8d4`. Không sửa catalog hoặc thêm transfer state.
- Kết quả offline cuối: **20/20 tests PASS**, gồm 11 test B3 và 9 test thử nghiệm. B3 validator vẫn PASS.

## Bảng từng sample

Thời lượng HLS/output tính bằng giây. Cột remux/integrity ghi trạng thái và exit code. Tất cả output có đúng một audio stream, file > 0 byte, duration > 0; full decode không ghi lỗi. HLS ở mỗi dòng gồm master một rendition → media VOD có ENDLIST, không key/encryption tag.

| Logical ID | Variant/type | Asset ID | Metadata duration | HLS duration (s) | Output duration (s) | Codec | Sample rate (Hz) | Channels/layout | Input/HLS structure | Remux | Output bytes | Integrity | Warning |
|---|---|---|---|---:|---:|---|---:|---|---|---|---:|---|---|
| watv:vi:newsong:main:1 | guide | watv:vi:guide:4177 | 00:02:06 | 125.016 | 125.016236 | AAC-LC | 44100 | 2/stereo | master→VOD; 13 AAC | PASS/0 | 2027172 | PASS/0 | — |
| watv:vi:newsong:main:1 | instrumental | watv:vi:instrumental:17407 | 00:02:04 | 125.251 | 125.248435 | AAC-LC | 44100 | 2/stereo | master→VOD; 13 AAC | PASS/0 | 2030903 | PASS/0 | — |
| watv:vi:newsong:main:335 | guide | watv:vi:guide:4144 | 00:03:07 | 185.228 | 185.225578 | AAC-LC | 44100 | 2/stereo | master→VOD; 19 AAC | PASS/0 | 3003093 | PASS/0 | — |
| watv:vi:newsong:main:335 | instrumental | watv:vi:instrumental:17741 | 00:03:25 | 185.594 | 185.573878 | AAC-LC | 44100 | 2/stereo | master→VOD; 19 AAC | PASS/0 | 3008705 | PASS/0 | Metadata lệch lớn |
| watv:vi:newsong:main:343 | guide | watv:vi:guide:4383 | 00:02:04 | 124.651 | 124.667937 | AAC-LC | 44100 | 2/stereo | master→VOD; 13 AAC | PASS/0 | 2021494 | PASS/0 | — |
| watv:vi:newsong:main:343 | instrumental | watv:vi:instrumental:17749 | 00:02:24 | 124.860 | 124.876916 | AAC-LC | 44100 | 2/stereo | master→VOD; 13 AAC | PASS/0 | 2024881 | PASS/0 | Metadata lệch lớn |
| watv:vi:newsong:main:452 | guide | watv:vi:guide:3995 | 00:03:35 | 214.277 | 214.296961 | AAC-LC | 44100 | 2/stereo | master→VOD; 22 AAC | PASS/0 | 3474279 | PASS/0 | — |
| watv:vi:newsong:main:452 | instrumental | watv:vi:instrumental:17858 | 00:03:24 | 214.695 | 214.714921 | AAC-LC | 44100 | 2/stereo | master→VOD; 22 AAC | PASS/0 | 3481054 | PASS/0 | Metadata lệch lớn |
| watv:vi:newsong:appendix:1 | guide | watv:vi:guide:25495 | 00:02:00 | 120.075 | 120.064000 | AAC-LC | 48000 | 2/stereo | master→VOD; 13 AAC | PASS/0 | 2904864 | PASS/0 | — |
| watv:vi:newsong:appendix:1 | instrumental | watv:vi:instrumental:25464 | 00:01:59 | 119.374 | 119.373787 | AAC-LC | 44100 | 2/stereo | master→VOD; 12 AAC | PASS/0 | 1931264 | PASS/0 | — |
| watv:vi:silent:19977 | silent | watv:vi:silent:19977 | 00:00:49 | 50.097 | 50.085442 | AAC-LC | 44100 | 2/stereo | master→VOD; 6 AAC | PASS/0 | 812648 | PASS/0 | — |

### SHA-256 output

| Asset ID | SHA-256 |
|---|---|
| watv:vi:guide:4177 | `ff9c2ad0d53e908a1f156561f15c16f00894b8b59f072324ee5aa53151d63393` |
| watv:vi:instrumental:17407 | `59bd741d28d3d1cdd4952ac6f3bd5e8d64588eb8252898ca897cab814dd7cbf3` |
| watv:vi:guide:4144 | `5f2219fa8c7dae6db95a9d64554722563bca997c00c88c76549261f141ce48be` |
| watv:vi:instrumental:17741 | `8b5c1183021623d77c3d4ea2e0a731d7765a93a6548c898de541859928b214fb` |
| watv:vi:guide:4383 | `75ab03aed01645d21647ba851721fb012a83ac1b672ae456164b669ce63e530a` |
| watv:vi:instrumental:17749 | `c05eadb6e18f0a4b7c98586a1fe3c13cff309bdca29c51bee10ce4f25e1c194b` |
| watv:vi:guide:3995 | `5d737351b292c1a777f2364169242fe560e6b52c76fbee7d44c62e7e211b9d9f` |
| watv:vi:instrumental:17858 | `ef506529843389b7ab94f3723e60f756b411e47c46e708888ba6cd0620a3c308` |
| watv:vi:guide:25495 | `90e4bacea859e22b0ec2d20d89f03f709c17ee40da0428351c4344f556fda5cf` |
| watv:vi:instrumental:25464 | `14f032f432538342decfd00ff722fa613dd841a2a6f898a4993a83eabd94eae8` |
| watv:vi:silent:19977 | `80f756f218d4c7fa0afbf9018cb6aee2cf705bb26a939d42e68237d42c0e7fe1` |

## Access

**11/11 master và 11/11 media playlist trả HTTP 200** qua request trực tiếp. FFprobe và FFmpeg đọc segment thành công trực tiếp cho cả 11 sample. Không cần cookie, browser session, Referer, Authorization hay token đăng nhập trong những phép thử này. Request dùng User-Agent mặc định của Python/FFmpeg, không giả lập browser; không lấy credential từ browser. URL playlist/segment được kiểm tra HTTPS, cùng host nguồn, không chứa credential hoặc query token.

Lần kiểm tra đầu tiên bị sandbox chặn socket trên máy (`WinError 10013`); sau khi chạy trong môi trường có quyền mạng, request thành công. Đây không phải phản hồi authentication từ WATV.

Kết luận chỉ áp dụng **11 URL tại thời điểm thử**; chưa kiểm tra khả dụng của toàn bộ 983 asset hoặc từ máy/vùng mạng khác.

## Media profile và playlist

- Root: master playlist HLS version 3, một rendition, CODECS `mp4a.40.2`.
- Child: media playlist VOD, EXTINF thường 10 giây, segment cuối ngắn hơn; có `EXT-X-ENDLIST`.
- Segment extension: `.aac`; FFprobe segment nhận `format_name=aac`. Kèm metadata ID3 transport timestamp Apple trong probe nguồn, phù hợp Packed Audio AAC/ADTS. Các sample này không phải MPEG-TS hoặc fMP4. Định nghĩa Packed Audio/ADTS và key tags: [RFC 8216, §3.4 và §4.3.2.4](https://www.rfc-editor.org/rfc/rfc8216.html).
- **Không thấy `EXT-X-KEY` hoặc `EXT-X-SESSION-KEY` trong cả 22 playlist**, không gặp encryption/DRM/access-control cần bypass.
- Codec tất cả: AAC-LC; codec_type audio; đúng một stream, 2 channels/stereo.
- 10 asset dùng 44.100 Hz. **Appendix:1 guide dùng 48.000 Hz**, instrumental dùng 44.100 Hz; giữ nguyên từng asset.
- Stream bit_rate do probe báo khoảng 133–136 kbit/s ở 10 asset; appendix:1 guide khoảng **196 kbit/s**. Đây là thông tin/ước lượng stream, không phải bitrate cố định nên ép cho toàn bộ. `format.bit_rate` của HLS có thể chỉ phản ánh file playlist cực nhỏ; không dùng nó làm bitrate audio.

## Remux và integrity

**11 PASS / 0 FAIL** với `-map 0:a:0 -c:a copy -movflags +faststart -f ipod` → `.m4a`. Không đặt bitrate/sample rate hoặc đổi codec, không tạo MP3. Mọi lệnh remux exit 0, stderr warning rỗng. Output FFprobe nhận container `mov,mp4,m4a,3gp,3g2,mj2`, AAC-LC, một audio stream; sample rate/channels được bảo toàn.

FFmpeg tự chèn AAC ADTS-to-ASC khi mux vào MOV/MP4/M4A; thao tác này đổi cách đóng gói, không mã hóa lại audio. Tham chiếu [FFmpeg streamcopy và aac_adtstoasc](https://ffmpeg.org/ffmpeg-all.html#aac_005fadtstoasc), [MOV/MP4 muxer và faststart](https://ffmpeg.org/ffmpeg-formats.html#mov_002c-mp4_002c-ismv).

Mỗi output được decode toàn bộ bằng `ffmpeg -v error -xerror ... -f null -`: exit 0, không có error-level diagnostic. Đây là kiểm tra máy đọc/giải mã hết file; chưa nghe thủ công hoặc thử phát trên từng browser/bot cụ thể.

## B5 — Duration

Quy ước delta: **output − metadata**, **output − HLS**. Metadata lấy nguyên từ catalog. Ở lượt cuối, FFprobe nguồn và FFmpeg remux dùng playlist media local được dựng tối thiểu từ đúng EXTINF và URL segment đã kiểm tra; segment vẫn được đọc trực tiếp qua HTTPS. HLS duration là FFprobe khai báo từ playlist này; output duration là container sau remux, đã decode toàn bộ. Lượt đầu probe trực tiếp URL master cho cùng toàn bộ 11 duration/hashes. Hai số đo HLS/output có thể khác nhỏ do EXTINF rounding/timestamp/audio-frame boundaries.

| Key | Variant/type | Output − metadata (s) | Output − HLS (s) | Source stream bit_rate (bit/s) |
|---|---|---:|---:|---:|
| main:1 | guide | -0.983764 | 0.000236 | 134339 |
| main:1 | instrumental | 1.248435 | -0.002565 | 133407 |
| main:335 | guide | -1.774422 | -0.002422 | 134794 |
| main:335 | instrumental | -19.426122 | -0.020122 | 134990 |
| main:343 | guide | 0.667937 | 0.016937 | 133361 |
| main:343 | instrumental | -19.123084 | 0.016916 | 133506 |
| main:452 | guide | -0.703039 | 0.019961 | 135031 |
| main:452 | instrumental | 10.714921 | 0.019921 | 134364 |
| appendix:1 | guide | 0.064000 | -0.011000 | 196213 |
| appendix:1 | instrumental | 0.373787 | -0.000213 | 135714 |
| watv:vi:silent:19977 | silent | 1.085442 | -0.011558 | 134438 |

Sai lệch tuyệt đối HLS/output lớn nhất **0.020122 giây** (khoảng 20 ms), nằm dưới một AAC frame ở 44,1 kHz. Ngưỡng integrity thử nghiệm là 0,5 giây; không dùng ngưỡng này để đánh giá metadata catalog. Metadata lệch từ −19,426122 đến +10,714921 giây trong sample.

### Các cặp bất thường

Dấu delta dưới đây là **guide − instrumental**:

| Key | Delta metadata (s) | Delta HLS (s) | Delta output (s) |
|---|---:|---:|---:|
| main:1 | 2 | -0.235000 | -0.232199 |
| main:335 | -18 | -0.366000 | -0.348300 |
| main:343 | -20 | -0.209000 | -0.208979 |
| main:452 | 11 | -0.418000 | -0.417960 |
| appendix:1 | 1 | 0.701000 | 0.690213 |

- **main:335:** instrumental metadata 205s nhưng output 185,573878s (−19,426122s). Hai output chỉ lệch khoảng 0,348s; chênh metadata −18s không tồn tại trong thời lượng media đo được.
- **main:343:** instrumental metadata 144s nhưng output 124,876916s (−19,123084s). Hai output lệch khoảng 0,209s; chênh metadata −20s không tồn tại trong thời lượng media đo được.
- **main:452:** instrumental metadata 204s nhưng output 214,714921s (+10,714921s). Hai output lệch khoảng 0,418s; chênh metadata +11s không tồn tại trong thời lượng media đo được.
- **main:1:** metadata guide dài hơn 2s, media guide ngắn hơn khoảng 0,232s.
- **Meditation:** metadata 49s, output 50,085442s. Metadata không phải số đo integrity đáng tin tuyệt đối.

Các quan sát xác định metadata hiện không khớp media hiện tại; chưa chứng minh nguyên nhân lịch sử là nhập sai metadata hay WATV đã thay media. Không sửa catalog. Duration đo thực cần được lưu ở evidence/artifact metadata của các bước sau.

## Default profile đề xuất cho B6 — chưa triển khai

```text
extension: .m4a
container: ISO BMFF / MP4 audio (FFmpeg ipod muxer)
audio codec: AAC nguồn; sample đã kiểm tra đều AAC-LC
strategy: copy
input: playlist media local dựng từ EXTINF và URL segment HTTPS đã kiểm tra
bitrate: giữ nguyên nguồn
sample rate: giữ nguyên nguồn, gồm 44100 và 48000 Hz
channels: giữ nguyên nguồn; sample hiện tại stereo
movflags: +faststart
```

Command template (chỉ áp dụng sau preflight xác nhận một AAC stream, HLS rõ nguồn và không mã hóa):

```powershell
ffmpeg -nostdin -hide_banner -v warning -xerror -rw_timeout 15000000 -protocol_whitelist file,https,tls,tcp -i "<CHECKED_MEDIA_PLAYLIST>.m3u8" -map 0:a:0 -map_metadata -1 -c:a copy -movflags +faststart -f ipod -n "<OUTPUT>.m4a"
```

Verification:

```powershell
ffprobe -v error -show_streams -show_format -of json "<OUTPUT>.m4a"
ffmpeg -nostdin -hide_banner -v error -xerror -i "<OUTPUT>.m4a" -map 0:a:0 -f null -
Get-FileHash -Algorithm SHA256 "<OUTPUT>.m4a"
```

Kiểm tra file > 0 byte, đúng một audio stream, AAC và sample rate/channels khớp nguồn, duration > 0 và HLS/output không lệch bất thường, decode exit 0 và không error diagnostic. [FFprobe documentation](https://ffmpeg.org/ffprobe.html) mô tả các trường probe và exit code. Nếu gặp codec khác, nhiều rendition/stream, key/encryption, fMP4/byterange/discontinuity hoặc access denial, dừng để review; không tự fallback transcode.

AAC-LC/M4A là profile phù hợp để đề xuất web/audio-player delivery; bot đích vẫn cần kiểm tra riêng endpoint nhận audio vì chưa chọn nền tảng bot. Không tuyên bố đã xác minh playback/voice-message trên một bot hoặc browser cụ thể.

Playlist input phải được kiểm tra và dựng local trước lệnh trên: chỉ giữ header VOD, EXTINF và URL segment HTTPS đã duyệt; không giữ key tag hoặc URI phụ. Không mở lại master/media playlist remote sau preflight. Đây là template đề xuất, chưa triển khai downloader B6.

## Rà soát cuối

Rà soát độc lập đối chiếu thành công toàn bộ hash/bytes, 55 exit code, error logs, 22 HTTP status và kết luận duration của lượt đầu. Hai vấn đề harness được sửa trong một lượt: tránh FFprobe/remux tự mở lại playlist remote có thể đã đổi sau kiểm tra; resolve relative URI theo URL cuối sau redirect. Hai kiểm thử hồi quy FAIL trước sửa, PASS sau sửa; suite cuối 20/20 PASS.

Đã chạy lại cùng 11 asset sau sửa: 11/11 PASS, hash/bytes/duration không đổi; kiểm tra argv xác nhận cả source probe và remux dùng `checked-input.m3u8`, không có crypto protocol. Không còn finding được hoãn lại. Chưa nghe thủ công, chưa test browser/bot hoặc production B6; các phần này không được suy ra từ full decode.

## Script, file tạo và lệnh chạy

- `scripts/test-media.py`: harness thử nghiệm tạm B4/B5; chỉ có `--list` hoặc chạy đúng 11 asset cố định, không có all/URL/catalog/sample selector. Không phải downloader production.
- `scripts/media_test_lib.py`: allowlist, giới hạn 11 asset, kiểm tra playlist/encryption, so sánh profile/duration.
- `tests/test_media.py`: 9 test offline, kiểm tra cả nonzero/timeout subprocess, CLI không có bulk mode, playlist local đã kiểm tra và redirect resolution.
- `docs/media-test-report.md`: báo cáo này.
- `docs/superpowers/plans/2026-10-10-media-b4-b5.md`: kế hoạch/nhật ký.
- `.gitignore`: thêm `tmp/media-test/`.
- `tmp/media-test/20261010T162856181711Z/`: output/evidence cuối; giữ cả run đầu để đối chứng, đều là dữ liệu thử nghiệm tạm và không phải delivery manifest production.

```powershell
# Chỉ liệt kê, không gọi mạng:
.\.venv\Scripts\python.exe scripts/test-media.py --list
# Kiểm tra offline:
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/validate-catalog.py
# Chạy lại sẽ tải lại đúng 11 sample vào thư mục run mới:
.\.venv\Scripts\python.exe scripts/test-media.py
```

Đã hoàn thành B4/B5 sample test. **Chưa bắt đầu B6**, không upload/cấu hình R2, không tạo manifest production, không sửa catalog/API/web/bot.

