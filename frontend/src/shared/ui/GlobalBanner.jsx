import { useEffect, useState } from 'react';
import logger from '@/utils/logger';
import { Megaphone, X } from 'lucide-react';
import { api } from '@/api';

const GlobalBanner = () => {
    const [message, setMessage] = useState('');
    const [visible, setVisible] = useState(false);

    useEffect(() => {
        const fetchBanner = async () => {
            try {
                const res = await api.get('/api/v1/global-settings');
                if (res.data?.banner) {
                    setMessage(res.data.banner);
                    setVisible(true);
                }
            } catch (error) {
                logger.error('Failed to fetch banner', error);
            }
        };
        fetchBanner();
    }, []);

    if (!visible || !message) return null;

    return (
        <div className="relative z-50 bg-gradient-to-r from-indigo-600 to-teal-600 px-2 py-2 text-white shadow-md animate-fade-in-down sm:px-4 sm:py-3">
            <div className="mx-auto flex min-w-0 max-w-7xl items-start justify-center gap-2 pe-12 text-start text-xs font-bold sm:items-center sm:text-center sm:text-sm md:text-base">
                <Megaphone size={18} className="mt-0.5 shrink-0 motion-reduce:animate-none sm:mt-0" aria-hidden="true" />
                <span className="min-w-0 break-words text-white">{message}</span>
            </div>
            <button
                type="button"
                onClick={() => setVisible(false)}
                className="absolute end-1 top-1/2 inline-flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-xl text-white transition-colors hover:bg-white/20 sm:end-2"
                aria-label="Close announcement"
            >
                <X size={18} aria-hidden="true" />
            </button>
        </div>
    );
};

export default GlobalBanner;
