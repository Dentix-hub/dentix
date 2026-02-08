
import React, { useEffect, useState } from 'react';
import { Megaphone, X } from 'lucide-react';
import { api } from '@/api';

const GlobalBanner = () => {
    const [message, setMessage] = useState('');
    const [visible, setVisible] = useState(false);

    useEffect(() => {
        const fetchBanner = async () => {
            try {
                // We use the new public endpoint
                const res = await api.get('/api/v1/global-settings'); // Verify path/prefix
                if (res.data?.banner) {
                    setMessage(res.data.banner);
                    setVisible(true);
                }
            } catch (error) {
                console.error("Failed to fetch banner", error);
            }
        };

        // Only fetch if authenticated? Or always?
        // App.jsx structure might check token.
        fetchBanner();
    }, []);

    if (!visible || !message) return null;

    return (
        <div className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white px-4 py-3 shadow-md relative animate-fade-in-down z-50">
            <div className="container mx-auto flex items-center justify-center text-sm md:text-base font-bold text-center pr-8 pl-8">
                <Megaphone size={18} className="ml-2 animate-bounce" />
                <span>{message}</span>
            </div>
            <button
                onClick={() => setVisible(false)}
                className="absolute left-4 top-1/2 -translate-y-1/2 p-1 hover:bg-white/20 rounded-full transition-colors"
            >
                <X size={18} />
            </button>
        </div>
    );
};

export default GlobalBanner;
