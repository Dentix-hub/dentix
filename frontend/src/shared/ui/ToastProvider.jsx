import { Toaster, toast } from 'react-hot-toast';
import { X, Check } from 'lucide-react';
const ToastProvider = () => {
    return (
        <Toaster
            position="top-center"
            reverseOrder={false}
            gutter={8}
            toastOptions={{
                duration: 4000,
                className: '!bg-surface !backdrop-blur-xl !shadow-2xl !rounded-2xl !border !border-white/20 !text-text-primary !font-medium',
                success: {
                    icon: <div className="p-1 bg-emerald-500/10 rounded-full"><Check size={18} className="text-emerald-500" /></div>,
                    className: '!border-emerald-500/20',
                },
                error: {
                    icon: <div className="p-1 bg-red-500/10 rounded-full"><X size={18} className="text-red-500" /></div>,
                    className: '!border-red-500/20',
                    duration: 5000,
                },
                loading: {
                    className: '!border-primary/20',
                },
            }}
        />
    );
};
export { toast };
export default ToastProvider;