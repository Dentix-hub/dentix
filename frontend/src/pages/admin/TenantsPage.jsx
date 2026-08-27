import { useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import logger from '@/utils/logger';
import { api } from '@/api';
import { Modal, toast, ConfirmDialog } from '@/shared/ui';
import { Building2, Key, CalendarPlus } from 'lucide-react';
import TenantsManager from '@/features/admin/SuperAdmin/TenantsManager';
import TenantDetailPanel from '@/features/admin/SuperAdmin/TenantDetailPanel';
import { setAdminToken } from '@/utils';
import { useTranslation } from 'react-i18next';

export default function TenantsPage() {
    const { t } = useTranslation();
    const [searchParams, setSearchParams] = useSearchParams();
    const [tenants, setTenants] = useState([]);
    const [plans, setPlans] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedTenantId, setSelectedTenantId] = useState(null);

    // Confirmation dialog state
    const [confirmState, setConfirmState] = useState({
        isOpen: false,
        title: '',
        message: '',
        confirmText: '',
        variant: 'primary',
        onConfirm: () => {},
    });

    useEffect(() => {
        const idParam = searchParams.get('id');
        if (idParam) {
            const parsedId = parseInt(idParam, 10);
            if (!isNaN(parsedId)) {
                setSelectedTenantId(parsedId);
            }
        }
    }, [searchParams]);

    const handleSelectTenant = (id) => {
        setSelectedTenantId(id);
        if (id) {
            const nextParams = new URLSearchParams(searchParams);
            nextParams.set('id', String(id));
            setSearchParams(nextParams, { replace: true });
        }
    };

    const handleCloseTenantDetail = () => {
        setSelectedTenantId(null);
        if (searchParams.get('id')) {
            const nextParams = new URLSearchParams(searchParams);
            nextParams.delete('id');
            setSearchParams(nextParams, { replace: true });
        }
    };

    // Password Reset State
    const [showPasswordResetModal, setShowPasswordResetModal] = useState(null); // {tenantId, tenantName}
    const [tenantUsers, setTenantUsers] = useState([]);
    const [passwordResetForm, setPasswordResetForm] = useState({ user_id: '', new_password: '' });

    // Manual Renewal Modal State
    const [renewalModalTenant, setRenewalModalTenant] = useState(null); // tenant object
    const [renewalForm, setRenewalForm] = useState({
        plan_id: '',
        extension_days: 30,
        notes: '',
    });
    const [renewing, setRenewing] = useState(false);

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            const [tRes, pRes] = await Promise.all([
                api.get('/api/v1/admin/tenants'),
                api.get('/api/v1/admin/subscriptions/plans')
            ]);
            setTenants(Array.isArray(tRes.data) ? tRes.data : []);
            setPlans(Array.isArray(pRes.data) ? pRes.data : []);
        } catch (err) {
            logger.error('Error fetching data:', err);
            setTenants([]);
            setPlans([]);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const handleImpersonate = async (tenantId, userId, reason, scope = 'read_only') => {
        if (!reason || reason.trim().length < 5) {
            toast.error(t('super_admin.impersonate.reason_required', 'سبب الدخول للنظام مطلوب (5 أحرف على الأقل)'));
            return;
        }
        try {
            const params = {
                reason: reason.trim(),
                scope: scope || 'read_only',
            };
            if (userId) {
                params.user_id = userId;
            }

            const res = await api.post(`/api/v1/admin/tenants/${tenantId}/impersonate`, null, { params });
            const payload = res.data || res;
            const token = payload.access_token;
            if (!token) {
                throw new Error('لم يتم استلام رمز الدخول المؤقت من الخادم');
            }

            setAdminToken(token);
            if (typeof window !== 'undefined' && window.sessionStorage) {
                window.sessionStorage.setItem('dentix_impersonation_token', token);
                window.sessionStorage.setItem('dentix_impersonation_tenant', payload.tenant_name || '');
                window.sessionStorage.setItem('dentix_impersonation_user', payload.target_user || '');
                window.sessionStorage.setItem('dentix_impersonation_scope', payload.scope || 'read_only');
            }

            toast.success(res.message || `تم بدء جلسة الدخول المؤقتة لعيادة ${payload.tenant_name || ''}`);

            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 500);
        } catch (err) {
            const detail = err.response?.data?.detail || err.message || 'فشل عملية الدخول';
            toast.error('فشل عملية الدخول: ' + (typeof detail === 'string' ? detail : JSON.stringify(detail)));
        }
    };

    const handlePlanChange = (e, tenantId) => {
        const newPlanId = parseInt(e.target.value, 10);
        if (!newPlanId) return;

        setConfirmState({
            isOpen: true,
            title: t('super_admin.tenants.change_plan_title', 'تغيير باقة الاشتراك'),
            message: t('super_admin.tenants.change_plan_msg', 'هل أنت متأكد من تغيير الخطة؟ سيتم احتساب المدة الجديدة بدءاً من اليوم.'),
            confirmText: t('common.confirm', 'تأكيد'),
            variant: 'primary',
            onConfirm: async () => {
                try {
                    await api.post(`/api/v1/admin/tenants/${tenantId}/assign-plan`, null, {
                        params: { plan_id: newPlanId }
                    });
                    toast.success(t('super_admin.tenants.plan_changed_success', 'تم تغيير الباقة بنجاح'));
                    fetchData();
                } catch {
                    toast.error(t('super_admin.tenants.plan_change_failed', 'فشل تغيير الخطة'));
                } finally {
                    setConfirmState(prev => ({ ...prev, isOpen: false }));
                }
            }
        });
    };

    const handleOpenRenewal = (tenant) => {
        setRenewalModalTenant(tenant);
        setRenewalForm({
            plan_id: tenant.plan_id || '',
            extension_days: 30,
            notes: '',
        });
    };

    const handleManualRenewalSubmit = async (e) => {
        e?.preventDefault();
        if (!renewalModalTenant) return;
        setRenewing(true);
        try {
            const generatedIdempotencyKey = `manual_renew_${renewalModalTenant.id}_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
            const payload = {
                plan_id: renewalForm.plan_id ? parseInt(renewalForm.plan_id, 10) : undefined,
                extension_days: parseInt(renewalForm.extension_days, 10) || 30,
                notes: renewalForm.notes?.trim() || undefined,
                idempotency_key: generatedIdempotencyKey,
            };
            const res = await api.post(`/api/v1/admin/tenants/${renewalModalTenant.id}/renew`, payload);
            toast.success(res.message || 'تم تجديد الاشتراك يدوياً بنجاح');
            setRenewalModalTenant(null);
            fetchData();
        } catch (err) {
            logger.error('Error renewing subscription:', err);
            toast.error('فشل تجديد الاشتراك: ' + (err.response?.data?.detail || err.message));
        } finally {
            setRenewing(false);
        }
    };

    const handleResetPassword = async (tenantId) => {
        try {
            const res = await api.get(`/api/v1/admin/tenants/${tenantId}/users`);
            setTenantUsers(res.data.users || []);
            const tenant = tenants.find(t => t.id === tenantId);
            setShowPasswordResetModal({ tenantId, tenantName: tenant?.name || 'العيادة' });
            setPasswordResetForm({ user_id: '', new_password: '' });
        } catch (err) {
            logger.error('Error in handleResetPassword:', err);
            toast.error('فشل تحميل مستخدمي العيادة');
        }
    };

    const handleSubmitPasswordReset = async () => {
        if (!passwordResetForm.user_id || !passwordResetForm.new_password) {
            return toast.error('الرجاء اختيار المستخدم وإدخال كلمة المرور الجديدة');
        }
        if (passwordResetForm.new_password.length < 6) {
            return toast.error('كلمة المرور يجب أن تكون 6 أحرف على الأقل');
        }

        setConfirmState({
            isOpen: true,
            title: t('super_admin.tenants.reset_pw_title', 'إعادة تعيين كلمة المرور'),
            message: t('super_admin.tenants.reset_pw_msg', 'هل أنت متأكد من إعادة تعيين كلمة المرور لهذا الحساب؟'),
            confirmText: t('common.confirm', 'تأكيد'),
            variant: 'warning',
            onConfirm: async () => {
                try {
                    await api.post(`/api/v1/admin/system/users/${passwordResetForm.user_id}/reset-password`, {
                        new_password: passwordResetForm.new_password
                    });
                    setShowPasswordResetModal(null);
                    setPasswordResetForm({ user_id: '', new_password: '' });
                    toast.success('تم إعادة تعيين كلمة المرور بنجاح');
                } catch (err) {
                    logger.error(err);
                    toast.error('فشل إعادة تعيين كلمة المرور');
                } finally {
                    setConfirmState(prev => ({ ...prev, isOpen: false }));
                }
            }
        });
    };

    const getDaysRemaining = (endDate) => {
        if (!endDate) return null;
        const days = Math.ceil((new Date(endDate) - new Date()) / (1000 * 60 * 60 * 24));
        return days;
    };

    const handleArchiveTenant = (tenantId) => {
        setConfirmState({
            isOpen: true,
            title: t('super_admin.tenants.archive_title', 'أرشفة العيادة'),
            message: t('super_admin.tenants.archive_msg', 'هل أنت متأكد من أرشفة هذه العيادة؟ يمكنك استعادتها وتفعيلها لاحقاً.'),
            confirmText: t('super_admin.tenants.archive_btn', 'أرشفة'),
            variant: 'warning',
            onConfirm: async () => {
                try {
                    await api.delete(`/api/v1/admin/tenants/${tenantId}`);
                    fetchData();
                    toast.success(t('super_admin.tenants.archive_success', 'تمت أرشفة العيادة بنجاح'));
                } catch {
                    toast.error(t('super_admin.tenants.archive_fail', 'فشلت عملية أرشفة العيادة'));
                } finally {
                    setConfirmState(prev => ({ ...prev, isOpen: false }));
                }
            }
        });
    };

    const handleRestoreTenant = (tenantId) => {
        setConfirmState({
            isOpen: true,
            title: t('super_admin.tenants.restore_title', 'استعادة العيادة'),
            message: t('super_admin.tenants.restore_msg', 'هل أنت متأكد من استعادة هذه العيادة وتفعيل الوصول إليها؟'),
            confirmText: t('super_admin.tenants.restore_btn', 'استعادة'),
            variant: 'primary',
            onConfirm: async () => {
                try {
                    await api.post(`/api/v1/admin/tenants/${tenantId}/restore`);
                    fetchData();
                    toast.success(t('super_admin.tenants.restore_success', 'تمت استعادة العيادة بنجاح'));
                } catch {
                    toast.error(t('super_admin.tenants.restore_fail', 'فشلت عملية الاستعادة'));
                } finally {
                    setConfirmState(prev => ({ ...prev, isOpen: false }));
                }
            }
        });
    };

    const handlePermanentDelete = (tenantId) => {
        setConfirmState({
            isOpen: true,
            title: t('super_admin.tenants.permanent_title', 'حذف نهائي مدمر للعيادة'),
            message: t('super_admin.tenants.permanent_msg', 'تحذير شديد: هذا الإجراء سيقوم بحذف العيادة وجميع بياناتها (المرضى، المواعيد، المستخدمين، السجلات) بشكل نهائي ودائم ولا يمكن التراجع عنه مطلقاً! هل أنت متأكد تماماً؟'),
            confirmText: t('super_admin.tenants.permanent_btn', 'حذف نهائي دائم'),
            variant: 'danger',
            onConfirm: async () => {
                try {
                    await api.delete(`/api/v1/admin/tenants/${tenantId}/permanent`);
                    fetchData();
                    toast.success(t('super_admin.tenants.permanent_success', 'تم الحذف النهائي بنجاح'));
                } catch (error) {
                    logger.error(error);
                    toast.error(t('super_admin.tenants.permanent_fail', 'فشلت عملية الحذف النهائي'));
                } finally {
                    setConfirmState(prev => ({ ...prev, isOpen: false }));
                }
            }
        });
    };

    if (loading) return <div className="p-8 text-center text-slate-500 font-bold">{t('common.loading', 'جاري تحميل العيادات...')}</div>;

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <div className="flex items-center gap-4 bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800">
                <div className="bg-indigo-50 dark:bg-indigo-900/20 p-4 rounded-2xl text-indigo-600 dark:text-indigo-400 shrink-0">
                    <Building2 size={32} />
                </div>
                <div>
                    <h1 className="text-2xl font-extrabold text-slate-800 dark:text-white">{t('sidebar.clinics', 'إدارة العيادات')}</h1>
                    <p className="text-slate-500 dark:text-slate-400 font-medium mt-1 text-sm">{t('super_admin.tenants.subtitle', 'التحكم في العيادات والتجديد الإداري اليدوي')}</p>
                </div>
            </div>

            <TenantsManager
                tenants={tenants}
                plans={plans}
                handlePlanChange={handlePlanChange}
                getDaysRemaining={getDaysRemaining}
                handleArchiveTenant={handleArchiveTenant}
                handleRestoreTenant={handleRestoreTenant}
                handlePermanentDelete={handlePermanentDelete}
                onResetPassword={handleResetPassword}
                onManualRenew={handleOpenRenewal}
                onSelectTenant={handleSelectTenant}
            />

            <TenantDetailPanel
                tenantId={selectedTenantId}
                onClose={handleCloseTenantDetail}
                onImpersonate={handleImpersonate}
            />

            {/* Manual Renewal Modal */}
            {renewalModalTenant && (
                <Modal
                    isOpen
                    onClose={() => setRenewalModalTenant(null)}
                    title={t('super_admin.tenants.manual_renewal_title', 'تجديد اشتراك يدوي موثق')}
                    size="lg"
                    mobileVariant="dialog"
                >
                    <div className="space-y-6">
                        <p className="text-slate-500 dark:text-slate-400 text-sm font-bold">{renewalModalTenant.name}</p>
                        <form onSubmit={handleManualRenewalSubmit} className="space-y-4">
                            <div>
                                <label className="block text-sm font-bold text-slate-500 mb-1.5">{t('super_admin.tenants.plan_label', 'باقة الاشتراك')}</label>
                                <select
                                    value={renewalForm.plan_id}
                                    onChange={(e) => setRenewalForm({ ...renewalForm, plan_id: e.target.value })}
                                    className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-emerald-500 outline-none font-bold"
                                >
                                    <option value="">{t('super_admin.tenants.current_plan', 'الباقة الحالية')} ({renewalModalTenant.plan || 'بدون تغيير'})</option>
                                    {(plans || []).map(p => (
                                        <option key={p.id} value={p.id}>
                                            {p.display_name_ar || p.name} ({p.duration_days} {t('common.days', 'يوم')})
                                        </option>
                                    ))}
                                </select>
                            </div>

                            <div>
                                <label className="block text-sm font-bold text-slate-500 mb-1.5">{t('super_admin.tenants.extension_days', 'أيام التمديد الإضافية')}</label>
                                <input
                                    type="number"
                                    min="1"
                                    max="3650"
                                    value={renewalForm.extension_days}
                                    onChange={(e) => setRenewalForm({ ...renewalForm, extension_days: e.target.value })}
                                    className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-emerald-500 outline-none font-bold"
                                    required
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-bold text-slate-500 mb-1.5">{t('super_admin.tenants.renewal_notes', 'ملاحظات التجديد / سبب التمديد')}</label>
                                <textarea
                                    rows={2}
                                    value={renewalForm.notes}
                                    onChange={(e) => setRenewalForm({ ...renewalForm, notes: e.target.value })}
                                    placeholder={t('super_admin.tenants.notes_placeholder', 'مثال: تم سداد الاشتراك نقداً أو بموجب إيصال بنكي رقم ...')}
                                    className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-emerald-500 outline-none text-sm"
                                />
                            </div>

                            <button
                                type="submit"
                                disabled={renewing}
                                className="w-full py-4 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg shadow-emerald-600/20 text-lg transition-all cursor-pointer"
                            >
                                <CalendarPlus size={20} />
                                {renewing ? t('super_admin.tenants.documenting', 'جاري توثيق التجديد...') : t('super_admin.tenants.confirm_renewal', 'تأكيد وتوثيق التجديد')}
                            </button>
                        </form>
                    </div>
                </Modal>
            )}

            {/* Password Reset Modal */}
            {showPasswordResetModal && (
                <Modal
                    isOpen
                    onClose={() => setShowPasswordResetModal(null)}
                    title={t('super_admin.tenants.reset_pw_modal_title', 'إعادة تعيين كلمة المرور')}
                    size="md"
                    mobileVariant="dialog"
                >
                    <div className="space-y-4">
                        <p className="text-slate-500 dark:text-slate-400 text-sm font-bold">{showPasswordResetModal.tenantName}</p>
                        <div>
                            <label className="block text-sm font-bold text-slate-500 mb-1.5">{t('super_admin.tenants.select_user', 'المستخدم')}</label>
                            <select
                                value={passwordResetForm.user_id}
                                onChange={(e) => setPasswordResetForm({ ...passwordResetForm, user_id: e.target.value })}
                                className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-amber-500 outline-none font-bold"
                            >
                                <option value="">{t('super_admin.tenants.choose_user', 'اختر المستخدم')}</option>
                                {tenantUsers.map(u => (
                                    <option key={u.id} value={u.id}>
                                        {u.username || u.email || 'Unknown User'} ({u.email}) - {u.role}
                                        {!u.is_active && ' [معطل]'}
                                        {u.account_locked_until && ' [مقفل]'}
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm font-bold text-slate-500 mb-1.5">{t('super_admin.tenants.new_pw', 'كلمة المرور الجديدة')}</label>
                            <input
                                type="text"
                                value={passwordResetForm.new_password}
                                onChange={(e) => setPasswordResetForm({ ...passwordResetForm, new_password: e.target.value })}
                                placeholder={t('super_admin.tenants.pw_placeholder', 'أدخل كلمة المرور الجديدة (6 أحرف على الأقل)')}
                                className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-amber-500 outline-none font-bold"
                            />
                            <p className="text-xs text-slate-500 mt-2">💡 {t('super_admin.tenants.pw_hint', 'سيتم إلغاء قفل الحساب وتفعيله تلقائياً')}</p>
                        </div>
                        <button
                            type="button"
                            onClick={handleSubmitPasswordReset}
                            className="w-full py-4 bg-amber-500 hover:bg-amber-600 text-white rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg shadow-amber-500/20 text-lg transition-all cursor-pointer"
                        >
                            <Key size={20} />
                            {t('super_admin.tenants.reset_pw_action', 'إعادة تعيين كلمة المرور')}
                        </button>
                    </div>
                </Modal>
            )}

            {/* Shared Confirmation Dialog */}
            <ConfirmDialog
                isOpen={confirmState.isOpen}
                title={confirmState.title}
                message={confirmState.message}
                confirmText={confirmState.confirmText}
                variant={confirmState.variant}
                onConfirm={confirmState.onConfirm}
                onClose={() => setConfirmState(prev => ({ ...prev, isOpen: false }))}
                onCancel={() => setConfirmState(prev => ({ ...prev, isOpen: false }))}
            />
        </div>
    );
}
