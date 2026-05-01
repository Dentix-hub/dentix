/**
 * Modal Component
 * Reusable modal wrapper with backdrop blur and close on escape.
 */
import { useEffect, useRef } from 'react';
import { X } from 'lucide-react';
export default function Modal({ isOpen, onClose, title, children, maxWidth, size = 'md', scrollable = true, className = '' }) {
    const modalRef = useRef(null);

    const sizeMap = {
        sm: 'max-w-sm',
        md: 'max-w-md',
        lg: 'max-w-lg',
        xl: 'max-w-xl',
        '2xl': 'max-w-2xl',
        '3xl': 'max-w-3xl',
        '4xl': 'max-w-4xl',
        '5xl': 'max-w-5xl'
    };

    const resolvedMaxWidth = maxWidth || sizeMap[size] || sizeMap.md;
    
    useEffect(() => {
        const handleEscape = (e) => {
            if (e.key === 'Escape') onClose();
        };
        const handleTab = (e) => {
            if (e.key === 'Tab' && modalRef.current) {
                const focusableElements = modalRef.current.querySelectorAll(
                    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
                );
                
                const firstElement = focusableElements[0];
                const lastElement = focusableElements[focusableElements.length - 1];

                if (e.shiftKey) {
                    if (document.activeElement === firstElement) {
                        lastElement?.focus();
                        e.preventDefault();
                    }
                } else {
                    if (document.activeElement === lastElement) {
                        firstElement?.focus();
                        e.preventDefault();
                    }
                }
            }
        };

        if (isOpen) {
            document.addEventListener('keydown', handleEscape);
            document.addEventListener('keydown', handleTab);
            document.body.style.overflow = 'hidden';
            
            // Auto focus
            setTimeout(() => {
                const focusableElements = modalRef.current?.querySelectorAll(
                    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
                );
                focusableElements?.[0]?.focus();
            }, 50);
        }
        return () => {
            document.removeEventListener('keydown', handleEscape);
            document.removeEventListener('keydown', handleTab);
            document.body.style.overflow = 'auto';
        };
    }, [isOpen, onClose]);
    if (!isOpen) return null;
    return (
        <div
            className="fixed inset-0 bg-black/50 z-50 flex items-end md:items-center justify-center backdrop-blur-sm transition-opacity duration-300"
            onClick={(e) => e.target === e.currentTarget && onClose()}
        >
            <div 
                ref={modalRef}
                className={`
                bg-white dark:bg-slate-900 w-full ${resolvedMaxWidth} 
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

