import { useState, useEffect } from 'react';
import MenuBar from './pages/MenuBar';
import Main from './pages/Main';

function App() {
  const [view, setView] = useState<'menubar' | 'main'>('menubar');

  useEffect(() => {
    // Check window size to determine view
    const checkView = () => {
      setView(window.innerHeight > 400 ? 'main' : 'menubar');
    };

    checkView();
    window.addEventListener('resize', checkView);
    return () => window.removeEventListener('resize', checkView);
  }, []);

  return view === 'menubar' ? <MenuBar /> : <Main />;
}

export default App;
