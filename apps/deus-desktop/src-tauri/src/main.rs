#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    tauri::Builder::default()
        // Baseline deliberately exposes no Rust commands to the webview.
        .run(tauri::generate_context!())
        .expect("failed to run DEUS desktop shell");
}
