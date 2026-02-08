/**
 * Modal Component
 * Reusable modal wrapper with backdrop blur and close on escape.
 */
import React, { useEffect } from 'react';
import { X } from 'lucide-react';

export default function Modal({ isOpen, onClose, title, children, maxWidth = 'max-w-md', scrollable = true, className = '' }) {
    useEffect(() => {
        const handleEscape = (e) => {
            if (e.key === 'Escape') onClose();
        };

        if (isOpen) {
            document.addEventListener('keydown', handleEscape);
            document.body.style.overflow = 'hidden';
        }

        return () => {
            document.removeEventListener('keydown', handleEscape);
            document.body.style.overflow = 'auto';
        };
    }, [isOpen, onClose]);

    if (!isOpen) return null;

    return (
        <div
            className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm"
            onClick={(e) => e.target === e.currentTarget && onClose()}
        >
            <div className={`bg-white dark:bg-slate-900 w-full ${maxWidth} rounded-2xl p-4 md:p-6 shadow-2xl max-h-[90vh] md:max-h-[95vh] ${scrollable ? 'overflow-y-auto' : 'overflow-hidden flex flex-col'} m-4 transition-all duration-300 scale-100 animate-in fade-in zoom-in-95 ${className}`}>
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-xl font-bold">{title}</h3>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-slate-100 rounded-lg text-slate-400 hover:text-slate-600"
                    >
                        <X size={20} />
                    </button>
                </div>
                {children}
            </div>
        </div>
    );
}
