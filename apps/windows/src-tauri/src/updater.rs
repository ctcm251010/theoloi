use std::{
    sync::{
        atomic::{AtomicU64, Ordering},
        Mutex,
    },
    time::Duration,
};
use tauri::Emitter;
use tauri_plugin_updater::{Update, UpdaterExt};

use crate::update_policy::{valid_release, valid_token, UpdateSession, API_ORIGIN};

const UNAVAILABLE: &str = "Cập nhật chưa được cấu hình cho bản cài này.";
const CHECK_FAILED: &str = "Không kiểm tra được cập nhật. Vui lòng thử lại sau.";
const INSTALL_FAILED: &str = "Không tải hoặc xác minh được bản cập nhật. Vui lòng thử lại sau.";
const CANCELLED: &str = "Phiên cập nhật đã thay đổi. Vui lòng kiểm tra lại.";
const BUSY: &str = "Ứng dụng đang xử lý cập nhật.";

pub fn configured(plugins: &tauri::utils::config::PluginConfig) -> bool {
    let Some(settings) = plugins.0.get("updater") else {
        return false;
    };
    settings
        .get("pubkey")
        .and_then(|key| key.as_str())
        .is_some_and(|key| !key.is_empty())
        && settings
            .get("requireSignedVersion")
            .and_then(|value| value.as_bool())
            == Some(true)
        && ![
            "dangerousInsecureTransportProtocol",
            "dangerousAcceptInvalidCerts",
            "dangerousAcceptInvalidHostnames",
            "dangerous-insecure-transport-protocol",
            "dangerous-accept-invalid-certs",
            "dangerous-accept-invalid-hostnames",
        ]
        .iter()
        .any(|name| settings.get(*name).and_then(|value| value.as_bool()) == Some(true))
}

#[derive(Default)]
pub struct PendingUpdates(Mutex<UpdateSession<Update>>);

#[derive(serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct AvailableUpdate {
    version: String,
    current_version: String,
}

const RELEASE_INFO_TIMEOUT: Duration = Duration::from_secs(5);
const MAX_RELEASE_INFO_BYTES: usize = 2048;

fn parse_release_info(body: &[u8], current: &str) -> Result<AvailableUpdate, String> {
    let result: AvailableUpdate = serde_json::from_slice(body).map_err(|_| CHECK_FAILED)?;
    let (Ok(version), Ok(current_version)) = (
        semver::Version::parse(&result.version),
        semver::Version::parse(current),
    ) else {
        return Err(CHECK_FAILED.into());
    };
    if result.current_version != current || !version.cmp_precedence(&current_version).is_gt() {
        return Err(CHECK_FAILED.into());
    }
    Ok(result)
}

async fn fetch_release_info(
    client: reqwest::Client,
    endpoint: &str,
    current: &str,
) -> Result<Option<AvailableUpdate>, String> {
    let mut response = client
        .get(endpoint)
        .send()
        .await
        .map_err(|_| CHECK_FAILED)?;
    if response.status() == reqwest::StatusCode::NO_CONTENT {
        return Ok(None);
    }
    if response.status() != reqwest::StatusCode::OK
        || response
            .content_length()
            .is_some_and(|size| size > MAX_RELEASE_INFO_BYTES as u64)
    {
        return Err(CHECK_FAILED.into());
    }
    let mut body = Vec::new();
    while let Some(chunk) = response.chunk().await.map_err(|_| CHECK_FAILED)? {
        if body.len() + chunk.len() > MAX_RELEASE_INFO_BYTES {
            return Err(CHECK_FAILED.into());
        }
        body.extend_from_slice(&chunk);
    }
    parse_release_info(&body, current).map(Some)
}

// Notification-only metadata: this command never creates a pending signed update or sends auth.
#[tauri::command]
pub async fn check_release_info(
    app: tauri::AppHandle,
    window: tauri::WebviewWindow,
) -> Result<Option<AvailableUpdate>, String> {
    require_main(&window)?;
    if !configured(&app.config().plugins) {
        return Ok(None);
    }
    let current = app.package_info().version.to_string();
    let endpoint = format!("{API_ORIGIN}/v1/release-info/windows-x86_64/{current}");
    // The pinned updater enables reqwest's rustls-no-provider feature. A public startup
    // check can run before the plugin initializes its provider for the signed check.
    let _ = rustls::crypto::ring::default_provider().install_default();
    let client = reqwest::Client::builder()
        .timeout(RELEASE_INFO_TIMEOUT)
        .redirect(reqwest::redirect::Policy::none())
        .build()
        .map_err(|_| CHECK_FAILED)?;
    fetch_release_info(client, &endpoint, &current).await
}

#[derive(Clone, serde::Serialize)]
#[serde(rename_all = "camelCase")]
struct UpdateProgress {
    phase: &'static str,
    downloaded: u64,
    total: Option<u64>,
    percent: Option<f64>,
}

fn emit_progress(
    window: &tauri::WebviewWindow,
    phase: &'static str,
    downloaded: u64,
    total: Option<u64>,
) {
    let percent = total
        .filter(|total| *total > 0)
        .map(|total| ((downloaded as f64 / total as f64) * 100.0).min(100.0));
    let _ = window.emit(
        "app-update-progress",
        UpdateProgress {
            phase,
            downloaded,
            total,
            percent,
        },
    );
}

fn require_main(window: &tauri::WebviewWindow) -> Result<(), String> {
    let url = window.url().map_err(|_| CANCELLED)?;
    if window.label() != "main" || !crate::internal_navigation(&url) {
        return Err(CANCELLED.into());
    }
    Ok(())
}

async fn request_update(app: &tauri::AppHandle, token: String) -> Result<Option<Update>, String> {
    // TEST/LOCAL builds omit the public-key configuration and never contact the update server.
    if !configured(&app.config().plugins) {
        return Err(UNAVAILABLE.into());
    }
    // Neither endpoint nor installer URL can be supplied by JavaScript. Refuse redirects on both
    // requests so the in-memory bearer header cannot be forwarded to another route or origin.
    let endpoint = format!(
        "{API_ORIGIN}/v1/updates/windows-x86_64/{}",
        app.package_info().version
    )
    .parse()
    .map_err(|_| UNAVAILABLE)?;
    let update = app
        .updater_builder()
        .endpoints(vec![endpoint])
        .map_err(|_| UNAVAILABLE)?
        .timeout(Duration::from_secs(30))
        .restart_after_install(true)
        .configure_client(|client| client.redirect(reqwest::redirect::Policy::none()))
        .header("Authorization", format!("Bearer {token}"))
        .map_err(|_| CHECK_FAILED)?
        .build()
        .map_err(|_| UNAVAILABLE)?
        .check()
        .await
        .map_err(|_| CHECK_FAILED)?;
    if let Some(update) = &update {
        if !valid_release(
            &app.package_info().version.to_string(),
            &update.version,
            &update.download_url,
        ) {
            return Err(CHECK_FAILED.into());
        }
    }
    Ok(update)
}

#[tauri::command]
pub async fn check_update(
    app: tauri::AppHandle,
    window: tauri::WebviewWindow,
    pending: tauri::State<'_, PendingUpdates>,
    token: String,
) -> Result<Option<AvailableUpdate>, String> {
    require_main(&window)?;
    if !valid_token(&token) {
        return Err(CHECK_FAILED.into());
    }
    let generation = pending
        .0
        .lock()
        .map_err(|_| CANCELLED)?
        .begin_check()
        .ok_or(BUSY)?;
    let result = request_update(&app, token).await;
    let response = result
        .as_ref()
        .ok()
        .and_then(|update| update.as_ref())
        .map(|update| AvailableUpdate {
            version: update.version.clone(),
            current_version: update.current_version.clone(),
        });
    let error = result.as_ref().err().cloned();
    let mut session = pending.0.lock().map_err(|_| CANCELLED)?;
    if !session.finish_check(generation, result.ok().flatten()) {
        return Err(CANCELLED.into());
    }
    if let Some(error) = error {
        return Err(error);
    }
    Ok(response)
}

#[tauri::command]
pub async fn install_update(
    window: tauri::WebviewWindow,
    pending: tauri::State<'_, PendingUpdates>,
) -> Result<(), String> {
    require_main(&window)?;
    let (generation, update) = pending
        .0
        .lock()
        .map_err(|_| CANCELLED)?
        .begin_install()
        .ok_or(CANCELLED)?;
    // The plugin's download verifies the Minisign signature before returning any bytes. Keep
    // install separate to recheck logout/cancellation after the awaited network operation.
    let downloaded = AtomicU64::new(0);
    let total = AtomicU64::new(0);
    let download = update
        .download(
            |chunk, content_length| {
                let count = downloaded.fetch_add(chunk as u64, Ordering::Relaxed) + chunk as u64;
                total.store(content_length.unwrap_or(0), Ordering::Relaxed);
                emit_progress(&window, "downloading", count, content_length);
            },
            || {
                // The plugin's finish callback runs before Minisign verification.
                emit_progress(
                    &window,
                    "verifying",
                    downloaded.load(Ordering::Relaxed),
                    Some(total.load(Ordering::Relaxed)).filter(|size| *size > 0),
                );
            },
        )
        .await;
    let mut session = pending.0.lock().map_err(|_| CANCELLED)?;
    let result = if !session.may_install(generation) {
        Err(CANCELLED.into())
    } else {
        // This synchronous hand-off holds the session lock so logout cannot race the installer.
        // On Windows the plugin starts the verified installer and exits the application.
        download
            .map_err(|_| INSTALL_FAILED.to_owned())
            .and_then(|bytes| {
                emit_progress(
                    &window,
                    "installing",
                    downloaded.load(Ordering::Relaxed),
                    Some(total.load(Ordering::Relaxed)).filter(|size| *size > 0),
                );
                update.install(bytes).map_err(|_| INSTALL_FAILED.to_owned())
            })
    };
    session.finish_install();
    result
}

#[tauri::command]
pub fn clear_update(
    window: tauri::WebviewWindow,
    pending: tauri::State<'_, PendingUpdates>,
) -> Result<(), String> {
    require_main(&window)?;
    pending.0.lock().map_err(|_| CANCELLED)?.clear();
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn incomplete_or_insecure_configuration_disables_updates() {
        let mut plugins = tauri::utils::config::PluginConfig::default();
        assert!(!configured(&plugins));
        plugins.0.insert(
            "updater".into(),
            serde_json::json!({"pubkey":"public-fixture", "requireSignedVersion":true}),
        );
        assert!(configured(&plugins));
        for config in [
            serde_json::json!({"pubkey":"public-fixture"}),
            serde_json::json!({"pubkey":"", "requireSignedVersion":true}),
            serde_json::json!({"pubkey":"public-fixture", "requireSignedVersion":false}),
            serde_json::json!({"pubkey":"public-fixture", "requireSignedVersion":true, "dangerousAcceptInvalidCerts":true}),
            serde_json::json!({"pubkey":"public-fixture", "requireSignedVersion":true, "dangerous-accept-invalid-hostnames":true}),
        ] {
            plugins.0.insert("updater".into(), config);
            assert!(!configured(&plugins));
        }
    }

    #[test]
    fn public_release_metadata_is_strict_and_cannot_authorize_an_installer() {
        let result =
            parse_release_info(br#"{"version":"1.0.4","currentVersion":"1.0.3"}"#, "1.0.3")
                .unwrap();
        assert_eq!(result.version, "1.0.4");
        for body in [
            r#"{"version":"1.0.3","currentVersion":"1.0.3"}"#,
            r#"{"version":"1.0.2","currentVersion":"1.0.3"}"#,
            r#"{"version":"1.0.4","currentVersion":"1.0.2"}"#,
            r#"{"version":"invalid","currentVersion":"1.0.3"}"#,
            r#"{"version":"1.0.4","currentVersion":"1.0.3","url":"https://other/installer"}"#,
        ] {
            assert!(parse_release_info(body.as_bytes(), "1.0.3").is_err());
        }
    }

    fn public_response(
        status: &str,
        body: &[u8],
        delay: Duration,
    ) -> Result<Option<AvailableUpdate>, String> {
        use std::{
            io::{Read, Write},
            net::TcpListener,
            thread,
        };
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let endpoint = format!("http://{}/release-info", listener.local_addr().unwrap());
        let response = format!("HTTP/1.1 {status}\r\nContent-Length: {}\r\nLocation: /installer\r\nConnection: close\r\n\r\n", body.len()).into_bytes();
        let body = body.to_vec();
        let server = thread::spawn(move || {
            let (mut stream, _) = listener.accept().unwrap();
            stream
                .set_read_timeout(Some(Duration::from_secs(2)))
                .unwrap();
            let mut request = Vec::new();
            while !request.ends_with(b"\r\n\r\n") {
                let mut byte = [0];
                stream.read_exact(&mut byte).unwrap();
                request.extend(byte);
                assert!(request.len() < 8192);
            }
            let request = String::from_utf8(request).unwrap().to_lowercase();
            assert!(request.starts_with("get /release-info http/1.1\r\n"));
            assert!(!request.contains("authorization:"));
            thread::sleep(delay);
            let _ = stream.write_all(&response);
            let _ = stream.write_all(&body);
        });
        let _ = rustls::crypto::ring::default_provider().install_default();
        let client = reqwest::Client::builder()
            .no_proxy()
            .timeout(Duration::from_millis(100))
            .redirect(reqwest::redirect::Policy::none())
            .build()
            .unwrap();
        let result = tauri::async_runtime::block_on(fetch_release_info(client, &endpoint, "1.0.3"));
        server.join().unwrap();
        result
    }

    #[test]
    fn public_check_is_anonymous_bounded_and_rejects_redirects_and_oversize_bodies() {
        let body = br#"{"version":"1.0.4","currentVersion":"1.0.3"}"#;
        assert!(public_response("200 OK", body, Duration::ZERO)
            .unwrap()
            .is_some());
        assert!(public_response("204 No Content", b"", Duration::ZERO)
            .unwrap()
            .is_none());
        assert!(public_response("302 Found", body, Duration::ZERO).is_err());
        assert!(public_response(
            "200 OK",
            &vec![b'x'; MAX_RELEASE_INFO_BYTES + 1],
            Duration::ZERO
        )
        .is_err());
        assert!(public_response("200 OK", body, Duration::from_millis(250)).is_err());
        assert_eq!(RELEASE_INFO_TIMEOUT, Duration::from_secs(5));
    }
}
