import React from 'react';
import logger from '@/utils/logger';
import { Edit3, Save, X, Users, Activity, PlusCircle, Trash2, CheckSquare, Square, Sparkles } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { createSubscriptionPlan, api } from '@/api';
import { toast } from '@/shared/ui';
import { KNOWN_PLAN_FEATURES, parseFeatures, serializeFeatures } from './planFeatureUtils';


const PlansManager = ({ plans, editingPlan, setEditingPlan, editedPlanData, setEditedPlanData, handleSavePlan, onRefresh }) => {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';
    const [isCreating, setIsCreating] = React.useState(false);
    const [newPlanData, setNewPlanData] = React.useState({
        name: '',
        display_name_ar: '',
        price: 0,
        duration_days: 30,
        max_users: null,
        max_patients: null,
        features: '[]',
        is_ai_enabled: false,
        ai_daily_limit: 0,
        is_default: false,
    });
    const [newSelectedFeatures, setNewSelectedFeatures] = React.useState([]);
    const [newCustomFeatures, setNewCustomFeatures] = React.useState('');

    // Feature toggling for creation
    const toggleNewFeature = (key) => {
        const updated = newSelectedFeatures.includes(key)
            ? newSelectedFeatures.filter(k => k !== key)
            : [...newSelectedFeatures, key];
        setNewSelectedFeatures(updated);
        setNewPlanData(prev => ({
            ...prev,
            features: serializeFeatures(updated, newCustomFeatures)
        }));
    };

    const handleNewCustomChange = (text) => {
        setNewCustomFeatures(text);
        setNewPlanData(prev => ({
            ...prev,
            features: serializeFeatures(newSelectedFeatures, text)
        }));
    };

    const handleCreatePlan = async () => {
        if (!newPlanData.name || !newPlanData.display_name_ar) {
            toast.error(t('super_admin.plans.fill_required') || 'يرجى ملء الحقول المطلوبة');
            return;
        }
        try {
            const payload = {
                ...newPlanData,
                features: serializeFeatures(newSelectedFeatures, newCustomFeatures),
            };
            await createSubscriptionPlan(payload);
            setIsCreating(false);
            setNewPlanData({
                name: '',
                display_name_ar: '',
                price: 0,
                duration_days: 30,
                max_users: null,
                max_patients: null,
                features: '[]',
                is_ai_enabled: false,
                ai_daily_limit: 0,
                is_default: false,
            });
            setNewSelectedFeatures([]);
            setNewCustomFeatures('');
            if (onRefresh) onRefresh();
            toast.success(t('super_admin.plans.create_success') || 'تم إنشاء الخطة بنجاح');
        } catch (err) {
            logger.error(err);
            const detail = err.response?.data?.detail || err.message;
            toast.error(t('super_admin.plans.create_fail') + ': ' + (typeof detail === 'string' ? detail : JSON.stringify(detail)));
        }
    };

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8" dir={isRtl ? 'rtl' : 'ltr'}>
            {(Array.isArray(plans) ? plans : []).map(plan => {
                const isEditing = editingPlan === plan.id;
                const currentFeatures = isEditing 
                    ? parseFeatures(editedPlanData.features !== undefined ? editedPlanData.features : plan.features)
                    : parseFeatures(plan.features);

                const toggleEditFeature = (key) => {
                    const keys = currentFeatures.keys.includes(key)
                        ? currentFeatures.keys.filter(k => k !== key)
                        : [...currentFeatures.keys, key];
                    const serialized = serializeFeatures(keys, currentFeatures.custom);
                    setEditedPlanData({ ...editedPlanData, features: serialized });
                };

                const handleEditCustomChange = (text) => {
                    const serialized = serializeFeatures(currentFeatures.keys, text);
                    setEditedPlanData({ ...editedPlanData, features: serialized });
                };

                return (
                    <div key={plan.id} className={`relative group bg-white dark:bg-slate-900 rounded-2xl p-8 border hover:border-indigo-500/50 transition-all duration-300 ${isEditing ? 'border-indigo-500 ring-4 ring-indigo-500/10 z-10 scale-105 shadow-2xl' : 'border-slate-100 dark:border-slate-800 shadow-lg'}`}>
                        {isEditing ? (
                            <div className="space-y-5 animate-fade-in">
                                <div className="flex items-center gap-2 mb-4 text-indigo-600 font-bold pb-4 border-b border-indigo-100 dark:border-indigo-900/30">
                                    <Edit3 size={20} />
                                    {t('super_admin.plans.edit_plan')}
                                </div>

                                <div>
                                    <label className={`block text-xs font-bold text-slate-500 mb-1.5 ${isRtl ? 'me-1' : 'ms-1'}`}>{t('super_admin.plans.plan_name_label')}</label>
                                    <input
                                        type="text"
                                        value={editedPlanData.display_name_ar ?? plan.display_name_ar}
                                        onChange={(e) => setEditedPlanData({ ...editedPlanData, display_name_ar: e.target.value })}
                                        className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all font-bold"
                                        placeholder={isRtl ? "مثال: الباقة الذهبية" : "Example: Gold Plan"}
                                    />
                                </div>

                                <div className="flex gap-4">
                                    <div className="flex-1">
                                        <label className={`block text-xs font-bold text-slate-500 mb-1.5 ${isRtl ? 'me-1' : 'ms-1'}`}>{t('super_admin.plans.price_label')} ({t('super_admin.finance.currency')})</label>
                                        <input
                                            type="number"
                                            value={editedPlanData.price ?? plan.price}
                                            onChange={(e) => setEditedPlanData({ ...editedPlanData, price: parseFloat(e.target.value) })}
                                            className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-indigo-500 outline-none font-bold"
                                        />
                                    </div>
                                    <div className="flex-1">
                                        <label className={`block text-xs font-bold text-slate-500 mb-1.5 ${isRtl ? 'me-1' : 'ms-1'}`}>{t('super_admin.plans.duration_label')}</label>
                                        <input
                                            type="number"
                                            value={editedPlanData.duration_days ?? plan.duration_days}
                                            onChange={(e) => setEditedPlanData({ ...editedPlanData, duration_days: parseInt(e.target.value) })}
                                            className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-indigo-500 outline-none font-bold"
                                        />
                                    </div>
                                </div>

                                <div className="flex gap-4">
                                    <div className="flex-1">
                                        <label className={`block text-xs font-bold text-slate-500 mb-1.5 ${isRtl ? 'me-1' : 'ms-1'}`}>{t('super_admin.plans.users_label')}</label>
                                        <input
                                            type="number"
                                            value={editedPlanData.max_users ?? plan.max_users ?? ''}
                                            onChange={(e) => setEditedPlanData({ ...editedPlanData, max_users: e.target.value ? parseInt(e.target.value) : null })}
                                            className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-indigo-500 outline-none font-bold placeholder-slate-300"
                                            placeholder="∞"
                                        />
                                    </div>
                                    <div className="flex-1">
                                        <label className={`block text-xs font-bold text-slate-500 mb-1.5 ${isRtl ? 'me-1' : 'ms-1'}`}>{t('super_admin.plans.patients_label')}</label>
                                        <input
                                            type="number"
                                            value={editedPlanData.max_patients ?? plan.max_patients ?? ''}
                                            onChange={(e) => setEditedPlanData({ ...editedPlanData, max_patients: e.target.value ? parseInt(e.target.value) : null })}
                                            className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-indigo-500 outline-none font-bold placeholder-slate-300"
                                            placeholder="∞"
                                        />
                                    </div>
                                </div>

                                {/* Synchronized Feature Checklist */}
                                <div className="p-4 bg-slate-50 dark:bg-slate-800/60 rounded-2xl border border-slate-200 dark:border-slate-700 space-y-3">
                                    <label className="block text-xs font-bold text-slate-600 dark:text-slate-300 uppercase tracking-wider">
                                        {t('super_admin.plans.features_label') || 'مميزات الخطة المتاحة'}
                                    </label>
                                    <div className="grid grid-cols-1 gap-2">
                                        {KNOWN_PLAN_FEATURES.map(feat => {
                                            const isChecked = currentFeatures.keys.includes(feat.key);
                                            return (
                                                <label
                                                    key={feat.key}
                                                    onClick={() => toggleEditFeature(feat.key)}
                                                    className={`flex items-center gap-3 p-2 rounded-xl text-xs font-bold cursor-pointer transition-all ${
                                                        isChecked 
                                                        ? 'bg-indigo-100/70 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300' 
                                                        : 'hover:bg-slate-200/50 dark:hover:bg-slate-700/50 text-slate-600 dark:text-slate-400'
                                                    }`}
                                                >
                                                    {isChecked ? <CheckSquare size={16} className="text-indigo-600 shrink-0" /> : <Square size={16} className="text-slate-400 shrink-0" />}
                                                    <span>{isRtl ? feat.label_ar : feat.label_en}</span>
                                                </label>
                                            );
                                        })}
                                    </div>
                                    <div className="pt-2 border-t border-slate-200 dark:border-slate-700">
                                        <input
                                            type="text"
                                            value={currentFeatures.custom}
                                            onChange={(e) => handleEditCustomChange(e.target.value)}
                                            placeholder="مميزات إضافية مخصصة (مفصولة بفواصل)"
                                            className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs outline-none focus:ring-2 focus:ring-indigo-500"
                                        />
                                    </div>
                                </div>

                                {/* AI Settings Section */}
                                <div className="bg-indigo-50 dark:bg-indigo-900/10 p-4 rounded-2xl border border-indigo-100 dark:border-indigo-900/30">
                                    <h4 className="font-bold text-indigo-600 mb-3 flex items-center gap-2">
                                        <Activity size={16} /> {t('super_admin.plans.ai_settings')}
                                    </h4>
                                    <div className="space-y-3">
                                        <div className="flex items-center justify-between">
                                            <label className="text-sm font-bold text-slate-600 dark:text-slate-300">{t('super_admin.plans.ai_helper_label')}</label>
                                            <input
                                                type="checkbox"
                                                checked={editedPlanData.is_ai_enabled ?? plan.is_ai_enabled ?? false}
                                                onChange={(e) => setEditedPlanData({ ...editedPlanData, is_ai_enabled: e.target.checked })}
                                                className="w-5 h-5 accent-indigo-600 rounded-lg cursor-pointer"
                                            />
                                        </div>
                                        <div>
                                            <label className={`block text-xs font-bold text-slate-500 mb-1`}>{t('super_admin.plans.ai_daily_limit')} (0 = {t('super_admin.plans.unlimited')})</label>
                                            <input
                                                type="number"
                                                value={editedPlanData.ai_daily_limit ?? plan.ai_daily_limit ?? 0}
                                                onChange={(e) => setEditedPlanData({ ...editedPlanData, ai_daily_limit: parseInt(e.target.value) })}
                                                className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 focus:ring-2 focus:ring-indigo-500 outline-none font-bold text-sm"
                                            />
                                        </div>
                                    </div>
                                    {/* Default Setting */}
                                    <div className="flex items-center justify-between pt-2 border-t border-indigo-100 dark:border-indigo-900/30 mt-2">
                                        <label className="text-sm font-bold text-slate-600 dark:text-slate-300">{t('super_admin.plans.default_plan_label')}</label>
                                        <input
                                            type="checkbox"
                                            checked={editedPlanData.is_default ?? plan.is_default ?? false}
                                            onChange={(e) => setEditedPlanData({ ...editedPlanData, is_default: e.target.checked })}
                                            className="w-5 h-5 accent-indigo-600 rounded-lg cursor-pointer"
                                        />
                                    </div>
                                </div>

                                <div className="flex gap-3 pt-2">
                                    <button onClick={() => handleSavePlan(plan.id)} className="flex-1 bg-emerald-500 hover:bg-emerald-600 text-white py-2.5 rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/20 transition-all">
                                        <Save size={18} /> {t('super_admin.plans.save_changes')}
                                    </button>
                                    <button onClick={() => { setEditingPlan(null); setEditedPlanData({}); }} className="px-4 bg-slate-200 hover:bg-slate-300 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-600 dark:text-slate-300 rounded-xl font-bold transition-all">
                                        <X size={18} />
                                    </button>
                                </div>
                            </div>
                        ) : (
                            <>
                                <div className={`absolute top-0 ${isRtl ? 'end-0' : 'start-0'} w-full h-[140px] bg-gradient-to-br from-indigo-500 to-teal-600 rounded-t-[2.5rem] opacity-10 group-hover:opacity-15 transition-opacity`} />
                                <div className="relative pt-4">
                                    <div className="flex justify-between items-start mb-6">
                                        <div>
                                            <div className="flex items-center gap-2">
                                                <h3 className="text-2xl font-bold text-slate-800 dark:text-white mb-2">
                                                    {isRtl ? plan.display_name_ar : plan.display_name_en || plan.name}
                                                </h3>
                                                {plan.is_default && (
                                                    <span className="bg-indigo-500 text-white text-[10px] px-2 py-0.5 rounded-full font-bold mb-2">{t('super_admin.plans.default_badge')}</span>
                                                )}
                                            </div>
                                            <div className="flex items-baseline gap-1">
                                                <span className="text-4xl font-bold text-indigo-600 dark:text-indigo-400">{plan.price}</span>
                                                <span className="text-sm font-bold text-slate-500">{t('super_admin.finance.currency')} / {plan.duration_days} {t('super_admin.plans.days_unit')}</span>
                                            </div>
                                        </div>
                                        <div className="flex gap-2">
                                            <button
                                                onClick={() => setEditingPlan(plan.id)}
                                                className="p-3 bg-white dark:bg-slate-800 hover:bg-indigo-50 dark:hover:bg-slate-700 text-indigo-600 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700 transition-all hover:scale-110"
                                                title={t('super_admin.plans.edit_plan')}
                                            >
                                                <Edit3 size={20} />
                                            </button>
                                            <button
                                                onClick={async () => {
                                                    if (window.confirm(t('super_admin.plans.delete_confirm', { name: isRtl ? plan.display_name_ar : plan.display_name_en || plan.name }))) {
                                                        try {
                                                            await api.delete(`/api/v1/admin/subscriptions/plans/${plan.id}`);
                                                            toast.success(t('super_admin.plans.delete_success') || 'تم حذف الخطة');
                                                            if (onRefresh) onRefresh();
                                                        } catch (err) {
                                                            toast.error(t('super_admin.plans.delete_fail') + ': ' + (err.response?.data?.detail || err.message));
                                                        }
                                                    }
                                                }}
                                                className="p-3 bg-white dark:bg-slate-800 hover:bg-red-50 dark:hover:bg-red-900/20 text-red-500 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700 transition-all hover:scale-110"
                                                title={t('super_admin.plans.delete_plan')}
                                            >
                                                <Trash2 size={20} />
                                            </button>
                                        </div>
                                    </div>

                                    <div className="space-y-4">
                                        <div className="flex items-center gap-3 p-3 bg-slate-50 dark:bg-slate-800/50 rounded-2xl">
                                            <div className="p-2 bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600 rounded-xl">
                                                <Users size={18} />
                                            </div>
                                            <div>
                                                <p className="text-xs text-slate-500 font-bold">{t('super_admin.plans.users_label')}</p>
                                                <p className="font-bold text-slate-700 dark:text-slate-200">{plan.max_users ? `${plan.max_users} ${t('super_admin.users.title')}` : t('super_admin.plans.unlimited')}</p>
                                            </div>
                                        </div>

                                        {/* AI Badge */}
                                        {plan.is_ai_enabled && (
                                            <div className="flex items-center gap-3 p-3 bg-indigo-50 dark:bg-indigo-900/10 rounded-2xl border border-indigo-100 dark:border-indigo-900/30">
                                                <div className="p-2 bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600 rounded-xl">
                                                    <Activity size={18} />
                                                </div>
                                                <div>
                                                    <p className="text-xs text-indigo-500 font-bold flex items-center gap-1">
                                                        {t('super_admin.plans.ai_settings')} <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse"></span>
                                                    </p>
                                                    <p className="font-bold text-indigo-700 dark:text-indigo-300">
                                                        {plan.ai_daily_limit > 0 ? `${plan.ai_daily_limit} ${t('super_admin.plans.requests_unit')}` : t('super_admin.plans.unlimited')}
                                                    </p>
                                                </div>
                                            </div>
                                        )}

                                        {/* Features List */}
                                        <div className="pt-4 border-t border-slate-100 dark:border-slate-800 space-y-2">
                                            <div className="flex flex-wrap gap-1.5">
                                                {currentFeatures.keys.map(key => {
                                                    const feat = KNOWN_PLAN_FEATURES.find(f => f.key === key);
                                                    return (
                                                        <span key={key} className="inline-flex items-center gap-1 px-2.5 py-1 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 text-xs font-bold rounded-lg border border-indigo-100 dark:border-indigo-900/50">
                                                            <Sparkles size={12} className="text-indigo-500" />
                                                            {feat ? (isRtl ? feat.label_ar : feat.label_en) : key}
                                                        </span>
                                                    );
                                                })}
                                            </div>
                                            {currentFeatures.custom && (
                                                <p className="text-xs text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/30 p-2.5 rounded-xl border border-dashed border-slate-200 dark:border-slate-700">
                                                    {currentFeatures.custom}
                                                </p>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </>
                        )}
                    </div>
                );
            })}

            {/* Add New Plan Card */}
            {isCreating ? (
                <div className="relative group bg-white dark:bg-slate-900 rounded-2xl p-8 border border-emerald-500 ring-4 ring-emerald-500/10 shadow-2xl animate-fade-in-up">
                    <div className="space-y-4">
                        <div className="flex items-center gap-2 mb-4 text-emerald-600 font-bold pb-4 border-b border-emerald-100 dark:border-emerald-900/30">
                            <PlusCircle size={20} />
                            {t('super_admin.plans.add_plan')}
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className={`block text-xs font-bold text-slate-500 mb-1.5 ${isRtl ? 'me-1' : 'ms-1'}`}>{t('super_admin.plans.plan_id_label')}</label>
                                <input
                                    type="text"
                                    value={newPlanData.name}
                                    onChange={(e) => setNewPlanData({ ...newPlanData, name: e.target.value })}
                                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-emerald-500 outline-none font-bold text-sm"
                                    placeholder="gold_plan"
                                />
                            </div>
                            <div>
                                <label className={`block text-xs font-bold text-slate-500 mb-1.5 ${isRtl ? 'me-1' : 'ms-1'}`}>{t('super_admin.plans.plan_name_label')}</label>
                                <input
                                    type="text"
                                    value={newPlanData.display_name_ar}
                                    onChange={(e) => setNewPlanData({ ...newPlanData, display_name_ar: e.target.value })}
                                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-emerald-500 outline-none font-bold text-sm"
                                    placeholder={isRtl ? "الباقة الذهبية" : "Gold Plan"}
                                />
                            </div>
                        </div>

                        <div className="flex gap-4">
                            <div className="flex-1">
                                <label className={`block text-xs font-bold text-slate-500 mb-1.5 ${isRtl ? 'me-1' : 'ms-1'}`}>{t('super_admin.plans.price_label')} ({t('super_admin.finance.currency')})</label>
                                <input
                                    type="number"
                                    value={newPlanData.price}
                                    onChange={(e) => setNewPlanData({ ...newPlanData, price: parseFloat(e.target.value) })}
                                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-emerald-500 outline-none font-bold"
                                />
                            </div>
                            <div className="flex-1">
                                <label className={`block text-xs font-bold text-slate-500 mb-1.5 ${isRtl ? 'me-1' : 'ms-1'}`}>{t('super_admin.plans.duration_label')}</label>
                                <input
                                    type="number"
                                    value={newPlanData.duration_days}
                                    onChange={(e) => setNewPlanData({ ...newPlanData, duration_days: parseInt(e.target.value) })}
                                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-emerald-500 outline-none font-bold"
                                />
                            </div>
                        </div>

                        <div className="flex gap-4">
                            <div className="flex-1">
                                <label className={`block text-xs font-bold text-slate-500 mb-1.5 ${isRtl ? 'me-1' : 'ms-1'}`}>{t('super_admin.plans.users_label')}</label>
                                <input
                                    type="number"
                                    value={newPlanData.max_users || ''}
                                    onChange={(e) => setNewPlanData({ ...newPlanData, max_users: e.target.value ? parseInt(e.target.value) : null })}
                                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-emerald-500 outline-none font-bold placeholder-slate-300"
                                    placeholder="∞"
                                />
                            </div>
                            <div className="flex-1">
                                <label className={`block text-xs font-bold text-slate-500 mb-1.5 ${isRtl ? 'me-1' : 'ms-1'}`}>{t('super_admin.plans.patients_label')}</label>
                                <input
                                    type="number"
                                    value={newPlanData.max_patients || ''}
                                    onChange={(e) => setNewPlanData({ ...newPlanData, max_patients: e.target.value ? parseInt(e.target.value) : null })}
                                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-emerald-500 outline-none font-bold placeholder-slate-300"
                                    placeholder="∞"
                                />
                            </div>
                        </div>

                        {/* Feature Checklist for Creation */}
                        <div className="p-4 bg-slate-50 dark:bg-slate-800/60 rounded-2xl border border-slate-200 dark:border-slate-700 space-y-3">
                            <label className="block text-xs font-bold text-slate-600 dark:text-slate-300 uppercase tracking-wider">
                                {t('super_admin.plans.features_label') || 'مميزات الخطة المتاحة'}
                            </label>
                            <div className="grid grid-cols-1 gap-2">
                                {KNOWN_PLAN_FEATURES.map(feat => {
                                    const isChecked = newSelectedFeatures.includes(feat.key);
                                    return (
                                        <label
                                            key={feat.key}
                                            onClick={() => toggleNewFeature(feat.key)}
                                            className={`flex items-center gap-3 p-2 rounded-xl text-xs font-bold cursor-pointer transition-all ${
                                                isChecked 
                                                ? 'bg-emerald-100/70 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300' 
                                                : 'hover:bg-slate-200/50 dark:hover:bg-slate-700/50 text-slate-600 dark:text-slate-400'
                                            }`}
                                        >
                                            {isChecked ? <CheckSquare size={16} className="text-emerald-600 shrink-0" /> : <Square size={16} className="text-slate-400 shrink-0" />}
                                            <span>{isRtl ? feat.label_ar : feat.label_en}</span>
                                        </label>
                                    );
                                })}
                            </div>
                            <div className="pt-2 border-t border-slate-200 dark:border-slate-700">
                                <input
                                    type="text"
                                    value={newCustomFeatures}
                                    onChange={(e) => handleNewCustomChange(e.target.value)}
                                    placeholder="مميزات إضافية مخصصة (مفصولة بفواصل)"
                                    className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs outline-none focus:ring-2 focus:ring-emerald-500"
                                />
                            </div>
                        </div>

                        {/* AI Settings Section for New Plan */}
                        <div className="bg-emerald-50 dark:bg-emerald-900/10 p-4 rounded-2xl border border-emerald-100 dark:border-emerald-900/30">
                            <h4 className="font-bold text-emerald-600 mb-3 flex items-center gap-2">
                                <Activity size={16} /> {t('super_admin.plans.ai_settings')}
                            </h4>
                            <div className="space-y-3">
                                <div className="flex items-center justify-between">
                                    <label className="text-sm font-bold text-slate-600 dark:text-slate-300">{t('super_admin.plans.ai_helper_label')}</label>
                                    <input
                                        type="checkbox"
                                        checked={newPlanData.is_ai_enabled || false}
                                        onChange={(e) => setNewPlanData({ ...newPlanData, is_ai_enabled: e.target.checked })}
                                        className="w-5 h-5 accent-emerald-600 rounded-lg cursor-pointer"
                                    />
                                </div>
                                <div className="flex items-center justify-between">
                                    <label className="text-sm font-bold text-slate-600 dark:text-slate-300">{t('super_admin.plans.default_plan_label')}</label>
                                    <input
                                        type="checkbox"
                                        checked={newPlanData.is_default || false}
                                        onChange={(e) => setNewPlanData({ ...newPlanData, is_default: e.target.checked })}
                                        className="w-5 h-5 accent-emerald-600 rounded-lg cursor-pointer"
                                    />
                                </div>
                                <div>
                                    <label className={`block text-xs font-bold text-slate-500 mb-1`}>{t('super_admin.plans.ai_daily_limit')} (0 = {t('super_admin.plans.unlimited')})</label>
                                    <input
                                        type="number"
                                        value={newPlanData.ai_daily_limit || 0}
                                        onChange={(e) => setNewPlanData({ ...newPlanData, ai_daily_limit: parseInt(e.target.value) })}
                                        className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 focus:ring-2 focus:ring-emerald-500 outline-none font-bold text-sm"
                                    />
                                </div>
                            </div>
                        </div>

                        <div className="flex gap-3 pt-2">
                            <button onClick={handleCreatePlan} className="flex-1 bg-emerald-500 hover:bg-emerald-600 text-white py-2.5 rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/20 transition-all">
                                <PlusCircle size={18} /> {t('super_admin.plans.create_button')}
                            </button>
                            <button onClick={() => setIsCreating(false)} className="px-4 bg-slate-200 hover:bg-slate-300 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-600 dark:text-slate-300 rounded-xl font-bold transition-all">
                                <X size={18} />
                            </button>
                        </div>
                    </div>
                </div>
            ) : (
                <button onClick={() => setIsCreating(true)} className="group border-3 border-dashed border-slate-200 dark:border-slate-700 rounded-2xl p-8 flex flex-col items-center justify-center gap-4 hover:border-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/10 transition-all min-h-[400px]">
                    <div className="p-4 bg-slate-100 dark:bg-slate-800 rounded-full text-slate-500 group-hover:bg-indigo-600 group-hover:text-white transition-all duration-300">
                        <PlusCircle size={32} />
                    </div>
                    <p className="font-bold text-slate-500 group-hover:text-indigo-600 transition-colors">{t('super_admin.plans.add_plan')}</p>
                </button>
            )}
        </div>
    );
};

export default PlansManager;
