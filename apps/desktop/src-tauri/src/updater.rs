// Auto-update module for Observer desktop app

use tauri::AppHandle;
use tauri_plugin_updater::UpdaterExt;

/// Check for updates and prompt user if available
pub async fn check_for_updates(app: AppHandle) {
    // Wait a bit before checking to let app fully initialize
    tokio::time::sleep(tokio::time::Duration::from_secs(5)).await;

    match app.updater() {
        Ok(updater) => {
            match updater.check().await {
                Ok(Some(update)) => {
                    let version = update.version.clone();
                    println!("Update available: v{}", version);

                    // Show notification about update
                    if let Err(e) = show_update_notification(&app, &version).await {
                        eprintln!("Failed to show update notification: {}", e);
                    }

                    // Auto-download and install
                    match download_and_install(update).await {
                        Ok(_) => println!("Update downloaded successfully"),
                        Err(e) => eprintln!("Failed to download update: {}", e),
                    }
                }
                Ok(None) => {
                    println!("App is up to date");
                }
                Err(e) => {
                    eprintln!("Failed to check for updates: {}", e);
                }
            }
        }
        Err(e) => {
            eprintln!("Updater not available: {}", e);
        }
    }
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
