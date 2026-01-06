import { Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Layout';
import Dashboard from './pages/Dashboard';
import Agents from './pages/Agents';
import Analytics from './pages/Analytics';
import History from './pages/History';
import Chat from './pages/Chat';
import Settings from './pages/Settings';
import Download from './pages/Download';

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/agents" element={<Agents />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/history" element={<History />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/download" element={<Download />} />
      </Routes>
    </Layout>
  );
}

export default App;
