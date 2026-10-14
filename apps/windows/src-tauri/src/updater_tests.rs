//! Offline characterization of the pinned plugin's header and cryptographic guarantees.
//! Fixtures are self-authored text plus public signatures. No installer is ever executed.
use std::{
    io::{Read, Write},
    net::TcpListener,
    thread,
    time::{Duration, Instant},
};
use tauri_plugin_updater::{Error, UpdaterExt};

#[derive(serde::Deserialize)]
#[serde(rename_all = "camelCase")]
struct Fixture {
    content: String,
    public_key: String,
    signed: String,
    legacy: String,
}

fn download_fixture(version: &str, legacy: bool, tamper: bool) -> Result<Vec<u8>, Error> {
    let fixture: Fixture =
        serde_json::from_str(include_str!("fixtures/update-signatures.json")).unwrap();
    let signature = if legacy {
        fixture.legacy
    } else {
        fixture.signed
    };
    let mut artifact = fixture.content.into_bytes();
    if tamper {
        artifact[0] ^= 1;
    }
    download_signed_bytes(version, fixture.public_key, signature, artifact)
}

fn download_signed_bytes(
    version: &str,
    public_key: String,
    signature: String,
    artifact: Vec<u8>,
) -> Result<Vec<u8>, Error> {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    listener.set_nonblocking(true).unwrap();
    let base = format!("http://{}", listener.local_addr().unwrap());
    let manifest = serde_json::json!({
        "version": version,
        "url": format!("{base}/installer"),
        "signature": signature,
    })
    .to_string();
    let server = thread::spawn(move || {
        for (route, body) in [("/check", manifest.into_bytes()), ("/installer", artifact)] {
            let deadline = Instant::now() + Duration::from_secs(5);
            let mut stream = loop {
                match listener.accept() {
                    Ok((stream, _)) => break stream,
                    Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                        assert!(Instant::now() < deadline, "fixture request timed out");
                        thread::sleep(Duration::from_millis(5));
                    }
                    Err(error) => panic!("fixture accept failed: {error}"),
                }
            };
            stream.set_nonblocking(false).unwrap();
            stream
                .set_read_timeout(Some(Duration::from_secs(3)))
                .unwrap();
            let mut request = Vec::new();
            while !request.ends_with(b"\r\n\r\n") {
                let mut byte = [0];
                stream.read_exact(&mut byte).unwrap();
                request.extend(byte);
                assert!(request.len() < 8192);
            }
            let request = String::from_utf8(request).unwrap().to_ascii_lowercase();
            assert!(request.starts_with(&format!("get {route} http/1.1\r\n")));
            assert!(request.contains("\r\nauthorization: bearer synthetic-fixture\r\n"));
            write!(
                stream,
                "HTTP/1.1 200 OK\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
                body.len()
            )
            .unwrap();
            stream.write_all(&body).unwrap();
        }
    });
    let mut context = tauri::test::mock_context(tauri::test::noop_assets());
    context.config_mut().plugins.0.insert(
        "updater".into(),
        serde_json::json!({
            "pubkey": public_key,
            "endpoints": [format!("{base}/check")],
            "requireSignedVersion": true,
            // Isolated localhost test server only; production rejects this setting.
            "dangerousInsecureTransportProtocol": true,
        }),
    );
    let app = tauri::test::mock_builder()
        .plugin(tauri_plugin_updater::Builder::new().build())
        .build(context)
        .unwrap();
    let result = tauri::async_runtime::block_on(async {
        let update = app
            .updater_builder()
            .timeout(Duration::from_secs(3))
            .no_proxy()
            .configure_client(|client| client.redirect(reqwest::redirect::Policy::none()))
            .header("Authorization", "Bearer synthetic-fixture")?
            .build()?
            .check()
            .await?
            .expect("fixture update is newer than mock app");
        update.download(|_, _| {}, || {}).await
    });
    server.join().unwrap();
    result
}

#[test]
fn updater_retains_bearer_headers_and_accepts_a_matching_signed_version() {
    assert_eq!(
        download_fixture("1.0.1", false, false).unwrap(),
        b"AudioTP offline updater signature fixture. This is not an installer."
    );
}

#[test]
fn updater_rejects_tampered_signed_bytes() {
    assert!(matches!(
        download_fixture("1.0.1", false, true),
        Err(Error::Minisign(_))
    ));
}

#[test]
fn updater_rejects_an_old_artifact_advertised_as_a_newer_version() {
    assert!(matches!(
        download_fixture("1.0.2", false, false),
        Err(Error::SignedVersionMismatch { .. })
    ));
}

#[test]
fn updater_rejects_legacy_signatures_without_a_signed_version() {
    assert!(matches!(
        download_fixture("1.0.1", true, false),
        Err(Error::MissingSignedVersion)
    ));
}

// Explicit local artifact validation. Downloads only from a temporary loopback
// server and NEVER calls install; needs no credential, R2 or private signing key.
#[test]
#[ignore = "Set AUDIOTP_VERIFY_RELEASE_DIR to a built production release directory"]
fn built_installer_signature_matches_the_pinned_public_key() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../..")
        .canonicalize()
        .unwrap();
    let folder = std::path::PathBuf::from(
        std::env::var_os("AUDIOTP_VERIFY_RELEASE_DIR")
            .expect("Explicit release directory required"),
    )
    .canonicalize()
    .unwrap();
    assert_eq!(
        folder.parent(),
        Some(root.join("release/windows").as_path())
    );
    let report: serde_json::Value =
        serde_json::from_slice(&std::fs::read(folder.join("build-report.json")).unwrap()).unwrap();
    let version = report["version"].as_str().unwrap();
    let parsed = semver::Version::parse(version).unwrap();
    assert!(parsed.pre.is_empty() && parsed.build.is_empty());
    let name = format!("AudioTP_{version}_x64-setup.exe");
    let path = folder.join(&name);
    assert!(std::fs::metadata(&path).unwrap().len() < 50 * 1024 * 1024);
    let bytes = std::fs::read(&path).unwrap();
    let signature = std::fs::read_to_string(folder.join(format!("{name}.sig"))).unwrap();
    let public_key = std::fs::read_to_string(root.join("config/audiotp-updater.pub")).unwrap();
    assert_eq!(
        download_signed_bytes(
            version,
            public_key.trim().into(),
            signature.trim().into(),
            bytes.clone()
        )
        .unwrap(),
        bytes
    );
}
