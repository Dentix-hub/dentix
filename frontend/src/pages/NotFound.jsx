import React from 'react';
import { Link } from 'react-router-dom';
import { Home, ArrowRight } from 'lucide-react';
import { useTranslation } from 'react-i18next';

export default function NotFound() {
    const { t } = useTranslation();

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-950 p-6" dir="rtl">
            <div className="text-center space-y-8">
                {/* 404 Number */}
                <div className="relative">
                    <h1 className="text-[12rem] font-black text-slate-200 dark:text-slate-800 leading-none select-none">
                        404
                    </h1>
                    <div className="absolute inset-0 flex items-center justify-center">
                        <div className="bg-white dark:bg-slate-800 rounded-3xl shadow-2xl px-8 py-4 border border-slate-100 dark:border-slate-700">
                            <p className="text-2xl font-bold text-slate-800 dark:text-white">
                                {t('static.not_found.title')}
                            </p>
                        </div>
                    </div>
                </div>

                {/* Message */}
                <div className="space-y-4 max-w-md mx-auto">
                    <p className="text-slate-500 dark:text-slate-400 text-lg">
                        {t('static.not_found.message')}
                    </p>
                </div>

                {/* Actions */}
                <div className="flex items-center justify-center gap-4">
                    <Link
                        to="/dashboard"
                        className="flex items-center gap-2 px-8 py-4 bg-primary text-white font-bold rounded-2xl hover:bg-sky-600 transition-all shadow-lg shadow-primary/20 hover:scale-105"
                    >
                        <Home size={20} />
                        {t('static.not_found.home_button')}
                    </Link>
                    <button
                        onClick={() => window.history.back()}
                        className="flex items-center gap-2 px-8 py-4 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 font-bold rounded-2xl hover:bg-slate-200 dark:hover:bg-slate-700 transition-all hover:scale-105"
                    >
                        <ArrowRight size={20} />
                        {t('static.not_found.back_button')}
                    </button>
                </div>

                {/* Decorative Elements */}
                <div className="flex items-center justify-center gap-2 text-slate-300 dark:text-slate-600">
                    <span className="w-12 h-0.5 bg-current rounded-full"></span>
                    <span className="text-sm font-medium">DENTIX</span>
                    <span className="w-12 h-0.5 bg-current rounded-full"></span>
                </div>
            </div>
        </div>
    );
}
