// Auto-update module for Observer desktop app

use tauri::AppHandle;
use tauri_plugin_updater::UpdaterExt;

/// Apply post-update fixes and restart the application
fn restart_app() {
    if let Ok(exe) = std::env::current_exe() {
        println!("Applying post-update fixes...");

        // Get the .app bundle path (go up from executable)
        // /Applications/Observer.app/Contents/MacOS/observer-desktop -> /Applications/Observer.app
        #[cfg(target_os = "macos")]
        {
            let app_path = exe
                .parent() // MacOS
                .and_then(|p| p.parent()) // Contents
                .and_then(|p| p.parent()); // Observer.app

            if let Some(app_path) = app_path {
                let app_path_str = app_path.to_string_lossy();

                // Remove quarantine attribute
                println!("Removing quarantine: xattr -cr {}", app_path_str);
                let _ = std::process::Command::new("xattr")
                    .args(["-cr", &app_path_str])
                    .output();

                // Re-sign the app with ad-hoc signature
                println!(
                    "Re-signing app: codesign --force --deep --sign - {}",
                    app_path_str
                );
                let _ = std::process::Command::new("codesign")
                    .args(["--force", "--deep", "--sign", "-", &app_path_str])
                    .output();

                println!("Post-update fixes applied!");
            }
        }

        println!("Restarting app from: {:?}", exe);

        // Small delay to ensure signing completes
        std::thread::sleep(std::time::Duration::from_secs(1));

        // Spawn a new instance of the app
        let _ = std::process::Command::new(&exe).spawn();

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
