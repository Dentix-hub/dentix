import { useState } from 'react';
import logger from '@/utils/logger';
import { Edit3, Save, X, Users, Activity, PlusCircle, Trash2, CheckSquare, Square, Sparkles } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { createSubscriptionPlan, deleteSubscriptionPlan } from '@/api';
import { toast, ConfirmDialog } from '@/shared/ui';
import { KNOWN_PLAN_FEATURES, parseFeatures, serializeFeatures } from './planFeatureUtils';

const sanitizeNumber = (val, fallback = 0) => {
    if (val === '' || val == null) return fallback;
    const num = Number(val);
    return isNaN(num) || !isFinite(num) ? fallback : num;
};

const sanitizeNullableInt = (val) => {
    if (val === '' || val == null) return null;
    const num = parseInt(val, 10);
    return isNaN(num) || num <= 0 ? null : num;
};

const PlansManager = ({ plans, editingPlan, setEditingPlan, editedPlanData, setEditedPlanData, handleSavePlan, onRefresh }) => {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';
    const [isCreating, setIsCreating] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [planToDelete, setPlanToDelete] = useState(null);
    const [isDeleting, setIsDeleting] = useState(false);

    const [newPlanData, setNewPlanData] = useState({
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
    const [newSelectedFeatures, setNewSelectedFeatures] = useState([]);
    const [newCustomFeatures, setNewCustomFeatures] = useState('');

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

    const validatePlanFields = (data, isNew = false) => {
        if (isNew && !data.name?.trim()) {
            toast.error(t('super_admin.plans.error_missing_code') || 'يرجى إدخال المعرف البرمجي للخطة');
            return false;
        }
        if (!data.display_name_ar?.trim()) {
            toast.error(t('super_admin.plans.fill_required') || 'يرجى إدخال اسم الخطة بالعربية');
            return false;
        }
        const price = sanitizeNumber(data.price, -1);
        if (price < 0) {
            toast.error(t('super_admin.plans.error_invalid_price') || 'يرجى إدخال سعر صحيح (0 أو أكثر)');
            return false;
        }
        const duration = sanitizeNumber(data.duration_days, 0);
        if (duration <= 0) {
            toast.error(t('super_admin.plans.error_invalid_duration') || 'يرجى إدخال مدة أيام صحيحة أكبر من الصفر');
            return false;
        }
        return true;
    };

    const handleCreatePlan = async () => {
        if (isSubmitting) return;

        const isValid = validatePlanFields(newPlanData, true);
        if (!isValid) return;

        setIsSubmitting(true);
        try {
            const payload = {
                name: newPlanData.name.trim(),
                display_name_ar: newPlanData.display_name_ar.trim(),
                price: Math.max(0, sanitizeNumber(newPlanData.price, 0)),
                duration_days: Math.max(1, parseInt(newPlanData.duration_days, 10) || 30),
                max_users: sanitizeNullableInt(newPlanData.max_users),
                max_patients: sanitizeNullableInt(newPlanData.max_patients),
                features: serializeFeatures(newSelectedFeatures, newCustomFeatures),
                is_ai_enabled: Boolean(newPlanData.is_ai_enabled),
                ai_daily_limit: Math.max(0, parseInt(newPlanData.ai_daily_limit, 10) || 0),
                is_default: Boolean(newPlanData.is_default),
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
            logger.error('Failed to create subscription plan:', err);
            const detail = err.response?.data?.detail || err.response?.data?.message || err.message;
            toast.error((t('super_admin.plans.create_fail') || 'فشل إنشاء الخطة') + ': ' + (typeof detail === 'string' ? detail : JSON.stringify(detail)));
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleConfirmDelete = async () => {
        if (!planToDelete) return;
        setIsDeleting(true);
        try {
            await deleteSubscriptionPlan(planToDelete.id);
            toast.success(t('super_admin.plans.delete_success') || 'تم حذف الخطة');
            setPlanToDelete(null);
            if (onRefresh) onRefresh();
        } catch (err) {
            logger.error('Failed to delete subscription plan:', err);
            const detail = err.response?.data?.detail || err.response?.data?.message || err.message;
            toast.error((t('super_admin.plans.delete_fail') || 'فشل حذف الخطة') + ': ' + (typeof detail === 'string' ? detail : JSON.stringify(detail)));
        } finally {
            setIsDeleting(false);
        }
    };

    const onSavePlanClicked = async (plan) => {
        const candidate = {
            display_name_ar: editedPlanData.display_name_ar !== undefined ? editedPlanData.display_name_ar : plan.display_name_ar,
            price: editedPlanData.price !== undefined ? editedPlanData.price : plan.price,
            duration_days: editedPlanData.duration_days !== undefined ? editedPlanData.duration_days : plan.duration_days,
            max_users: editedPlanData.max_users !== undefined ? editedPlanData.max_users : plan.max_users,
            max_patients: editedPlanData.max_patients !== undefined ? editedPlanData.max_patients : plan.max_patients,
            features: editedPlanData.features !== undefined ? editedPlanData.features : plan.features,
            is_ai_enabled: editedPlanData.is_ai_enabled !== undefined ? editedPlanData.is_ai_enabled : plan.is_ai_enabled,
            ai_daily_limit: editedPlanData.ai_daily_limit !== undefined ? editedPlanData.ai_daily_limit : plan.ai_daily_limit,
            is_default: editedPlanData.is_default !== undefined ? editedPlanData.is_default : plan.is_default,
        };

        const isValid = validatePlanFields(candidate, false);
        if (!isValid) return;

        const payload = {
            ...candidate,
            display_name_ar: candidate.display_name_ar.trim(),
            price: Math.max(0, sanitizeNumber(candidate.price, 0)),
            duration_days: Math.max(1, parseInt(candidate.duration_days, 10) || 30),
            max_users: sanitizeNullableInt(candidate.max_users),
            max_patients: sanitizeNullableInt(candidate.max_patients),
            ai_daily_limit: Math.max(0, parseInt(candidate.ai_daily_limit, 10) || 0),
            is_ai_enabled: Boolean(candidate.is_ai_enabled),
            is_default: Boolean(candidate.is_default),
        };

        if (handleSavePlan) {
            handleSavePlan(plan.id, payload);
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
                    setEditedPlanData(prev => ({ ...prev, features: serialized }));
                };

                const handleEditCustomChange = (text) => {
                    const serialized = serializeFeatures(currentFeatures.keys, text);
                    setEditedPlanData(prev => ({ ...prev, features: serialized }));
                };

                return (
                    <div key={plan.id} className={`relative group bg-white dark:bg-slate-900 rounded-2xl p-8 border hover:border-indigo-500/50 transition-all duration-300 ${isEditing ? 'border-indigo-500 ring-4 ring-indigo-500/10 z-10 scale-105 shadow-2xl' : 'border-slate-100 dark:border-slate-800 shadow-lg'}`}>
                        {isEditing ? (
                            <div className="space-y-5 animate-fade-in">
                                <div className="flex items-center gap-2 mb-4 text-indigo-600 font-bold pb-4 border-b border-indigo-100 dark:border-indigo-900/30">
                                    <Edit3 size={20} />
                                    {t('super_admin.plans.edit_plan') || 'تعديل الخطة'}
                                </div>

                                <div>
                                    <label className={`block text-xs font-bold text-slate-500 mb-1.5 ${isRtl ? 'me-1' : 'ms-1'}`}>{t('super_admin.plans.plan_name_label') || 'اسم الخطة (عربي)'}</label>
                                    <input
                                        type="text"
                                        value={editedPlanData.display_name_ar ?? plan.display_name_ar ?? ''}
                                        onChange={(e) => setEditedPlanData(prev => ({ ...prev, display_name_ar: e.target.value }))}
                                        className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all font-bold"
                                        placeholder={isRtl ? "مثال: الباقة الذهبية" : "Example: Gold Plan"}
                                    />
                                </div>

                                <div className="flex gap-4">
                                    <div className="flex-1">
                                        <label className={`block text-xs font-bold text-slate-500 mb-1.5 ${isRtl ? 'me-1' : 'ms-1'}`}>{t('super_admin.plans.price_label') || 'السعر'} ({t('super_admin.finance.currency') || 'ج.م'})</label>
                                        <input
                                            type="number"
                                            min="0"
                                            step="any"
                                            value={editedPlanData.price ?? plan.price ?? 0}
                                            onChange={(e) => setEditedPlanData(prev => ({ ...prev, price: e.target.value === '' ? '' : parseFloat(e.target.value) }))}
                                            className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:ring-2 focus:ring-indigo-500 outline-none font-bold"
                                        />
                                    </div>
                                    <div className="flex-1">
                                        <label className={`block text-xs font-bold text-slate-500 mb-1.5 ${isRtl ? 'me-1' : 'ms-1'}`}>{t('super_admin.plans.duration_label') || 'المدة (بالأيام)'}</label>
                                        <input
                                            type="number"
                                            min="1"
                                            value={editedPlanData.duration_days ?? plan.duration_days ?? 30}
                                            onChange={(e) => setEditedPlanData(prev => ({ ...prev, duration_days: e.target.value === '' ? '' : parseInt(e.target.value, 10) }))}
                                            className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:ring-2 focus:ring-indigo-500 outline-none font-bold"
                                        />
                                    </div>
                                </div>

                                <div className="flex gap-4">
                                    <div className="flex-1">
                                        <label className={`block text-xs font-bold text-slate-500 mb-1.5 ${isRtl ? 'me-1' : 'ms-1'}`}>{t('super_admin.plans.users_label') || 'الحد الأقصى للمستخدمين'}</label>
                                        <input
                                            type="number"
                                            min="1"
                                            value={editedPlanData.max_users !== undefined ? (editedPlanData.max_users ?? '') : (plan.max_users ?? '')}
                                            onChange={(e) => setEditedPlanData(prev => ({ ...prev, max_users: e.target.value === '' ? null : parseInt(e.target.value, 10) }))}
                                            className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:ring-2 focus:ring-indigo-500 outline-none font-bold placeholder-slate-300"
                                            placeholder="∞"
                                        />
                                    </div>
                                    <div className="flex-1">
                                        <label className={`block text-xs font-bold text-slate-500 mb-1.5 ${isRtl ? 'me-1' : 'ms-1'}`}>{t('super_admin.plans.patients_label') || 'الحد الأقصى للمرضى'}</label>
                                        <input
                                            type="number"
                                            min="1"
                                            value={editedPlanData.max_patients !== undefined ? (editedPlanData.max_patients ?? '') : (plan.max_patients ?? '')}
                                            onChange={(e) => setEditedPlanData(prev => ({ ...prev, max_patients: e.target.value === '' ? null : parseInt(e.target.value, 10) }))}
                                            className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:ring-2 focus:ring-indigo-500 outline-none font-bold placeholder-slate-300"
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
                                                <button
                                                    type="button"
                                                    key={feat.key}
                                                    onClick={() => toggleEditFeature(feat.key)}
                                                    className={`w-full flex items-center gap-3 p-2 rounded-xl text-xs font-bold transition-all text-start ${
                                                        isChecked 
                                                        ? 'bg-indigo-100/70 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300' 
                                                        : 'hover:bg-slate-200/50 dark:hover:bg-slate-700/50 text-slate-600 dark:text-slate-400'
                                                    }`}
                                                >
                                                    {isChecked ? <CheckSquare size={16} className="text-indigo-600 shrink-0" /> : <Square size={16} className="text-slate-400 shrink-0" />}
                                                    <span>{isRtl ? feat.label_ar : feat.label_en}</span>
                                                </button>
                                            );
                                        })}
                                    </div>
                                    <div className="pt-2 border-t border-slate-200 dark:border-slate-700">
                                        <input
                                            type="text"
                                            value={currentFeatures.custom}
                                            onChange={(e) => handleEditCustomChange(e.target.value)}
                                            placeholder={t('super_admin.plans.custom_features_placeholder') || "مميزات إضافية مخصصة (مفصولة بفواصل)"}
                                            className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 text-xs outline-none focus:ring-2 focus:ring-indigo-500"
                                        />
                                    </div>
                                </div>

                                {/* AI Settings Section */}
                                <div className="bg-indigo-50 dark:bg-indigo-900/10 p-4 rounded-2xl border border-indigo-100 dark:border-indigo-900/30">
                                    <h4 className="font-bold text-indigo-600 mb-3 flex items-center gap-2">
                                        <Activity size={16} /> {t('super_admin.plans.ai_settings') || 'إعدادات الذكاء الاصطناعي'}
                                    </h4>
                                    <div className="space-y-3">
                                        <div className="flex items-center justify-between">
                                            <label htmlFor={`edit_ai_enabled_${plan.id}`} className="text-sm font-bold text-slate-600 dark:text-slate-300">{t('super_admin.plans.ai_helper_label') || 'المساعد الذكي (AI)'}</label>
                                            <input
                                                id={`edit_ai_enabled_${plan.id}`}
                                                type="checkbox"
                                                checked={editedPlanData.is_ai_enabled ?? plan.is_ai_enabled ?? false}
                                                onChange={(e) => setEditedPlanData(prev => ({ ...prev, is_ai_enabled: e.target.checked }))}
                                                className="w-5 h-5 accent-indigo-600 rounded-lg cursor-pointer"
                                            />
                                        </div>
                                        <div>
                                            <label htmlFor={`edit_ai_limit_${plan.id}`} className={`block text-xs font-bold text-slate-500 mb-1`}>{t('super_admin.plans.ai_daily_limit') || 'الحد اليومي لطلبات الذكاء الاصطناعي'} (0 = {t('super_admin.plans.unlimited') || 'غير محدود'})</label>
                                            <input
                                                id={`edit_ai_limit_${plan.id}`}
                                                type="number"
                                                min="0"
                                                value={editedPlanData.ai_daily_limit ?? plan.ai_daily_limit ?? 0}
                                                onChange={(e) => setEditedPlanData(prev => ({ ...prev, ai_daily_limit: e.target.value === '' ? 0 : parseInt(e.target.value, 10) }))}
                                                className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 focus:ring-2 focus:ring-indigo-500 outline-none font-bold text-sm"
                                            />
                                        </div>
                                    </div>
                                    {/* Default Setting */}
                                    <div className="flex items-center justify-between pt-2 border-t border-indigo-100 dark:border-indigo-900/30 mt-2">
                                        <label htmlFor={`edit_default_plan_${plan.id}`} className="text-sm font-bold text-slate-600 dark:text-slate-300">{t('super_admin.plans.default_plan_label') || 'الخطة الافتراضية للعيادات الجديدة'}</label>
                                        <input
                                            id={`edit_default_plan_${plan.id}`}
                                            type="checkbox"
                                            checked={editedPlanData.is_default ?? plan.is_default ?? false}
                                            onChange={(e) => setEditedPlanData(prev => ({ ...prev, is_default: e.target.checked }))}
                                            className="w-5 h-5 accent-indigo-600 rounded-lg cursor-pointer"
                                        />
                                    </div>
                                </div>

                                <div className="flex gap-3 pt-2">
                                    <button 
                                        type="button"
                                        onClick={() => onSavePlanClicked(plan)} 
                                        className="flex-1 bg-emerald-500 hover:bg-emerald-600 text-white py-2.5 rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/20 transition-all"
                                    >
                                        <Save size={18} /> {t('super_admin.plans.save_changes') || 'حفظ التعديلات'}
                                    </button>
                                    <button 
                                        type="button"
                                        onClick={() => { setEditingPlan(null); setEditedPlanData({}); }} 
                                        className="px-4 bg-slate-200 hover:bg-slate-300 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-600 dark:text-slate-300 rounded-xl font-bold transition-all"
                                    >
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
                                                    {isRtl ? plan.display_name_ar : (plan.display_name_en || plan.name)}
                                                </h3>
                                                {plan.is_default && (
                                                    <span className="bg-indigo-500 text-white text-[10px] px-2 py-0.5 rounded-full font-bold mb-2">{t('super_admin.plans.default_badge') || 'افتراضية'}</span>
                                                )}
                                            </div>
                                            <div className="flex items-baseline gap-1">
                                                <span className="text-4xl font-bold text-indigo-600 dark:text-indigo-400">{plan.price}</span>
                                                <span className="text-sm font-bold text-slate-500">{t('super_admin.finance.currency') || 'ج.م'} / {plan.duration_days} {t('super_admin.plans.days_unit') || 'يوم'}</span>
                                            </div>
                                        </div>
                                        <div className="flex gap-2">
                                            <button
                                                type="button"
                                                onClick={() => setEditingPlan(plan.id)}
                                                className="p-3 bg-white dark:bg-slate-800 hover:bg-indigo-50 dark:hover:bg-slate-700 text-indigo-600 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700 transition-all hover:scale-110"
                                                title={t('super_admin.plans.edit_plan') || 'تعديل'}
                                                aria-label={t('super_admin.plans.edit_plan') || 'تعديل'}
                                            >
                                                <Edit3 size={20} />
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => setPlanToDelete(plan)}
                                                className="p-3 bg-white dark:bg-slate-800 hover:bg-red-50 dark:hover:bg-red-900/20 text-red-500 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700 transition-all hover:scale-110"
                                                title={t('super_admin.plans.delete_plan') || 'حذف'}
                                                aria-label={t('super_admin.plans.delete_plan') || 'حذف'}
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
                                                <p className="text-xs text-slate-500 font-bold">{t('super_admin.plans.users_label') || 'المستخدمين'}</p>
                                                <p className="font-bold text-slate-700 dark:text-slate-200">{plan.max_users ? `${plan.max_users} ${t('super_admin.users.title') || 'مستخدم'}` : (t('super_admin.plans.unlimited') || 'غير محدود')}</p>
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
                                                        {t('super_admin.plans.ai_settings') || 'الذكاء الاصطناعي'} <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse"></span>
                                                    </p>
                                                    <p className="font-bold text-indigo-700 dark:text-indigo-300">
                                                        {plan.ai_daily_limit > 0 ? `${plan.ai_daily_limit} ${t('super_admin.plans.requests_unit') || 'طلب / يوم'}` : (t('super_admin.plans.unlimited') || 'غير محدود')}
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
                            {t('super_admin.plans.add_plan') || 'إضافة خطة جديدة'}
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label htmlFor="new_plan_code" className={`block text-xs font-bold text-slate-500 mb-1.5 ${isRtl ? 'me-1' : 'ms-1'}`}>{t('super_admin.plans.plan_id_label') || 'المعرف البرمجي'}</label>
                                <input
                                    id="new_plan_code"
                                    type="text"
                                    value={newPlanData.name}
                                    onChange={(e) => setNewPlanData(prev => ({ ...prev, name: e.target.value }))}
                                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:ring-2 focus:ring-emerald-500 outline-none font-bold text-sm"
                                    placeholder="gold_plan"
                                />
                            </div>
                            <div>
                                <label htmlFor="new_plan_name_ar" className={`block text-xs font-bold text-slate-500 mb-1.5 ${isRtl ? 'me-1' : 'ms-1'}`}>{t('super_admin.plans.plan_name_label') || 'اسم الخطة (عربي)'}</label>
                                <input
                                    id="new_plan_name_ar"
                                    type="text"
                                    value={newPlanData.display_name_ar}
                                    onChange={(e) => setNewPlanData(prev => ({ ...prev, display_name_ar: e.target.value }))}
                                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:ring-2 focus:ring-emerald-500 outline-none font-bold text-sm"
                                    placeholder={isRtl ? "الباقة الذهبية" : "Gold Plan"}
                                />
                            </div>
                        </div>

                        <div className="flex gap-4">
                            <div className="flex-1">
                                <label htmlFor="new_plan_price" className={`block text-xs font-bold text-slate-500 mb-1.5 ${isRtl ? 'me-1' : 'ms-1'}`}>{t('super_admin.plans.price_label') || 'السعر'} ({t('super_admin.finance.currency') || 'ج.م'})</label>
                                <input
                                    id="new_plan_price"
                                    type="number"
                                    min="0"
                                    step="any"
                                    value={newPlanData.price}
                                    onChange={(e) => setNewPlanData(prev => ({ ...prev, price: e.target.value === '' ? '' : parseFloat(e.target.value) }))}
                                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:ring-2 focus:ring-emerald-500 outline-none font-bold"
                                />
                            </div>
                            <div className="flex-1">
                                <label htmlFor="new_plan_duration" className={`block text-xs font-bold text-slate-500 mb-1.5 ${isRtl ? 'me-1' : 'ms-1'}`}>{t('super_admin.plans.duration_label') || 'المدة (بالأيام)'}</label>
                                <input
                                    id="new_plan_duration"
                                    type="number"
                                    min="1"
                                    value={newPlanData.duration_days}
                                    onChange={(e) => setNewPlanData(prev => ({ ...prev, duration_days: e.target.value === '' ? '' : parseInt(e.target.value, 10) }))}
                                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:ring-2 focus:ring-emerald-500 outline-none font-bold"
                                />
                            </div>
                        </div>

                        <div className="flex gap-4">
                            <div className="flex-1">
                                <label htmlFor="new_plan_users" className={`block text-xs font-bold text-slate-500 mb-1.5 ${isRtl ? 'me-1' : 'ms-1'}`}>{t('super_admin.plans.users_label') || 'المستخدمين'}</label>
                                <input
                                    id="new_plan_users"
                                    type="number"
                                    min="1"
                                    value={newPlanData.max_users || ''}
                                    onChange={(e) => setNewPlanData(prev => ({ ...prev, max_users: e.target.value ? parseInt(e.target.value, 10) : null }))}
                                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:ring-2 focus:ring-emerald-500 outline-none font-bold placeholder-slate-300"
                                    placeholder="∞"
                                />
                            </div>
                            <div className="flex-1">
                                <label htmlFor="new_plan_patients" className={`block text-xs font-bold text-slate-500 mb-1.5 ${isRtl ? 'me-1' : 'ms-1'}`}>{t('super_admin.plans.patients_label') || 'المرضى'}</label>
                                <input
                                    id="new_plan_patients"
                                    type="number"
                                    min="1"
                                    value={newPlanData.max_patients || ''}
                                    onChange={(e) => setNewPlanData(prev => ({ ...prev, max_patients: e.target.value ? parseInt(e.target.value, 10) : null }))}
                                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:ring-2 focus:ring-emerald-500 outline-none font-bold placeholder-slate-300"
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
                                        <button
                                            type="button"
                                            key={feat.key}
                                            onClick={() => toggleNewFeature(feat.key)}
                                            className={`w-full flex items-center gap-3 p-2 rounded-xl text-xs font-bold transition-all text-start ${
                                                isChecked 
                                                ? 'bg-emerald-100/70 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300' 
                                                : 'hover:bg-slate-200/50 dark:hover:bg-slate-700/50 text-slate-600 dark:text-slate-400'
                                            }`}
                                        >
                                            {isChecked ? <CheckSquare size={16} className="text-emerald-600 shrink-0" /> : <Square size={16} className="text-slate-400 shrink-0" />}
                                            <span>{isRtl ? feat.label_ar : feat.label_en}</span>
                                        </button>
                                    );
                                })}
                            </div>
                            <div className="pt-2 border-t border-slate-200 dark:border-slate-700">
                                <input
                                    type="text"
                                    value={newCustomFeatures}
                                    onChange={(e) => handleNewCustomChange(e.target.value)}
                                    placeholder={t('super_admin.plans.custom_features_placeholder') || "مميزات إضافية مخصصة (مفصولة بفواصل)"}
                                    className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 text-xs outline-none focus:ring-2 focus:ring-emerald-500"
                                />
                            </div>
                        </div>

                        {/* AI Settings Section for New Plan */}
                        <div className="bg-emerald-50 dark:bg-emerald-900/10 p-4 rounded-2xl border border-emerald-100 dark:border-emerald-900/30">
                            <h4 className="font-bold text-emerald-600 mb-3 flex items-center gap-2">
                                <Activity size={16} /> {t('super_admin.plans.ai_settings') || 'إعدادات الذكاء الاصطناعي'}
                            </h4>
                            <div className="space-y-3">
                                <div className="flex items-center justify-between">
                                    <label htmlFor="new_ai_enabled" className="text-sm font-bold text-slate-600 dark:text-slate-300">{t('super_admin.plans.ai_helper_label') || 'المساعد الذكي (AI)'}</label>
                                    <input
                                        id="new_ai_enabled"
                                        type="checkbox"
                                        checked={newPlanData.is_ai_enabled || false}
                                        onChange={(e) => setNewPlanData(prev => ({ ...prev, is_ai_enabled: e.target.checked }))}
                                        className="w-5 h-5 accent-emerald-600 rounded-lg cursor-pointer"
                                    />
                                </div>
                                <div className="flex items-center justify-between">
                                    <label htmlFor="new_default_plan" className="text-sm font-bold text-slate-600 dark:text-slate-300">{t('super_admin.plans.default_plan_label') || 'الخطة الافتراضية للعيادات الجديدة'}</label>
                                    <input
                                        id="new_default_plan"
                                        type="checkbox"
                                        checked={newPlanData.is_default || false}
                                        onChange={(e) => setNewPlanData(prev => ({ ...prev, is_default: e.target.checked }))}
                                        className="w-5 h-5 accent-emerald-600 rounded-lg cursor-pointer"
                                    />
                                </div>
                                <div>
                                    <label htmlFor="new_ai_limit" className={`block text-xs font-bold text-slate-500 mb-1`}>{t('super_admin.plans.ai_daily_limit') || 'الحد اليومي لطلبات الذكاء الاصطناعي'} (0 = {t('super_admin.plans.unlimited') || 'غير محدود'})</label>
                                    <input
                                        id="new_ai_limit"
                                        type="number"
                                        min="0"
                                        value={newPlanData.ai_daily_limit || 0}
                                        onChange={(e) => setNewPlanData(prev => ({ ...prev, ai_daily_limit: e.target.value === '' ? 0 : parseInt(e.target.value, 10) }))}
                                        className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 focus:ring-2 focus:ring-emerald-500 outline-none font-bold text-sm"
                                    />
                                </div>
                            </div>
                        </div>

                        <div className="flex gap-3 pt-2">
                            <button 
                                type="button"
                                disabled={isSubmitting}
                                onClick={handleCreatePlan} 
                                className="flex-1 bg-emerald-500 hover:bg-emerald-600 disabled:bg-slate-400 text-white py-2.5 rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/20 transition-all"
                            >
                                <PlusCircle size={18} /> {isSubmitting ? (t('common.saving') || 'جاري الإنشاء...') : (t('super_admin.plans.create_button') || 'إنشاء الخطة')}
                            </button>
                            <button 
                                type="button"
                                disabled={isSubmitting}
                                onClick={() => setIsCreating(false)} 
                                className="px-4 bg-slate-200 hover:bg-slate-300 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-600 dark:text-slate-300 rounded-xl font-bold transition-all"
                            >
                                <X size={18} />
                            </button>
                        </div>
                    </div>
                </div>
            ) : (
                <button 
                    type="button"
                    onClick={() => setIsCreating(true)} 
                    className="group border-3 border-dashed border-slate-200 dark:border-slate-700 rounded-2xl p-8 flex flex-col items-center justify-center gap-4 hover:border-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/10 transition-all min-h-[400px]"
                >
                    <div className="p-4 bg-slate-100 dark:bg-slate-800 rounded-full text-slate-500 group-hover:bg-indigo-600 group-hover:text-white transition-all duration-300">
                        <PlusCircle size={32} />
                    </div>
                    <p className="font-bold text-slate-500 group-hover:text-indigo-600 transition-colors">{t('super_admin.plans.add_plan') || 'إضافة خطة جديدة'}</p>
                </button>
            )}

            {/* Confirm Dialog for Deleting Plan */}
            <ConfirmDialog
                isOpen={Boolean(planToDelete)}
                onClose={() => setPlanToDelete(null)}
                onConfirm={handleConfirmDelete}
                title={t('super_admin.plans.delete_title') || 'حذف الخطة'}
                message={t('super_admin.plans.delete_confirm', { name: planToDelete ? (isRtl ? planToDelete.display_name_ar : (planToDelete.display_name_en || planToDelete.name)) : '' }) || 'هل أنت متأكد من حذف هذه الخطة؟'}
                confirmText={t('common.delete') || 'حذف'}
                cancelText={t('common.cancel') || 'إلغاء'}
                variant="danger"
                isLoading={isDeleting}
            />
        </div>
    );
};

export default PlansManager;
