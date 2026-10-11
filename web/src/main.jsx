import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './kit.css';
import './app.css';
import './kit-fsp.css';
import './type.css';
import App from './App.jsx';

createRoot(document.getElementById('root')).render(<StrictMode><App /></StrictMode>);

// Прелоадер уходит, когда приложение отрисовано и шрифты готовы, но не раньше, чем знак собрался (~1 с).
const boot = document.getElementById('boot');
if (boot) {
  const t0 = performance.now();
  Promise.race([document.fonts?.ready || Promise.resolve(), new Promise((r) => setTimeout(r, 2500))]).then(() => {
    setTimeout(() => { boot.classList.add('is-done'); setTimeout(() => boot.remove(), 350); }, Math.max(0, 1000 - (performance.now() - t0)));
  });
}
