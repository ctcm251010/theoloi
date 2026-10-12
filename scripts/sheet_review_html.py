"""Static offline review proposal UI; no server, credentials or document assets."""
import json
import secrets
from catalog_lib import ROOT


def render_review_html(queue):
    nonce=secrets.token_hex(16)
    data=json.dumps(queue,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    script=(ROOT/'scripts/sheet-review-ui.js').read_text(encoding='utf-8')
    return f'''<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'nonce-{nonce}'; style-src 'nonce-{nonce}'; base-uri 'none'; form-action 'none'; connect-src 'none'">
<title>AudioTP — Mapping Review local</title>
<style nonce="{nonce}">
*{{box-sizing:border-box}}body{{margin:0;background:#f4f6f9;color:#18253b;font:16px/1.5 system-ui, sans-serif}}
header,main{{max-width:1100px;margin:auto;padding:24px}}header{{padding-bottom:8px}}h1{{font-size:28px;margin:0 0 10px}}
.notice{{border-left:4px solid #3064a8;padding:12px;background:#e9f0fa}}.toolbar{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:18px 0}}
label{{display:block;font-weight:600}}input,select,textarea,button{{font:inherit;border:1px solid #b1bed0;border-radius:6px;padding:9px;background:white;color:inherit}}
input:not([type=checkbox]),select,textarea{{width:100%}}textarea{{min-height:72px}}button{{cursor:pointer;background:#245ba7;color:white}}button:disabled{{opacity:.5;cursor:default}}
article{{background:white;padding:20px;border:1px solid #d8e0ea;border-radius:10px;margin:16px 0}}h2{{font-size:20px;margin:6px 0}}.small{{font-size:13px;color:#4c5b70;overflow-wrap:anywhere}}.tag{{font-size:13px;font-weight:700;color:#744012;background:#fff0d5;padding:4px 8px;border-radius:4px}}
.choices{{display:grid;grid-template-columns:1fr 2fr;gap:14px;margin:14px 0}}.check{{display:flex;gap:10px;align-items:center;margin-top:12px}}.actions{{display:flex;gap:12px;align-items:center;flex-wrap:wrap}}#error{{color:#a51c30;font-weight:600}}a{{color:#245ba7}}@media(max-width:650px){{.toolbar,.choices{{grid-template-columns:1fr}}header,main{{padding:16px}}}}
</style></head><body>
<header><h1>AudioTP · Mapping Review</h1>
<p class="notice">Chỉ review định danh tác phẩm. Không tải tài liệu và không cấp quyền sử dụng. Trang này chỉ chuẩn bị batch; CLI mới lưu quyết định sau dry-run và xác nhận số mục.</p>
<div class="toolbar"><label>Người review<input id="reviewer" autocomplete="off" placeholder="Tên người thực sự kiểm tra"></label>
<label>Provenance / tham chiếu kiểm tra<input id="provenance" autocomplete="off" placeholder="Ghi nguồn bằng chứng, ngày/biên bản kiểm tra"></label>
<label>Tìm số, tên hoặc source ID<input id="search" type="search" placeholder="464, title, post ID..."></label>
<label>Phạm vi<select id="scope"><option value="priority">Ưu tiên: bài 464 + 5 cặp phụ lục</option><option value="all">Toàn bộ nguồn</option><option value="unmatched">Chưa có ứng viên</option></select></label></div>
<div class="actions"><button id="download">Xuất batch đã chọn (tối đa 50)</button><span id="selected"></span></div><p id="error" role="alert"></p>
</header><main><p id="summary"></p><div class="actions"><button id="previous">Trang trước</button><button id="next">Trang sau</button><span id="page"></span></div><div id="rows"></div></main>
<datalist id="audio-options"></datalist>
<script id="queue-data" type="application/json" nonce="{nonce}">{data}</script>
<script nonce="{nonce}">{script}</script></body></html>
'''
