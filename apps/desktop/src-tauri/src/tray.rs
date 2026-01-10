use crate::sync::get_dashboard_url;
use std::sync::atomic::{AtomicBool, Ordering};
use tauri::{
    image::Image,
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    App, Manager,
};

/// Global flag to track window visibility (more reliable than is_visible() on macOS)
static WINDOW_VISIBLE: AtomicBool = AtomicBool::new(true);

/// Create a proper eye-shaped tray icon for macOS menu bar
/// Uses higher resolution (44x44) for Retina displays
fn create_eye_icon() -> (Vec<u8>, u32, u32) {
    let size = 44u32; // @2x for Retina
    let mut rgba = vec![0u8; (size * size * 4) as usize];
    let center_x = size as f32 / 2.0;
    let center_y = size as f32 / 2.0;
    let scale = size as f32 / 22.0; // Scale factor for Retina

    for y in 0..size {
        for x in 0..size {
            let idx = ((y * size + x) * 4) as usize;
            let px = x as f32;
            let py = y as f32;
            let dx = px - center_x;
            let dy = py - center_y;

            // Eye shape using almond/leaf curve (scaled for @2x)
            let norm_x = dx / (size as f32 / 2.0 - 4.0 * scale);
            let eye_height = 7.0 * scale * (1.0 - norm_x * norm_x).max(0.0);

            // Pupil and iris (scaled)
            let pupil_dist = (dx * dx + dy * dy).sqrt();
            let pupil_radius = 5.0 * scale;
            let iris_radius = 8.0 * scale;

            // For macOS template icons: use black with varying alpha
            // This allows macOS to properly invert colors for dark/light mode
            if pupil_dist <= pupil_radius {
                // Pupil - solid black
                rgba[idx] = 0;        // R
                rgba[idx + 1] = 0;    // G
                rgba[idx + 2] = 0;    // B
                rgba[idx + 3] = 255;  // A (fully opaque)
            } else if pupil_dist <= iris_radius && dy.abs() < eye_height {
                // Iris - semi-transparent black
                rgba[idx] = 0;
                rgba[idx + 1] = 0;
                rgba[idx + 2] = 0;
                rgba[idx + 3] = 180;  // Semi-opaque
            } else if dy.abs() < eye_height && norm_x.abs() < 1.0 {
                // Eye white area - light gray (will show as white in menu bar)
                rgba[idx] = 0;
                rgba[idx + 1] = 0;
                rgba[idx + 2] = 0;
                rgba[idx + 3] = 60;   // Very transparent
            } else if dy.abs() < eye_height + 2.0 * scale && norm_x.abs() < 1.05 {
                // Eye outline - solid black
                rgba[idx] = 0;
                rgba[idx + 1] = 0;
                rgba[idx + 2] = 0;
                rgba[idx + 3] = 255;  // Fully opaque
            } else {
                // Transparent
                rgba[idx] = 0;
                rgba[idx + 1] = 0;
                rgba[idx + 2] = 0;
                rgba[idx + 3] = 0;
            }
        }
    }

    (rgba, size, size)
}

pub fn create_tray(app: &App) -> Result<(), Box<dyn std::error::Error>> {
    let quit = MenuItem::with_id(app, "quit", "Выйти из Observer", true, None::<&str>)?;
    let show = MenuItem::with_id(app, "show", "Показать окно", true, None::<&str>)?;
    let dashboard = MenuItem::with_id(app, "dashboard", "Открыть дашборд", true, None::<&str>)?;
    let separator = MenuItem::with_id(app, "sep", "─────────────", false, None::<&str>)?;

    let menu = Menu::with_items(app, &[&show, &dashboard, &separator, &quit])?;

    // Create eye-shaped tray icon
    let (rgba, width, height) = create_eye_icon();
    let icon = Image::new_owned(rgba, width, height);

    let tray = TrayIconBuilder::new()
        .icon(icon)
        .icon_as_template(true) // Enable template mode for proper macOS light/dark mode support
        .menu(&menu)
        .show_menu_on_left_click(false)
        .tooltip("Observer - Activity Tracker")
        .on_menu_event(move |app, event| match event.id.as_ref() {
            "quit" => {
                app.exit(0);
            }
            "show" => {
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.show();
                    let _ = window.set_focus();
                }
            }
            "dashboard" => {
                let _ = open::that(get_dashboard_url());
            }
            _ => {}
        })
        .on_tray_icon_event(|tray, event| {
            match event {
                TrayIconEvent::Click {
                    button: MouseButton::Left,
                    button_state: MouseButtonState::Up,
                    position,
                    ..
                } => {
                    println!("Tray icon clicked at position: {:?}", position);
                    let app = tray.app_handle();
                    if let Some(window) = app.get_webview_window("main") {
                        // Use our atomic flag instead of is_visible() for reliable state tracking
                        let is_visible = WINDOW_VISIBLE.load(Ordering::SeqCst);
                        println!("Window visible (tracked): {}", is_visible);

                        if is_visible {
                            println!("Hiding window");
                            let _ = window.hide();
                            WINDOW_VISIBLE.store(false, Ordering::SeqCst);
                        } else {
                            println!("Showing window");

                            // Position window near tray icon on macOS
                            #[cfg(target_os = "macos")]
                            {
                                // Get window size
                                let size = window.outer_size().unwrap_or(tauri::PhysicalSize { width: 320, height: 400 });
                                // Position below tray icon, centered
                                let x = position.x as i32 - (size.width as i32 / 2);
                                let y = position.y as i32 + 5; // Small offset below tray
                                println!("Setting window position to ({}, {})", x, y);
                                let _ = window.set_position(tauri::PhysicalPosition::new(x, y));
                            }

                            let _ = window.show();
                            let _ = window.set_focus();
                            WINDOW_VISIBLE.store(true, Ordering::SeqCst);
                            println!("Window show and focus called");
                        }
                    } else {
                        println!("ERROR: Could not find 'main' window!");
                    }
                }
                TrayIconEvent::DoubleClick { .. } => {
                    println!("Tray icon double clicked");
                }
                _ => {}
            }
        })
        .build(app)?;

    // Store tray in app state to prevent it from being dropped
    app.manage(TrayState { _tray: tray });

    // Show window on first launch for better UX
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.show();
        let _ = window.set_focus();
    }

    Ok(())
}

/// State to keep tray icon alive
pub struct TrayState {
    _tray: tauri::tray::TrayIcon,
}

/// Set window visibility flag (call this when window is shown/hidden from frontend)
pub fn set_window_visible(visible: bool) {
    WINDOW_VISIBLE.store(visible, Ordering::SeqCst);
    println!("Window visibility flag set to: {}", visible);
}
