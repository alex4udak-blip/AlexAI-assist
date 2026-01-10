// Database module for persisting events to disk
use crate::collector::Event;
use rusqlite::{params, Connection, Result as SqliteResult};
use std::path::PathBuf;
use std::sync::{Arc, Mutex};

pub struct EventDatabase {
    conn: Arc<Mutex<Connection>>,
}

impl EventDatabase {
    /// Create new database connection and initialize schema
    pub fn new() -> SqliteResult<Self> {
        let db_path = Self::get_db_path();

        // Ensure parent directory exists
        if let Some(parent) = db_path.parent() {
            std::fs::create_dir_all(parent).ok();
        }

        let conn = Connection::open(&db_path)?;

        // Create events table if it doesn't exist
        conn.execute(
            "CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                device_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                app_name TEXT,
                window_title TEXT,
                url TEXT,
                data TEXT NOT NULL,
                category TEXT,
                browser_tab TEXT,
                messages TEXT,
                screenshot_path TEXT,
                system_metrics TEXT,
                typed_text TEXT,
                created_at INTEGER DEFAULT (strftime('%s', 'now'))
            )",
            [],
        )?;

        // Create index on created_at for efficient ordering
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at)",
            [],
        )?;

        Ok(Self {
            conn: Arc::new(Mutex::new(conn)),
        })
    }

    /// Get database file path
    fn get_db_path() -> PathBuf {
        dirs::config_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join("observer")
            .join("events.db")
    }

    /// Insert event into database
    pub fn insert_event(&self, event: &Event) -> SqliteResult<()> {
        let conn = self.conn.lock().unwrap();

        println!("[DB::insert_event] Inserting: {} | {}", event.id, event.app_name.as_deref().unwrap_or("?"));

        conn.execute(
            "INSERT INTO events (
                id, device_id, event_type, timestamp, app_name, window_title, url,
                data, category, browser_tab, messages, screenshot_path,
                system_metrics, typed_text
            ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14)",
            params![
                event.id,
                event.device_id,
                event.event_type,
                event.timestamp.to_rfc3339(),
                event.app_name,
                event.window_title,
                event.url,
                serde_json::to_string(&event.data).unwrap_or_default(),
                event.category,
                event.browser_tab.as_ref().and_then(|b| serde_json::to_string(b).ok()),
                event.messages.as_ref().and_then(|m| serde_json::to_string(m).ok()),
                event.screenshot_path,
                event.system_metrics.as_ref().and_then(|s| serde_json::to_string(s).ok()),
                event.typed_text,
            ],
        )?;

        Ok(())
    }

    /// Load all events from database, ordered by creation time
    pub fn load_all_events(&self) -> SqliteResult<Vec<Event>> {
        let conn = self.conn.lock().unwrap();

        let mut stmt = conn.prepare(
            "SELECT id, device_id, event_type, timestamp, app_name, window_title, url,
                    data, category, browser_tab, messages, screenshot_path,
                    system_metrics, typed_text
             FROM events
             ORDER BY created_at ASC"
        )?;

        let events = stmt.query_map([], |row| {
            let timestamp_str: String = row.get(3)?;
            let data_str: String = row.get(7)?;
            let browser_tab_str: Option<String> = row.get(9)?;
            let messages_str: Option<String> = row.get(10)?;
            let system_metrics_str: Option<String> = row.get(12)?;

            Ok(Event {
                id: row.get(0)?,
                device_id: row.get(1)?,
                event_type: row.get(2)?,
                timestamp: chrono::DateTime::parse_from_rfc3339(&timestamp_str)
                    .map(|dt| dt.with_timezone(&chrono::Utc))
                    .unwrap_or_else(|_| chrono::Utc::now()),
                app_name: row.get(4)?,
                window_title: row.get(5)?,
                url: row.get(6)?,
                data: serde_json::from_str(&data_str).unwrap_or(serde_json::json!({})),
                category: row.get(8)?,
                browser_tab: browser_tab_str.and_then(|s| serde_json::from_str(&s).ok()),
                messages: messages_str.and_then(|s| serde_json::from_str(&s).ok()),
                screenshot_path: row.get(11)?,
                system_metrics: system_metrics_str.and_then(|s| serde_json::from_str(&s).ok()),
                typed_text: row.get(13)?,
            })
        })?;

        events.collect()
    }

    /// Delete events by their IDs
    pub fn delete_events(&self, event_ids: &[String]) -> SqliteResult<()> {
        if event_ids.is_empty() {
            return Ok(());
        }

        let conn = self.conn.lock().unwrap();

        // Build placeholders for SQL IN clause
        let placeholders = event_ids.iter()
            .map(|_| "?")
            .collect::<Vec<_>>()
            .join(",");

        let query = format!("DELETE FROM events WHERE id IN ({})", placeholders);

        let mut stmt = conn.prepare(&query)?;
        let params: Vec<&dyn rusqlite::ToSql> = event_ids
            .iter()
            .map(|id| id as &dyn rusqlite::ToSql)
            .collect();

        stmt.execute(&params[..])?;

        Ok(())
    }

    /// Get count of events in database
    pub fn count(&self) -> SqliteResult<usize> {
        let conn = self.conn.lock().unwrap();
        let count: i64 = conn.query_row("SELECT COUNT(*) FROM events", [], |row| row.get(0))?;
        Ok(count as usize)
    }

    /// Clear all events from database (used for testing/debugging)
    #[allow(dead_code)]
    pub fn clear_all(&self) -> SqliteResult<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute("DELETE FROM events", [])?;
        Ok(())
    }
}
