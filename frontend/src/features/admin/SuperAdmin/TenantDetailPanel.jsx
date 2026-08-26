import { memo, useEffect, useState } from 'react';
import logger from '@/utils/logger';
import {
    Users,
    Calendar,
    DollarSign,
    Clock,
    Activity,
    Shield,
    Mail,
    Globe,
    Phone,
} from 'lucide-react';
import { api } from '@/api';
import { format } from 'date-fns';
import { ar, enUS } from 'date-fns/locale';
import { useTranslation } from 'react-i18next';
import { DentixDrawer } from '@/shared/ui';

const TenantDetailPanel = memo(function TenantDetailPanel({ tenantId, onClose, onImpersonate }) {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';
    const dateLocale = isRtl ? ar : enUS;
    const [data, setData] = useState(null);
    const [users, setUsers] = useState([]);
    const [selectedUser, setSelectedUser] = useState('');
    const [reason, setReason] = useState('');
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!tenantId) return;
        const fetchDetails = async () => {
            try {
                setLoading(true);
                const [detailsRes, usersRes] = await Promise.all([
                    api.get(`/api/v1/admin/tenants/${tenantId}/details`),
                    api.get(`/api/v1/admin/tenants/${tenantId}/users`),
                ]);
                setData(detailsRes.data);
                setUsers(usersRes.data.users || []);
                setSelectedUser('');
                setReason('');
            } catch (error) {
                logger.error(error);
                setData(null);
                setUsers([]);
            } finally {
                setLoading(false);
            }
        };
        fetchDetails();
    }, [tenantId]);

    if (!tenantId) return null;

    const handleStartImpersonation = () => {
        if (!reason || reason.trim().length < 5) return;
        onImpersonate(data?.tenant?.id || tenantId, selectedUser, reason.trim(), 'read_only');
    };

    const unavailable = t('super_admin.tenant_detail.unavailable');

    return (
        <DentixDrawer
            open={Boolean(tenantId)}
            onOpenChange={(open) => {
                if (!open) onClose?.();
            }}
            title={t('super_admin.tenant_detail.title')}
            size="md"
            closeLabel={t('super_admin.tenant_detail.close_drawer')}
        >
            <div className="space-y-8" dir={isRtl ? 'rtl' : 'ltr'}>
                <p className="text-sm text-text-muted">{t('super_admin.tenant_detail.subtitle')}</p>

                {loading ? (
                    <div className="space-y-6 animate-pulse">
                        <div className="h-32 bg-slate-100 dark:bg-slate-800 rounded-3xl" />
                        <div className="grid grid-cols-2 gap-4">
                            <div className="h-24 bg-slate-100 dark:bg-slate-800 rounded-2xl" />
                            <div className="h-24 bg-slate-100 dark:bg-slate-800 rounded-2xl" />
                        </div>
                    </div>
                ) : !data ? (
                    <div className="p-8 text-center text-slate-500 bg-slate-50 dark:bg-slate-800/50 rounded-2xl">
                        <Activity className="mx-auto mb-3 opacity-20" size={48} />
                        <p className="font-bold">{t('super_admin.tenant_detail.load_failed')}</p>
                        <p className="text-xs mt-1">{t('super_admin.tenant_detail.retry_hint')}</p>
                    </div>
                ) : (
                    <>
                        <div className="bg-gradient-to-br from-indigo-500 to-teal-600 p-6 rounded-3xl text-white shadow-lg shadow-indigo-500/20">
                            <h3 className="text-2xl font-bold mb-1">
                                {data.tenant?.name || t('super_admin.tenant_detail.unnamed')}
                            </h3>
                            <p className="text-indigo-100 flex items-center gap-2 text-sm">
                                <Globe size={14} />
                                <span>
                                    {data.tenant?.domain
                                        ? `${data.tenant.domain}.dentix.com`
                                        : t('super_admin.tenant_detail.clinic_number', { id: data.tenant?.id || tenantId })}
                                </span>
                            </p>

                            <div className="mt-6 flex flex-col gap-3">
                                <select
                                    aria-label={t('super_admin.tenant_detail.auto_admin')}
                                    className="w-full bg-white/20 text-white placeholder-white/50 border border-white/20 rounded-xl px-4 py-2.5 outline-none focus:ring-2 focus:ring-white/50 [&>option]:text-slate-800 text-sm"
                                    value={selectedUser}
                                    onChange={(event) => setSelectedUser(event.target.value)}
                                >
                                    <option value="">{t('super_admin.tenant_detail.auto_admin')}</option>
                                    {users.filter((user) => user.is_active).map((user) => (
                                        <option key={user.id} value={user.id}>
                                            {user.username || user.email} ({user.role})
                                        </option>
                                    ))}
                                </select>

                                <div>
                                    <input
                                        type="text"
                                        value={reason}
                                        onChange={(event) => setReason(event.target.value)}
                                        placeholder={t('super_admin.tenant_detail.reason_placeholder')}
                                        aria-label={t('super_admin.tenant_detail.reason_placeholder')}
                                        className="w-full bg-white/20 text-white placeholder-white/70 border border-white/20 rounded-xl px-4 py-2 text-sm outline-none focus:ring-2 focus:ring-white/50"
                                    />
                                    <div className="flex items-center justify-between text-[11px] text-white/80 mt-1 px-1">
                                        <span>{t('super_admin.tenant_detail.readonly_scope')}</span>
                                        {reason && reason.trim().length < 5 && (
                                            <span className="text-rose-200">{t('super_admin.tenant_detail.min_reason')}</span>
                                        )}
                                    </div>
                                </div>

                                <button
                                    type="button"
                                    onClick={handleStartImpersonation}
                                    disabled={!reason || reason.trim().length < 5}
                                    className="w-full bg-white/20 hover:bg-white/30 disabled:opacity-40 disabled:cursor-not-allowed backdrop-blur-md px-4 py-2.5 rounded-xl text-sm font-bold flex items-center justify-center gap-2 transition-all"
                                >
                                    <Shield size={16} />
                                    {t('super_admin.tenant_detail.start_impersonation')}
                                </button>
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="bg-slate-50 dark:bg-slate-800/40 p-4 rounded-2xl border border-slate-100 dark:border-slate-800">
                                <Users size={20} className="text-teal-500 mb-2" />
                                <div className="text-xl font-bold text-slate-800 dark:text-white">{data.stats?.patients_count || 0}</div>
                                <div className="text-xs text-slate-500">{t('super_admin.tenant_detail.patients')}</div>
                            </div>
                            <div className="bg-slate-50 dark:bg-slate-800/40 p-4 rounded-2xl border border-slate-100 dark:border-slate-800">
                                <Calendar size={20} className="text-blue-500 mb-2" />
                                <div className="text-xl font-bold text-slate-800 dark:text-white">{data.stats?.appointments_count || 0}</div>
                                <div className="text-xs text-slate-500">{t('super_admin.tenant_detail.appointments')}</div>
                            </div>
                            <div className="bg-slate-50 dark:bg-slate-800/40 p-4 rounded-2xl border border-slate-100 dark:border-slate-800">
                                <DollarSign size={20} className="text-amber-500 mb-2" />
                                <div className="text-xl font-bold text-slate-800 dark:text-white">{(data.stats?.total_revenue || 0).toLocaleString(i18n.language)}</div>
                                <div className="text-xs text-slate-500">{t('super_admin.tenant_detail.revenue')}</div>
                            </div>
                            <div className="bg-slate-50 dark:bg-slate-800/40 p-4 rounded-2xl border border-slate-100 dark:border-slate-800">
                                <Shield size={20} className="text-indigo-500 mb-2" />
                                <div className="text-xl font-bold text-slate-800 dark:text-white">{data.tenant?.plan || 'trial'}</div>
                                <div className="text-xs text-slate-500">{t('super_admin.tenant_detail.current_plan')}</div>
                            </div>
                        </div>

                        <div className="space-y-4">
                            <h4 className="text-sm font-bold text-slate-400 uppercase tracking-wider">
                                {t('super_admin.tenant_detail.contact_info')}
                            </h4>
                            <div className="space-y-3">
                                <div className="flex items-center gap-4 p-4 bg-slate-50 dark:bg-slate-800/40 rounded-2xl border border-slate-100 dark:border-slate-800">
                                    <div className="p-2.5 bg-white dark:bg-slate-800 rounded-xl shadow-sm text-indigo-500">
                                        <Mail size={18} />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="text-xs text-slate-500 mb-0.5">{t('super_admin.tenant_detail.email')}</div>
                                        <div className="text-sm font-bold text-slate-800 dark:text-white truncate">
                                            {data.tenant?.admin_email || unavailable}
                                        </div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-4 p-4 bg-slate-50 dark:bg-slate-800/40 rounded-2xl border border-slate-100 dark:border-slate-800">
                                    <div className="p-2.5 bg-white dark:bg-slate-800 rounded-xl shadow-sm text-teal-500">
                                        <Phone size={18} />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="text-xs text-slate-500 mb-0.5">{t('super_admin.tenant_detail.phone')}</div>
                                        <div className="text-sm font-bold text-slate-800 dark:text-white">
                                            {data.tenant?.contact_phone || unavailable}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="space-y-4">
                            <h4 className="text-sm font-bold text-slate-400 uppercase tracking-wider">
                                {t('super_admin.tenant_detail.activity_title')}
                            </h4>
                            <div className="space-y-3">
                                <div className="flex items-center justify-between p-4 bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-800">
                                    <div className="flex items-center gap-3">
                                        <div className="p-2 bg-slate-50 dark:bg-slate-700 rounded-lg text-slate-500">
                                            <Clock size={16} />
                                        </div>
                                        <span className="text-sm font-medium text-slate-600 dark:text-slate-300">
                                            {t('super_admin.tenant_detail.joined')}
                                        </span>
                                    </div>
                                    <span className="text-sm font-bold text-slate-800 dark:text-white">
                                        {data.tenant?.created_at
                                            ? format(new Date(data.tenant.created_at), 'dd MMM yyyy', { locale: dateLocale })
                                            : '-'}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between p-4 bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-800">
                                    <div className="flex items-center gap-3">
                                        <div className="p-2 bg-slate-50 dark:bg-slate-700 rounded-lg text-slate-500">
                                            <Activity size={16} />
                                        </div>
                                        <span className="text-sm font-medium text-slate-600 dark:text-slate-300">
                                            {t('super_admin.tenant_detail.last_activity')}
                                        </span>
                                    </div>
                                    <span className="text-sm font-bold text-slate-800 dark:text-white">
                                        {data.stats?.last_activity
                                            ? format(new Date(data.stats.last_activity), 'dd MMM HH:mm', { locale: dateLocale })
                                            : t('super_admin.tenant_detail.no_activity')}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </>
                )}

                <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
                    <button
                        type="button"
                        className="w-full py-3 bg-slate-800 dark:bg-slate-700 text-white font-bold rounded-2xl hover:bg-slate-900 transition-colors"
                        onClick={onClose}
                    >
                        {t('super_admin.tenant_detail.close')}
                    </button>
                </div>
            </div>
        </DentixDrawer>
    );
});

export default TenantDetailPanel;
