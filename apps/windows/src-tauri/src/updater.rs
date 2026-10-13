use std::{sync::Mutex, time::Duration};
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

#[derive(serde::Serialize)]
#[serde(rename_all = "camelCase")]
pub struct AvailableUpdate {
    version: String,
    current_version: String,
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
    let download = update.download(|_, _| {}, || {}).await;
    let mut session = pending.0.lock().map_err(|_| CANCELLED)?;
    let result = if !session.may_install(generation) {
        Err(CANCELLED.into())
    } else {
        // This synchronous hand-off holds the session lock so logout cannot race the installer.
        // On Windows the plugin starts the verified installer and exits the application.
        download
            .map_err(|_| INSTALL_FAILED.to_owned())
            .and_then(|bytes| update.install(bytes).map_err(|_| INSTALL_FAILED.to_owned()))
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
}
