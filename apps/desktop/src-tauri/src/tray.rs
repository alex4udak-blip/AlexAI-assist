use crate::sync::get_dashboard_url;
use tauri::{
    image::Image,
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    App, Manager,
};

pub fn create_tray(app: &App) -> Result<(), Box<dyn std::error::Error>> {
    let quit = MenuItem::with_id(app, "quit", "Выйти из Observer", true, None::<&str>)?;
    let show = MenuItem::with_id(app, "show", "Показать окно", true, None::<&str>)?;
    let dashboard = MenuItem::with_id(app, "dashboard", "Открыть дашборд", true, None::<&str>)?;
    let separator = MenuItem::with_id(app, "sep", "─────────────", false, None::<&str>)?;

    let menu = Menu::with_items(app, &[&show, &dashboard, &separator, &quit])?;

    // Create a simple 22x22 colored tray icon (standard macOS menu bar size)
    // Using indigo color (#6366f1) as a circle
    let size = 22u32;
    let mut rgba = vec![0u8; (size * size * 4) as usize];
    let center = size as f32 / 2.0;
    let radius = size as f32 / 2.0 - 1.0;

    for y in 0..size {
        for x in 0..size {
            let idx = ((y * size + x) * 4) as usize;
            let dx = x as f32 - center;
            let dy = y as f32 - center;
            let dist = (dx * dx + dy * dy).sqrt();

            if dist <= radius {
                // Inside circle - indigo color
                rgba[idx] = 99;      // R
                rgba[idx + 1] = 102; // G
                rgba[idx + 2] = 241; // B
                rgba[idx + 3] = 255; // A
            } else {
                // Outside circle - transparent
                rgba[idx] = 0;
                rgba[idx + 1] = 0;
                rgba[idx + 2] = 0;
                rgba[idx + 3] = 0;
            }
        }
    }

    let icon = Image::new_owned(rgba, size, size);

    let tray = TrayIconBuilder::new()
        .icon(icon)
        .icon_as_template(false)
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
                        let is_visible = window.is_visible().unwrap_or(false);
                        println!("Window visible: {}", is_visible);

                        if is_visible {
                            println!("Hiding window");
                            let _ = window.hide();
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
