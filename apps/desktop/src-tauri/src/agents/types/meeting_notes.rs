//! Meeting Notes Agent
//!
//! Agent for summarizing meetings from audio transcriptions,
//! extracting action items, and saving notes to markdown files.

use super::AgentType;
use crate::agents::prompts;
use chrono::{DateTime, Local};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;

/// Apps that indicate a video call
const VIDEO_CALL_APPS: &[&str] = &[
    "Zoom",
    "zoom.us",
    "Google Meet",
    "meet.google.com",
    "Microsoft Teams",
    "Teams",
    "Slack",
    "Slack huddle",
    "Discord",
    "FaceTime",
    "Webex",
    "GoToMeeting",
];

/// Patterns indicating meeting end
const MEETING_END_PATTERNS: &[&str] = &[
    "meeting ended",
    "call ended",
    "you left the meeting",
    "meeting has ended",
    "the meeting ended",
    "call disconnected",
    "left the call",
    "meeting ended for everyone",
    "has left the meeting",
    "meeting was ended",
    "goodbye",
    "thanks everyone",
    "talk to you later",
    "the host ended the meeting",
];

/// Action item extracted from meeting
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActionItem {
    /// Person responsible for the action
    pub assignee: String,
    /// Task description
    pub task: String,
    /// Deadline if specified
    pub deadline: Option<String>,
    /// Priority level (optional)
    pub priority: Option<String>,
}

/// Meeting participant
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Participant {
    /// Participant name
    pub name: String,
    /// Role if known (e.g., "host", "presenter")
    pub role: Option<String>,
}

/// Parsed meeting data
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MeetingData {
    /// Meeting title or topic
    pub title: String,
    /// List of participants
    pub participants: Vec<String>,
    /// Meeting summary
    pub summary: String,
    /// Key decisions made during the meeting
    pub key_decisions: Vec<String>,
    /// Action items extracted from the meeting
    pub action_items: Vec<ActionItem>,
    /// Meeting date and time
    pub timestamp: DateTime<Local>,
    /// Duration in minutes if known
    pub duration_minutes: Option<u32>,
    /// Source application (Zoom, Meet, etc.)
    pub source_app: Option<String>,
}

impl Default for MeetingData {
    fn default() -> Self {
        Self {
            title: String::new(),
            participants: Vec::new(),
            summary: String::new(),
            key_decisions: Vec::new(),
            action_items: Vec::new(),
            timestamp: Local::now(),
            duration_minutes: None,
            source_app: None,
        }
    }
}

/// Meeting Notes Agent for summarizing meetings and extracting action items
pub struct MeetingNotesAgent {
    /// System prompt for the agent
    pub system_prompt: String,
    /// Track recently closed apps to detect meeting end
    last_known_app: Option<String>,
}

impl MeetingNotesAgent {
    /// Create a new Meeting Notes Agent
    pub fn new() -> Self {
        Self {
            system_prompt: prompts::load_meeting_notes_prompt(),
            last_known_app: None,
        }
    }

    /// Parse audio transcription into MeetingData structure
    ///
    /// # Arguments
    /// * `audio_text` - Raw audio transcription from Screenpipe
    ///
    /// # Returns
    /// Parsed MeetingData with extracted information
    pub fn parse_transcript(&self, audio_text: &str) -> MeetingData {
        let mut meeting = MeetingData::default();

        // Extract participants from common patterns
        meeting.participants = self.extract_participants(audio_text);

        // Extract action items
        meeting.action_items = self.extract_action_items(audio_text);

        // Try to extract title from first meaningful sentence
        meeting.title = self.extract_title(audio_text);

        // Generate summary (first ~200 chars of cleaned text)
        meeting.summary = self.generate_summary(audio_text);

        // Extract key decisions
        meeting.key_decisions = self.extract_decisions(audio_text);

        meeting
    }

    /// Extract action items from meeting text
    ///
    /// Looks for patterns like:
    /// - "I will...", "We need to...", "You should..."
    /// - "@name will do..."
    /// - "Action item: ..."
    /// - "TODO: ..."
    /// - "by Friday", "by next week" (deadline patterns)
    ///
    /// # Arguments
    /// * `text` - Meeting transcription text
    ///
    /// # Returns
    /// Vector of extracted ActionItems
    pub fn extract_action_items(&self, text: &str) -> Vec<ActionItem> {
        let mut items = Vec::new();
        let text_lower = text.to_lowercase();

        // Common action patterns
        let action_patterns = [
            ("i will ", "Speaker"),
            ("i'll ", "Speaker"),
            ("we need to ", "Team"),
            ("we should ", "Team"),
            ("you will ", "Assignee"),
            ("you should ", "Assignee"),
            ("action item:", "TBD"),
            ("todo:", "TBD"),
            ("task:", "TBD"),
            ("let's ", "Team"),
            ("please ", "Assignee"),
            ("can you ", "Assignee"),
            ("could you ", "Assignee"),
            ("make sure to ", "Assignee"),
        ];

        for (pattern, default_assignee) in action_patterns {
            let mut search_pos = 0;
            while let Some(pos) = text_lower[search_pos..].find(pattern) {
                let abs_pos = search_pos + pos;
                let task_start = abs_pos + pattern.len();

                // Extract task until end of sentence
                if let Some(task) = self.extract_until_sentence_end(&text[task_start..]) {
                    let deadline = self.extract_deadline(&task);

                    items.push(ActionItem {
                        assignee: default_assignee.to_string(),
                        task: task.trim().to_string(),
                        deadline,
                        priority: None,
                    });
                }

                search_pos = task_start;
            }
        }

        // Deduplicate similar action items
        self.deduplicate_actions(items)
    }

    /// Save meeting notes to a markdown file
    ///
    /// # Arguments
    /// * `meeting` - MeetingData to save
    /// * `path` - File path for the markdown file
    ///
    /// # Returns
    /// Ok(()) on success, Err with description on failure
    pub fn save_notes(&self, meeting: &MeetingData, path: &str) -> Result<(), String> {
        let markdown = self.format_as_markdown(meeting);

        // Ensure parent directory exists
        if let Some(parent) = Path::new(path).parent() {
            fs::create_dir_all(parent).map_err(|e| format!("Failed to create directory: {}", e))?;
        }

        fs::write(path, markdown).map_err(|e| format!("Failed to write meeting notes: {}", e))?;

        Ok(())
    }

    /// Format MeetingData as markdown
    fn format_as_markdown(&self, meeting: &MeetingData) -> String {
        let mut md = String::new();

        // Title
        md.push_str(&format!(
            "# {}\n\n",
            if meeting.title.is_empty() {
                "Meeting Notes"
            } else {
                &meeting.title
            }
        ));

        // Metadata
        md.push_str(&format!(
            "**Date:** {}\n",
            meeting.timestamp.format("%Y-%m-%d %H:%M")
        ));
        if let Some(duration) = meeting.duration_minutes {
            md.push_str(&format!("**Duration:** {} minutes\n", duration));
        }
        if let Some(app) = &meeting.source_app {
            md.push_str(&format!("**Platform:** {}\n", app));
        }
        md.push('\n');

        // Participants
        if !meeting.participants.is_empty() {
            md.push_str("## Participants\n\n");
            for participant in &meeting.participants {
                md.push_str(&format!("- {}\n", participant));
            }
            md.push('\n');
        }

        // Summary
        if !meeting.summary.is_empty() {
            md.push_str("## Summary\n\n");
            md.push_str(&meeting.summary);
            md.push_str("\n\n");
        }

        // Key Decisions
        if !meeting.key_decisions.is_empty() {
            md.push_str("## Key Decisions\n\n");
            for (i, decision) in meeting.key_decisions.iter().enumerate() {
                md.push_str(&format!("{}. {}\n", i + 1, decision));
            }
            md.push('\n');
        }

        // Action Items
        if !meeting.action_items.is_empty() {
            md.push_str("## Action Items\n\n");
            md.push_str("| Assignee | Task | Deadline |\n");
            md.push_str("|----------|------|----------|\n");
            for item in &meeting.action_items {
                let deadline = item.deadline.as_deref().unwrap_or("-");
                md.push_str(&format!(
                    "| {} | {} | {} |\n",
                    item.assignee, item.task, deadline
                ));
            }
            md.push('\n');
        }

        md
    }

    /// Extract participants from text
    fn extract_participants(&self, text: &str) -> Vec<String> {
        let mut participants = Vec::new();
        let text_lower = text.to_lowercase();

        // Look for "joined" patterns
        let join_patterns = ["joined the meeting", "joined the call", "has joined"];
        for pattern in join_patterns {
            // Simple extraction: look for words before the pattern
            if let Some(pos) = text_lower.find(pattern) {
                if pos > 0 {
                    // Get previous word(s) as participant name
                    let before = &text[..pos].trim();
                    if let Some(last_word) = before.split_whitespace().last() {
                        let name = last_word.trim_matches(|c: char| !c.is_alphanumeric());
                        if !name.is_empty() && name.len() > 1 {
                            participants.push(name.to_string());
                        }
                    }
                }
            }
        }

        // Deduplicate
        participants.sort();
        participants.dedup();
        participants
    }

    /// Extract title from transcription
    fn extract_title(&self, text: &str) -> String {
        // Look for "about", "discuss", "meeting for" patterns
        let title_patterns = [
            ("let's talk about ", 50),
            ("we're here to discuss ", 50),
            ("meeting about ", 50),
            ("agenda for today:", 100),
            ("topic:", 50),
        ];

        let text_lower = text.to_lowercase();
        for (pattern, max_len) in title_patterns {
            if let Some(pos) = text_lower.find(pattern) {
                let start = pos + pattern.len();
                if let Some(title) = self.extract_until_sentence_end(&text[start..]) {
                    let title = title.trim();
                    if title.len() <= max_len {
                        return title.to_string();
                    }
                }
            }
        }

        String::new()
    }

    /// Generate a brief summary
    fn generate_summary(&self, text: &str) -> String {
        // Clean and truncate for summary
        let cleaned: String = text
            .chars()
            .filter(|c| !c.is_control() || *c == ' ')
            .collect();

        let cleaned = cleaned.trim();
        if cleaned.len() <= 500 {
            cleaned.to_string()
        } else {
            // Find a good break point
            if let Some(break_pos) = cleaned[..500].rfind(". ") {
                format!("{}...", &cleaned[..break_pos + 1])
            } else {
                format!("{}...", &cleaned[..497])
            }
        }
    }

    /// Extract key decisions from text
    fn extract_decisions(&self, text: &str) -> Vec<String> {
        let mut decisions = Vec::new();
        let text_lower = text.to_lowercase();

        let decision_patterns = [
            "we decided to ",
            "we agreed to ",
            "the decision is ",
            "we will go with ",
            "we're going with ",
            "final decision:",
            "agreed:",
            "consensus:",
        ];

        for pattern in decision_patterns {
            if let Some(pos) = text_lower.find(pattern) {
                let start = pos + pattern.len();
                if let Some(decision) = self.extract_until_sentence_end(&text[start..]) {
                    let decision = decision.trim().to_string();
                    if !decision.is_empty() {
                        decisions.push(decision);
                    }
                }
            }
        }

        decisions
    }

    /// Extract text until end of sentence
    fn extract_until_sentence_end(&self, text: &str) -> Option<String> {
        let end_markers = ['.', '!', '?', '\n'];

        for (i, c) in text.char_indices() {
            if end_markers.contains(&c) {
                if i > 0 {
                    return Some(text[..i].to_string());
                }
                break;
            }
            // Limit extraction length
            if i > 200 {
                return Some(text[..i].to_string());
            }
        }

        // If no end marker found, take first 100 chars
        if text.len() > 0 {
            let end = text
                .char_indices()
                .nth(100)
                .map(|(i, _)| i)
                .unwrap_or(text.len());
            return Some(text[..end].to_string());
        }

        None
    }

    /// Extract deadline from task text
    fn extract_deadline(&self, text: &str) -> Option<String> {
        let text_lower = text.to_lowercase();

        let deadline_patterns = [
            ("by friday", "Friday"),
            ("by monday", "Monday"),
            ("by tuesday", "Tuesday"),
            ("by wednesday", "Wednesday"),
            ("by thursday", "Thursday"),
            ("by saturday", "Saturday"),
            ("by sunday", "Sunday"),
            ("by tomorrow", "Tomorrow"),
            ("by next week", "Next week"),
            ("by end of day", "EOD"),
            ("by eod", "EOD"),
            ("by end of week", "EOW"),
            ("by eow", "EOW"),
            ("asap", "ASAP"),
            ("urgent", "ASAP"),
        ];

        for (pattern, deadline) in deadline_patterns {
            if text_lower.contains(pattern) {
                return Some(deadline.to_string());
            }
        }

        None
    }

    /// Deduplicate similar action items
    fn deduplicate_actions(&self, items: Vec<ActionItem>) -> Vec<ActionItem> {
        let mut unique = Vec::new();

        for item in items {
            let is_duplicate = unique.iter().any(|existing: &ActionItem| {
                // Check for similar tasks (simple similarity)
                let task_lower = item.task.to_lowercase();
                let existing_lower = existing.task.to_lowercase();

                task_lower == existing_lower
                    || (task_lower.len() > 10 && existing_lower.contains(&task_lower[..10]))
            });

            if !is_duplicate {
                unique.push(item);
            }
        }

        unique
    }

    /// Check if a video call app was recently active
    fn is_video_call_app(app_name: &str) -> bool {
        let app_lower = app_name.to_lowercase();
        VIDEO_CALL_APPS
            .iter()
            .any(|app| app_lower.contains(&app.to_lowercase()))
    }

    /// Check if text indicates meeting has ended
    fn has_meeting_end_indicator(text: &str) -> bool {
        let text_lower = text.to_lowercase();
        MEETING_END_PATTERNS
            .iter()
            .any(|pattern| text_lower.contains(pattern))
    }

    /// Update last known app (for tracking app switches)
    pub fn update_last_app(&mut self, app_name: &str) {
        self.last_known_app = Some(app_name.to_string());
    }

    /// Check if we just switched away from a video call app
    pub fn just_left_video_call(&self, current_app: &str) -> bool {
        if let Some(last_app) = &self.last_known_app {
            // Previously in video call app, now in different app
            Self::is_video_call_app(last_app) && !Self::is_video_call_app(current_app)
        } else {
            false
        }
    }

    /// Generate default notes path
    pub fn default_notes_path() -> String {
        let now = Local::now();
        let home = dirs::home_dir().unwrap_or_default();
        let notes_dir = home.join("Documents").join("MeetingNotes");
        let filename = format!("meeting_{}.md", now.format("%Y%m%d_%H%M%S"));
        notes_dir.join(filename).to_string_lossy().to_string()
    }
}

impl Default for MeetingNotesAgent {
    fn default() -> Self {
        Self::new()
    }
}

impl AgentType for MeetingNotesAgent {
    fn name(&self) -> &'static str {
        "Meeting Notes"
    }

    fn system_prompt(&self) -> &str {
        &self.system_prompt
    }

    fn should_handle(&self, app_name: &str, text: &str) -> bool {
        // Check if current app is a video call app with meeting end indicators
        if Self::is_video_call_app(app_name) && Self::has_meeting_end_indicator(text) {
            return true;
        }

        // Check for explicit meeting end patterns in text
        let text_lower = text.to_lowercase();
        if text_lower.contains("meeting ended") || text_lower.contains("call ended") {
            return true;
        }

        // Check if app contains video call app names
        let app_lower = app_name.to_lowercase();
        let is_meeting_app = app_lower.contains("zoom")
            || app_lower.contains("meet")
            || app_lower.contains("teams")
            || app_lower.contains("slack huddle");

        if is_meeting_app && Self::has_meeting_end_indicator(text) {
            return true;
        }

        false
    }

    fn max_iterations(&self) -> u32 {
        5 // Meeting notes don't need many iterations
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_should_handle_zoom_meeting_ended() {
        let agent = MeetingNotesAgent::new();
        assert!(agent.should_handle("Zoom", "The meeting ended at 3pm"));
        assert!(agent.should_handle("zoom.us", "call ended"));
    }

    #[test]
    fn test_should_handle_google_meet() {
        let agent = MeetingNotesAgent::new();
        assert!(agent.should_handle("Google Meet", "You left the meeting"));
        assert!(agent.should_handle("meet.google.com", "meeting has ended"));
    }

    #[test]
    fn test_should_handle_teams() {
        let agent = MeetingNotesAgent::new();
        assert!(agent.should_handle("Microsoft Teams", "call ended"));
        assert!(agent.should_handle("Teams", "meeting ended"));
    }

    #[test]
    fn test_should_not_handle_regular_app() {
        let agent = MeetingNotesAgent::new();
        assert!(!agent.should_handle("Chrome", "browsing web"));
        assert!(!agent.should_handle("VS Code", "writing code"));
    }

    #[test]
    fn test_extract_action_items() {
        let agent = MeetingNotesAgent::new();
        let text = "I will send the report by Friday. We need to review the design.";
        let items = agent.extract_action_items(text);

        assert!(!items.is_empty());
        assert!(items.iter().any(|i| i.task.contains("send the report")));
    }

    #[test]
    fn test_extract_deadline() {
        let agent = MeetingNotesAgent::new();

        assert_eq!(
            agent.extract_deadline("send report by friday"),
            Some("Friday".to_string())
        );
        assert_eq!(
            agent.extract_deadline("do it by tomorrow"),
            Some("Tomorrow".to_string())
        );
        assert_eq!(
            agent.extract_deadline("finish by eod"),
            Some("EOD".to_string())
        );
        assert_eq!(agent.extract_deadline("no deadline mentioned"), None);
    }

    #[test]
    fn test_format_as_markdown() {
        let agent = MeetingNotesAgent::new();
        let meeting = MeetingData {
            title: "Sprint Planning".to_string(),
            participants: vec!["Alice".to_string(), "Bob".to_string()],
            summary: "Discussed sprint goals".to_string(),
            key_decisions: vec!["Focus on feature X".to_string()],
            action_items: vec![ActionItem {
                assignee: "Alice".to_string(),
                task: "Create design doc".to_string(),
                deadline: Some("Friday".to_string()),
                priority: None,
            }],
            timestamp: Local::now(),
            duration_minutes: Some(60),
            source_app: Some("Zoom".to_string()),
        };

        let markdown = agent.format_as_markdown(&meeting);

        assert!(markdown.contains("# Sprint Planning"));
        assert!(markdown.contains("Alice"));
        assert!(markdown.contains("Bob"));
        assert!(markdown.contains("Create design doc"));
        assert!(markdown.contains("Friday"));
    }

    #[test]
    fn test_is_video_call_app() {
        assert!(MeetingNotesAgent::is_video_call_app("Zoom"));
        assert!(MeetingNotesAgent::is_video_call_app("zoom.us"));
        assert!(MeetingNotesAgent::is_video_call_app("Google Meet"));
        assert!(MeetingNotesAgent::is_video_call_app("Microsoft Teams"));
        assert!(MeetingNotesAgent::is_video_call_app("Slack"));
        assert!(!MeetingNotesAgent::is_video_call_app("Chrome"));
        assert!(!MeetingNotesAgent::is_video_call_app("VS Code"));
    }

    #[test]
    fn test_has_meeting_end_indicator() {
        assert!(MeetingNotesAgent::has_meeting_end_indicator(
            "The meeting ended"
        ));
        assert!(MeetingNotesAgent::has_meeting_end_indicator(
            "call ended at 3pm"
        ));
        assert!(MeetingNotesAgent::has_meeting_end_indicator(
            "You left the meeting"
        ));
        assert!(!MeetingNotesAgent::has_meeting_end_indicator(
            "Meeting in progress"
        ));
    }

    #[test]
    fn test_parse_transcript() {
        let agent = MeetingNotesAgent::new();
        let transcript = "John joined the meeting. Let's talk about the new feature. \
                          We decided to use React. I will create the prototype by Friday.";

        let meeting = agent.parse_transcript(transcript);

        // Check that parsing works
        assert!(
            !meeting.action_items.is_empty()
                || !meeting.key_decisions.is_empty()
                || !meeting.participants.is_empty()
        );
    }
}
