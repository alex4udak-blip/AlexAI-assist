import { useState, useEffect } from 'react';
import MenuBar from './pages/MenuBar';
import Main from './pages/Main';
import Settings from './pages/Settings';

type View = 'menubar' | 'main' | 'settings';

function App() {
  const [view, setView] = useState<View>('menubar');
  const [baseView, setBaseView] = useState<'menubar' | 'main'>('menubar');

  useEffect(() => {
    // Check window size to determine view
    const checkView = () => {
      const newBaseView = window.innerHeight > 400 ? 'main' : 'menubar';
      setBaseView(newBaseView);
      // Only update view if not in settings
      if (view !== 'settings') {
        setView(newBaseView);
      }
    };

    checkView();
    window.addEventListener('resize', checkView);
    return () => window.removeEventListener('resize', checkView);
  }, [view]);

  const openSettings = () => setView('settings');
  const closeSettings = () => setView(baseView);

  if (view === 'settings') {
    return <Settings onBack={closeSettings} />;
  }

  return view === 'menubar' ? (
    <MenuBar onOpenSettings={openSettings} />
  ) : (
    <Main onOpenSettings={openSettings} />
  );
}

export default App;
