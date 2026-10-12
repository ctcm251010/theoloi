"""Production preflight: bounded clear VOD playlists, direct HTTPS, no credentials."""
import math
from pathlib import PurePosixPath
from urllib.parse import urljoin, urlsplit
import urllib.error
import urllib.request


class MediaFailure(Exception):
    def __init__(self, message, kind="integrity"):
        super().__init__(message)
        self.kind = kind


class RateLimited(MediaFailure):
    def __init__(self, message):
        super().__init__(message, "transient")


def checked_url(reference, base=""):
    url = urljoin(base, reference)
    try:
        p = urlsplit(url)
        valid = (p.scheme == "https" and p.hostname == "vod.watv.org" and p.port in (None, 443)
                 and not (p.username or p.password or p.query or p.fragment)
                 and not any(c.isspace() for c in url)
                 and p.path.startswith("/watv_media_newsong/_definst_/mp4:WATV_NEWSONG/"))
    except ValueError:
        valid = False
    if not valid:
        raise MediaFailure("Invalid/cross-origin/token-bearing HLS URL; no bypass", "access")
    return url


def inspect(text, url):
    lines = [s.strip() for s in text.splitlines() if s.strip()]
    if not lines or lines[0] != "#EXTM3U":
        raise MediaFailure("Expected HLS, possibly access/login response", "access")
    if len(lines) > 5000:
        raise MediaFailure("Oversized playlist requires review", "structure")
    if any(s.startswith(("#EXT-X-KEY", "#EXT-X-SESSION-KEY")) for s in lines):
        raise MediaFailure("Key/encryption tag found; no key requested", "encryption")
    unsupported = ("#EXT-X-MEDIA:", "#EXT-X-MAP:", "#EXT-X-BYTERANGE:", "#EXT-X-DISCONTINUITY",
                   "#EXT-X-GAP", "#EXT-X-PART:", "#EXT-X-SKIP:", "#EXT-X-I-FRAMES-ONLY")
    if any(s.startswith(unsupported) for s in lines):
        raise MediaFailure("Unsupported HLS structure needs review", "structure")
    urls = [checked_url(s, url) for s in lines if not s.startswith("#")]
    if any(s.startswith("#EXT-X-STREAM-INF:") for s in lines):
        if len(urls) != 1:
            raise MediaFailure("Expected exactly one master rendition", "structure")
        return {"type": "master", "children": urls}
    try:
        durations = [float(s.split(":", 1)[1].split(",", 1)[0]) for s in lines if s.startswith("#EXTINF:")]
    except ValueError as exc:
        raise MediaFailure("Malformed EXTINF duration", "structure") from exc
    if (not urls or len(urls) != len(durations) or "#EXT-X-ENDLIST" not in lines
            or any(not math.isfinite(n) or n <= 0 for n in durations) or sum(durations) > 3600):
        raise MediaFailure("Malformed/live/over-one-hour VOD requires review", "structure")
    if any(PurePosixPath(urlsplit(u).path).suffix != ".aac" for u in urls):
        raise MediaFailure("Segment format changed from tested AAC; review required", "structure")
    return {"type": "media", "segments": urls, "durations": durations, "duration": sum(durations)}


class DirectRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        checked_url(newurl, req.full_url)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url):
    checked_url(url)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), DirectRedirect())
    try:
        with opener.open(url, timeout=20) as response:
            final = checked_url(response.geturl())
            data = response.read(1048577)
            if len(data) > 1048576:
                raise MediaFailure("Playlist exceeds 1 MiB", "structure")
            return inspect(data.decode("utf-8-sig"), final)
    except urllib.error.HTTPError as exc:
        if exc.code in (429, 503):
            raise RateLimited(f"HTTP {exc.code}; controlled stop, no immediate retry") from exc
        kind = "transient" if 500 <= exc.code < 600 else "access"
        raise MediaFailure(f"HTTP {exc.code}; direct request without cookies/auth", kind) from exc
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        raise MediaFailure(f"Direct network read failed: {exc}", "transient") from exc
    except UnicodeError as exc:
        raise MediaFailure("Playlist is not UTF-8 HLS", "structure") from exc


def preflight(url, output):
    media = fetch(url)
    if media["type"] == "master":
        media = fetch(media["children"][0])
    if media["type"] != "media":
        raise MediaFailure("Nested master exceeds traversal limit", "structure")
    lines = ["#EXTM3U", "#EXT-X-VERSION:3", f"#EXT-X-TARGETDURATION:{math.ceil(max(media['durations']))}",
             "#EXT-X-MEDIA-SEQUENCE:0"]
    for duration, segment in zip(media["durations"], media["segments"], strict=True):
        lines.extend([f"#EXTINF:{duration:.6f},", segment])
    output.write_bytes(("\n".join(lines + ["#EXT-X-ENDLIST", ""])).encode("utf-8"))
    return media
