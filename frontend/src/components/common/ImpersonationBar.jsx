import { useState, useEffect } from 'react';
import { Shield, LogOut } from 'lucide-react';
import { getImpersonationToken, clearImpersonationSession } from '@/utils';

export default function ImpersonationBar() {
    const [token, setToken] = useState(() => getImpersonationToken());
    const [tenantName, setTenantName] = useState('');
    const [targetUser, setTargetUser] = useState('');
    const [scope, setScope] = useState('read_only');

    useEffect(() => {
        const activeToken = getImpersonationToken();
        setToken(activeToken);
        if (typeof window !== 'undefined' && window.sessionStorage) {
            setTenantName(sessionStorage.getItem('dentix_impersonation_tenant') || '');
            setTargetUser(sessionStorage.getItem('dentix_impersonation_user') || '');
            setScope(sessionStorage.getItem('dentix_impersonation_scope') || 'read_only');
        }
    }, []);

    if (!token) return null;

    const handleReturn = async () => {
        clearImpersonationSession();

        try {
            const { queryClient } = await import('@/lib/queryClient');
            await queryClient.cancelQueries();
            queryClient.clear();
        } catch {
            // best effort cache clearance
        }

        try {
            const { useTenantStore } = await import('@/store/tenant.store');
            useTenantStore.getState().clearTenant?.();
        } catch {
            // best effort tenant clearance
        }

        window.location.href = '/admin/tenants';
    };

    const isReadOnly = scope === 'read_only';

    return (
        <div className="bg-amber-500 text-white py-2 px-6 flex justify-between items-center z-[100] sticky top-0 shadow-lg border-b border-amber-600 animate-slide-down">
            <div className="flex items-center gap-3">
                <Shield size={18} className="animate-pulse" />
                <span className="font-bold text-sm">
                    وضع المحاكاة ({isReadOnly ? 'قراءة فقط' : 'وصول كامل'}):{' '}
                    {tenantName ? `عيادة ${tenantName}` : 'المستأجر'}
                    {targetUser ? ` (${targetUser})` : ''}
                </span>
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

