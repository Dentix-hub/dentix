import { Shield, LogOut } from 'lucide-react';
import { getAdminToken, setAdminToken, removeAdminToken } from '@/utils';

export default function ImpersonationBar() {
    const adminToken = getAdminToken();
    if (!adminToken) return null;

    const handleReturn = () => {
        // Return to admin session
        setAdminToken(adminToken);
        removeAdminToken();
        window.location.href = '/admin/tenants';
    };

    return (
        <div className="bg-amber-500 text-white py-2 px-6 flex justify-between items-center z-[100] sticky top-0 shadow-lg border-b border-amber-600 animate-slide-down">
            <div className="flex items-center gap-3">
                <Shield size={18} className="animate-pulse" />
                <span className="font-bold text-sm">وضع المحاكاة: أنت تتصفح النظام الآن بصلاحيات "مدير العيادة"</span>
            </div>
            <button
                onClick={handleReturn}
                className="bg-white/20 hover:bg-white/30 backdrop-blur-md px-4 py-1.5 rounded-lg text-xs font-bold flex items-center gap-2 transition-all active:scale-95"
            >
                <LogOut size={14} />
                العودة للوحة الإشراف
            </button>
        </div>
    );
}