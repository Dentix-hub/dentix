import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export default function GlobalErrorFallback() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900 p-4">
            <div className="max-w-md w-full bg-white dark:bg-slate-800 rounded-2xl shadow-xl p-8 text-center">
                <div className="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                    <AlertTriangle className="w-8 h-8 text-red-600 dark:text-red-400" />
                </div>
                <h2 className="text-xl font-bold text-slate-800 dark:text-white mb-2">
                    Something went wrong
                </h2>
                <p className="text-slate-500 dark:text-slate-400 mb-6">
                    An unexpected error occurred. Please try refreshing the page.
                </p>
                <button
                    onClick={() => window.location.reload()}
                    className="inline-flex items-center gap-2 px-6 py-3 bg-primary text-white rounded-xl font-medium hover:bg-primary/90 transition-colors"
                >
                    <RefreshCw size={18} />
                    Refresh Page
                </button>
            </div>
        </div>
    );
}
