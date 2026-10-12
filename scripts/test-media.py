"""Temporary B4/B5 experiment: exactly eleven allowlisted assets, never B6.

No URL/selector/all-assets flags. Run again only when repeating this sample is intended.
All network requests are direct, without browser cookies or authentication headers.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

from catalog_lib import CATALOG, ROOT, json_text, load_json
from media_test_lib import AccessStop, inspect_playlist, measured_duration, pinned_playlist, safe_url, select_samples, validate_output

BASELINE_HASH = "e449b3a25ed49c6879bf06c72219863857632491f4a2ca424c2bc692e45ca8d4"
NETWORK_OPTIONS = ["-rw_timeout", "15000000", "-protocol_whitelist", "file,https,tls,tcp"]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_bytes(json_text(value).encode("utf-8"))


def command(folder, stage, argv, timeout=90):
    evidence = {"argv": argv, "timeoutSeconds": timeout}
    env = os.environ.copy()
    for key in list(env):
        if key.lower() in ("http_proxy", "https_proxy", "all_proxy", "no_proxy"):
            del env[key]
    try:
        result = subprocess.run(argv, capture_output=True, encoding="utf-8", errors="replace",
                                timeout=timeout, env=env)
        evidence.update(exitCode=result.returncode)
        stdout, stderr = result.stdout, result.stderr
    except subprocess.TimeoutExpired as exc:
        evidence.update(exitCode=None, timedOut=True)
        stdout, stderr = exc.stdout or b"", exc.stderr or b""
        stdout = stdout.decode("utf-8", "replace") if isinstance(stdout, bytes) else stdout
        stderr = stderr.decode("utf-8", "replace") if isinstance(stderr, bytes) else stderr
    (folder / f"{stage}.stdout.txt").write_bytes(stdout.encode("utf-8"))
    (folder / f"{stage}.stderr.txt").write_bytes(stderr.encode("utf-8"))
    write_json(folder / f"{stage}.command.json", evidence)
    if evidence["exitCode"] != 0:
        raise ValueError(f"{stage} failed/timeout, see retained command/log evidence")
    return stdout, stderr


class DirectOnly(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        safe_url(newurl, req.full_url)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def read_playlist(url, folder, name):
    safe_url(url, "")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), DirectOnly())
    access = {"url": url, "cookies": False, "customAuthHeaders": False, "proxy": False}
    try:
        with opener.open(url, timeout=15) as response:
            access.update(httpStatus=response.status, contentType=response.headers.get("Content-Type"),
                          finalUrl=response.geturl())
            body = response.read(1048577)
        if len(body) > 1048576:
            raise ValueError("Playlist exceeds 1 MiB cap")
        text = body.decode("utf-8-sig")
        (folder / f"{name}.m3u8").write_bytes(body)
        return inspect_playlist(text, access["finalUrl"]), access
    except urllib.error.HTTPError as exc:
        access.update(httpStatus=exc.code, error="HTTP access failed; no browser credentials used")
        raise ValueError(f"HTTP {exc.code}; no auth retry/bypass") from exc
    except (urllib.error.URLError, OSError) as exc:
        access.update(error=str(exc))
        raise ValueError(f"Direct network access failed: {exc}") from exc
    finally:
        write_json(folder / f"{name}.access.json", access)


def playlist_tree(url, folder):
    root, root_access = read_playlist(url, folder, "master")
    evidence = {"root": root, "rootAccess": root_access}
    if root["type"] == "master":
        # This experiment only handles one rendition. Do not silently choose a
        # lower-quality rendition or omit encryption on another variant.
        if len(root["children"]) != 1:
            raise ValueError("Multiple master variants require review; no automatic choice")
        media, access = read_playlist(root["children"][0], folder, "media")
        evidence["mediaAccess"] = access
    else:
        media = root
    if media["type"] != "media":
        raise ValueError("Nested master playlist exceeds sample traversal limit")
    evidence["media"] = media
    write_json(folder / "playlist-structure.json", evidence)
    return evidence


def ffprobe(folder, stage, url, remote):
    args = ["ffprobe", "-v", "error"] + (NETWORK_OPTIONS if remote else [])
    stdout, stderr = command(folder, stage, args + ["-show_streams", "-show_format", "-of", "json", str(url)])
    if stderr.strip():
        raise ValueError(f"{stage}: error-level FFprobe diagnostic, see stderr")
    result = json.loads(stdout)
    write_json(folder / f"{stage}.json", result)
    return result


def test_sample(sample, folder):
    folder.mkdir()
    result = {"logicalId": sample["logicalId"], "key": sample["key"], "kind": sample["kind"],
              "assetId": sample["asset"]["assetId"], "sourceDuration": sample["asset"]["sourceDuration"],
              "metadataSeconds": sample["asset"]["durationSeconds"], "status": "FAIL", "folder": str(folder.relative_to(ROOT))}
    try:
        url = sample["asset"]["source"]["hlsUrl"]
        result["playlist"] = playlist_tree(url, folder)
        checked_input = folder / "checked-input.m3u8"
        checked_input.write_bytes(pinned_playlist(result["playlist"]["media"]).encode("utf-8"))
        result["sourceProbeInput"] = "Local pinned media playlist with validated direct HTTPS segment URLs"
        source = ffprobe(folder, "source-probe", checked_input, True)
        result["sourceProbe"] = source
        result["sourceSeconds"] = measured_duration(source)
        streams = source.get("streams", [])
        if len(streams) != 1 or streams[0].get("codec_type") != "audio" or streams[0].get("codec_name") != "aac":
            raise ValueError("Expected one AAC audio stream; no automatic transcode")
        if result["sourceSeconds"] is None or result["sourceSeconds"] > 600:
            raise ValueError("Source duration missing or exceeds ten-minute sample cap")
        # Inspect one complete first segment per sample, not the entire HLS input
        # twice; format_name establishes ADTS AAC vs TS/fMP4 beyond its extension.
        segment = result["playlist"]["media"]["segments"][0]
        result["segmentProbe"] = ffprobe(folder, "segment-probe", segment, True)
        output = folder / "output.m4a"
        _, remux_stderr = command(folder, "remux", ["ffmpeg", "-nostdin", "-hide_banner", "-v", "warning", "-xerror"]
            + NETWORK_OPTIONS + ["-i", str(checked_input), "-map", "0:a:0", "-map_metadata", "-1", "-c:a", "copy",
                                 "-movflags", "+faststart", "-f", "ipod", "-n", str(output)], timeout=180)
        result["remuxExitCode"] = 0
        result["remuxWarnings"] = remux_stderr.strip()
        if not output.is_file() or output.stat().st_size <= 0:
            raise ValueError("Missing/empty remux output")
        result.update(outputBytes=output.stat().st_size, sha256=digest(output))
        output_probe = ffprobe(folder, "output-probe", output, False)
        result["outputProbe"] = output_probe
        result["outputSeconds"] = measured_duration(output_probe)
        errors = validate_output(source, output_probe)
        if output_probe.get("format", {}).get("format_name") != "mov,mp4,m4a,3gp,3g2,mj2":
            errors.append("Unexpected output container")
        if errors:
            raise ValueError("; ".join(errors))
        _, stderr = command(folder, "decode", ["ffmpeg", "-nostdin", "-hide_banner", "-v", "error", "-xerror",
            "-i", str(output), "-map", "0:a:0", "-f", "null", "-"], timeout=90)
        if stderr.strip():
            raise ValueError("Full decode emitted error-level diagnostics")
        result.update(status="PASS", decodeExitCode=0,
                      outputMinusMetadata=result["outputSeconds"] - result["metadataSeconds"],
                      outputMinusHls=result["outputSeconds"] - result["sourceSeconds"])
    except AccessStop as exc:
        result.update(status="STOP", error=str(exc))
    except (OSError, ValueError) as exc:
        result["error"] = str(exc)
    finally:
        write_json(folder / "result.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="List the fixed eleven assets without network requests")
    args = parser.parse_args()
    if digest(CATALOG) != BASELINE_HASH:
        parser.error("B3 catalog hash differs from reviewed immutable baseline")
    samples = select_samples(load_json(CATALOG))
    if args.list:
        for sample in samples:
            print(sample["asset"]["assetId"])
        return 0
    for binary in ("ffmpeg", "ffprobe"):
        if shutil.which(binary) is None:
            parser.error(f"Required tool missing: {binary}")
    run = ROOT / "tmp/media-test" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run.mkdir(parents=True)
    report = {"phase": "B4/B5 temporary experiment", "catalogSha256Before": digest(CATALOG),
              "sampleLimit": 11, "startedUtc": datetime.now(timezone.utc).isoformat(), "results": []}
    for binary in ("ffmpeg", "ffprobe"):
        stdout, _ = command(run, binary + "-version", [binary, "-version"])
        report[binary + "Version"] = stdout.splitlines()[0]
    print(f"RUN: {run}", flush=True)
    try:
        for index, sample in enumerate(samples, 1):
            print(f"[{index}/11] START {sample['key']} {sample['kind']}", flush=True)
            folder = run / sample["asset"]["assetId"].replace(":", "_")
            result = test_sample(sample, folder)
            report["results"].append(result)
            write_json(run / "results.json", report)
            print(f"[{index}/11] {result['status']} {result.get('outputBytes', 0)} bytes {result.get('error', '')}", flush=True)
            if result["status"] == "STOP":
                print("STOP: encryption/special access condition; no further media work", flush=True)
                break
    finally:
        report.update(catalogSha256After=digest(CATALOG), finishedUtc=datetime.now(timezone.utc).isoformat())
        report["catalogUnchanged"] = report["catalogSha256After"] == BASELINE_HASH
        report["passed"] = sum(r["status"] == "PASS" for r in report["results"])
        report["attempted"] = len(report["results"])
        write_json(run / "results.json", report)
    print(f"RESULT: {report['passed']}/{report['attempted']} PASS; evidence {run / 'results.json'}", flush=True)
    return 0 if report["catalogUnchanged"] and report["passed"] == 11 else 1


if __name__ == "__main__":
    sys.exit(main())
