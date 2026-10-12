#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    // Bundled local frontend only. No shell/fs/network plugin, secret or R2 binding.
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("AudioTP could not initialize WebView2");
}
