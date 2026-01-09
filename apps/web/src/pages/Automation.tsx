import { motion } from 'framer-motion';
import { AutomationPanel } from '../components/automation/AutomationPanel';

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

export default function Automation() {
  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="space-y-6 max-w-7xl mx-auto"
    >
      <motion.div variants={item}>
        <h1 className="text-2xl font-bold text-text-primary">
          Automation Control
        </h1>
        <p className="text-text-secondary mt-1">
          Control connected devices and execute automation commands
        </p>
      </motion.div>

      <motion.div variants={item}>
        <AutomationPanel />
      </motion.div>
    </motion.div>
  );
}
