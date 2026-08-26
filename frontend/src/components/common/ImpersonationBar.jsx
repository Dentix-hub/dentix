import { useEffect, useState } from 'react';
import { Shield, LogOut } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { getImpersonationToken, clearImpersonationSession } from '@/utils';

export default function ImpersonationBar() {
    const { t } = useTranslation();
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
        <div className="bg-amber-500 text-white py-2 px-4 sm:px-6 flex flex-wrap gap-2 justify-between items-center z-system sticky top-0 shadow-lg border-b border-amber-600 motion-reduce:transition-none">
            <div className="flex items-center gap-3 min-w-0">
                <Shield size={18} aria-hidden="true" />
                <span className="font-bold text-sm truncate">
                    {t('super_admin.impersonation.banner', {
                        scope: isReadOnly
                            ? t('super_admin.impersonation.read_only')
                            : t('super_admin.impersonation.full_access'),
                        tenant: tenantName || t('super_admin.impersonation.tenant_fallback'),
                        user: targetUser ? ` (${targetUser})` : '',
                    })}
                </span>
            </div>
            <button
                type="button"
                onClick={handleReturn}
                className="bg-white/20 hover:bg-white/30 backdrop-blur-md px-4 py-1.5 rounded-lg text-xs font-bold flex items-center gap-2 transition-all active:scale-95 motion-reduce:transform-none"
            >
                <LogOut size={14} aria-hidden="true" />
                {t('super_admin.impersonation.return')}
            </button>
        </div>
    );
}
