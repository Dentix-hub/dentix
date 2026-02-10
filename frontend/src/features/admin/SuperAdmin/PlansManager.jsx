import { useState, useEffect } from 'react';
import { Edit3, Save, X, Users, Activity, PlusCircle, Trash2 } from 'lucide-react';
import { api } from '@/api';
const PlansManager = () => {
    const [plans, setPlans] = useState([]);
    const [loading, setLoading] = useState(true);
    const [editingPlan, setEditingPlan] = useState(null);
    const [editedPlanData, setEditedPlanData] = useState({});
    // Create Mode State
    const [isCreating, setIsCreating] = useState(false);
    const [newPlanData, setNewPlanData] = useState({
        name: '',
        display_name_ar: '',
        price: 0,
        duration_days: 30,
        max_users: null,
        max_patients: null,
        features: '',
        is_ai_enabled: false,
        ai_daily_limit: 0,
        is_default: false
    });
    useEffect(() => {
        fetchPlans();
    }, []);
    const fetchPlans = async () => {
        try {
            setLoading(true);
            const res = await api.get('/api/v1/admin/plans');
            setPlans(Array.isArray(res.data) ? res.data : []);
        } catch (err) {
            console.error("Failed to fetch plans", err);
        } finally {
            setLoading(false);
        }
    };
    const handleCreatePlan = async () => {
        if (!newPlanData.name || !newPlanData.display_name_ar) {
            alert('يرجى تعبئة الاسم والمعرف');
            return;
        }
        try {
            await api.post('/api/v1/admin/plans', newPlanData);
            setIsCreating(false);
            setNewPlanData({
                name: '',
                display_name_ar: '',
                price: 0,
                duration_days: 30,
                max_users: null,
                max_patients: null,
                features: '',
                is_ai_enabled: false,
                ai_daily_limit: 0,
                is_default: false
            });
            fetchPlans();
            alert('تم إنشاء الخطة بنجاح');
        } catch (err) {
            console.error(err);
            alert('فشل إنشاء الخطة: ' + (err.response?.data?.detail || err.message));
        }
    };
    const handleSavePlan = async (planId) => {
        try {
            await api.put(`/api/v1/admin/plans/${planId}`, editedPlanData);
            setEditingPlan(null);
            setEditedPlanData({});
            fetchPlans();
            alert('تم تعديل الخطة بنجاح');
        } catch (err) {
            console.error(err);
            alert('فشل التعديل: ' + (err.response?.data?.detail || err.message));
        }
    };
    const handleDeletePlan = async (planId) => {
        if (!window.confirm("هل أنت متأكد من حذف هذه الخطة؟")) return;
        try {
            await api.delete(`/api/v1/admin/plans/${planId}`);
            fetchPlans();
            alert('تم حذف الخطة بنجاح');
        } catch (err) {
            console.error(err);
            alert('فشل الحذف: ' + (err.response?.data?.detail || err.message));
        }
    };
    if (loading) return <div className="p-10 text-center text-slate-500 animate-pulse">جاري تحميل الخطط...</div>;
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
            {plans.map(plan => (
                <div key={plan.id} className={`relative group bg-white dark:bg-slate-900 rounded-[2.5rem] p-8 border hover:border-indigo-500/50 transition-all duration-300 ${editingPlan === plan.id ? 'border-indigo-500 ring-4 ring-indigo-500/10 z-10 scale-105 shadow-2xl' : 'border-slate-100 dark:border-slate-800 shadow-lg'}`}>
                    {editingPlan === plan.id ? (
                        <div className="space-y-5 animate-fade-in">
                            <div className="flex items-center gap-2 mb-4 text-indigo-600 font-bold pb-4 border-b border-indigo-100 dark:border-indigo-900/30">
                                <Edit3 size={20} />
                                تعديل الخطة
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-slate-500 mb-1.5 mr-1">اسم الخطة (للعرض)</label>
                                <input
                                    type="text"
                                    value={editedPlanData.display_name_ar ?? plan.display_name_ar}
                                    onChange={(e) => setEditedPlanData({ ...editedPlanData, display_name_ar: e.target.value })}
                                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all font-bold"
                                    placeholder="مثال: الباقة الذهبية"
                                />
                            </div>
                            <div className="flex gap-4">
                                <div className="flex-1">
                                    <label className="block text-xs font-bold text-slate-500 mb-1.5 mr-1">السعر (ج.م)</label>
                                    <input
                                        type="number"
                                        value={editedPlanData.price ?? plan.price}
                                        onChange={(e) => setEditedPlanData({ ...editedPlanData, price: parseFloat(e.target.value) })}
                                        className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-indigo-500 outline-none font-bold"
                                    />
                                </div>
                                <div className="flex-1">
                                    <label className="block text-xs font-bold text-slate-500 mb-1.5 mr-1">المدة (أيام)</label>
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
                                    <label className="block text-xs font-bold text-slate-500 mb-1.5 mr-1">مستخدمين</label>
                                    <input
                                        type="number"
                                        value={editedPlanData.max_users ?? plan.max_users ?? ''}
                                        onChange={(e) => setEditedPlanData({ ...editedPlanData, max_users: e.target.value ? parseInt(e.target.value) : null })}
                                        className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-indigo-500 outline-none font-bold placeholder-slate-300"
                                        placeholder="∞"
                                    />
                                </div>
                                <div className="flex-1">
                                    <label className="block text-xs font-bold text-slate-500 mb-1.5 mr-1">مرضى</label>
                                    <input
                                        type="number"
                                        value={editedPlanData.max_patients ?? plan.max_patients ?? ''}
                                        onChange={(e) => setEditedPlanData({ ...editedPlanData, max_patients: e.target.value ? parseInt(e.target.value) : null })}
                                        className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-indigo-500 outline-none font-bold placeholder-slate-300"
                                        placeholder="∞"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-slate-500 mb-1.5 mr-1">المميزات (نص وصفي)</label>
                                <textarea
                                    value={editedPlanData.features ?? plan.features}
                                    onChange={(e) => setEditedPlanData({ ...editedPlanData, features: e.target.value })}
                                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-indigo-500 outline-none text-sm min-h-[80px]"
                                />
                            </div>
                            {/* AI Settings Section */}
                            <div className="bg-indigo-50 dark:bg-indigo-900/10 p-4 rounded-2xl border border-indigo-100 dark:border-indigo-900/30">
                                <h4 className="font-bold text-indigo-600 mb-3 flex items-center gap-2">
                                    <Activity size={16} /> إعدادات الذكاء الاصطناعي
                                </h4>
                                <div className="space-y-3">
                                    <div className="flex items-center justify-between">
                                        <label className="text-sm font-bold text-slate-600 dark:text-slate-300">تفعيل المساعد الذكي</label>
                                        <input
                                            type="checkbox"
                                            checked={editedPlanData.is_ai_enabled ?? plan.is_ai_enabled ?? false}
                                            onChange={(e) => setEditedPlanData({ ...editedPlanData, is_ai_enabled: e.target.checked })}
                                            className="w-5 h-5 accent-indigo-600 rounded-lg cursor-pointer"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-xs font-bold text-slate-500 mb-1">الحد اليومي (0 = غير نشط)</label>
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
                                    <label className="text-sm font-bold text-slate-600 dark:text-slate-300">تعيين كخطة افتراضية</label>
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
                                    <Save size={18} /> حفظ التعديلات
                                </button>
                                <button onClick={() => { setEditingPlan(null); setEditedPlanData({}); }} className="px-4 bg-slate-200 hover:bg-slate-300 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-600 dark:text-slate-300 rounded-xl font-bold transition-all">
                                    <X size={18} />
                                </button>
                            </div>
                        </div>
                    ) : (
                        <>
                            <div className="absolute top-0 left-0 w-full h-[140px] bg-gradient-to-br from-indigo-500 to-purple-600 rounded-t-[2.5rem] opacity-10 group-hover:opacity-15 transition-opacity" />
                            <div className="relative pt-4">
                                <div className="flex justify-between items-start mb-6">
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <h3 className="text-2xl font-black text-slate-800 dark:text-white mb-2">{plan.display_name_ar}</h3>
                                            {plan.is_default && (
                                                <span className="bg-indigo-500 text-white text-[10px] px-2 py-0.5 rounded-full font-bold mb-2">افتراضي</span>
                                            )}
                                        </div>
                                        <div className="flex items-baseline gap-1">
                                            <span className="text-4xl font-black text-indigo-600 dark:text-indigo-400">{plan.price}</span>
                                            <span className="text-sm font-bold text-slate-500">ج.م / {plan.duration_days} يوم</span>
                                        </div>
                                    </div>
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => setEditingPlan(plan.id)}
                                            className="p-3 bg-white dark:bg-slate-800 hover:bg-indigo-50 dark:hover:bg-slate-700 text-indigo-600 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700 transition-all hover:scale-110"
                                            title="تعديل الخطة"
                                        >
                                            <Edit3 size={20} />
                                        </button>
                                        <button
                                            onClick={() => handleDeletePlan(plan.id)}
                                            className="p-3 bg-white dark:bg-slate-800 hover:bg-red-50 dark:hover:bg-red-900/20 text-red-500 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700 transition-all hover:scale-110"
                                            title="حذف الخطة"
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
                                            <p className="text-xs text-slate-500 font-bold">المستخدمين</p>
                                            <p className="font-bold text-slate-700 dark:text-slate-200">{plan.max_users ? `${plan.max_users} مستخدم` : 'غير محدود'}</p>
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
                                                    ذكاء اصطناعي <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse"></span>
                                                </p>
                                                <p className="font-bold text-indigo-700 dark:text-indigo-300">
                                                    {plan.ai_daily_limit > 0 ? `${plan.ai_daily_limit} طلب/يوم` : 'غير محدود'}
                                                </p>
                                            </div>
                                        </div>
                                    )}
                                    <div className="pt-4 border-t border-slate-100 dark:border-slate-800">
                                        <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed bg-slate-50/50 dark:bg-slate-800/20 p-4 rounded-2xl border border-dashed border-slate-200 dark:border-slate-700">
                                            {plan.features}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </>
                    )}
                </div>
            ))}
            {/* Add New Plan Card */}
            {isCreating ? (
                <div className="relative group bg-white dark:bg-slate-900 rounded-[2.5rem] p-8 border border-emerald-500 ring-4 ring-emerald-500/10 shadow-2xl animate-fade-in-up">
                    <div className="space-y-4">
                        <div className="flex items-center gap-2 mb-4 text-emerald-600 font-bold pb-4 border-b border-emerald-100 dark:border-emerald-900/30">
                            <PlusCircle size={20} />
                            إضافة خطة جديدة
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-xs font-bold text-slate-500 mb-1.5 mr-1">المعرف (EN)</label>
                                <input
                                    type="text"
                                    value={newPlanData.name}
                                    onChange={(e) => setNewPlanData({ ...newPlanData, name: e.target.value })}
                                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-emerald-500 outline-none font-bold text-sm"
                                    placeholder="gold_plan"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-slate-500 mb-1.5 mr-1">الاسم (للعرض)</label>
                                <input
                                    type="text"
                                    value={newPlanData.display_name_ar}
                                    onChange={(e) => setNewPlanData({ ...newPlanData, display_name_ar: e.target.value })}
                                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-emerald-500 outline-none font-bold text-sm"
                                    placeholder="الباقة الذهبية"
                                />
                            </div>
                        </div>
                        <div className="flex gap-4">
                            <div className="flex-1">
                                <label className="block text-xs font-bold text-slate-500 mb-1.5 mr-1">السعر (ج.م)</label>
                                <input
                                    type="number"
                                    value={newPlanData.price}
                                    onChange={(e) => setNewPlanData({ ...newPlanData, price: parseFloat(e.target.value) })}
                                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-emerald-500 outline-none font-bold"
                                />
                            </div>
                            <div className="flex-1">
                                <label className="block text-xs font-bold text-slate-500 mb-1.5 mr-1">المدة (أيام)</label>
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
                                <label className="block text-xs font-bold text-slate-500 mb-1.5 mr-1">مستخدمين</label>
                                <input
                                    type="number"
                                    value={newPlanData.max_users || ''}
                                    onChange={(e) => setNewPlanData({ ...newPlanData, max_users: e.target.value ? parseInt(e.target.value) : null })}
                                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-emerald-500 outline-none font-bold placeholder-slate-300"
                                    placeholder="∞"
                                />
                            </div>
                            <div className="flex-1">
                                <label className="block text-xs font-bold text-slate-500 mb-1.5 mr-1">مرضى</label>
                                <input
                                    type="number"
                                    value={newPlanData.max_patients || ''}
                                    onChange={(e) => setNewPlanData({ ...newPlanData, max_patients: e.target.value ? parseInt(e.target.value) : null })}
                                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-emerald-500 outline-none font-bold placeholder-slate-300"
                                    placeholder="∞"
                                />
                            </div>
                        </div>
                        <div>
                            <label className="block text-xs font-bold text-slate-500 mb-1.5 mr-1">المميزات</label>
                            <textarea
                                value={newPlanData.features}
                                onChange={(e) => setNewPlanData({ ...newPlanData, features: e.target.value })}
                                className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-emerald-500 outline-none text-sm min-h-[80px]"
                                placeholder="دعم كامل، وصول لجميع الخصائص..."
                            />
                        </div>
                        {/* AI Settings Section for New Plan */}
                        <div className="bg-emerald-50 dark:bg-emerald-900/10 p-4 rounded-2xl border border-emerald-100 dark:border-emerald-900/30">
                            <h4 className="font-bold text-emerald-600 mb-3 flex items-center gap-2">
                                <Activity size={16} /> إعدادات الذكاء الاصطناعي
                            </h4>
                            <div className="space-y-3">
                                <div className="flex items-center justify-between">
                                    <label className="text-sm font-bold text-slate-600 dark:text-slate-300">تفعيل المساعد الذكي</label>
                                    <input
                                        type="checkbox"
                                        checked={newPlanData.is_ai_enabled || false}
                                        onChange={(e) => setNewPlanData({ ...newPlanData, is_ai_enabled: e.target.checked })}
                                        className="w-5 h-5 accent-emerald-600 rounded-lg cursor-pointer"
                                    />
                                </div>
                                <div className="flex items-center justify-between">
                                    <label className="text-sm font-bold text-slate-600 dark:text-slate-300">تعيين كخطة افتراضية</label>
                                    <input
                                        type="checkbox"
                                        checked={newPlanData.is_default || false}
                                        onChange={(e) => setNewPlanData({ ...newPlanData, is_default: e.target.checked })}
                                        className="w-5 h-5 accent-emerald-600 rounded-lg cursor-pointer"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 mb-1">الحد اليومي (0 = غير نشط)</label>
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
                                <PlusCircle size={18} /> إنشاء
                            </button>
                            <button onClick={() => setIsCreating(false)} className="px-4 bg-slate-200 hover:bg-slate-300 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-600 dark:text-slate-300 rounded-xl font-bold transition-all">
                                <X size={18} />
                            </button>
                        </div>
                    </div>
                </div>
            ) : (
                <button onClick={() => setIsCreating(true)} className="group border-3 border-dashed border-slate-200 dark:border-slate-700 rounded-[2.5rem] p-8 flex flex-col items-center justify-center gap-4 hover:border-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/10 transition-all min-h-[400px]">
                    <div className="p-4 bg-slate-100 dark:bg-slate-800 rounded-full text-slate-400 group-hover:bg-indigo-600 group-hover:text-white transition-all duration-300">
                        <PlusCircle size={32} />
                    </div>
                    <p className="font-bold text-slate-500 group-hover:text-indigo-600 transition-colors">إضافة خطة جديدة</p>
                </button>
            )}
        </div>
    );
};
export default PlansManager;
