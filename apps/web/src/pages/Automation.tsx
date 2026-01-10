import { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { AutomationPanel } from '../components/automation/AutomationPanel';
import { PatternsPanel } from '../components/automation/PatternsPanel';
import { AuditLogList } from '../components/automation/AuditLogList';
import { Cpu, Sparkles, FileText } from 'lucide-react';

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

type TabType = 'devices' | 'patterns' | 'logs';

export default function Automation() {
  const location = useLocation();
  const navigate = useNavigate();
  const patternsPanelRef = useRef<HTMLDivElement>(null);

  // Determine initial tab based on URL hash or state
  const getInitialTab = (): TabType => {
    const hash = location.hash.replace('#', '');
    if (hash === 'patterns') return 'patterns';
    if (hash === 'logs') return 'logs';
    // Check if navigated from patterns insight
    if (location.state?.fromPatterns) return 'patterns';
    return 'devices';
  };

  const [activeTab, setActiveTab] = useState<TabType>(getInitialTab);

  // Update hash when tab changes
  const handleTabChange = (tab: TabType) => {
    setActiveTab(tab);
    navigate(`/automation#${tab}`, { replace: true });
  };

  // Scroll to patterns panel if hash is #patterns
  useEffect(() => {
    if (location.hash === '#patterns' && patternsPanelRef.current) {
      patternsPanelRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [location.hash]);

  const handleAgentCreated = (_agentId: string) => {
    navigate(`/agents`);
  };

  const tabs = [
    { id: 'devices' as const, label: 'Устройства', icon: Cpu },
    { id: 'patterns' as const, label: 'Паттерны', icon: Sparkles },
    { id: 'logs' as const, label: 'Журнал', icon: FileText },
  ];

  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="space-y-6 max-w-7xl mx-auto"
    >
      <motion.div variants={item}>
        <h1 className="text-2xl font-bold text-text-primary">
          Управление автоматизацией
        </h1>
        <p className="text-text-secondary mt-1">
          Управление подключенными устройствами, паттернами активности и автоматизацией
        </p>
      </motion.div>

      {/* Tab Navigation */}
      <motion.div variants={item}>
        <div className="flex items-center gap-1 p-1 bg-bg-secondary/60 backdrop-blur-md rounded-lg border border-border-subtle w-fit">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => handleTabChange(tab.id)}
                className={`
                  flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all
                  ${isActive
                    ? 'bg-accent-primary text-white shadow-sm'
                    : 'text-text-secondary hover:text-text-primary hover:bg-bg-tertiary'
                  }
                `}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </motion.div>

      {/* Tab Content */}
      {activeTab === 'devices' && (
        <motion.div variants={item}>
          <AutomationPanel />
        </motion.div>
      )}

      {activeTab === 'patterns' && (
        <motion.div variants={item} ref={patternsPanelRef}>
          <PatternsPanel onAgentCreated={handleAgentCreated} />
        </motion.div>
      )}

      {activeTab === 'logs' && (
        <motion.div variants={item}>
          <AuditLogList />
        </motion.div>
      )}
    </motion.div>
  );
}
