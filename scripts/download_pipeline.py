"""B6/B7 production processing, verification and crash-safe completion."""
import errno
import json
import logging
import math
import os
from pathlib import Path
import re
import subprocess
import time
import uuid

from download_state import now, sha256
from hls_source import MediaFailure, RateLimited, preflight

LOG = logging.getLogger("download-media")
NETWORK = ["-rw_timeout", "20000000", "-protocol_whitelist", "file,https,tls,tcp"]


class Interrupted(Exception):
    pass


def duration(probe):
    try:
        n = float(probe["format"]["duration"])
    except (KeyError, TypeError, ValueError):
        return None
    return n if math.isfinite(n) and n > 0 else None


def validate_media(source, output):
    a, b = source.get("streams", []), output.get("streams", [])
    if len(a) != 1 or len(b) != 1 or any(s.get("codec_type") != "audio" or s.get("codec_name") != "aac" for s in a + b):
        raise MediaFailure("Expected exactly one AAC audio stream, no video or transcode", "profile")
    for field in ("codec_name", "sample_rate", "channels", "profile", "channel_layout"):
        if field in a[0] and a[0][field] != b[0].get(field):
            raise MediaFailure(f"Source/output {field} changed", "profile")
    d, src = duration(output), duration(source)
    if d is None or src is None:
        raise MediaFailure("Missing/nonfinite/nonpositive source/output duration")
    if output.get("format", {}).get("format_name") != "mov,mp4,m4a,3gp,3g2,mj2":
        raise MediaFailure("Unexpected output container", "profile")
    try:
        rate, channels = int(b[0]["sample_rate"]), int(b[0]["channels"])
        if rate <= 0 or channels <= 0: raise ValueError()
    except (KeyError, TypeError, ValueError) as exc:
        raise MediaFailure("Invalid sample rate/channels", "profile") from exc
    return {"probed_duration": d, "source_duration": src, "codec": b[0]["codec_name"], "sample_rate": rate,
            "channels": channels, "channel_layout": b[0].get("channel_layout")}


def command_failure(message):
    lowered = message.lower()
    if re.search(r"\b(429|503)\b", lowered):
        return RateLimited(message)
    if re.search(r"\b(401|402|403|404|410)\b", lowered) or "unauthorized" in lowered or "forbidden" in lowered:
        return MediaFailure(message, "access")
    if any(s in lowered for s in ("timed out", "timeout", "connection", "reset", "i/o error", "input/output error",
                                   "http error 5", "server returned 5", "failed to open segment", "error when loading first segment")):
        return MediaFailure(message, "transient")
    return MediaFailure(message, "integrity")


class Backend:
    def run(self, job, stage, argv, stop, timeout=180):
        if stop.is_set(): raise Interrupted()
        env = os.environ.copy()
        for key in list(env):
            if key.lower() in ("http_proxy", "https_proxy", "all_proxy", "no_proxy"): del env[key]
        child = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        started = time.monotonic()
        timed_out = interrupted = False
        try:
            while True:
                try:
                    stdout, stderr = child.communicate(timeout=0.25)
                    break
                except subprocess.TimeoutExpired:
                    if stop.is_set() or time.monotonic() - started > timeout:
                        interrupted, timed_out = stop.is_set(), not stop.is_set()
                        child.terminate()
                        try: stdout, stderr = child.communicate(timeout=3)
                        except subprocess.TimeoutExpired:
                            child.kill(); stdout, stderr = child.communicate()
                        break
        finally:
            if child.poll() is None:
                child.kill(); child.wait()
        stdout, stderr = stdout.decode("utf-8", "replace"), stderr.decode("utf-8", "replace")
        record = {"at": now(), "stage": stage, "argv": argv, "exitCode": child.returncode,
                  "seconds": round(time.monotonic() - started, 3), "timedOut": timed_out,
                  "interrupted": interrupted, "stderr": stderr[-8000:]}
        with (Path(job["work_dir"]) / "commands.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        if interrupted: raise Interrupted()
        if timed_out: raise MediaFailure(f"{stage} timeout after {timeout}s", "transient")
        if child.returncode != 0:
            raise command_failure(f"{stage} exit {child.returncode}: {stderr[-1800:]}")
        if stage in ("source-probe", "output-probe", "decode") and stderr.strip():
            raise command_failure(f"{stage} error diagnostic: {stderr[-1800:]}")
        if stage == "remux" and any(s in stderr.lower() for s in ("failed to open", "error", "skipping segment")):
            raise command_failure(f"remux incomplete input: {stderr[-1800:]}")
        return stdout, stderr

    def probe(self, job, path, stop, remote=False):
        stage = "source-probe" if remote else "output-probe"
        stdout, _ = self.run(job, stage, ["ffprobe", "-v", "error"] + (NETWORK if remote else [])
                            + ["-show_streams", "-show_format", "-of", "json", str(path)], stop, timeout=90)
        try: return json.loads(stdout)
        except ValueError as exc: raise MediaFailure("Malformed FFprobe JSON") from exc

    def prepare(self, job, stop):
        checked = Path(job["work_dir"]) / "checked-input.m3u8"
        media = preflight(job["source_url"], checked)
        if stop.is_set(): raise Interrupted()
        source = self.probe(job, checked, stop, remote=True)
        streams = source.get("streams", [])
        if len(streams) != 1 or streams[0].get("codec_type") != "audio" or streams[0].get("codec_name") != "aac":
            raise MediaFailure("Source no longer one AAC stream; no automatic transcode", "profile")
        if duration(source) is None:
            raise MediaFailure("Source duration unavailable", "profile")
        return {"source": source, "input": str(checked), "playlistDuration": media["duration"], "segmentCount": len(media["segments"])}

    def remux(self, job, prepared, stop):
        self.run(job, "remux", ["ffmpeg", "-nostdin", "-hide_banner", "-v", "warning", "-xerror"] + NETWORK
                 + ["-i", prepared["input"], "-map", "0:a:0", "-map_metadata", "-1", "-c:a", "copy",
                    "-movflags", "+faststart", "-f", "ipod", "-n", job["temp_path"]], stop, timeout=300)

    def verify(self, job, path, prepared, stop):
        path = Path(path)
        if not path.is_file() or path.stat().st_size <= 0:
            raise MediaFailure("Missing/empty output")
        output = self.probe(job, path, stop)
        result = validate_media(prepared["source"], output)
        self.run(job, "decode", ["ffmpeg", "-nostdin", "-hide_banner", "-v", "error", "-xerror", "-i", str(path),
                                "-map", "0:a:0", "-f", "null", "-"], stop, timeout=180)
        warnings = []
        delta = result["probed_duration"] - job["metadata_duration"]
        if abs(delta) > 2:
            warnings.append(f"metadata_duration_delta_seconds={delta:.6f}")
        difference = result["probed_duration"] - result["source_duration"]
        if abs(difference) > 0.5:
            warnings.append(f"hls_duration_delta_seconds={difference:.6f}; manual review")
        result.update(byte_size=path.stat().st_size, sha256=sha256(path), probe_verified=1, decode_verified=1,
                      verification_json=json.dumps({"source": prepared["source"], "output": output,
                          "remux": "AAC streamcopy, M4A, faststart", "probeExitCode": 0, "decodeExitCode": 0, "verifiedAt": now()}, ensure_ascii=False),
                      warnings_json=json.dumps(warnings))
        return result


def cache_valid(row, path):
    try:
        path = Path(path)
        return (bool(row["sha256"] and row["probe_verified"] and row["decode_verified"] and row["verification_json"])
                and path.is_file() and path.stat().st_size == row["byte_size"] and sha256(path) == row["sha256"])
    except OSError:
        return False


def quarantine(job):
    final = Path(job["final_path"])
    if final.exists():
        target = Path(job["work_dir"]) / f"quarantine-{uuid.uuid4().hex}.m4a"
        os.replace(final, target)


def publish(job, state, evidence):
    """Evidence commit → fsync temp → atomic rename → completed commit."""
    state.update(job["asset_id"], status="verifying", **evidence)
    part, final = Path(job["temp_path"]), Path(job["final_path"])
    final.parent.mkdir(parents=True, exist_ok=True)
    if part.drive != final.drive:
        raise MediaFailure("Atomic publication requires same filesystem", "local")
    with part.open("r+b") as stream:
        stream.flush(); os.fsync(stream.fileno())
    os.replace(part, final)
    if sha256(final) != evidence["sha256"]:
        quarantine(job)
        raise MediaFailure("Final bytes hash differs after rename")
    state.update(job["asset_id"], status="completed", finished_at=now(), last_error=None, error_kind=None)


def process(job, state, backend, stop, backoff=(2, 4)):
    asset = job["asset_id"]
    work = Path(job["work_dir"]); work.mkdir(parents=True, exist_ok=True)
    row = state.get(asset)
    if cache_valid(row, job["final_path"]):
        state.update(asset, status="completed", finished_at=row["finished_at"] or now(), last_error=None, error_kind=None)
        state.event(asset, "skip_verified")
        return "skipped"
    if cache_valid(row, job["temp_path"]):
        quarantine(job)
        evidence_fields = ("byte_size", "sha256", "probed_duration", "source_duration", "codec", "sample_rate", "channels",
                           "channel_layout", "probe_verified", "decode_verified", "verification_json", "warnings_json")
        publish(job, state, {k: row[k] for k in evidence_fields})
        state.event(asset, "recovered_verified_temp")
        return "skipped"
    if row["status"] == "failed": return "failed"
    if row["status"] == "completed":
        state.event(asset, "invalid_completed_output")
        state.update(asset, status="pending", failures=0)
    quarantine(job)
    state.update(asset, sha256=None, byte_size=None, probe_verified=0, decode_verified=0, verification_json=None)
    while True:
        row = state.get(asset)
        if stop.is_set(): return "interrupted"
        if row["failures"] >= 3:
            state.update(asset, status="failed", finished_at=now())
            return "failed"
        part = Path(job["temp_path"])
        if part.exists(): part.unlink()
        state.update(asset, status="downloading", attempts=row["attempts"] + 1, started_at=now(), finished_at=None)
        state.event(asset, "attempt")
        LOG.debug("%s %s Downloading attempt=%s", job["key"], job["variant"], row["attempts"] + 1)
        try:
            prepared = backend.prepare(job, stop)
            backend.remux(job, prepared, stop)
            state.update(asset, status="verifying")
            LOG.debug("%s %s Verifying", job["key"], job["variant"])
            evidence = backend.verify(job, part, prepared, stop)
            if stop.is_set(): raise Interrupted()
            publish(job, state, evidence)
            state.event(asset, "completed")
            return "completed"
        except Interrupted:
            state.update(asset, status="pending", last_error="Interrupted; safe to resume")
            state.event(asset, "interrupted")
            return "interrupted"
        except OSError as exc:
            failure = MediaFailure(f"Local filesystem error: {exc}", "local")
            if exc.errno == errno.ENOSPC: stop.set()
        except MediaFailure as exc:
            failure = exc
        failures = row["failures"] + 1
        retry = failure.kind == "transient" and failures < 3 and not isinstance(failure, RateLimited)
        state.update(asset, status="pending" if retry else "failed", failures=failures, last_error=str(failure),
                     error_kind=failure.kind, finished_at=None if retry else now(), probe_verified=0, decode_verified=0)
        state.event(asset, "retry" if retry else "failed", str(failure))
        LOG.warning("%s %s %s: %s", job["key"], job["variant"], "RETRY" if retry else "FAIL", failure)
        if isinstance(failure, RateLimited): stop.set()
        if not retry: return "failed"
        if stop.wait(backoff[min(failures - 1, len(backoff) - 1)]): return "interrupted"


def audit(job, state, backend, stop):
    row = state.get(job["asset_id"])
    if row["status"] != "completed": return "failed"
    try:
        if not cache_valid(row, job["final_path"]): raise MediaFailure("Missing/modified completed bytes")
        prepared = json.loads(row["verification_json"])
        evidence = backend.verify(job, job["final_path"], prepared, stop)
        if evidence["sha256"] != row["sha256"]: raise MediaFailure("Audit hash differs")
        state.update(job["asset_id"], **evidence)
        state.event(job["asset_id"], "audit_pass")
        return "audited"
    except Interrupted: return "interrupted"
    except (OSError, ValueError, MediaFailure) as exc:
        state.update(job["asset_id"], status="pending", decode_verified=0, probe_verified=0,
                     last_error=f"Audit failed: {exc}", error_kind="integrity")
        state.event(job["asset_id"], "audit_failed", str(exc))
        return "failed"
