import { useState } from 'react';
import MenuBar from './pages/MenuBar';
import Settings from './pages/Settings';

type View = 'popup' | 'settings';

function App() {
  const [view, setView] = useState<View>('popup');

  if (view === 'settings') {
    return <Settings onBack={() => setView('popup')} />;
  }

  return <MenuBar onOpenSettings={() => setView('settings')} />;
}

export default App;
