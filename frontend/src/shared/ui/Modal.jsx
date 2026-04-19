/**
 * Modal Component
 * Reusable modal wrapper with backdrop blur and close on escape.
 */
import { useEffect } from 'react';
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
            className="fixed inset-0 bg-black/50 z-50 flex items-end md:items-center justify-center backdrop-blur-sm transition-opacity duration-300"
            onClick={(e) => e.target === e.currentTarget && onClose()}
        >
            <div className={`
                bg-white dark:bg-slate-900 w-full ${maxWidth} 
                rounded-t-3xl md:rounded-3xl p-4 md:p-6 shadow-2xl 
                max-h-[95vh] md:max-h-[90vh] 
                ${scrollable ? 'overflow-y-auto' : 'overflow-hidden flex flex-col'} 
                transition-all duration-300 
                animate-slide-up md:animate-in md:fade-in md:zoom-in-95 
                safe-bottom md:pb-6
                ${className}
            `}>
                <div className="flex justify-between items-center mb-6 sticky top-0 bg-white dark:bg-slate-900 z-10 py-2 -mt-2">
                    <div className="w-12 h-1.5 bg-slate-200 rounded-full mx-auto md:hidden absolute -top-4 left-1/2 -translate-x-1/2 mb-4" />
                    <h3 className="text-xl font-black text-slate-800 dark:text-white tracking-tight">{title}</h3>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-slate-100 rounded-xl text-slate-400 hover:text-slate-600 transition-colors"
                    >
                        <X size={20} />
                    </button>
                </div>
                <div className="relative">
                    {children}
                </div>
            </div>
        </div>
    );
}

