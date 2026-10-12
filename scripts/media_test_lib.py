"""B4/B5 temporary experiment helpers; intentionally fixed to eleven assets."""
import math
from pathlib import PurePosixPath
import re
from urllib.parse import urljoin, urlsplit

from catalog_lib import CATALOG, load_json

SONGS = ("main:1", "main:335", "main:343", "main:452", "appendix:1")
SILENT = "watv:vi:silent:19977"
MAX_SAMPLES = 11
MAX_DURATION = 600
DURATION_TOLERANCE = 0.5


class AccessStop(ValueError):
    """An access/encryption condition requiring the experiment to stop."""


def safe_url(reference, base):
    url = urljoin(base, reference)
    p = urlsplit(url)
    if (p.scheme != "https" or p.hostname != "vod.watv.org" or p.port not in (None, 443)
            or p.username or p.password or p.query or p.fragment
            or any(c.isspace() for c in url)
            or not p.path.startswith("/watv_media_newsong/_definst_/mp4:WATV_NEWSONG/")):
        raise AccessStop("Unsafe, cross-origin or token-bearing playlist reference; no bypass attempted")
    return url


def select_samples(catalog):
    rows = []
    try:
        for key in SONGS:
            song = catalog["songs"][key]
            for kind in ("guide", "instrumental"):
                rows.append({"key": key, "logicalId": song["id"], "kind": kind, "asset": song["variants"][kind]})
        meditation = catalog["meditations"][SILENT]
        rows.append({"key": SILENT, "logicalId": meditation["id"], "kind": "silent", "asset": meditation["asset"]})
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Required sample missing/malformed: {exc}") from exc
    if len(rows) != MAX_SAMPLES or len({r["asset"]["assetId"] for r in rows}) != MAX_SAMPLES:
        raise ValueError("Fixed sample cap/uniqueness violated")
    for row in rows:
        safe_url(row["asset"]["source"]["hlsUrl"], "")
    return rows


def inspect_playlist(text, url):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines or lines[0] != "#EXTM3U":
        raise ValueError("Not an HLS playlist (possible HTML/access response)")
    if len(lines) > 5000:
        raise ValueError("Playlist exceeds sample limits")
    for line in lines:
        if line.startswith(("#EXT-X-KEY:", "#EXT-X-SESSION-KEY:")):
            attrs = dict(re.findall(r'([A-Z0-9-]+)=("[^"]*"|[^,]*)', line.split(":", 1)[1]))
            if attrs.get("METHOD") != "NONE":
                raise AccessStop("Encryption/key tag found; no key requested or media decoded")
    references = [safe_url(line, url) for line in lines if not line.startswith("#")]
    if any(line.startswith("#EXT-X-MEDIA:") for line in lines):
        raise AccessStop("Alternate rendition requires separate review; no automatic selection")
    master = any(line.startswith("#EXT-X-STREAM-INF:") for line in lines)
    if master:
        if not references or len(references) > 3:
            raise ValueError("Master playlist has unsupported rendition count")
        return {"type": "master", "children": references, "encrypted": False}
    durations = [float(line.split(":", 1)[1].split(",", 1)[0]) for line in lines if line.startswith("#EXTINF:")]
    if (not references or len(durations) != len(references) or "#EXT-X-ENDLIST" not in lines
            or any(not math.isfinite(n) or n <= 0 for n in durations)
            or sum(durations) > MAX_DURATION):
        raise ValueError("Malformed, live or oversized media playlist")
    if any(line.startswith(("#EXT-X-MAP:", "#EXT-X-BYTERANGE:", "#EXT-X-DISCONTINUITY")) for line in lines):
        raise ValueError("fMP4/byterange/discontinuity sample requires manual investigation")
    return {"type": "media", "segments": references, "segmentCount": len(references),
            "segmentExtensions": sorted({PurePosixPath(urlsplit(s).path).suffix for s in references}),
            "segmentDurations": durations, "duration": sum(durations), "encrypted": False, "endlist": True}


def pinned_playlist(media):
    """Build an inert VOD manifest from checked durations and absolute URLs only.

    FFmpeg cannot refetch a changed master/media manifest or discover key tags.
    Segment bytes are still fetched from the direct public HTTPS URLs.
    """
    lines = ["#EXTM3U", "#EXT-X-VERSION:3",
             f"#EXT-X-TARGETDURATION:{math.ceil(max(media['segmentDurations']))}", "#EXT-X-MEDIA-SEQUENCE:0"]
    for duration, url in zip(media["segmentDurations"], media["segments"], strict=True):
        lines.extend([f"#EXTINF:{duration:.6f},", safe_url(url, "")])
    return "\n".join(lines + ["#EXT-X-ENDLIST", ""])


def measured_duration(probe):
    try:
        value = float(probe["format"]["duration"])
    except (KeyError, TypeError, ValueError):
        return None
    return value if math.isfinite(value) and value > 0 else None


def validate_output(source, output):
    errors = []
    src, dst = source.get("streams", []), output.get("streams", [])
    if len(src) != 1 or len(dst) != 1 or any(s.get("codec_type") != "audio" for s in src + dst):
        return ["Expected exactly one audio stream in source and output"]
    if src[0].get("codec_name") != "aac" or dst[0].get("codec_name") != "aac":
        errors.append("This sample profile requires AAC; no automatic transcode")
    for field in ("codec_name", "sample_rate", "channels"):
        if src[0].get(field) is None or src[0].get(field) != dst[0].get(field):
            errors.append(f"Source/output {field} mismatch")
    a, b = measured_duration(source), measured_duration(output)
    if a is None or b is None or abs(a - b) > DURATION_TOLERANCE:
        errors.append(f"Invalid duration or source/output difference > {DURATION_TOLERANCE}s")
    return errors
