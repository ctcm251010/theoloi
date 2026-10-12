#!/usr/bin/env python3
"""AudioTP local R2 preview: no uploads, private bucket, temporary signed GET URLs.

Place this file in D:\\Workspace\\AudioTP\\scripts\\audiotp_r2_preview.py
Run from project root: .\\.venv\\Scripts\\python.exe scripts/audiotp_r2_preview.py
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

try:
    import boto3
except ImportError as exc:
    raise SystemExit("Thieu boto3: chay .\\.venv\\Scripts\\python.exe -m pip install boto3") from exc

HOST = "127.0.0.1"  # Local-only, not accessible from outside this PC
PORT = 8765
URL_TTL = 3600  # 1 hour. A fresh URL is issued on every Play.
AUDIO_EXTS = (".mp3", ".m4a", ".mp4", ".aac", ".wav", ".ogg", ".flac")
MEDITATION_TAGS = {"silent", "meditation", "meditations", "reflect", "reflection"}

HTML = r'''<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="referrer" content="no-referrer">
  <title>AudioTP • Nghe thử từ R2</title>
  <style>
    :root {color-scheme:dark; font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif;
      --bg:#0b1220; --panel:#131f32; --stroke:#2c3b51; --muted:#a5b5c9;
      --text:#f2f6fb; --mint:#6fe7c8; --shade:#172a3c; }
    * {box-sizing:border-box}
    body {margin:0; min-height:100vh; background: radial-gradient(ellipse at top left,#193850 0%,var(--bg) 55%);color:var(--text)}
    .wrap {max-width:820px;margin:0 auto;padding:48px 20px 64px}
    .tag {display:inline-block;border:1px solid #37635e;border-radius:999px;background:#173b37;color:#a9f4dc;
      padding:7px 12px;font-size:12px;font-weight:750;letter-spacing:.06em}
    h1 {font-size:clamp(30px,5vw,47px);line-height:1.08;letter-spacing:-.04em;margin:19px 0 12px}
    .lead {color:var(--muted);margin:0 0 28px;line-height:1.6}
    .panel {background:rgba(19,31,50,.97);border:1px solid var(--stroke);border-radius:22px;
      padding:25px;box-shadow:0 20px 75px #0003}
    label {display:block;font-size:13px;font-weight:750;letter-spacing:.01em;margin:0 0 9px}
    input,select {width:100%;border:1px solid #42536b;border-radius:12px;background:#0b1727;color:var(--text);
      font-size:15px;padding:14px;outline:none;min-height:48px}
    input:focus,select:focus {border-color:var(--mint);box-shadow:0 0 0 3px #6fe7c822}
    select {margin:0 0 16px}
    .rows {display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:20px}
    .muted {font-size:12px;color:var(--muted);line-height:1.5;margin-top:-7px}
    .line {border-top:1px solid var(--stroke);margin:24px 0}
    .actionTitle {font-size:14px;color:var(--muted);margin:0 0 13px}
    .actions {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
    button {appearance:none;border:1px solid #4e6880;background:#21344c;color:var(--text);
      border-radius:15px;font:inherit;padding:15px 8px;min-height:70px;cursor:pointer;transition:.15s ease;
      font-size:14px;font-weight:700}
    button:hover:not(:disabled) {transform:translateY(-2px);border-color:var(--mint);background:#29425b}
    button:disabled {cursor:not-allowed;opacity:.35}
    button .emoji {display:block;font-size:22px;margin:0 0 5px}
    button.active {background:#16443e;border-color:var(--mint);color:#c9fff0}
    .playing {margin-top:24px;border:1px solid #335267;border-radius:16px;padding:18px;background:#10263a}
    .playingLabel {font-size:11px;text-transform:uppercase;letter-spacing:.11em;color:var(--mint);font-weight:800}
    #current {margin:8px 0 14px;font-weight:750;min-height:22px}
    audio {display:block;width:100%;height:44px}
    #status {margin-top:16px;color:#bbd0e5;font-size:13px;line-height:1.5;min-height:20px}
    .footer {color:#90a8bd;font-size:12px;line-height:1.6;margin-top:16px}
    @media (max-width:610px){.wrap{padding:28px 14px}.panel{padding:18px}.rows{grid-template-columns:1fr;gap:6px}
      .actions{gap:7px}button{padding:12px 3px;font-size:12px}button .emoji{font-size:20px}}
  </style>
</head>
<body><main class="wrap">
  <span class="tag">● AUDIO TP · R2 PRIVATE PREVIEW</span>
  <h1>Nghe thử âm thanh</h1>
  <p class="lead">Chọn bài hát, sau đó chọn bản muốn nghe. Phát trực tiếp từ kho Cloudflare R2 đã upload.</p>
  <section class="panel">
    <label for="search">Tìm bài theo số hoặc phân loại</label>
    <input id="search" autocomplete="off" placeholder="Ví dụ: 0001, main, appendix…">
    <div class="rows">
      <div>
        <label for="songs">Chọn bài hát</label>
        <select id="songs"><option>Đang tải danh sách…</option></select>
        <div class="muted" id="songsInfo">—</div>
      </div>
      <div>
        <label for="meditations">Chọn nhạc ngẫm nghĩ</label>
        <select id="meditations"><option>Đang tải danh sách…</option></select>
        <div class="muted" id="meditationsInfo">Bản ngẫm nghĩ có danh sách riêng.</div>
      </div>
    </div>
    <div class="line"></div>
    <p class="actionTitle">Chọn một phiên bản để phát</p>
    <div class="actions">
      <button id="guide" type="button" disabled><span class="emoji">📖</span>Hướng dẫn</button>
      <button id="instrumental" type="button" disabled><span class="emoji">🎼</span>Nhạc đệm</button>
      <button id="meditation" type="button" disabled><span class="emoji">🌙</span>Ngẫm nghĩ</button>
    </div>
    <section class="playing" aria-label="Trình phát">
      <div class="playingLabel">Đang phát</div>
      <div id="current">Chưa chọn bài</div>
      <audio id="player" controls preload="none"></audio>
    </section>
    <div id="status" role="status">Đang kết nối R2…</div>
  </section>
  <p class="footer">Chỉ mở trên máy này (127.0.0.1). Mỗi lượt phát tạo một link đọc tạm thời 1 giờ.
    Không chỉnh sửa hoặc upload file trên R2. Nếu file hết hạn khi đang nghe, bấm lại nút tương ứng.</p>
</main>
<script>
  'use strict';
  const byId = id => document.getElementById(id);
  const songsEl=byId('songs'), medEl=byId('meditations'), searchEl=byId('search');
  const player=byId('player'), status=byId('status'), current=byId('current');
  let songs=[], meditations=[], busy=false;
  const modes=['guide','instrumental','meditation'];
  function setStatus(message,error=false){status.textContent=message;status.style.color=error?'#ffaaa7':'#bbd0e5'}
  function fill(el,items,emptyLabel){
    const previous=el.value;el.replaceChildren();
    if(!items.length){const opt=new Option(emptyLabel,'');el.add(opt);return}
    for(const item of items){el.add(new Option(item.label,item.id))}
    if(items.some(item=>item.id===previous)) el.value=previous;
  }
  function selectedSong(){return songs.find(s=>s.id===songsEl.value)}
  function selectedMeditation(){return meditations.find(m=>m.id===medEl.value)}
  function updateButtons(){
    const song=selectedSong(), med=selectedMeditation();
    byId('guide').disabled=busy||!(song&&song.variants.guide);
    byId('instrumental').disabled=busy||!(song&&song.variants.instrumental);
    byId('meditation').disabled=busy||!((song&&song.variants.meditation)||med);
  }
  function filterSongs(){
    const q=searchEl.value.trim().toLocaleLowerCase('vi');
    const filtered=songs.filter(s=>s.label.toLocaleLowerCase('vi').includes(q));
    fill(songsEl,filtered,'Không tìm thấy bài phù hợp');
    byId('songsInfo').textContent=`Hiển thị ${filtered.length} / ${songs.length} bài`;
    updateButtons();
  }
  async function play(mode){
    const song=selectedSong(), med=selectedMeditation();
    let key, label;
    if(mode==='meditation'){
      if(song&&song.variants.meditation){key=song.variants.meditation;label=`${song.label} · Ngẫm nghĩ`}
      else if(med){key=med.key;label=`${med.label} · Ngẫm nghĩ`}
    } else if(song){key=song.variants[mode];label=`${song.label} · ${mode==='guide'?'Hướng dẫn':'Nhạc đệm'}`}
    if(!key)return setStatus('Chưa có file tương ứng cho lựa chọn này.',true);
    busy=true;updateButtons();setStatus('Đang lấy link phát âm thanh…');
    try{
      const response=await fetch('/api/play?key='+encodeURIComponent(key),{cache:'no-store'});
      const result=await response.json();
      if(!response.ok)throw new Error(result.error||'Không lấy được link phát');
      player.pause();player.src=result.url;player.load();current.textContent=label;
      for(const m of modes)byId(m).classList.toggle('active',m===mode);
      try{await player.play();setStatus('Đang phát trực tiếp từ Cloudflare R2.')}
      catch(e){setStatus('Link đã tạo. Nhấn nút ▶ trên thanh phát để bắt đầu.')} 
    }catch(e){setStatus('Lỗi: '+e.message,true)}
    finally{busy=false;updateButtons()}
  }
  for(const mode of modes)byId(mode).addEventListener('click',()=>play(mode));
  songsEl.addEventListener('change',updateButtons);
  medEl.addEventListener('change',updateButtons);
  searchEl.addEventListener('input',filterSongs);
  player.addEventListener('error',()=>setStatus('Không phát được file. Kiểm tra định dạng, quyền R2 và hạn link; thử bấm lại.',true));
  async function init(){
    try{
      const response=await fetch('/api/library',{cache:'no-store'});
      const data=await response.json();
      if(!response.ok)throw new Error(data.error||'Không thể tải danh sách');
      songs=data.songs;meditations=data.meditations;
      fill(medEl,meditations,'Không có bản ngẫm nghĩ');filterSongs();
      byId('meditationsInfo').textContent=`Có ${meditations.length} bản ngẫm nghĩ`;
      setStatus(`Đã kết nối R2: ${data.asset_count} file âm thanh, ${songs.length} bài hát, ${meditations.length} bản ngẫm nghĩ.`)
    }catch(e){songsEl.replaceChildren(new Option('Lỗi kết nối',''));
      medEl.replaceChildren(new Option('Lỗi kết nối',''));setStatus('Lỗi kết nối: '+e.message,true)}
  }
  init();
</script></body></html>'''


def project_root() -> Path:
    choices = [Path.cwd(), Path(__file__).resolve().parent, Path(__file__).resolve().parent.parent]
    for folder in choices:
        if (folder / ".secrets" / "r2.env").is_file():
            return folder
    raise FileNotFoundError("Khong thay .secrets/r2.env. Hay luu file vao thu muc scripts cua AudioTP.")


def read_config(root: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in (root / ".secrets" / "r2.env").read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        name, sep, value = stripped.partition("=")
        if sep:
            entries[name.strip()] = value.strip().strip('"').strip("'")
    needed = ("R2_ENDPOINT", "R2_BUCKET", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY")
    if not all(entries.get(k) for k in needed):
        raise ValueError("File r2.env thieu truong bat buoc; khong in secret.")
    return entries


def song_label(prefix: list[str]) -> str:
    if "newsong" in prefix:
        pos = prefix.index("newsong")
        tail = prefix[pos+1:]
        if len(tail) >= 2:
            section, number = tail[0], tail[1]
            section_name = {"main":"Bài", "appendix":"Phụ lục"}.get(section, section)
            return f"{section_name} {number}"
    return " / ".join(prefix[-3:])


def build_library(keys: list[str]) -> dict:
    """Group genuine R2 keys; don't infer associations that aren't in the paths."""
    by_song: dict[str, dict] = {}
    med: dict[str, dict] = {}
    playable = 0
    for key in keys:
        if not key.lower().endswith(AUDIO_EXTS):
            continue
        parts = key.strip("/").split("/")
        lower = [p.lower() for p in parts]
        variant_at = next((i for i, p in enumerate(lower[:-1]) if p in {"guide", "instrumental"}), None)
        if variant_at is not None:
            # e.g. audio/v1/watv/vi/newsong/main/0001/guide/25495/<hash>.m4a
            variant = lower[variant_at]
            prefix = parts[:variant_at]
            group_id = "/".join(prefix)
            if group_id not in by_song:
                by_song[group_id] = {"id": group_id, "label": song_label(prefix), "variants": {}}
            by_song[group_id]["variants"].setdefault(variant, key)
            playable += 1
            continue
        med_at = next((i for i,p in enumerate(lower[:-1]) if p in MEDITATION_TAGS), None)
        if med_at is not None:
            # Only map to a song if the key itself names a song (not the standalone silent collection).
            if "newsong" in lower and med_at > lower.index("newsong") + 2:
                prefix=parts[:med_at]
                group_id="/".join(prefix)
                if group_id not in by_song:
                    by_song[group_id] = {"id":group_id,"label":song_label(prefix),"variants":{}}
                by_song[group_id]["variants"].setdefault("meditation", key)
            else:
                identifier = parts[med_at + 1] if med_at + 1 < len(parts) - 1 else parts[-1]
                group_id = "/".join(parts[:med_at+2])
                med.setdefault(group_id, {"id":group_id,"label":f"Ngẫm nghĩ {identifier}","key":key})
            playable += 1
    songs = sorted(by_song.values(), key=lambda s: (
        0 if "/main/" in s["id"] else 1 if "/appendix/" in s["id"] else 2,
        s["label"].casefold(), s["id"]
    ))
    meditations = sorted(med.values(), key=lambda m: m["label"].casefold())
    whitelist = {key for s in songs for key in s["variants"].values()}
    whitelist.update(m["key"] for m in meditations)
    return {"songs":songs,"meditations":meditations,"asset_count":playable, "allowed_keys":whitelist}


def make_handler(s3, bucket: str, catalog: dict):
    allowed = catalog["allowed_keys"]
    public = {k:v for k,v in catalog.items() if k!="allowed_keys"}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            # URLs contain private signatures. Avoid logging any request path/query.
            return

        def send_bytes(self, code: int, body: bytes, content_type: str):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, code: int, obj: dict):
            self.send_bytes(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"),"application/json; charset=utf-8")

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/":
                return self.send_bytes(200, HTML.encode("utf-8"), "text/html; charset=utf-8")
            if parsed.path == "/api/library":
                return self.send_json(200, public)
            if parsed.path == "/api/play":
                raw_key = parse_qs(parsed.query).get("key",[""])[0]
                if raw_key not in allowed:
                    return self.send_json(404,{"error":"Khong tim thay file trong danh sach cho phep"})
                try:
                    url = s3.generate_presigned_url("get_object", Params={"Bucket":bucket,"Key":raw_key}, ExpiresIn=URL_TTL)
                    return self.send_json(200,{"url":url})
                except Exception:
                    return self.send_json(500,{"error":"Khong tao duoc URL nghe thu"})
            if parsed.path == "/favicon.ico":
                return self.send_bytes(200,b"","image/x-icon")
            return self.send_json(404,{"error":"Not found"})
    return Handler


def main():
    config = read_config(project_root())
    s3 = boto3.client(
        "s3", endpoint_url=config["R2_ENDPOINT"],
        aws_access_key_id=config["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=config["R2_SECRET_ACCESS_KEY"], region_name="auto"
    )
    print("Dang lay danh sach file tu bucket R2 (chi doc)...", flush=True)
    keys = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=config["R2_BUCKET"]):
        keys.extend(item["Key"] for item in page.get("Contents", []))
    catalog = build_library(keys)
    if not catalog["allowed_keys"]:
        raise SystemExit("Khong tim thay file am thanh. Kiem tra bucket va ten object key.")
    print(f"Tim thay {len(keys)} objects; nhan dien {len(catalog['songs'])} bai, "
          f"{len(catalog['meditations'])} ban ngam nghi, {catalog['asset_count']} file am thanh.", flush=True)
    print(f"MO TRONG TRINH DUYET: http://{HOST}:{PORT}", flush=True)
    print("Nhan Ctrl+C de dung. Chi chay tren may ban; R2 van Private.", flush=True)
    server = ThreadingHTTPServer((HOST, PORT), make_handler(s3,config["R2_BUCKET"],catalog))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDa dung preview.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
