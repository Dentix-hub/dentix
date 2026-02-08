import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
// Sentry Removed - Replaced by Internal Logger
import App from './App.jsx';
import './index.css';
import './i18n'; // Initialize i18n

const container = document.getElementById('root');
const root = createRoot(container);

root.render(
  <StrictMode>
    <App />
  </StrictMode>
);