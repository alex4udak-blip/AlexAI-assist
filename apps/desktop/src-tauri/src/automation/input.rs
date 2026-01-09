/// Input automation module for mouse and keyboard control
/// Uses enigo library with singleton pattern for optimization

use enigo::{Enigo, Settings, Mouse, Keyboard, Direction, Key, Button};
use once_cell::sync::Lazy;
use std::sync::Mutex;

/// Global singleton instance of Enigo for optimized performance
static ENIGO: Lazy<Mutex<Enigo>> = Lazy::new(|| {
    let settings = Settings::default();
    Mutex::new(Enigo::new(&settings).expect("Failed to create Enigo instance"))
});

/// Click at specific screen coordinates
pub fn click_at(x: i32, y: i32, button: MouseButton) -> Result<(), String> {
    let mut enigo = ENIGO.lock().map_err(|e| format!("Failed to lock enigo: {}", e))?;

    // Move to position
    enigo.move_mouse(x, y, enigo::Coordinate::Abs)
        .map_err(|e| format!("Failed to move mouse: {}", e))?;

    // Click
    let btn = match button {
        MouseButton::Left => Button::Left,
        MouseButton::Right => Button::Right,
        MouseButton::Middle => Button::Middle,
    };

    enigo.button(btn, Direction::Click)
        .map_err(|e| format!("Failed to click: {}", e))?;

    Ok(())
}

/// Type text at current cursor position
pub fn type_text(text: &str) -> Result<(), String> {
    let mut enigo = ENIGO.lock().map_err(|e| format!("Failed to lock enigo: {}", e))?;

    enigo.text(text)
        .map_err(|e| format!("Failed to type text: {}", e))?;

    Ok(())
}

/// Press a keyboard hotkey (e.g., Command+C, Control+V)
pub fn press_hotkey(modifiers: &[Modifier], key: &str) -> Result<(), String> {
    let mut enigo = ENIGO.lock().map_err(|e| format!("Failed to lock enigo: {}", e))?;

    // Press modifiers
    for modifier in modifiers {
        let mod_key = match modifier {
            Modifier::Control => Key::Control,
            Modifier::Alt => Key::Alt,
            Modifier::Shift => Key::Shift,
            Modifier::Meta => Key::Meta,
        };
        enigo.key(mod_key, Direction::Press)
            .map_err(|e| format!("Failed to press modifier: {}", e))?;
    }

    // Parse and press the main key
    let main_key = parse_key(key)?;
    enigo.key(main_key, Direction::Click)
        .map_err(|e| format!("Failed to press key: {}", e))?;

    // Release modifiers in reverse order
    for modifier in modifiers.iter().rev() {
        let mod_key = match modifier {
            Modifier::Control => Key::Control,
            Modifier::Alt => Key::Alt,
            Modifier::Shift => Key::Shift,
            Modifier::Meta => Key::Meta,
        };
        enigo.key(mod_key, Direction::Release)
            .map_err(|e| format!("Failed to release modifier: {}", e))?;
    }

    Ok(())
}

/// Move mouse to coordinates without clicking
pub fn move_mouse(x: i32, y: i32) -> Result<(), String> {
    let mut enigo = ENIGO.lock().map_err(|e| format!("Failed to lock enigo: {}", e))?;

    enigo.move_mouse(x, y, enigo::Coordinate::Abs)
        .map_err(|e| format!("Failed to move mouse: {}", e))?;

    Ok(())
}

/// Scroll the mouse wheel
pub fn scroll(amount: i32, axis: ScrollAxis) -> Result<(), String> {
    let mut enigo = ENIGO.lock().map_err(|e| format!("Failed to lock enigo: {}", e))?;

    match axis {
        ScrollAxis::Vertical => {
            enigo.scroll(amount, enigo::Axis::Vertical)
                .map_err(|e| format!("Failed to scroll: {}", e))?;
        }
        ScrollAxis::Horizontal => {
            enigo.scroll(amount, enigo::Axis::Horizontal)
                .map_err(|e| format!("Failed to scroll: {}", e))?;
        }
    }

    Ok(())
}

/// Parse string key name to enigo Key enum
fn parse_key(key_str: &str) -> Result<Key, String> {
    match key_str.to_lowercase().as_str() {
        "return" | "enter" => Ok(Key::Return),
        "tab" => Ok(Key::Tab),
        "space" => Ok(Key::Space),
        "backspace" => Ok(Key::Backspace),
        "escape" | "esc" => Ok(Key::Escape),
        "delete" => Ok(Key::Delete),
        "home" => Ok(Key::Home),
        "end" => Ok(Key::End),
        "pageup" => Ok(Key::PageUp),
        "pagedown" => Ok(Key::PageDown),
        "leftarrow" | "left" => Ok(Key::LeftArrow),
        "rightarrow" | "right" => Ok(Key::RightArrow),
        "uparrow" | "up" => Ok(Key::UpArrow),
        "downarrow" | "down" => Ok(Key::DownArrow),
        "f1" => Ok(Key::F1),
        "f2" => Ok(Key::F2),
        "f3" => Ok(Key::F3),
        "f4" => Ok(Key::F4),
        "f5" => Ok(Key::F5),
        "f6" => Ok(Key::F6),
        "f7" => Ok(Key::F7),
        "f8" => Ok(Key::F8),
        "f9" => Ok(Key::F9),
        "f10" => Ok(Key::F10),
        "f11" => Ok(Key::F11),
        "f12" => Ok(Key::F12),
        single if single.len() == 1 => {
            // Single character key
            Ok(Key::Unicode(single.chars().next().unwrap()))
        }
        _ => Err(format!("Unknown key: {}", key_str)),
    }
}

/// Mouse button type
#[derive(Debug, Clone, Copy)]
pub enum MouseButton {
    Left,
    Right,
    Middle,
}

/// Keyboard modifier keys
#[derive(Debug, Clone, Copy)]
pub enum Modifier {
    Control,
    Alt,
    Shift,
    Meta, // Command on macOS, Windows key on Windows
}

/// Scroll axis
#[derive(Debug, Clone, Copy)]
pub enum ScrollAxis {
    Vertical,
    Horizontal,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_key() {
        assert!(parse_key("return").is_ok());
        assert!(parse_key("a").is_ok());
        assert!(parse_key("invalid_key_name_xyz").is_err());
    }
}
