import { useEffect, useState } from 'react';
import logger from '@/utils/logger';
import { api } from '@/api';
import { ToggleLeft, ToggleRight, Settings, Plus } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Modal, toast } from '@/shared/ui';

const EMPTY_FEATURE_FORM = {
    key: '',
    description: '',
    is_global_enabled: false,
    rollout_percentage: 0,
};

export default function FeatureManager({ tenants = [], onToggleGlobal }) {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';
    const [flags, setFlags] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [form, setForm] = useState(EMPTY_FEATURE_FORM);
    const [overrideTenants, setOverrideTenants] = useState({});

    useEffect(() => {
        fetchFlags();
    }, []);

    const fetchFlags = async () => {
        try {
            setLoading(true);
            const res = await api.get('/api/v1/admin/features');
            setFlags(Array.isArray(res.data) ? res.data : (Array.isArray(res) ? res : []));
        } catch (error) {
            logger.error(error);
            setFlags([]);
        } finally {
            setLoading(false);
        }
    };

    const closeCreateModal = () => {
        setShowModal(false);
        setForm(EMPTY_FEATURE_FORM);
    };

    const handleCreateFlag = async () => {
        if (!form.key.trim()) {
            toast.error(t('super_admin.features.key_required'));
            return;
        }

        const rollout = Number(form.rollout_percentage);
        if (!Number.isFinite(rollout) || rollout < 0 || rollout > 100) {
            toast.error(t('super_admin.features.rollout_invalid'));
            return;
        }

        try {
            await api.post('/api/v1/admin/features', {
                ...form,
                key: form.key.trim(),
                description: form.description.trim(),
                rollout_percentage: rollout,
            });
            closeCreateModal();
            await fetchFlags();
            toast.success(t('super_admin.features.create_success'));
        } catch (error) {
            const detail = error.response?.data?.detail || error.message;
            toast.error(`${t('super_admin.features.create_fail')}${detail ? `: ${detail}` : ''}`);
        }
    };

    const handleToggleGlobal = async (key, currentStatus) => {
        const nextStatus = !currentStatus;

        setFlags((prev) =>
            prev.map((flag) => (flag.key === key ? { ...flag, is_global_enabled: nextStatus } : flag)),
        );

        onToggleGlobal?.(key, nextStatus);

        try {
            await api.put(`/api/v1/admin/features/${key}`, { is_global_enabled: nextStatus });
            toast.success(
                t(
                    nextStatus
                        ? 'super_admin.features.global_enable_success'
                        : 'super_admin.features.global_disable_success',
                ),
            );
        } catch (error) {
            setFlags((prev) =>
                prev.map((flag) => (flag.key === key ? { ...flag, is_global_enabled: currentStatus } : flag)),
            );
            const detail = error.response?.data?.detail || error.message;
            toast.error(`${t('super_admin.features.global_update_fail')}${detail ? `: ${detail}` : ''}`);
        }
    };

    const handleOverride = async (key, tenantId, enabled) => {
        if (!tenantId) {
            toast.error(t('super_admin.features.select_clinic'));
            return;
        }

        try {
            await api.post('/api/v1/admin/features/override', {
                tenant_id: Number(tenantId),
                feature_key: key,
                is_enabled: enabled,
            });
            toast.success(t('super_admin.features.override_success'));
        } catch {
            toast.error(t('super_admin.features.override_fail'));
        }
    };

    if (loading) {
        return <div className="p-8 text-center text-slate-500">{t('super_admin.features.loading')}</div>;
    }

    return (
        <div className="space-y-6" dir={isRtl ? 'rtl' : 'ltr'}>
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 gap-4">
                <div className={isRtl ? 'text-right' : 'text-left'}>
                    <h3 className="text-2xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
                        <Settings className="text-indigo-500" />
                        {t('super_admin.features.title')}
                    </h3>
                    <p className="text-slate-500 mt-1">{t('super_admin.features.subtitle')}</p>
                </div>
                <button
                    type="button"
                    onClick={() => setShowModal(true)}
                    className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold flex items-center gap-2 shadow-lg shadow-indigo-500/20"
                >
                    <Plus size={20} />
                    {t('super_admin.features.new_feature')}
                </button>
            </div>

            <div className="grid grid-cols-1 gap-4">
                {flags.map((flag) => (
                    <div
                        key={flag.id}
                        className="bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 flex flex-col md:flex-row justify-between items-start md:items-center gap-4"
                    >
                        <div className="flex items-center gap-4">
                            <div className={`p-3 rounded-2xl ${flag.is_global_enabled ? 'bg-emerald-100 text-emerald-600' : 'bg-slate-100 text-slate-500'}`}>
                                <Settings size={24} />
                            </div>
                            <div className={isRtl ? 'text-right' : 'text-left'}>
                                <h4 className="font-bold text-lg text-slate-800 dark:text-white font-mono">{flag.key}</h4>
                                <p className="text-slate-500 text-sm">{flag.description}</p>
                                <div className={`flex items-center gap-2 mt-2 ${isRtl ? 'flex-row-reverse' : 'flex-row'}`}>
                                    <span className="text-xs bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded-lg text-slate-500 font-bold">
                                        {t('super_admin.features.rollout_label', { percentage: flag.rollout_percentage })}
                                    </span>
                                </div>
                            </div>
                        </div>

                        <div className={`flex flex-col md:flex-row items-center gap-4 w-full md:w-auto ${isRtl ? 'md:flex-row-reverse' : ''}`}>
                            <div className={`flex items-center gap-2 ${isRtl ? 'text-right' : 'text-left'}`}>
                                <select
                                    className="w-full md:w-40 text-sm p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800"
                                    value={overrideTenants[flag.key] || ''}
                                    onChange={(event) => setOverrideTenants((prev) => ({ ...prev, [flag.key]: event.target.value }))}
                                >
                                    <option value="">{t('super_admin.features.select_clinic')}</option>
                                    {tenants.map((tenant) => (
                                        <option key={tenant.id} value={tenant.id}>{tenant.name}</option>
                                    ))}
                                </select>
                                <button
                                    type="button"
                                    onClick={() => handleOverride(flag.key, overrideTenants[flag.key], true)}
                                    className="px-2.5 py-1.5 text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition-colors"
                                >
                                    {t('super_admin.features.enable')}
                                </button>
                                <button
                                    type="button"
                                    onClick={() => handleOverride(flag.key, overrideTenants[flag.key], false)}
                                    className="px-2.5 py-1.5 text-xs font-bold bg-rose-600 hover:bg-rose-700 text-white rounded-lg transition-colors"
                                >
                                    {t('super_admin.features.disable')}
                                </button>
                            </div>

                            <button
                                type="button"
                                onClick={() => handleToggleGlobal(flag.key, flag.is_global_enabled)}
                                className={`flex items-center gap-2 px-4 py-2 rounded-xl font-bold transition-all ${flag.is_global_enabled
                                    ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/20'
                                    : 'bg-slate-200 text-slate-500'}`}
                            >
                                {flag.is_global_enabled ? <ToggleRight /> : <ToggleLeft />}
                                {flag.is_global_enabled
                                    ? t('super_admin.features.global_enabled')
                                    : t('super_admin.features.disabled')}
                            </button>
                        </div>
                    </div>
                ))}
            </div>

            <Modal
                isOpen={showModal}
                onClose={closeCreateModal}
                title={t('super_admin.features.add_title')}
                maxWidth="max-w-md"
                closeLabel={t('super_admin.features.close_create')}
            >
                <div className="space-y-4" dir={isRtl ? 'rtl' : 'ltr'}>
                    <div className={isRtl ? 'text-right' : 'text-left'}>
                        <label htmlFor="feature-key" className="block text-sm font-bold text-slate-500 mb-1.5">
                            {t('super_admin.features.feature_key_label')}
                        </label>
                        <input
                            id="feature-key"
                            type="text"
                            dir="ltr"
                            placeholder="new_ai_feature"
                            value={form.key}
                            onChange={(event) => setForm({ ...form, key: event.target.value })}
                            className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 outline-none font-mono"
                        />
                    </div>
                    <div className={isRtl ? 'text-right' : 'text-left'}>
                        <label htmlFor="feature-description" className="block text-sm font-bold text-slate-500 mb-1.5">
                            {t('super_admin.features.description')}
                        </label>
                        <input
                            id="feature-description"
                            type="text"
                            value={form.description}
                            onChange={(event) => setForm({ ...form, description: event.target.value })}
                            className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 outline-none"
                        />
                    </div>
                    <div className={isRtl ? 'text-right' : 'text-left'}>
                        <label htmlFor="feature-rollout" className="block text-sm font-bold text-slate-500 mb-1.5">
                            {t('super_admin.features.rollout_percentage_label')}
                        </label>
                        <input
                            id="feature-rollout"
                            type="number"
                            min="0"
                            max="100"
                            value={form.rollout_percentage}
                            onChange={(event) => setForm({
                                ...form,
                                rollout_percentage: Math.max(0, Math.min(100, Number(event.target.value))),
                            })}
                            className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 outline-none"
                        />
                    </div>
                    <label className={`flex items-center gap-2 cursor-pointer ${isRtl ? 'flex-row-reverse justify-end' : ''}`}>
                        <input
                            type="checkbox"
                            checked={form.is_global_enabled}
                            onChange={(event) => setForm({ ...form, is_global_enabled: event.target.checked })}
                            className="w-5 h-5 accent-indigo-500"
                        />
                        <span className="font-bold text-slate-700 dark:text-slate-300">
                            {t('super_admin.features.global_enable')}
                        </span>
                    </label>

                    <button
                        type="button"
                        onClick={handleCreateFlag}
                        className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold shadow-lg"
                    >
                        {t('super_admin.features.save_btn')}
                    </button>
                </div>
            </Modal>
        </div>
    );
}
