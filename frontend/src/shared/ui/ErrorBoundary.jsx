import { Component } from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';
class ErrorBoundary extends Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null, errorInfo: null };
    }
    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }
    componentDidCatch(error, errorInfo) {
        this.setState({ errorInfo });
        // Log to internal backend logger
        import('@/lib/logger').then(({ logger }) => {
            logger.error(error, errorInfo.componentStack);
        });
    }
    handleReload = () => {
        window.location.reload();
    };
    handleGoHome = () => {
        window.location.href = '/dashboard';
    };
    render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-950 p-6" dir="rtl">
                    <div className="bg-white dark:bg-slate-800 rounded-3xl shadow-2xl p-10 max-w-lg w-full text-center space-y-6 border border-slate-100 dark:border-slate-700">
                        <div className="w-20 h-20 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto">
                            <AlertTriangle size={40} className="text-red-500" />
                        </div>
                        <div className="space-y-2">
                            <h1 className="text-2xl font-black text-slate-800 dark:text-white">
                                حدث خطأ غير متوقع
                            </h1>
                            <p className="text-slate-500 dark:text-slate-400">
                                عذراً، حدث خطأ أثناء تحميل الصفحة. يرجى المحاولة مرة أخرى.
                            </p>
                        </div>
                        {import.meta.env.DEV && this.state.error && (
                            <div className="bg-slate-50 dark:bg-slate-900 rounded-xl p-4 text-left text-xs font-mono text-red-600 dark:text-red-400 overflow-auto max-h-40">
                                {this.state.error.toString()}
                            </div>
                        )}
                        <div className="flex items-center justify-center gap-4">
                            <button
                                onClick={this.handleReload}
                                className="flex items-center gap-2 px-6 py-3 bg-primary text-white font-bold rounded-xl hover:bg-sky-600 transition-all shadow-lg shadow-primary/20"
                            >
                                <RefreshCw size={18} />
                                إعادة المحاولة
                            </button>
                            <button
                                onClick={this.handleGoHome}
                                className="flex items-center gap-2 px-6 py-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 font-bold rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 transition-all"
                            >
                                <Home size={18} />
                                الصفحة الرئيسية
                            </button>
                        </div>
                    </div>
                </div>
            );
        }
        return this.props.children;
    }
}
export default ErrorBoundary;

