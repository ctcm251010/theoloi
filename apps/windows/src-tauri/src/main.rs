#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

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
    // Bundled local frontend only. No shell/fs/network plugin, secret or R2 binding.
    tauri::Builder::default()
        .setup(|app| {
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
