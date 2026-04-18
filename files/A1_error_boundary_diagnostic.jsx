// ============================================================
// DIAGNOSTIC PATCH — احذفه بعد ما تعرف المشكلة
// أضفه في: frontend/src/main.jsx
// ============================================================

// 1. أضف الـ class ده فوق ReactDOM.createRoot
class DiagnosticErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    // ← هنا هيظهر اسم الـ component المسبب بالظبط
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

// 2. غلّف الـ App بيه:
// قبل:
//   ReactDOM.createRoot(document.getElementById('root')).render(
//     <React.StrictMode><App /></React.StrictMode>
//   );
//
// بعد:
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <DiagnosticErrorBoundary>
      <App />
    </DiagnosticErrorBoundary>
  </React.StrictMode>
);

// ============================================================
// بعد ما تشغل الـ app وتشوف الـ componentStack في الـ console،
// ابعتلي أول 5 سطور من الـ stack وهنحدد الملف بالظبط.
// ============================================================
