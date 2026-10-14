use super::*;
use sha2::{Digest, Sha256};

fn manifest(bytes: &[u8]) -> Manifest {
    Manifest {
        schema_version: 1,
        revision: "self-authored-fixture-v1".into(),
        tracks: vec![Track {
            id: "fixture:guide:1".into(),
            logical_id: "fixture:song:1".into(),
            mode: "guide".into(),
            section: Some("main".into()),
            number: 1,
            title: "Self-authored native fixture".into(),
            category: "Fixture".into(),
            duration_seconds: 1.,
        }],
        assets: vec![Asset {
            asset_id: "fixture:guide:1".into(),
            bytes: bytes.len() as u64,
            sha256: format!("{:x}", Sha256::digest(bytes)),
            content_type: "audio/wav".into(),
        }],
    }
}

#[test]
fn manifest_exact_membership_hash_size_and_core_only() {
    let good = manifest(b"Self-authored bytes");
    assert!(good.validate(true).is_ok());
    assert!(good.validate(false).is_err());
    let mut bad = good.clone();
    bad.assets[0].asset_id = "other".into();
    assert!(bad.validate(true).is_err());
    let mut bad = good.clone();
    bad.assets.push(bad.assets[0].clone());
    assert!(bad.validate(true).is_err());
    let mut bad = good.clone();
    bad.assets[0].bytes = 0;
    assert!(bad.validate(true).is_err());
    let mut bad = good.clone();
    bad.assets[0].bytes = MAX_ASSET_BYTES + 1;
    assert!(bad.validate(true).is_err());
    let mut bad = good.clone();
    bad.assets[0].sha256 = "x".repeat(64);
    assert!(bad.validate(true).is_err());
    let mut bad = good.clone();
    bad.tracks[0].mode = "prayer".into();
    assert!(bad.validate(true).is_err());
    let mut bad = good.clone();
    bad.tracks[0].id = "../elsewhere".into();
    assert!(bad.validate(true).is_err());
    let mut bad = serde_json::to_value(&good).unwrap();
    bad["assets"][0]["objectKey"] = "never accepted".into();
    assert!(serde_json::from_value::<Manifest>(bad).is_err());
}
#[test]
fn origin_pins_production_and_isolates_local_acceptance() {
    assert!(valid_base(crate::update_policy::API_ORIGIN, false));
    assert!(valid_base("http://127.0.0.1:8766", true));
    assert!(valid_base("http://localhost:8766", true));
    for base in [
        "http://127.0.0.1:8766",
        "http://localhost:8766",
        "https://other.test",
        "https://audiotp-media-api.ctcm251010.workers.dev/",
        "https://audiotp-media-api.ctcm251010.workers.dev?token=x",
        "https://user@audiotp-media-api.ctcm251010.workers.dev",
        "https://audiotp-media-api.ctcm251010.workers.dev:444",
    ] {
        assert!(!valid_base(base, false), "{base}");
    }
    for base in [
        "http://127.0.0.1:8766/path",
        "http://127.0.0.1:8766?x=1",
        "http://user@localhost:8766",
        "http://localhost.evil:8766",
    ] {
        assert!(!valid_base(base, true));
    }
}
#[test]
fn ranges_are_single_bounded_and_resume_requires_exact_representation() {
    assert_eq!(encode("fixture:guide:1"), "fixture%3Aguide%3A1");
    assert_eq!(range("bytes=2-4", 10), Some((2, 4)));
    assert_eq!(range("bytes=8-", 10), Some((8, 9)));
    assert_eq!(range("bytes=-3", 10), Some((7, 9)));
    assert_eq!(range("bytes=0-99", 10), Some((0, 9)));
    for value in [
        "bytes=10-",
        "bytes=3-2",
        "bytes=-0",
        "bytes=0-1,4-5",
        "bytes=-",
        "bytes=999999999999999999999999-",
    ] {
        assert_eq!(range(value, 10), None);
    }
    assert!(content_range("bytes 4-9/10", 4, 9, 10));
    for value in [
        "bytes 0-9/10",
        "bytes 4-8/10",
        "bytes 4-9/11",
        "bytes 4-9/*",
        "garbage",
    ] {
        assert!(!content_range(value, 4, 9, 10));
    }
}

fn temp() -> std::path::PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("target")
        .join(format!(
            "audiotp-offline-{}-{}",
            std::process::id(),
            SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ))
}
#[test]
fn disk_preflight_reserves_space_and_checks_overflow() {
    assert!(disk_preflight(RESERVE_BYTES + 100, 100).is_ok());
    assert!(disk_preflight(RESERVE_BYTES + 99, 100).is_err());
    assert!(disk_preflight(u64::MAX, u64::MAX).is_err());
}
#[test]
fn offline_restart_verifies_local_bytes_without_network_and_invalidates_corruption() {
    let dir = temp();
    let bytes = b"Self-authored retained offline file";
    let metadata = manifest(bytes);
    let cache = Cache::open(&dir).unwrap();
    cache.write_json("manifest", &metadata).unwrap();
    let mut file = cache
        .open_write(&cache.name(&metadata.assets[0].asset_id, "audio"), true)
        .unwrap();
    file.write_all(bytes).unwrap();
    drop(file);
    drop(cache);
    let manager = OfflineManager::open(&dir, true).unwrap();
    let status = manager.status().unwrap();
    assert_eq!(status.completed, vec![metadata.assets[0].asset_id.clone()]);
    std::fs::write(
        manager.cache.name(&metadata.assets[0].asset_id, "audio"),
        b"corrupt",
    )
    .unwrap();
    let status = manager.status().unwrap();
    assert!(status.completed.is_empty());
    assert!(status.manifest.is_some());
    drop(manager);
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn removal_accepts_only_current_ids_and_never_original_files() {
    let dir = temp();
    let bytes = b"Self-authored deleted bytes";
    let metadata = manifest(bytes);
    let cache = Cache::open(&dir).unwrap();
    cache.write_json("manifest", &metadata).unwrap();
    let original = dir.join("original.audio");
    std::fs::write(&original, b"preserved").unwrap();
    let mut file = cache
        .open_write(&cache.name(&metadata.assets[0].asset_id, "audio"), true)
        .unwrap();
    file.write_all(bytes).unwrap();
    drop(file);
    drop(cache);
    let manager = OfflineManager::open(&dir, true).unwrap();
    assert!(manager.remove(vec!["../original.audio".into()]).is_err());
    assert_eq!(manager.status().unwrap().completed.len(), 1);
    assert!(manager
        .remove(vec![metadata.assets[0].asset_id.clone()])
        .unwrap()
        .completed
        .is_empty());
    assert_eq!(std::fs::read(original).unwrap(), b"preserved");
    drop(manager);
    std::fs::remove_dir_all(dir).unwrap();
}

struct Server {
    base: String,
    requests: Arc<Mutex<Vec<String>>>,
    stop: Arc<AtomicBool>,
    thread: Option<std::thread::JoinHandle<()>>,
}
impl Server {
    fn new(metadata: Manifest, bytes: Vec<u8>, behavior: &'static str) -> Self {
        use std::net::TcpListener;
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        listener.set_nonblocking(true).unwrap();
        let base = format!("http://{}", listener.local_addr().unwrap());
        let requests = Arc::new(Mutex::new(Vec::new()));
        let observed = requests.clone();
        let stop = Arc::new(AtomicBool::new(false));
        let stopping = stop.clone();
        let handle = std::thread::spawn(move || {
            while !stopping.load(Ordering::Relaxed) {
                let (mut stream, _) = match listener.accept() {
                    Ok(value) => value,
                    Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                        std::thread::sleep(Duration::from_millis(2));
                        continue;
                    }
                    Err(error) => panic!("fixture {error}"),
                };
                // Winsock may inherit FIONBIO from the nonblocking listener. A
                // partial HTTP header must wait for the next packet, not close/RST.
                stream.set_nonblocking(false).unwrap();
                stream
                    .set_read_timeout(Some(Duration::from_secs(3)))
                    .unwrap();
                let mut request = Vec::new();
                let mut byte = [0];
                while !request.ends_with(b"\r\n\r\n") {
                    if stream.read_exact(&mut byte).is_err() {
                        break;
                    }
                    request.extend_from_slice(&byte);
                    assert!(request.len() < 16384);
                }
                if request.is_empty() {
                    continue;
                }
                let header = String::from_utf8(request).unwrap();
                let lower = header.to_ascii_lowercase();
                observed.lock().unwrap().push(lower.clone());
                if let Some(length) = lower
                    .lines()
                    .find_map(|line| line.strip_prefix("content-length: "))
                    .and_then(|length| length.parse::<usize>().ok())
                {
                    let mut body = vec![0; length];
                    stream.read_exact(&mut body).unwrap();
                }
                let route = header.lines().next().unwrap_or_default();
                if behavior == "slow-manifest" && route.contains("/v1/offline-manifest ") {
                    std::thread::sleep(Duration::from_millis(150));
                }
                let (status, headers, body) = if route.contains("/v1/offline-manifest ") {
                    assert!(lower.contains("authorization: bearer synthetic-test-session\r\n"));
                    (
                        "200 OK",
                        String::from("Content-Type: application/json\r\n"),
                        serde_json::to_vec(&metadata).unwrap(),
                    )
                } else if route.contains("/v1/play-tickets ") {
                    assert!(lower.contains("authorization: bearer synthetic-test-session\r\n"));
                    ("200 OK",String::from("Content-Type: application/json\r\n"),serde_json::to_vec(&serde_json::json!({"assetId":metadata.assets[0].asset_id,"path":"/v1/media/fixture%3Aguide%3A1","ticket":"synthetic-ticket","expiresAt":9999999999u64})).unwrap())
                } else {
                    assert!(
                        route.contains("/v1/media/fixture%3Aguide%3A1?ticket=synthetic-ticket ")
                    );
                    assert!(!lower.contains("authorization:"));
                    let requested = lower
                        .lines()
                        .find_map(|line| line.strip_prefix("range: "))
                        .unwrap_or("bytes=0-");
                    let (start, end) = range(requested, bytes.len() as u64).unwrap();
                    let media_requests = observed
                        .lock()
                        .unwrap()
                        .iter()
                        .filter(|r| r.starts_with("get /v1/media/"))
                        .count();
                    if behavior == "rate-long" {
                        let _=stream.write_all(b"HTTP/1.1 429 Too Many Requests\r\nRetry-After: 3600\r\nContent-Length: 0\r\nConnection: close\r\n\r\n");
                        continue;
                    }
                    if behavior == "rate-always" || behavior == "rate-once" && media_requests == 1 {
                        let _=stream.write_all(b"HTTP/1.1 429 Too Many Requests\r\nRetry-After: 1\r\nContent-Length: 0\r\nConnection: close\r\n\r\n");
                        continue;
                    }
                    if behavior == "offline" {
                        let _=stream.write_all(b"HTTP/1.1 503 Service Unavailable\r\nContent-Length: 0\r\nConnection: close\r\n\r\n");
                        continue;
                    }
                    if behavior == "redirect" {
                        let _=stream.write_all(b"HTTP/1.1 302 Found\r\nLocation: http://127.0.0.1:1/not-permitted\r\nContent-Length: 0\r\nConnection: close\r\n\r\n");
                        continue;
                    }
                    let (status, start, end) = if behavior == "full-response" {
                        ("200 OK", 0, bytes.len() as u64 - 1)
                    } else {
                        ("206 Partial Content", start, end)
                    };
                    let mut body = bytes[start as usize..=end as usize].to_vec();
                    if behavior == "corrupt" {
                        body[0] ^= 1;
                    }
                    let header_start = if behavior == "wrong-range" {
                        start + 1
                    } else {
                        start
                    };
                    let etag = if behavior == "changing-etag" {
                        format!("self-authored-{}", observed.lock().unwrap().len())
                    } else {
                        "self-authored-v1".into()
                    };
                    (status,format!("Content-Type: audio/wav\r\nETag: \"{etag}\"\r\nX-AudioTP-Asset-Id: fixture:guide:1\r\nContent-Range: bytes {header_start}-{end}/{}\r\n",bytes.len()),body)
                };
                let head = format!(
                    "HTTP/1.1 {status}\r\nContent-Length: {}\r\n{headers}Connection: close\r\n\r\n",
                    body.len()
                );
                let _ = stream.write_all(head.as_bytes());
                if behavior == "slow" && route.contains("/v1/media/") {
                    for chunk in body.chunks(8192) {
                        if stream.write_all(chunk).is_err() {
                            break;
                        }
                        std::thread::sleep(Duration::from_millis(3));
                    }
                } else if behavior == "disconnect" && route.contains("/v1/media/") {
                    let _ = stream.write_all(&body[..body.len() / 2]);
                } else {
                    let _ = stream.write_all(&body);
                }
            }
        });
        Self {
            base,
            requests,
            stop,
            thread: Some(handle),
        }
    }
}
impl Drop for Server {
    fn drop(&mut self) {
        self.stop.store(true, Ordering::Relaxed);
        if let Some(thread) = self.thread.take() {
            thread.join().unwrap();
        }
    }
}
fn wait_finished(manager: &OfflineManager) -> Status {
    let deadline = std::time::Instant::now() + Duration::from_secs(10);
    loop {
        if !manager.inner.lock().unwrap().worker {
            return manager.status().unwrap();
        }
        assert!(
            std::time::Instant::now() < deadline,
            "download did not finish"
        );
        std::thread::sleep(Duration::from_millis(5));
    }
}
#[test]
fn authentic_download_verifies_skips_and_survives_restart() {
    let dir = temp();
    let bytes = b"Native HTTP self-authored fixture".repeat(400);
    let metadata = manifest(&bytes);
    let server = Server::new(metadata.clone(), bytes.clone(), "normal");
    let manager = OfflineManager::open(&dir, true).unwrap();
    manager
        .sync(server.base.clone(), "synthetic-test-session".into())
        .unwrap_or_else(|error| {
            panic!(
                "sync {error}; requests {:?}",
                server.requests.lock().unwrap()
            )
        });
    let ids = vec![metadata.assets[0].asset_id.clone()];
    manager
        .start(
            server.base.clone(),
            "synthetic-test-session".into(),
            ids.clone(),
        )
        .unwrap();
    let status = wait_finished(&manager);
    assert_eq!(
        status.completed,
        ids,
        "{} requests {:?}",
        serde_json::to_string(&status).unwrap(),
        server.requests.lock().unwrap()
    );
    assert_eq!(status.job.completed, 1);
    assert_eq!(
        std::fs::read(manager.cache.name(&ids[0], "audio")).unwrap(),
        bytes
    );
    let requests = server.requests.lock().unwrap().len();
    manager
        .start(
            server.base.clone(),
            "synthetic-test-session".into(),
            ids.clone(),
        )
        .unwrap();
    wait_finished(&manager);
    assert_eq!(server.requests.lock().unwrap().len(), requests);
    for name in ["manifest.json", "queue.json"] {
        let metadata = std::fs::read(manager.cache.root.join(name)).unwrap();
        assert!(!metadata
            .windows(b"synthetic-test-session".len())
            .any(|b| b == b"synthetic-test-session"));
    }
    drop(manager);
    drop(server);
    let restarted = OfflineManager::open(&dir, true).unwrap();
    assert_eq!(restarted.status().unwrap().completed, ids);
    drop(restarted);
    std::fs::remove_dir_all(dir).unwrap();
}
#[test]
fn failed_downloads_never_become_completed_and_can_retry() {
    for behavior in [
        "offline",
        "disconnect",
        "corrupt",
        "wrong-range",
        "redirect",
    ] {
        let dir = temp();
        let bytes = b"Failure test self-authored fixture".repeat(4000);
        let metadata = manifest(&bytes);
        let server = Server::new(metadata.clone(), bytes.clone(), behavior);
        let manager = OfflineManager::open(&dir, true).unwrap();
        manager
            .sync(server.base.clone(), "synthetic-test-session".into())
            .unwrap();
        manager
            .start(
                server.base.clone(),
                "synthetic-test-session".into(),
                vec![metadata.assets[0].asset_id.clone()],
            )
            .unwrap();
        let status = wait_finished(&manager);
        assert!(status.completed.is_empty(), "{behavior}");
        assert_eq!(
            status.job.failed,
            1,
            "{behavior} {}",
            serde_json::to_string(&status).unwrap()
        );
        assert!(!manager
            .cache
            .name(&metadata.assets[0].asset_id, "audio")
            .exists());
        drop(server);
        let server = Server::new(metadata.clone(), bytes, "normal");
        manager
            .control(
                "retry",
                Some(server.base.clone()),
                Some("synthetic-test-session".into()),
            )
            .unwrap();
        let retried = wait_finished(&manager);
        assert_eq!(
            retried.completed.len(),
            1,
            "{behavior} status={} requests={:?}",
            serde_json::to_string(&retried).unwrap(),
            server.requests.lock().unwrap()
        );
        drop(server);
        drop(manager);
        std::fs::remove_dir_all(dir).unwrap();
    }
}

fn seeded() -> (std::path::PathBuf, Arc<OfflineManager>, Vec<u8>) {
    let dir = temp();
    let bytes = b"Self-authored protocol bytes 0123456789".repeat(4000);
    let metadata = manifest(&bytes);
    let cache = Cache::open(&dir).unwrap();
    cache.write_json("manifest", &metadata).unwrap();
    let mut file = cache
        .open_write(&cache.name("fixture:guide:1", "audio"), true)
        .unwrap();
    file.write_all(&bytes).unwrap();
    drop(file);
    drop(cache);
    let manager = OfflineManager::open(&dir, true).unwrap();
    (dir, manager, bytes)
}
fn request(
    method: &str,
    path: &str,
    requested_range: Option<&str>,
    origin: Option<&str>,
) -> tauri::http::Request<Vec<u8>> {
    let mut request = tauri::http::Request::builder()
        .method(method)
        .uri(format!("http://offline.localhost/{path}"));
    if let Some(range) = requested_range {
        request = request.header("Range", range);
    }
    if let Some(origin) = origin {
        request = request.header("Origin", origin);
    }
    request.body(Vec::new()).unwrap()
}
#[test]
fn protocol_reads_verified_files_without_auth_and_supports_head_ranges() {
    let (dir, manager, bytes) = seeded();
    let full = manager.serve(request(
        "GET",
        "fixture%3Aguide%3A1",
        None,
        Some("http://tauri.localhost"),
    ));
    assert_eq!(full.status(), 200);
    assert_eq!(full.body(), &bytes);
    assert_eq!(
        full.headers()["access-control-allow-origin"],
        "http://tauri.localhost"
    );
    let head = manager.serve(request("HEAD", "fixture%3Aguide%3A1", None, None));
    assert_eq!(head.status(), 200);
    assert!(head.body().is_empty());
    assert_eq!(
        head.headers()["content-length"].to_str().unwrap(),
        bytes.len().to_string()
    );
    for (range, start, end) in [
        ("bytes=2-4", 2, 4),
        ("bytes=-3", bytes.len() - 3, bytes.len() - 1),
        ("bytes=7-", 7, bytes.len() - 1),
    ] {
        let response = manager.serve(request("GET", "fixture%3Aguide%3A1", Some(range), None));
        assert_eq!(response.status(), 206);
        assert_eq!(response.body(), &bytes[start..=end]);
    }
    for bad in ["bytes=999999999-", "bytes=0-1,4-5", "bytes=-0"] {
        let response = manager.serve(request("GET", "fixture%3Aguide%3A1", Some(bad), None));
        assert_eq!(response.status(), 416);
        assert!(response.body().is_empty());
    }
    for path in [
        "..%2Foriginal.audio",
        "%ZZ",
        "fixture%3Aguide%3A1?path=elsewhere",
        "unknown",
    ] {
        assert_eq!(
            manager.serve(request("GET", path, None, None)).status(),
            404
        );
    }
    assert_eq!(
        manager
            .serve(request("DELETE", "fixture%3Aguide%3A1", None, None))
            .status(),
        405
    );
    assert_eq!(
        manager
            .serve(request(
                "GET",
                "fixture%3Aguide%3A1",
                None,
                Some("https://evil.test")
            ))
            .status(),
        403
    );
    drop(manager);
    std::fs::remove_dir_all(dir).unwrap();
}
#[test]
fn protocol_detects_same_size_corruption_even_with_restored_timestamp() {
    let (dir, manager, bytes) = seeded();
    let path = manager.cache.name("fixture:guide:1", "audio");
    let modified = std::fs::metadata(&path).unwrap().modified().unwrap();
    let mut file = std::fs::OpenOptions::new().write(true).open(&path).unwrap();
    file.write_all(&vec![b'x'; bytes.len()]).unwrap();
    file.set_times(std::fs::FileTimes::new().set_modified(modified))
        .unwrap();
    drop(file);
    assert_eq!(
        manager
            .serve(request(
                "GET",
                "fixture%3Aguide%3A1",
                Some("bytes=0-3"),
                None
            ))
            .status(),
        409
    );
    assert!(manager.status().unwrap().completed.is_empty());
    drop(manager);
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn pause_resume_uses_range_and_cancel_preserves_verified_and_partial_files() {
    let dir = temp();
    let bytes = b"Self-authored pause resume fixture".repeat(60_000);
    let metadata = manifest(&bytes);
    let server = Server::new(metadata.clone(), bytes.clone(), "slow");
    let manager = OfflineManager::open(&dir, true).unwrap();
    manager
        .sync(server.base.clone(), "synthetic-test-session".into())
        .unwrap();
    let ids = vec![metadata.assets[0].asset_id.clone()];
    manager
        .start(
            server.base.clone(),
            "synthetic-test-session".into(),
            ids.clone(),
        )
        .unwrap();
    let deadline = std::time::Instant::now() + Duration::from_secs(5);
    while manager.status().unwrap().job.bytes == 0 {
        assert!(std::time::Instant::now() < deadline);
        std::thread::sleep(Duration::from_millis(5));
    }
    let paused = manager.control("pause", None, None).unwrap();
    assert_eq!(paused.job.status, "paused");
    assert!(paused.completed.is_empty());
    std::thread::sleep(Duration::from_millis(50));
    let progress = manager.status().unwrap().job.bytes;
    std::thread::sleep(Duration::from_millis(50));
    assert_eq!(manager.status().unwrap().job.bytes, progress);
    manager
        .control(
            "resume",
            Some(server.base.clone()),
            Some("synthetic-test-session".into()),
        )
        .unwrap();
    assert_eq!(wait_finished(&manager).completed, ids);
    assert!(server
        .requests
        .lock()
        .unwrap()
        .iter()
        .any(|r| r.contains("if-range: \"self-authored-v1\"")));
    manager.control("cancel", None, None).unwrap();
    assert!(manager.inner.lock().unwrap().session.is_none());
    assert_eq!(manager.status().unwrap().completed, ids);
    drop(server);
    drop(manager);
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn full_response_restarts_partial_instead_of_appending() {
    let dir = temp();
    let bytes = b"Self-authored full HTTP response fixture".repeat(500);
    let metadata = manifest(&bytes);
    let server = Server::new(metadata.clone(), bytes.clone(), "full-response");
    let manager = OfflineManager::open(&dir, true).unwrap();
    manager
        .sync(server.base.clone(), "synthetic-test-session".into())
        .unwrap();
    let id = metadata.assets[0].asset_id.clone();
    let mut part = manager
        .cache
        .open_write(&manager.cache.name(&id, "part"), true)
        .unwrap();
    part.write_all(&bytes[..200]).unwrap();
    drop(part);
    manager.inner.lock().unwrap().items = vec![QueueItem {
        asset_id: id.clone(),
        status: "paused".into(),
        bytes: 200,
        error: None,
        etag: Some("\"self-authored-v1\"".into()),
        attempts: 0,
    }];
    manager
        .start(
            server.base.clone(),
            "synthetic-test-session".into(),
            vec![id.clone()],
        )
        .unwrap();
    assert_eq!(wait_finished(&manager).completed, vec![id.clone()]);
    assert_eq!(
        std::fs::read(manager.cache.name(&id, "audio")).unwrap(),
        bytes
    );
    drop(server);
    drop(manager);
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn cancel_invalidates_a_manifest_request_in_flight() {
    let dir = temp();
    let bytes = b"Self-authored cancellation bytes";
    let metadata = manifest(bytes);
    let server = Server::new(metadata, bytes.to_vec(), "slow-manifest");
    let manager = OfflineManager::open(&dir, true).unwrap();
    let pending = manager.clone();
    let base = server.base.clone();
    let thread = std::thread::spawn(move || pending.sync(base, "synthetic-test-session".into()));
    let deadline = std::time::Instant::now() + Duration::from_secs(5);
    while server.requests.lock().unwrap().is_empty() {
        assert!(std::time::Instant::now() < deadline);
        std::thread::sleep(Duration::from_millis(2));
    }
    manager.control("cancel", None, None).unwrap();
    assert!(thread.join().unwrap().is_err());
    assert!(manager.status().unwrap().manifest.is_none());
    assert!(!manager.cache.root.join("manifest.json").exists());
    drop(server);
    drop(manager);
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn corruption_is_not_skipped_when_starting_a_new_download() {
    let (dir, manager, bytes) = seeded();
    let metadata = manifest(&bytes);
    let server = Server::new(metadata, bytes.clone(), "normal");
    let path = manager.cache.name("fixture:guide:1", "audio");
    let modified = std::fs::metadata(&path).unwrap().modified().unwrap();
    let mut file = std::fs::OpenOptions::new().write(true).open(&path).unwrap();
    file.write_all(&vec![0; bytes.len()]).unwrap();
    file.set_times(std::fs::FileTimes::new().set_modified(modified))
        .unwrap();
    drop(file);
    manager
        .start(
            server.base.clone(),
            "synthetic-test-session".into(),
            vec!["fixture:guide:1".into()],
        )
        .unwrap();
    assert_eq!(wait_finished(&manager).completed.len(), 1);
    assert_eq!(std::fs::read(path).unwrap(), bytes);
    drop(server);
    drop(manager);
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn cancellation_retains_partial_and_restart_can_resume_it() {
    let dir = temp();
    let bytes = b"Self-authored durable queue fixture".repeat(50_000);
    let metadata = manifest(&bytes);
    let server = Server::new(metadata.clone(), bytes.clone(), "slow");
    let id = metadata.assets[0].asset_id.clone();
    let manager = OfflineManager::open(&dir, true).unwrap();
    manager
        .sync(server.base.clone(), "synthetic-test-session".into())
        .unwrap();
    manager
        .start(
            server.base.clone(),
            "synthetic-test-session".into(),
            vec![id.clone()],
        )
        .unwrap();
    let deadline = std::time::Instant::now() + Duration::from_secs(5);
    while manager.status().unwrap().job.bytes == 0 {
        assert!(std::time::Instant::now() < deadline);
        std::thread::sleep(Duration::from_millis(5));
    }
    manager.control("cancel", None, None).unwrap();
    assert!(wait_finished(&manager).completed.is_empty());
    let part = manager.cache.name(&id, "part");
    assert!(std::fs::metadata(&part).unwrap().len() > 0);
    drop(manager);
    drop(server);
    let manager = OfflineManager::open(&dir, true).unwrap();
    assert_eq!(manager.status().unwrap().job.status, "cancelled");
    let server = Server::new(metadata, bytes.clone(), "normal");
    manager
        .start(
            server.base.clone(),
            "synthetic-test-session".into(),
            vec![id.clone()],
        )
        .unwrap();
    assert_eq!(wait_finished(&manager).completed, vec![id.clone()]);
    assert_eq!(
        std::fs::read(manager.cache.name(&id, "audio")).unwrap(),
        bytes
    );
    drop(server);
    drop(manager);
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn a_changing_representation_has_a_bounded_restart_budget() {
    let dir = temp();
    let bytes = vec![42; CHUNK_BYTES as usize + 1024];
    let metadata = manifest(&bytes);
    let server = Server::new(metadata.clone(), bytes, "changing-etag");
    let manager = OfflineManager::open(&dir, true).unwrap();
    manager
        .sync(server.base.clone(), "synthetic-test-session".into())
        .unwrap();
    manager
        .start(
            server.base.clone(),
            "synthetic-test-session".into(),
            vec![metadata.assets[0].asset_id.clone()],
        )
        .unwrap();
    let result = wait_finished(&manager);
    assert!(result.completed.is_empty());
    assert_eq!(result.job.failed, 1);
    assert!(server.requests.lock().unwrap().len() <= 8);
    drop(server);
    drop(manager);
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn rapid_pause_then_resume_cannot_strand_the_current_item() {
    let dir = temp();
    let bytes = b"Self-authored rapid resume fixture".repeat(30_000);
    let metadata = manifest(&bytes);
    let server = Server::new(metadata.clone(), bytes, "slow");
    let manager = OfflineManager::open(&dir, true).unwrap();
    manager
        .sync(server.base.clone(), "synthetic-test-session".into())
        .unwrap();
    manager
        .start(
            server.base.clone(),
            "synthetic-test-session".into(),
            vec![metadata.assets[0].asset_id.clone()],
        )
        .unwrap();
    let deadline = std::time::Instant::now() + Duration::from_secs(5);
    while manager.status().unwrap().job.bytes == 0 {
        assert!(std::time::Instant::now() < deadline);
        std::thread::sleep(Duration::from_millis(2));
    }
    for _ in 0..4 {
        manager.control("pause", None, None).unwrap();
        manager
            .control(
                "resume",
                Some(server.base.clone()),
                Some("synthetic-test-session".into()),
            )
            .unwrap();
    }
    assert_eq!(wait_finished(&manager).completed.len(), 1);
    drop(server);
    drop(manager);
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn an_unavailable_server_pauses_remaining_queue_instead_of_hammering_it() {
    let dir = temp();
    let bytes = b"Self-authored outage fixture";
    let mut metadata = manifest(bytes);
    let mut next = metadata.tracks[0].clone();
    next.id = "fixture:guide:2".into();
    next.logical_id = "fixture:song:2".into();
    next.number = 2;
    metadata.tracks.push(next);
    let mut next = metadata.assets[0].clone();
    next.asset_id = "fixture:guide:2".into();
    metadata.assets.push(next);
    let server = Server::new(metadata.clone(), bytes.to_vec(), "offline");
    let manager = OfflineManager::open(&dir, true).unwrap();
    manager
        .sync(server.base.clone(), "synthetic-test-session".into())
        .unwrap();
    manager
        .start(
            server.base.clone(),
            "synthetic-test-session".into(),
            metadata.assets.iter().map(|a| a.asset_id.clone()).collect(),
        )
        .unwrap();
    let status = wait_finished(&manager);
    assert_eq!(status.job.failed, 1);
    assert!(status
        .items
        .iter()
        .any(|item| item.asset_id == "fixture:guide:2" && item.status == "paused"));
    assert_eq!(
        server
            .requests
            .lock()
            .unwrap()
            .iter()
            .filter(|r| r.starts_with("post /v1/play-tickets"))
            .count(),
        1
    );
    drop(server);
    drop(manager);
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn rate_limit_backoff_can_be_cancelled_without_waiting_for_the_delay() {
    let dir = temp();
    let bytes = b"Self-authored cancel 429 fixture";
    let metadata = manifest(bytes);
    let server = Server::new(metadata.clone(), bytes.to_vec(), "rate-always");
    let manager = OfflineManager::open(&dir, true).unwrap();
    manager
        .sync(server.base.clone(), "synthetic-test-session".into())
        .unwrap();
    manager
        .start(
            server.base.clone(),
            "synthetic-test-session".into(),
            vec![metadata.assets[0].asset_id.clone()],
        )
        .unwrap();
    let deadline = std::time::Instant::now() + Duration::from_secs(5);
    while !server
        .requests
        .lock()
        .unwrap()
        .iter()
        .any(|r| r.starts_with("get /v1/media/"))
    {
        assert!(std::time::Instant::now() < deadline);
        std::thread::sleep(Duration::from_millis(2));
    }
    let before = std::time::Instant::now();
    manager.control("cancel", None, None).unwrap();
    let status = wait_finished(&manager);
    assert_eq!(status.job.status, "cancelled");
    assert!(before.elapsed() < Duration::from_millis(900));
    assert!(status.completed.is_empty());
    drop(server);
    drop(manager);
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn rate_limit_waits_and_retries_with_a_bounded_budget() {
    for behavior in ["rate-once", "rate-always", "rate-long"] {
        let dir = temp();
        let bytes = b"Self-authored 429 fixture";
        let metadata = manifest(bytes);
        let server = Server::new(metadata.clone(), bytes.to_vec(), behavior);
        let manager = OfflineManager::open(&dir, true).unwrap();
        manager
            .sync(server.base.clone(), "synthetic-test-session".into())
            .unwrap();
        let started = std::time::Instant::now();
        manager
            .start(
                server.base.clone(),
                "synthetic-test-session".into(),
                vec![metadata.assets[0].asset_id.clone()],
            )
            .unwrap();
        let result = wait_finished(&manager);
        let count = server
            .requests
            .lock()
            .unwrap()
            .iter()
            .filter(|r| r.starts_with("get /v1/media/"))
            .count();
        if behavior == "rate-long" {
            assert!(result.completed.is_empty());
            assert_eq!(result.job.failed, 1);
            assert_eq!(count, 1);
            assert!(started.elapsed() < Duration::from_secs(5));
        } else if behavior == "rate-once" {
            assert_eq!(result.completed.len(), 1);
            assert_eq!(count, 2);
        } else {
            assert!(result.completed.is_empty());
            assert_eq!(result.job.failed, 1);
            assert_eq!(count, 3);
        }
        if behavior != "rate-long" {
            assert!(started.elapsed() >= Duration::from_secs(1));
        }
        drop(server);
        drop(manager);
        std::fs::remove_dir_all(dir).unwrap();
    }
}
