// Auto-update module for Observer desktop app

use tauri::AppHandle;
use tauri_plugin_updater::UpdaterExt;

/// Restart the application after update
fn restart_app() {
    // Get the current executable path and restart
    if let Ok(exe) = std::env::current_exe() {
        println!("Restarting app from: {:?}", exe);

        // Spawn a new instance of the app
        let _ = std::process::Command::new(&exe)
            .spawn();

        // Exit the current instance
        std::process::exit(0);
    }
}

/// Check for updates and prompt user if available
pub async fn check_for_updates(app: AppHandle) {
    // Wait a bit before checking to let app fully initialize
    tokio::time::sleep(tokio::time::Duration::from_secs(5)).await;

    println!("=== Checking for updates ===");
    println!("Current version: {}", env!("CARGO_PKG_VERSION"));

    match app.updater() {
        Ok(updater) => {
            println!("Updater initialized, fetching latest.json from GitHub...");
            match updater.check().await {
                Ok(Some(update)) => {
                    let version = update.version.clone();
                    println!("UPDATE AVAILABLE: v{}", version);
                    println!("Current: v{} -> New: v{}", env!("CARGO_PKG_VERSION"), version);

                    // Show notification about update
                    if let Err(e) = show_update_notification(&app, &version).await {
                        eprintln!("Failed to show update notification: {}", e);
                    }

                    // Auto-download and install
                    println!("Starting download...");
                    match download_and_install(update).await {
                        Ok(_) => {
                            println!("Update installed successfully!");
                            println!("Restarting app to apply update...");
                            restart_app();
                        }
                        Err(e) => {
                            eprintln!("FAILED to download/install update: {}", e);
                            eprintln!("Please download manually from GitHub Releases");
                        }
                    }
                }
                Ok(None) => {
                    println!("App is up to date (v{})", env!("CARGO_PKG_VERSION"));
                }
                Err(e) => {
                    eprintln!("Failed to check for updates: {}", e);
                    // Common errors:
                    // - Network error: can't reach github.com
                    // - Parse error: latest.json doesn't exist or is malformed
                    // - Signature mismatch: update signed with different key
                    if e.to_string().contains("404") || e.to_string().contains("Not Found") {
                        eprintln!("Hint: No release found on GitHub. Check if releases are published.");
                    } else if e.to_string().contains("signature") {
                        eprintln!("Hint: Signature mismatch. The update may be signed with a different key.");
                    }
                }
            }
        }
        Err(e) => {
            eprintln!("Updater not available: {}", e);
            eprintln!("Hint: Make sure 'updater' plugin is configured in tauri.conf.json");
        }
    }
    println!("=== Update check complete ===");
}

/// Show notification about available update
async fn show_update_notification(app: &AppHandle, version: &str) -> Result<(), String> {
    use tauri_plugin_notification::NotificationExt;

    app.notification()
        .builder()
        .title("Observer Update Available")
        .body(&format!(
            "Version {} is available. The update will be installed automatically.",
            version
        ))
        .show()
        .map_err(|e| e.to_string())?;

    Ok(())
}

/// Download and install update
async fn download_and_install(
    update: tauri_plugin_updater::Update,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    use std::sync::atomic::{AtomicUsize, Ordering};
    use std::sync::Arc;

    // Track download progress
    let downloaded = Arc::new(AtomicUsize::new(0));
    let downloaded_clone = downloaded.clone();

    update
        .download_and_install(
            move |chunk_length, content_length| {
                let prev = downloaded_clone.fetch_add(chunk_length, Ordering::SeqCst);
                let current = prev + chunk_length;
                if let Some(total) = content_length {
                    if total > 0 {
                        let percent = (current as f64 / total as f64) * 100.0;
                        println!("Downloading update: {:.1}%", percent);
                    }
                }
            },
            || {
                println!("Download complete, preparing to install...");
            },
        )
        .await?;

    println!("Update installed. Restart app to apply changes.");
    Ok(())
}
