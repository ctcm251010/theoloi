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
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    listener.set_nonblocking(true).unwrap();
    let base = format!("http://{}", listener.local_addr().unwrap());
    let manifest = serde_json::json!({
        "version": version,
        "url": format!("{base}/installer"),
        "signature": if legacy { &fixture.legacy } else { &fixture.signed },
    })
    .to_string();
    let mut artifact = fixture.content.into_bytes();
    if tamper {
        artifact[0] ^= 1;
    }
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
            "pubkey": fixture.public_key,
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
