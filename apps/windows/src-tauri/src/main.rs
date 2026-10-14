#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod remember;
mod offline_fs;
mod offline;
mod update_policy;
mod updater;
#[cfg(test)]
mod updater_tests;
use std::sync::Mutex;
use tauri::Manager;

fn credential_directory(
    app: &tauri::AppHandle,
    window: &tauri::WebviewWindow,
) -> Result<std::path::PathBuf, String> {
    let url = window
        .url()
        .map_err(|_| "Không xác minh được cửa sổ ứng dụng.")?;
    if window.label() != "main" || !internal_navigation(&url) {
        return Err("Chỉ cửa sổ AudioTP được truy cập đăng nhập đã lưu.".into());
    }
    app.path()
        .app_local_data_dir()
        .map_err(|_| "Không mở được dữ liệu ứng dụng.".into())
}

#[tauri::command]
fn save_access_code(
    app: tauri::AppHandle,
    window: tauri::WebviewWindow,
    lock: tauri::State<'_, Mutex<()>>,
    base: String,
    code: String,
) -> Result<(), String> {
    let _guard = lock
        .lock()
        .map_err(|_| "Không mở được dữ liệu đăng nhập.")?;
    remember::save(&credential_directory(&app, &window)?, &base, &code)
}

#[tauri::command]
fn read_access_code(
    app: tauri::AppHandle,
    window: tauri::WebviewWindow,
    lock: tauri::State<'_, Mutex<()>>,
    base: String,
) -> Result<Option<String>, String> {
    let _guard = lock
        .lock()
        .map_err(|_| "Không mở được dữ liệu đăng nhập.")?;
    remember::read(&credential_directory(&app, &window)?, &base)
}

#[tauri::command]
fn forget_access_code(
    app: tauri::AppHandle,
    window: tauri::WebviewWindow,
    lock: tauri::State<'_, Mutex<()>>,
) -> Result<(), String> {
    let _guard = lock
        .lock()
        .map_err(|_| "Không mở được dữ liệu đăng nhập.")?;
    remember::forget(&credential_directory(&app, &window)?)
}

fn internal_navigation(url: &tauri::Url) -> bool {
    url.username().is_empty()
        && url.password().is_none()
        && url.port().is_none()
        && ((url.scheme() == "tauri" && url.host_str() == Some("localhost"))
            || (matches!(url.scheme(), "http" | "https")
                && url.host_str() == Some("tauri.localhost")))
}

#[cfg(test)]
mod tests {
    #[test]
    fn navigation_is_limited_to_the_bundled_frontend() {
        for url in [
            "tauri://localhost/",
            "http://tauri.localhost/index.html",
            "https://tauri.localhost/",
        ] {
            assert!(super::internal_navigation(&tauri::Url::parse(url).unwrap()));
        }
        for url in [
            "https://example.com/",
            "http://localhost:8766/",
            "https://tauri.localhost.evil/",
            "https://user@tauri.localhost/",
            "https://tauri.localhost:444/",
            "file:///C:/Windows/",
            "data:text/html,hello",
            "javascript:alert(1)",
        ] {
            assert!(!super::internal_navigation(
                &tauri::Url::parse(url).unwrap()
            ));
        }
    }
}

fn main() {
    // Bundled frontend only. No general shell/fs/network plugin or R2 credential.
    offline::register(tauri::Builder::default())
        .manage(Mutex::new(()))
        .manage(updater::PendingUpdates::default())
        .invoke_handler(tauri::generate_handler![
            save_access_code,
            read_access_code,
            forget_access_code,
            updater::check_update,
            updater::check_release_info,
            updater::install_update,
            updater::clear_update,
            offline::offline_status,
            offline::offline_sync,
            offline::offline_start,
            offline::offline_control,
            offline::offline_remove
        ])
        .setup(|app| {
            offline::initialize(app.handle());
            // The updater requires a public key. LOCAL/TEST builds intentionally have no plugin
            // configuration, so leave it unregistered rather than failing application startup.
            if updater::configured(&app.config().plugins) {
                app.handle()
                    .plugin(tauri_plugin_updater::Builder::new().build())?;
            }
            let config = app
                .config()
                .app
                .windows
                .first()
                .ok_or("Missing main window config")?;
            tauri::WebviewWindowBuilder::from_config(app, config)?
                .on_navigation(internal_navigation)
                .on_new_window(|_, _| tauri::webview::NewWindowResponse::Deny)
                .build()?;
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("AudioTP could not initialize WebView2");
}
