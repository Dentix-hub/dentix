import React, { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
// Sentry Removed - Replaced by Internal Logger
import App from './App.jsx';
import './index.css';
import './i18n'; // Initialize i18n

class DiagnosticErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error('🔴 [DENTIX DIAGNOSTIC] Error:', error.message);
    console.error('🔴 [DENTIX DIAGNOSTIC] Component Stack:', info.componentStack);
    console.error('🔴 [DENTIX DIAGNOSTIC] Full Error:', error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 20, fontFamily: 'monospace', color: 'red' }}>
          <h2>React Error #130 — Component Diagnostic</h2>
          <p>{this.state.error?.message}</p>
          <p style={{ fontSize: 12 }}>Check browser console for componentStack</p>
        </div>
      );
    }
    return this.props.children;
  }
}

const container = document.getElementById('root');
const root = createRoot(container);

root.render(
  <StrictMode>
    <DiagnosticErrorBoundary>
      <App />
    </DiagnosticErrorBoundary>
  </StrictMode>
);
