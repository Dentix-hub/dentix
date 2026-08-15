import { useState, useEffect } from 'react';
import logger from '@/utils/logger';
import { api } from '@/api';
import { ToggleLeft, ToggleRight, Settings, Plus, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';

export default function FeatureManager({ tenants }) {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';
    const [flags, setFlags] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);

    // Form State
    const [form, setForm] = useState({ key: '', description: '', is_global_enabled: false, rollout_percentage: 100 });

    // Override State
    const [overrideTenant, setOverrideTenant] = useState(null); // ID of tenant to override

    useEffect(() => {
        fetchFlags();
    }, []);

    const fetchFlags = async () => {
        try {
            setLoading(true);
            const res = await api.get('/api/v1/admin/features/');
            setFlags(res.data);
        } catch (error) {
            logger.error(error);
        } finally {
            setLoading(false);
        }
    };

    const handleCreateFlag = async () => {
        if (!form.key) return alert(t('super_admin.features.key_required'));
        try {
            await api.post('/api/v1/admin/features/', form);
            setShowModal(false);
            setForm({ key: '', description: '', is_global_enabled: false, rollout_percentage: 100 });
            fetchFlags();
            alert(t('super_admin.features.create_success'));
        } catch (error) {
            alert(t('super_admin.features.create_fail'));
        }
    };

    const handleToggleGlobal = async (key, currentStatus) => {
        try {
            await api.put(`/api/v1/admin/features/${key}`, { is_global_enabled: !currentStatus });
            fetchFlags();
        } catch (err) {
            alert("غير مدعوم حالياً (API Update Missing)");
        }
    };

    const handleOverride = async (key, tenantId, enabled) => {
        try {
            await api.post('/api/v1/admin/features/override', {
                tenant_id: tenantId,
                feature_key: key,
                is_enabled: enabled
            });
            alert(t('super_admin.features.override_success'));
        } catch (err) {
            alert(t('super_admin.features.override_fail'));
        }
    };

    if (loading) return <div className="p-8 text-center text-slate-500">{t('super_admin.features.loading')}</div>;

    return (
        <div className="space-y-6" dir={isRtl ? 'rtl' : 'ltr'}>
            <div className={`flex flex-col md:flex-row justify-between items-start md:items-center bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 gap-4`}>
                <div className={isRtl ? 'text-right' : 'text-left'}>
                    <h3 className="text-2xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
                        <Settings className="text-indigo-500" />
                        {t('super_admin.features.title')}
                    </h3>
                    <p className="text-slate-500 mt-1">{t('super_admin.features.subtitle')}</p>
                </div>
                <button
                    onClick={() => setShowModal(true)}
                    className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold flex items-center gap-2 shadow-lg shadow-indigo-500/20"
                >
                    <Plus size={20} />
                    {t('super_admin.features.new_feature')}
                </button>
            </div>

            <div className="grid grid-cols-1 gap-4">
                {flags.map(flag => (
                    <div key={flag.id} className={`bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 flex flex-col md:flex-row justify-between items-start md:items-center gap-4`}>
                        <div className="flex items-center gap-4">
                            <div className={`p-3 rounded-2xl ${flag.is_global_enabled ? 'bg-emerald-100 text-emerald-600' : 'bg-slate-100 text-slate-500'}`}>
                                <Settings size={24} />
                            </div>
                            <div className={isRtl ? 'text-right' : 'text-left'}>
                                <h4 className="font-bold text-lg text-slate-800 dark:text-white font-mono">{flag.key}</h4>
                                <p className="text-slate-500 text-sm">{flag.description}</p>
                                <div className={`flex items-center gap-2 mt-2 ${isRtl ? 'flex-row-reverse' : 'flex-row'}`}>
                                    <span className="text-xs bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded-lg text-slate-500 font-bold">
                                        Rollout: {flag.rollout_percentage}%
                                    </span>
                                </div>
                            </div>
                        </div>

                        <div className={`flex flex-col md:flex-row items-center gap-4 w-full md:w-auto ${isRtl ? 'md:flex-row-reverse' : ''}`}>
                            <div className={isRtl ? 'text-right' : 'text-left'}>
                                <label className="text-xs font-bold text-slate-500 block mb-1">override tenant</label>
                                <select
                                    className="w-full md:w-40 text-sm p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800"
                                    onChange={(e) => {
                                        if (e.target.value) handleOverride(flag.key, parseInt(e.target.value), !flag.is_global_enabled)
                                    }}
                                >
                                    <option value="">{t('super_admin.features.select_clinic')}</option>
                                    {(tenants || []).map(t => (
                                        <option key={t.id} value={t.id}>{t.name}</option>
                                    ))}
                                </select>
                            </div>

                            <button
                                onClick={() => handleToggleGlobal(flag.key, flag.is_global_enabled)}
                                className={`flex items-center gap-2 px-4 py-2 rounded-xl font-bold transition-all ${flag.is_global_enabled
                                    ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/20'
                                    : 'bg-slate-200 text-slate-500'}`}
                            >
                                {flag.is_global_enabled ? <ToggleRight /> : <ToggleLeft />}
                                {flag.is_global_enabled ? t('super_admin.features.global_enabled') : t('super_admin.features.disabled')}
                            </button>
                        </div>
                    </div>
                ))}
            </div>

            {/* Create Modal */}
            {showModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-fade-in" dir={isRtl ? 'rtl' : 'ltr'}>
                    <div className="bg-white dark:bg-slate-900 rounded-3xl p-8 w-full max-w-md shadow-2xl space-y-6">
                        <div className="flex justify-between items-center">
                            <h3 className="text-xl font-bold text-slate-800 dark:text-white">{t('super_admin.features.add_title')}</h3>
                            <button onClick={() => setShowModal(false)}><X className="text-slate-500" /></button>
                        </div>

                        <div className="space-y-4">
                            <div className={isRtl ? 'text-right' : 'text-left'}>
                                <label className="block text-sm font-bold text-slate-500 mb-1.5">Feature Key (Unique)</label>
                                <input
                                    type="text"
                                    dir="ltr"
                                    placeholder="new_ai_feature"
                                    value={form.key}
                                    onChange={(e) => setForm({ ...form, key: e.target.value })}
                                    className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 outline-none font-mono"
                                />
                            </div>
                            <div className={isRtl ? 'text-right' : 'text-left'}>
                                <label className="block text-sm font-bold text-slate-500 mb-1.5">{t('super_admin.features.description')}</label>
                                <input
                                    type="text"
                                    value={form.description}
                                    onChange={(e) => setForm({ ...form, description: e.target.value })}
                                    className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 outline-none"
                                />
                            </div>
                            <div className={`flex items-center gap-3 ${isRtl ? 'flex-row-reverse' : ''}`}>
                                <label className={`flex items-center gap-2 cursor-pointer ${isRtl ? 'flex-row-reverse' : ''}`}>
                                    <input
                                        type="checkbox"
                                        checked={form.is_global_enabled}
                                        onChange={(e) => setForm({ ...form, is_global_enabled: e.target.checked })}
                                        className="w-5 h-5 accent-indigo-500"
                                    />
                                    <span className="font-bold text-slate-700 dark:text-slate-300">{t('super_admin.features.global_enable')}</span>
                                </label>
                            </div>

                            <button
                                onClick={handleCreateFlag}
                                className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold shadow-lg"
                            >
                                {t('super_admin.features.save_btn')}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}


