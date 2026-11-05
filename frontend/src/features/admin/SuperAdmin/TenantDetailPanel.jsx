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
    CheckCircle2,
    XCircle,
    AlertTriangle,
    Cpu,
    Lock,
    PauseCircle,
    PlayCircle,
    PowerOff,
    ArrowDownCircle,
} from 'lucide-react';
import { api } from '@/api';
import { format } from 'date-fns';
import { ar, enUS } from 'date-fns/locale';
import { useTranslation } from 'react-i18next';
import { DentixDrawer, Modal } from '@/shared/ui';

const TenantDetailPanel = memo(function TenantDetailPanel({ tenantId, onClose, onImpersonate }) {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';
    const dateLocale = isRtl ? ar : enUS;
    const [data, setData] = useState(null);
    const [users, setUsers] = useState([]);
    const [selectedUser, setSelectedUser] = useState('');
    const [reason, setReason] = useState('');
    const [loading, setLoading] = useState(true);
    const [onboardingFeature, setOnboardingFeature] = useState(null);
    const [entitlements, setEntitlements] = useState(null);
    const [overrideLoading, setOverrideLoading] = useState(false);
    const [availablePlans, setAvailablePlans] = useState([]);
    const [selectedDowngradePlan, setSelectedDowngradePlan] = useState('');
    const [downgradeLoading, setDowngradeLoading] = useState(false);
    const [actionModal, setActionModal] = useState({
        open: false,
        type: null,
        title: '',
        preview: null,
        reason: '',
        loading: false,
    });

    useEffect(() => {
        if (!tenantId) return;
        const fetchDetails = async () => {
            try {
                setLoading(true);
                const [detailsRes, usersRes, entitlementsRes, plansRes] = await Promise.all([
                    api.get(`/api/v1/admin/tenants/${tenantId}/details`),
                    api.get(`/api/v1/admin/tenants/${tenantId}/users`),
                    api.get(`/api/v1/admin/tenants/${tenantId}/entitlements`).catch((err) => {
                        logger.error('Failed to load entitlements:', err);
                        return { data: null };
                    }),
                    api.get('/api/v1/admin/subscriptions/plans').catch((err) => {
                        logger.error('Failed to load plans:', err);
                        return { data: [] };
                    }),
                ]);
                setData(detailsRes.data);
                setOnboardingFeature(detailsRes.data?.tenant?.onboarding_feature || null);
                setUsers(usersRes.data.users || []);
                setEntitlements(entitlementsRes.data || null);
                setAvailablePlans(Array.isArray(plansRes?.data) ? plansRes.data : []);
                setSelectedUser('');
                setReason('');
            } catch (error) {
                logger.error(error);
                setData(null);
                setOnboardingFeature(null);
                setUsers([]);
                setEntitlements(null);
                setAvailablePlans([]);
            } finally {
                setLoading(false);
            }
        };
        fetchDetails();
    }, [tenantId]);

    if (!tenantId) return null;

    const handleOpenAction = async (type) => {
        const titleMap = {
            suspend: t('super_admin.tenant_detail.action_suspend_title', 'إيقاف الاشتراك تجارياً'),
            security_disable: t('super_admin.tenant_detail.action_security_title', 'تعطيل العيادة أمنياً (طوارئ)'),
            reactivate: t('super_admin.tenant_detail.action_reactivate_title', 'إعادة تفعيل العيادة'),
        };
        const endpointMap = {
            suspend: `/api/v1/admin/tenants/${tenantId}/suspend`,
            security_disable: `/api/v1/admin/tenants/${tenantId}/security-disable`,
            reactivate: `/api/v1/admin/tenants/${tenantId}/reactivate`,
        };
        setActionModal({
            open: true,
            type,
            title: titleMap[type] || '',
            preview: null,
            reason: '',
            loading: true,
        });
        try {
            const res = await api.post(endpointMap[type], {
                reason: 'Super Admin Preview Inspection',
                preview: true,
            });
            setActionModal((prev) => ({
                ...prev,
                preview: res.data || null,
                loading: false,
            }));
        } catch (err) {
            logger.error('Action preview failed:', err);
            setActionModal((prev) => ({ ...prev, loading: false }));
        }
    };

    const handleConfirmAction = async () => {
        if (!actionModal.reason || actionModal.reason.trim().length < 5) return;
        const endpointMap = {
            suspend: `/api/v1/admin/tenants/${tenantId}/suspend`,
            security_disable: `/api/v1/admin/tenants/${tenantId}/security-disable`,
            reactivate: `/api/v1/admin/tenants/${tenantId}/reactivate`,
        };
        try {
            setActionModal((prev) => ({ ...prev, loading: true }));
            const res = await api.post(endpointMap[actionModal.type], {
                reason: actionModal.reason.trim(),
                preview: false,
            });
            if (res.data?.resulting_state) {
                setData((prev) => (prev ? {
                    ...prev,
                    tenant: {
                        ...prev.tenant,
                        ...res.data.resulting_state,
                    },
                } : prev));
            }
            const entRes = await api.get(`/api/v1/admin/tenants/${tenantId}/entitlements`).catch(() => ({ data: null }));
            if (entRes.data) setEntitlements(entRes.data);

            setActionModal({ open: false, type: null, title: '', preview: null, reason: '', loading: false });
        } catch (err) {
            logger.error('Action execute failed:', err);
            setActionModal((prev) => ({ ...prev, loading: false }));
        }
    };

    const handleScheduleDowngrade = async () => {
        if (!selectedDowngradePlan) return;
        try {
            setDowngradeLoading(true);
            await api.post(`/api/v1/admin/tenants/${tenantId}/schedule-downgrade?plan_id=${selectedDowngradePlan}`);
            setData((prev) => (prev ? {
                ...prev,
                tenant: {
                    ...prev.tenant,
                    scheduled_downgrade_plan_id: Number(selectedDowngradePlan),
                },
            } : prev));
            setSelectedDowngradePlan('');
        } catch (err) {
            logger.error('Schedule downgrade failed:', err);
        } finally {
            setDowngradeLoading(false);
        }
    };

    const handleStartImpersonation = () => {
        if (!reason || reason.trim().length < 5) return;
        onImpersonate(data?.tenant?.id || tenantId, selectedUser, reason.trim(), 'read_only');
    };

    const handleSetOverride = async (target) => {
        try {
            setOverrideLoading(true);
            if (target === 'inherit') {
                await api.delete('/api/v1/admin/features/override', {
                    params: { tenant_id: tenantId, feature_key: 'onboarding_checklist' },
                });
            } else {
                await api.post('/api/v1/admin/features/override', {
                    tenant_id: tenantId,
                    feature_key: 'onboarding_checklist',
                    is_enabled: target === 'on',
                });
            }
            const updated = await api.get(`/api/v1/admin/features/tenant/${tenantId}/onboarding_checklist`);
            setOnboardingFeature(updated.data);
        } catch (err) {
            logger.error(err);
        } finally {
            setOverrideLoading(false);
        }
    };

    const overrideState = onboardingFeature?.override === true ? 'on' : onboardingFeature?.override === false ? 'off' : 'inherit';
    const effectiveState = onboardingFeature?.effective ?? false;

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

                        {/* PR-03: Commercial Entitlements & Subscription Access (Visually distinct from rollout pilots) */}
                        {entitlements && (
                            <div className="space-y-4">
                                <div className="flex items-center justify-between">
                                    <h4 className="text-sm font-bold text-slate-400 uppercase tracking-wider">
                                        {t('super_admin.tenant_detail.entitlements_title', 'الاستحقاقات التجارية والاشتراك')}
                                    </h4>
                                    <span
                                        className={`px-2.5 py-1 rounded-lg text-xs font-bold border ${
                                            entitlements.enforcement_mode === 'enforce'
                                                ? 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800'
                                                : entitlements.enforcement_mode === 'observe'
                                                ? 'bg-sky-50 text-sky-700 border-sky-200 dark:bg-sky-950/40 dark:text-sky-300 dark:border-sky-800'
                                                : 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800'
                                        }`}
                                    >
                                        {entitlements.enforcement_mode === 'enforce'
                                            ? t('super_admin.tenant_detail.mode_enforced', 'مفعّل وإلزامي')
                                            : entitlements.enforcement_mode === 'observe'
                                            ? t('super_admin.tenant_detail.mode_observe', 'مراقبة فقط')
                                            : t('super_admin.tenant_detail.mode_off', 'تقييم ظل (غير مفعّل)')}
                                    </span>
                                </div>

                                {/* Hard Disabled Alert */}
                                {entitlements.is_hard_disabled && (
                                    <div className="flex items-center gap-3 p-3.5 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-200 rounded-2xl text-xs font-semibold">
                                        <AlertTriangle size={18} className="text-rose-600 shrink-0" />
                                        <span>
                                            {t(
                                                'super_admin.tenant_detail.hard_disabled_warning',
                                                'حساب العيادة معطل أمنياً أو إدارياً (Hard Disabled) - يمنع أي وصول للعيادة حتى إعادة التفعيل.'
                                            )}
                                        </span>
                                    </div>
                                )}

                                {/* Plan & Lifecycle Summary */}
                                <div className="p-4 bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-800 space-y-3">
                                    <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-700/60">
                                        <div>
                                            <span className="text-xs text-slate-400 block font-medium">
                                                {t('super_admin.tenant_detail.effective_plan', 'الباقة المعتمدة')}
                                            </span>
                                            <span className="text-base font-bold text-slate-800 dark:text-white">
                                                {isRtl ? entitlements.plan_display_name_ar : entitlements.plan_display_name_en}
                                            </span>
                                        </div>
                                        <div className="text-end">
                                            <span className="text-xs text-slate-400 block font-medium">
                                                {t('super_admin.tenant_detail.status', 'حالة الاشتراك')}
                                            </span>
                                            <span
                                                className={`inline-block px-2 py-0.5 rounded-md text-xs font-bold uppercase ${
                                                    entitlements.effective_subscription_status === 'active' || entitlements.effective_subscription_status === 'trial'
                                                        ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300'
                                                        : entitlements.effective_subscription_status === 'grace'
                                                        ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'
                                                        : 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300'
                                                }`}
                                            >
                                                {entitlements.effective_subscription_status}
                                            </span>
                                        </div>
                                    </div>

                                    {/* Dates & Periods */}
                                    <div className="grid grid-cols-2 gap-2 text-xs">
                                        <div className="p-2.5 bg-slate-50 dark:bg-slate-700/40 rounded-xl">
                                            <span className="text-slate-400 block mb-0.5">
                                                {t('super_admin.tenant_detail.sub_end_date', 'تاريخ انتهاء الباقة')}
                                            </span>
                                            <span className="font-bold text-slate-700 dark:text-slate-200">
                                                {entitlements.subscription_end_date
                                                    ? format(new Date(entitlements.subscription_end_date), 'dd MMM yyyy', { locale: dateLocale })
                                                    : t('super_admin.tenant_detail.not_set', 'غير محدد')}
                                            </span>
                                        </div>
                                        <div className="p-2.5 bg-slate-50 dark:bg-slate-700/40 rounded-xl">
                                            <span className="text-slate-400 block mb-0.5">
                                                {t('super_admin.tenant_detail.grace_until', 'فترة السماح حتى')}
                                            </span>
                                            <span className="font-bold text-slate-700 dark:text-slate-200">
                                                {entitlements.grace_period_until
                                                    ? format(new Date(entitlements.grace_period_until), 'dd MMM yyyy', { locale: dateLocale })
                                                    : t('super_admin.tenant_detail.none', 'لا توجد')}
                                            </span>
                                        </div>
                                    </div>

                                    {/* Clinical Invariant Notice */}
                                    <div className="p-2.5 bg-indigo-50/70 dark:bg-indigo-950/30 border border-indigo-100 dark:border-indigo-900/50 rounded-xl text-xs text-indigo-900 dark:text-indigo-200 flex items-center gap-2">
                                        <Lock size={14} className="text-indigo-600 dark:text-indigo-400 shrink-0" />
                                        <span>
                                            {t(
                                                'super_admin.tenant_detail.clinical_invariant_notice',
                                                'حق دائم: قراءة السجلات الطبية السابقة متاحة دائماً ومحمية قانونياً ولا تحجب بأي سبب تجاري.'
                                            )}
                                        </span>
                                    </div>
                                </div>

                                {/* Truthful Capacities: Seats & AI */}
                                <div className="grid grid-cols-2 gap-3">
                                    <div className="p-3.5 bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-800 space-y-1">
                                        <div className="flex items-center gap-2 text-teal-600 dark:text-teal-400">
                                            <Users size={16} />
                                            <span className="text-xs font-bold">
                                                {t('super_admin.tenant_detail.seats_capacity', 'المقاعد النشطة')}
                                            </span>
                                        </div>
                                        <div className="text-lg font-bold text-slate-800 dark:text-white">
                                            {entitlements.capacities?.seats?.used || 0}
                                            <span className="text-xs font-normal text-slate-400">
                                                {' / '}
                                                {entitlements.capacities?.seats?.limit != null
                                                    ? entitlements.capacities.seats.limit
                                                    : t('super_admin.tenant_detail.unlimited', 'غير محدد')}
                                            </span>
                                        </div>
                                        <div className="text-[11px] text-slate-400">
                                            {entitlements.capacities?.seats?.is_exhausted
                                                ? t('super_admin.tenant_detail.seats_exhausted', 'تم استنفاد المقاعد')
                                                : `${t('super_admin.tenant_detail.seats_remaining', 'المتبقي')}: ${entitlements.capacities?.seats?.remaining ?? '-'}`}
                                        </div>
                                    </div>

                                    <div className="p-3.5 bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-800 space-y-1">
                                        <div className="flex items-center gap-2 text-indigo-600 dark:text-indigo-400">
                                            <Cpu size={16} />
                                            <span className="text-xs font-bold">
                                                {t('super_admin.tenant_detail.ai_capacity', 'حد الذكاء الاصطناعي')}
                                            </span>
                                        </div>
                                        <div className="text-lg font-bold text-slate-800 dark:text-white">
                                            {entitlements.capacities?.ai?.daily_limit || 0}
                                            <span className="text-xs font-normal text-slate-400">
                                                {' '}
                                                {t('super_admin.tenant_detail.per_day', 'طلب / يوم')}
                                            </span>
                                        </div>
                                        <div className="text-[11px] text-slate-400 truncate" title={entitlements.capacities?.ai?.historical_diagnostic_label}>
                                            {t('super_admin.tenant_detail.diagnostic_count', 'سجل تشخيص اليوم')}:{' '}
                                            {entitlements.capacities?.ai?.historical_diagnostic_count ?? 0}
                                        </div>
                                    </div>
                                </div>

                                {/* Capabilities Access Table */}
                                <div className="p-4 bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-800 space-y-2.5">
                                    <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                                        {t('super_admin.tenant_detail.capabilities_matrix', 'مصفوفة الخدمات والإمكانيات')}
                                    </div>
                                    <div className="space-y-1.5 divide-y divide-slate-100 dark:divide-slate-700/50">
                                        {Object.values(entitlements.capabilities || {})
                                            .filter((cap) => cap.is_sellable)
                                            .map((cap) => (
                                                <div key={cap.key} className="pt-1.5 first:pt-0 flex items-center justify-between text-xs">
                                                    <div className="flex items-center gap-2 min-w-0">
                                                        {cap.effective_allowed ? (
                                                            <CheckCircle2 size={15} className="text-emerald-500 shrink-0" />
                                                        ) : (
                                                            <XCircle size={15} className="text-slate-400 shrink-0" />
                                                        )}
                                                        <span className="font-semibold text-slate-700 dark:text-slate-200 truncate">
                                                            {isRtl ? cap.display_name_ar : cap.display_name_en}
                                                        </span>
                                                    </div>
                                                    <div className="flex items-center gap-1.5 shrink-0">
                                                        <span
                                                            className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                                                cap.effective_allowed
                                                                    ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-400'
                                                                    : 'bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400'
                                                            }`}
                                                        >
                                                            {cap.effective_allowed
                                                                ? t('super_admin.tenant_detail.allowed', 'متاح')
                                                                : t('super_admin.tenant_detail.denied', 'محجوب')}
                                                        </span>
                                                        <span className="text-[10px] text-slate-400">
                                                            ({cap.enforcement_status === 'enforced'
                                                                ? t('super_admin.tenant_detail.status_enforced', 'مطبق')
                                                                : t('super_admin.tenant_detail.status_shadow', 'ظل')})
                                                        </span>
                                                    </div>
                                                </div>
                                            ))}
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* PR-11 Commercial & Security Lifecycle Actions */}
                        <div className="space-y-4">
                            <h4 className="text-sm font-bold text-slate-400 uppercase tracking-wider">
                                {t('super_admin.tenant_detail.admin_actions_title', 'التحكم الإداري والتجاري')}
                            </h4>
                            <div className="p-4 bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-800 space-y-3">
                                <div className="grid grid-cols-2 gap-2 text-xs font-bold">
                                    {data.tenant?.subscription_status !== 'suspended_admin' ? (
                                        <button
                                            type="button"
                                            onClick={() => handleOpenAction('suspend')}
                                            className="flex items-center justify-center gap-1.5 py-2.5 px-3 bg-amber-50 hover:bg-amber-100 dark:bg-amber-950/30 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800 rounded-xl transition-all cursor-pointer"
                                        >
                                            <PauseCircle size={15} />
                                            <span>{t('super_admin.tenant_detail.btn_suspend', 'إيقاف تجاري')}</span>
                                        </button>
                                    ) : (
                                        <button
                                            type="button"
                                            onClick={() => handleOpenAction('reactivate')}
                                            className="flex items-center justify-center gap-1.5 py-2.5 px-3 bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 rounded-xl transition-all cursor-pointer"
                                        >
                                            <PlayCircle size={15} />
                                            <span>{t('super_admin.tenant_detail.btn_reactivate', 'إعادة التفعيل')}</span>
                                        </button>
                                    )}

                                    {data.tenant?.is_active !== false ? (
                                        <button
                                            type="button"
                                            onClick={() => handleOpenAction('security_disable')}
                                            className="flex items-center justify-center gap-1.5 py-2.5 px-3 bg-rose-50 hover:bg-rose-100 dark:bg-rose-950/30 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800 rounded-xl transition-all cursor-pointer"
                                        >
                                            <PowerOff size={15} />
                                            <span>{t('super_admin.tenant_detail.btn_security_disable', 'تعطيل أمني')}</span>
                                        </button>
                                    ) : (
                                        <button
                                            type="button"
                                            onClick={() => handleOpenAction('reactivate')}
                                            className="flex items-center justify-center gap-1.5 py-2.5 px-3 bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 rounded-xl transition-all cursor-pointer"
                                        >
                                            <PlayCircle size={15} />
                                            <span>{t('super_admin.tenant_detail.btn_reactivate', 'إعادة التفعيل')}</span>
                                        </button>
                                    )}
                                </div>

                                {/* Scheduled Downgrade Section */}
                                <div className="pt-3 border-t border-slate-100 dark:border-slate-700/60 space-y-2">
                                    <div className="flex items-center justify-between text-xs">
                                        <span className="font-bold text-slate-600 dark:text-slate-300 flex items-center gap-1.5">
                                            <ArrowDownCircle size={14} className="text-slate-400" />
                                            {t('super_admin.tenant_detail.schedule_downgrade', 'جدولة تخفيض عند التجديد')}
                                        </span>
                                        {data.tenant?.scheduled_downgrade_plan_id && (
                                            <span className="text-[11px] font-bold text-amber-600 bg-amber-50 dark:bg-amber-950/40 px-2 py-0.5 rounded-md border border-amber-200 dark:border-amber-800">
                                                {t('super_admin.tenant_detail.downgrade_scheduled', 'مجدول')}
                                            </span>
                                        )}
                                    </div>
                                    <div className="flex gap-2">
                                        <select
                                            value={selectedDowngradePlan}
                                            onChange={(e) => setSelectedDowngradePlan(e.target.value)}
                                            className="flex-1 bg-slate-50 dark:bg-slate-700/60 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 text-xs rounded-xl px-3 py-2 outline-none"
                                        >
                                            <option value="">{t('super_admin.tenant_detail.select_downgrade_plan', 'اختر الباقة المستهدفة...')}</option>
                                            {(Array.isArray(availablePlans) ? availablePlans : [])
                                                .filter((p) => p && p.is_active && p.id !== data.tenant?.plan_id)
                                                .map((p) => (
                                                    <option key={p.id} value={p.id}>
                                                        {isRtl ? (p.display_name_ar || p.name) : (p.display_name_en || p.name)} ({p.price} EGP)
                                                    </option>
                                                ))}
                                        </select>
                                        <button
                                            type="button"
                                            onClick={handleScheduleDowngrade}
                                            disabled={!selectedDowngradePlan || downgradeLoading}
                                            className="px-3 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 text-white text-xs font-bold rounded-xl transition-all shrink-0 cursor-pointer"
                                        >
                                            {t('super_admin.tenant_detail.schedule_btn', 'جدولة')}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="space-y-4">
                            <h4 className="text-sm font-bold text-slate-400 uppercase tracking-wider">
                                {t('super_admin.tenant_detail.features_title', 'ميزات العيادة ومسار البداية')}
                            </h4>
                            <div className="p-4 bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-800 space-y-3">
                                <div>
                                    <span className="text-sm font-bold text-slate-800 dark:text-white block">
                                        {t('super_admin.tenant_detail.onboarding_checklist', 'دليل البداية وقائمة المهام')}
                                    </span>
                                    <span className="text-xs text-slate-500">
                                        {t('super_admin.tenant_detail.effective_status', 'الحالة الفعلية')}:{' '}
                                        <strong className={effectiveState ? 'text-emerald-500 font-bold' : 'text-slate-400 font-bold'}>
                                            {effectiveState
                                                ? t('super_admin.tenant_detail.status_enabled', 'مفعل')
                                                : t('super_admin.tenant_detail.status_disabled', 'معطل')}
                                        </strong>
                                        {overrideState === 'inherit' && ` (${t('super_admin.tenant_detail.inherited', 'موروث من الإعداد العام')})`}
                                    </span>
                                </div>

                                <div className="flex rounded-xl bg-slate-100 dark:bg-slate-700/60 p-1 gap-1 text-xs font-bold">
                                    <button
                                        type="button"
                                        onClick={() => handleSetOverride('inherit')}
                                        disabled={overrideLoading}
                                        className={`flex-1 py-1.5 rounded-lg transition-colors ${
                                            overrideState === 'inherit'
                                                ? 'bg-white dark:bg-slate-800 text-slate-800 dark:text-white shadow-xs'
                                                : 'text-slate-500 hover:text-slate-800 dark:hover:text-white'
                                        }`}
                                    >
                                        {t('super_admin.tenant_detail.inherit', 'تلقائي (وراثة)')}
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => handleSetOverride('on')}
                                        disabled={overrideLoading}
                                        className={`flex-1 py-1.5 rounded-lg transition-colors ${
                                            overrideState === 'on'
                                                ? 'bg-emerald-500 text-white shadow-xs'
                                                : 'text-slate-500 hover:text-slate-800 dark:hover:text-white'
                                        }`}
                                    >
                                        {t('super_admin.tenant_detail.force_on', 'تفعيل إجباري')}
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => handleSetOverride('off')}
                                        disabled={overrideLoading}
                                        className={`flex-1 py-1.5 rounded-lg transition-colors ${
                                            overrideState === 'off'
                                                ? 'bg-rose-500 text-white shadow-xs'
                                                : 'text-slate-500 hover:text-slate-800 dark:hover:text-white'
                                        }`}
                                    >
                                        {t('super_admin.tenant_detail.force_off', 'تعطيل إجباري')}
                                    </button>
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

                {/* PR-11 Action Confirmation & Preview Modal */}
                <Modal
                    isOpen={actionModal.open}
                    onClose={() => setActionModal({ open: false, type: null, title: '', preview: null, reason: '', loading: false })}
                    title={actionModal.title}
                    maxWidth="max-w-md"
                >
                    <div className="space-y-4 pt-2">
                        {actionModal.loading && !actionModal.preview ? (
                            <div className="p-4 text-center text-xs text-slate-500 animate-pulse">
                                {t('super_admin.tenant_detail.loading_preview', 'جاري جلب معاينة الأثر...')}
                            </div>
                        ) : (
                            <>
                                {actionModal.preview && (
                                    <div className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-xl space-y-2 text-xs border border-slate-100 dark:border-slate-700/60">
                                        <div className="flex justify-between">
                                            <span className="text-slate-400">{t('super_admin.tenant_detail.current_status', 'الحالة الحالية')}:</span>
                                            <span className="font-bold text-slate-700 dark:text-slate-300">
                                                {String(actionModal.preview.previous_state?.subscription_status || '')}
                                            </span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-slate-400">{t('super_admin.tenant_detail.resulting_status', 'الحالة الناتجة')}:</span>
                                            <span className="font-bold text-indigo-600 dark:text-indigo-400">
                                                {String(actionModal.preview.resulting_state?.subscription_status || '')}
                                            </span>
                                        </div>
                                        {actionModal.preview.clinical_history_preserved && (
                                            <div className="pt-2 border-t border-slate-200 dark:border-slate-700 text-[11px] text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                                                <Lock size={12} className="shrink-0" />
                                                <span>{t('super_admin.tenant_detail.invariant_guarantee', 'قراءة السجلات السريرية السابقة تظل متاحة ومحمية قانونياً.')}</span>
                                            </div>
                                        )}
                                    </div>
                                )}

                                <div>
                                    <label className="block text-xs font-bold text-slate-600 dark:text-slate-400 mb-1">
                                        {t('super_admin.tenant_detail.reason_label', 'سبب القرار الإداري (مطلوب - للتوثيق الأمني):')}
                                    </label>
                                    <textarea
                                        value={actionModal.reason}
                                        onChange={(e) => setActionModal((prev) => ({ ...prev, reason: e.target.value }))}
                                        placeholder={t('super_admin.tenant_detail.reason_min_placeholder', 'اكتب سبب الإجراء هنا (5 أحرف على الأقل)...')}
                                        rows={3}
                                        className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-3 text-xs outline-none focus:ring-2 focus:ring-indigo-500"
                                    />
                                    {actionModal.reason && actionModal.reason.trim().length < 5 && (
                                        <p className="text-[11px] text-rose-500 mt-1">
                                            {t('super_admin.tenant_detail.min_reason', 'الحد الأدنى 5 أحرف')}
                                        </p>
                                    )}
                                </div>
                            </>
                        )}

                        <div className="flex gap-2 pt-2">
                            <button
                                type="button"
                                onClick={() => setActionModal({ open: false, type: null, title: '', preview: null, reason: '', loading: false })}
                                className="flex-1 py-2.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 font-bold text-xs rounded-xl transition-all cursor-pointer"
                            >
                                {t('common.cancel', 'إلغاء')}
                            </button>
                            <button
                                type="button"
                                onClick={handleConfirmAction}
                                disabled={!actionModal.reason || actionModal.reason.trim().length < 5 || actionModal.loading}
                                className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 text-white font-bold text-xs rounded-xl transition-all cursor-pointer"
                            >
                                {actionModal.loading ? t('common.loading', 'جاري التنفيذ...') : t('common.confirm', 'تأكيد التنفيذ')}
                            </button>
                        </div>
                    </div>
                </Modal>
            </div>
        </DentixDrawer>
    );
});

export default TenantDetailPanel;
