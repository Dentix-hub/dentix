import { useState } from 'react';
import { Building2 } from 'lucide-react';
import { API_URL } from '@/api';

export default function BrandLogo({ src, alt = "Logo", className = "", fallbackUrl = '/logo.png?v=2' }) {
    const [logoError, setLogoError] = useState(false);

    let logoUrl = fallbackUrl;
    if (src && src !== 'null' && !logoError) {
        logoUrl = src.startsWith('http') || src.startsWith('/') ? src : `${API_URL}/${src}`;
    }

    if (logoError) {
        return (
            <div className={`flex items-center justify-center text-primary bg-primary/10 rounded-2xl ${className}`}>
                <Building2 size={40} className="w-1/2 h-1/2" />
            </div>
        );
    }

    return (
        <img
            src={logoUrl}
            alt={alt}
            className={className}
            onError={(e) => {
                if (e.target.src.includes(fallbackUrl)) {
                    setLogoError(true);
                } else {
                    e.target.src = fallbackUrl;
                }
            }}
            onLoad={() => setLogoError(false)}
        />
    );
}
