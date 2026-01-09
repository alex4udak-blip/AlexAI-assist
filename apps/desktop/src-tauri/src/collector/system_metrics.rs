use serde::{Deserialize, Serialize};
use std::sync::Mutex;
use sysinfo::{System, CpuRefreshKind, MemoryRefreshKind, RefreshKind};

/// System performance metrics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemMetrics {
    /// CPU usage percentage (0-100)
    pub cpu_usage: f32,
    /// RAM usage in bytes
    pub ram_used: u64,
    /// Total RAM in bytes
    pub ram_total: u64,
    /// RAM usage percentage (0-100)
    pub ram_usage_percent: f32,
}

/// System metrics collector
pub struct SystemMetricsCollector {
    system: Mutex<System>,
}

impl SystemMetricsCollector {
    /// Create a new SystemMetricsCollector instance
    pub fn new() -> Self {
        let system = System::new_with_specifics(
            RefreshKind::new()
                .with_cpu(CpuRefreshKind::everything())
                .with_memory(MemoryRefreshKind::everything()),
        );

        Self {
            system: Mutex::new(system),
        }
    }

    /// Collect current system metrics
    ///
    /// # Errors
    /// Returns an error if unable to lock the system instance
    pub fn collect(&self) -> Result<SystemMetrics, String> {
        let mut system = self
            .system
            .lock()
            .map_err(|e| format!("Failed to lock system: {}", e))?;

        // Refresh CPU and memory information
        system.refresh_cpu_usage();
        system.refresh_memory();

        // Calculate CPU usage (average across all cores)
        let cpu_usage = system.global_cpu_usage();

        // Get memory information
        let ram_used = system.used_memory();
        let ram_total = system.total_memory();
        let ram_usage_percent = if ram_total > 0 {
            (ram_used as f32 / ram_total as f32) * 100.0
        } else {
            0.0
        };

        Ok(SystemMetrics {
            cpu_usage,
            ram_used,
            ram_total,
            ram_usage_percent,
        })
    }

    /// Collect metrics asynchronously (non-blocking)
    ///
    /// This is a convenience wrapper around collect() that can be awaited.
    /// System metrics collection is fast enough to not need true async behavior.
    pub async fn collect_async(&self) -> Result<SystemMetrics, String> {
        // System metrics collection is fast enough to call directly
        self.collect()
    }
}

impl Default for SystemMetricsCollector {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_system_metrics_collector_creation() {
        let collector = SystemMetricsCollector::new();
        assert!(true); // Just ensure it can be created
    }

    #[test]
    fn test_collect_metrics() {
        let collector = SystemMetricsCollector::new();
        let metrics = collector.collect();
        assert!(metrics.is_ok());

        if let Ok(metrics) = metrics {
            // CPU usage should be between 0 and 100
            assert!(metrics.cpu_usage >= 0.0 && metrics.cpu_usage <= 100.0);
            // RAM usage should be less than or equal to total
            assert!(metrics.ram_used <= metrics.ram_total);
            // RAM usage percent should be between 0 and 100
            assert!(metrics.ram_usage_percent >= 0.0 && metrics.ram_usage_percent <= 100.0);
        }
    }

    #[tokio::test]
    async fn test_collect_metrics_async() {
        let collector = SystemMetricsCollector::new();
        let metrics = collector.collect_async().await;
        assert!(metrics.is_ok());
    }
}
