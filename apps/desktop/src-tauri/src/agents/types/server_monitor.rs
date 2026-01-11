//! Server Monitor Agent
//!
//! Monitors server health, responds to alerts, and can restart failed services.
//! Designed for Railway deployments but adaptable to other platforms.

use super::AgentType;
use crate::agents::prompts;
use serde::{Deserialize, Serialize};
use std::process::Command;
use std::time::{Duration, Instant};

/// Default check interval in seconds (5 minutes)
const DEFAULT_CHECK_INTERVAL_SECS: u64 = 300;

/// Patterns that indicate server issues
const ALERT_PATTERNS: &[&str] = &[
    "503",
    "502",
    "500",
    "connection refused",
    "timeout",
    "timed out",
    "ECONNREFUSED",
    "ETIMEDOUT",
    "service unavailable",
    "bad gateway",
    "internal server error",
    "health check failed",
    "unhealthy",
    "down",
    "crashed",
    "OOMKilled",
    "memory limit",
    "cpu throttling",
];

/// Health status of an endpoint
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum HealthStatus {
    /// Service is healthy (2xx response)
    Healthy,
    /// Service is degraded (slow response or non-critical errors)
    Degraded {
        reason: String,
        response_time_ms: u64,
    },
    /// Service is unhealthy (5xx, timeout, connection refused)
    Unhealthy {
        reason: String,
        status_code: Option<u16>,
    },
    /// Could not determine status
    Unknown { reason: String },
}

impl HealthStatus {
    /// Check if status indicates a problem
    pub fn is_problem(&self) -> bool {
        matches!(
            self,
            HealthStatus::Unhealthy { .. } | HealthStatus::Unknown { .. }
        )
    }

    /// Check if status is degraded
    pub fn is_degraded(&self) -> bool {
        matches!(self, HealthStatus::Degraded { .. })
    }

    /// Get status as string for logging
    pub fn as_str(&self) -> &'static str {
        match self {
            HealthStatus::Healthy => "healthy",
            HealthStatus::Degraded { .. } => "degraded",
            HealthStatus::Unhealthy { .. } => "unhealthy",
            HealthStatus::Unknown { .. } => "unknown",
        }
    }
}

/// Server Monitor Agent for health monitoring and alerting
#[derive(Debug, Clone)]
pub struct ServerMonitorAgent {
    /// System prompt for Claude
    system_prompt: String,
    /// Check interval in seconds (default 300 = 5 min)
    check_interval_secs: u64,
    /// Endpoints to monitor
    endpoints: Vec<String>,
    /// Last check timestamp
    last_check: Option<Instant>,
    /// Consecutive failure counts per endpoint
    failure_counts: Vec<u32>,
}

impl ServerMonitorAgent {
    /// Create new Server Monitor Agent with default settings
    pub fn new() -> Self {
        Self {
            system_prompt: prompts::load_server_monitor_prompt(),
            check_interval_secs: DEFAULT_CHECK_INTERVAL_SECS,
            endpoints: Vec::new(),
            last_check: None,
            failure_counts: Vec::new(),
        }
    }

    /// Create with custom configuration
    pub fn with_config(check_interval_secs: u64, endpoints: Vec<String>) -> Self {
        let failure_counts = vec![0; endpoints.len()];
        Self {
            system_prompt: prompts::load_server_monitor_prompt(),
            check_interval_secs,
            endpoints,
            last_check: None,
            failure_counts,
        }
    }

    /// Add endpoint to monitor
    pub fn add_endpoint(&mut self, endpoint: &str) {
        self.endpoints.push(endpoint.to_string());
        self.failure_counts.push(0);
    }

    /// Remove endpoint from monitoring
    pub fn remove_endpoint(&mut self, endpoint: &str) {
        if let Some(idx) = self.endpoints.iter().position(|e| e == endpoint) {
            self.endpoints.remove(idx);
            self.failure_counts.remove(idx);
        }
    }

    /// Get monitored endpoints
    pub fn endpoints(&self) -> &[String] {
        &self.endpoints
    }

    /// Set check interval
    pub fn set_check_interval(&mut self, secs: u64) {
        self.check_interval_secs = secs;
    }

    /// Get check interval
    pub fn check_interval_secs(&self) -> u64 {
        self.check_interval_secs
    }

    /// Check if scheduled check is due
    pub fn is_check_due(&self) -> bool {
        match self.last_check {
            Some(last) => last.elapsed() >= Duration::from_secs(self.check_interval_secs),
            None => true, // First check is always due
        }
    }

    /// Record check performed
    pub fn record_check(&mut self) {
        self.last_check = Some(Instant::now());
    }

    /// Check health of a single endpoint
    pub fn check_endpoint_health(&self, url: &str) -> HealthStatus {
        let start = Instant::now();

        // Use curl to check endpoint health
        let output = Command::new("curl")
            .args([
                "-s",
                "-o",
                "/dev/null",
                "-w",
                "%{http_code}",
                "--connect-timeout",
                "5",
                "--max-time",
                "10",
                url,
            ])
            .output();

        let response_time_ms = start.elapsed().as_millis() as u64;

        match output {
            Ok(output) => {
                let status_str = String::from_utf8_lossy(&output.stdout);
                match status_str.trim().parse::<u16>() {
                    Ok(status_code) => {
                        if (200..300).contains(&status_code) {
                            // Check if response time is too slow (>3 seconds = degraded)
                            if response_time_ms > 3000 {
                                HealthStatus::Degraded {
                                    reason: format!("Slow response: {}ms", response_time_ms),
                                    response_time_ms,
                                }
                            } else {
                                HealthStatus::Healthy
                            }
                        } else if (500..600).contains(&status_code) {
                            HealthStatus::Unhealthy {
                                reason: format!("Server error: HTTP {}", status_code),
                                status_code: Some(status_code),
                            }
                        } else if status_code == 0 {
                            HealthStatus::Unhealthy {
                                reason: "Connection refused or timeout".to_string(),
                                status_code: None,
                            }
                        } else {
                            HealthStatus::Degraded {
                                reason: format!("Non-success status: HTTP {}", status_code),
                                response_time_ms,
                            }
                        }
                    }
                    Err(_) => HealthStatus::Unknown {
                        reason: format!("Invalid status code response: {}", status_str),
                    },
                }
            }
            Err(e) => HealthStatus::Unhealthy {
                reason: format!("Failed to execute curl: {}", e),
                status_code: None,
            },
        }
    }

    /// Check health of all endpoints
    pub fn check_all_endpoints(&mut self) -> Vec<(String, HealthStatus)> {
        self.record_check();

        let mut results = Vec::new();
        for (idx, endpoint) in self.endpoints.clone().iter().enumerate() {
            let status = self.check_endpoint_health(endpoint);

            // Update failure counts
            if status.is_problem() {
                if idx < self.failure_counts.len() {
                    self.failure_counts[idx] += 1;
                }
            } else if idx < self.failure_counts.len() {
                self.failure_counts[idx] = 0;
            }

            results.push((endpoint.clone(), status));
        }
        results
    }

    /// Get server logs for a service (Railway)
    pub fn get_server_logs(&self, service: &str) -> String {
        let output = Command::new("railway")
            .args(["logs", "--service", service, "-n", "100"])
            .output();

        match output {
            Ok(output) => {
                let stdout = String::from_utf8_lossy(&output.stdout);
                let stderr = String::from_utf8_lossy(&output.stderr);
                if output.status.success() {
                    stdout.to_string()
                } else {
                    format!("Error getting logs: {}\n{}", stderr, stdout)
                }
            }
            Err(e) => format!("Failed to execute railway logs: {}", e),
        }
    }

    /// Restart a service (Railway)
    pub fn restart_service(&self, service: &str) -> Result<(), String> {
        println!("[ServerMonitor] Restarting service: {}", service);

        let output = Command::new("railway")
            .args(["restart", "--service", service])
            .output()
            .map_err(|e| format!("Failed to execute railway restart: {}", e))?;

        if output.status.success() {
            println!("[ServerMonitor] Service {} restarted successfully", service);
            Ok(())
        } else {
            let stderr = String::from_utf8_lossy(&output.stderr);
            Err(format!("Failed to restart service: {}", stderr))
        }
    }

    /// Get Railway deployment status
    pub fn get_deployment_status(&self) -> String {
        let output = Command::new("railway").args(["status"]).output();

        match output {
            Ok(output) => {
                let stdout = String::from_utf8_lossy(&output.stdout);
                let stderr = String::from_utf8_lossy(&output.stderr);
                if output.status.success() {
                    stdout.to_string()
                } else {
                    format!("Error getting status: {}\n{}", stderr, stdout)
                }
            }
            Err(e) => format!("Failed to execute railway status: {}", e),
        }
    }

    /// Check if text contains alert patterns
    fn contains_alert_pattern(text: &str) -> bool {
        let text_lower = text.to_lowercase();
        ALERT_PATTERNS
            .iter()
            .any(|pattern| text_lower.contains(pattern))
    }

    /// Get failure count for endpoint
    pub fn get_failure_count(&self, endpoint: &str) -> u32 {
        self.endpoints
            .iter()
            .position(|e| e == endpoint)
            .and_then(|idx| self.failure_counts.get(idx).copied())
            .unwrap_or(0)
    }

    /// Check if endpoint needs critical attention (3+ consecutive failures)
    pub fn needs_critical_attention(&self, endpoint: &str) -> bool {
        self.get_failure_count(endpoint) >= 3
    }

    /// Build context for Claude with current server state
    pub fn build_server_context(&mut self) -> String {
        let mut context = String::new();

        // Add endpoint health status
        context.push_str("=== ENDPOINT HEALTH STATUS ===\n");
        let health_results = self.check_all_endpoints();
        for (endpoint, status) in &health_results {
            let failure_count = self.get_failure_count(endpoint);
            context.push_str(&format!(
                "Endpoint: {}\nStatus: {:?}\nConsecutive Failures: {}\n\n",
                endpoint, status, failure_count
            ));
        }

        // Add deployment status
        context.push_str("=== DEPLOYMENT STATUS ===\n");
        context.push_str(&self.get_deployment_status());
        context.push('\n');

        context
    }
}

impl Default for ServerMonitorAgent {
    fn default() -> Self {
        Self::new()
    }
}

impl AgentType for ServerMonitorAgent {
    fn name(&self) -> &'static str {
        "Server Monitor"
    }

    fn system_prompt(&self) -> &str {
        &self.system_prompt
    }

    fn should_handle(&self, _app_name: &str, text: &str) -> bool {
        // Trigger on scheduled check (every 5 minutes by default)
        if self.is_check_due() {
            return true;
        }

        // Trigger on alert patterns in logs/text
        if Self::contains_alert_pattern(text) {
            return true;
        }

        false
    }

    fn max_iterations(&self) -> u32 {
        5 // Server monitor should be more conservative
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_server_monitor_agent_new() {
        let agent = ServerMonitorAgent::new();
        assert_eq!(agent.name(), "Server Monitor");
        assert_eq!(agent.check_interval_secs(), DEFAULT_CHECK_INTERVAL_SECS);
        assert!(agent.endpoints().is_empty());
    }

    #[test]
    fn test_server_monitor_with_config() {
        let endpoints = vec![
            "https://api.example.com/health".to_string(),
            "https://web.example.com".to_string(),
        ];
        let agent = ServerMonitorAgent::with_config(60, endpoints.clone());
        assert_eq!(agent.check_interval_secs(), 60);
        assert_eq!(agent.endpoints(), &endpoints);
    }

    #[test]
    fn test_add_remove_endpoint() {
        let mut agent = ServerMonitorAgent::new();
        agent.add_endpoint("https://api.example.com");
        assert_eq!(agent.endpoints().len(), 1);

        agent.remove_endpoint("https://api.example.com");
        assert!(agent.endpoints().is_empty());
    }

    #[test]
    fn test_should_handle_alert_patterns() {
        let agent = ServerMonitorAgent::new();

        // Should trigger on 503
        assert!(agent.should_handle("Terminal", "Error: 503 Service Unavailable"));

        // Should trigger on connection refused
        assert!(agent.should_handle("Terminal", "ECONNREFUSED - connection refused"));

        // Should trigger on timeout
        assert!(agent.should_handle("Browser", "Request timeout after 30s"));

        // Should not trigger on normal text
        // Note: will trigger if check is due, so we need to manually set last_check
        let mut agent_checked = ServerMonitorAgent::new();
        agent_checked.record_check();
        assert!(!agent_checked.should_handle("Terminal", "Build successful"));
    }

    #[test]
    fn test_health_status_methods() {
        let healthy = HealthStatus::Healthy;
        assert!(!healthy.is_problem());
        assert!(!healthy.is_degraded());
        assert_eq!(healthy.as_str(), "healthy");

        let degraded = HealthStatus::Degraded {
            reason: "Slow".to_string(),
            response_time_ms: 5000,
        };
        assert!(!degraded.is_problem());
        assert!(degraded.is_degraded());
        assert_eq!(degraded.as_str(), "degraded");

        let unhealthy = HealthStatus::Unhealthy {
            reason: "503".to_string(),
            status_code: Some(503),
        };
        assert!(unhealthy.is_problem());
        assert!(!unhealthy.is_degraded());
        assert_eq!(unhealthy.as_str(), "unhealthy");
    }

    #[test]
    fn test_is_check_due() {
        let mut agent = ServerMonitorAgent::new();

        // First check is always due
        assert!(agent.is_check_due());

        // After recording check, should not be due immediately
        agent.record_check();
        assert!(!agent.is_check_due());
    }

    #[test]
    fn test_failure_count() {
        let mut agent = ServerMonitorAgent::with_config(300, vec!["https://test.com".to_string()]);

        assert_eq!(agent.get_failure_count("https://test.com"), 0);
        assert!(!agent.needs_critical_attention("https://test.com"));
    }

    #[test]
    fn test_contains_alert_pattern() {
        assert!(ServerMonitorAgent::contains_alert_pattern(
            "Error 503 Service Unavailable"
        ));
        assert!(ServerMonitorAgent::contains_alert_pattern(
            "Connection REFUSED"
        ));
        assert!(ServerMonitorAgent::contains_alert_pattern(
            "request TIMEOUT"
        ));
        assert!(!ServerMonitorAgent::contains_alert_pattern(
            "Request successful"
        ));
    }
}
