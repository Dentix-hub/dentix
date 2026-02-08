import React, { useEffect, useState } from 'react';
import { api, broadcastNotification, deleteNotification, deleteSupportMessage } from '../api';
import {
    LayoutDashboard, Building2, CreditCard, CalendarRange,
    MessageSquare, Bell, ShieldCheck, X, Banknote, Landmark,
    PlusCircle, Activity, Users, Settings, Puzzle, Key
} from 'lucide-react';

// Imported Sub-Components
// Imported Sub-Components
import DashboardStats from '@/features/admin/SuperAdmin/DashboardStats';
import TenantsManager from '@/features/admin/SuperAdmin/TenantsManager';
import PlansManager from '@/features/admin/SuperAdmin/PlansManager';
import PaymentsManager from '@/features/admin/SuperAdmin/PaymentsManager';
import UsersManager from '@/features/admin/SuperAdmin/UsersManager'; // Phase 2
import SettingsManager from '@/features/admin/SuperAdmin/SettingsManager'; // Phase 3
import SupportInbox from '@/features/admin/SuperAdmin/SupportInbox';
import NotificationsManager from '@/features/admin/SuperAdmin/NotificationsManager';
import AuditLogViewer from '@/features/admin/SuperAdmin/AuditLogViewer';
import SecurityPanel from '@/features/admin/SuperAdmin/SecurityPanel'; // Phase 3
import FeatureManager from '@/features/admin/SuperAdmin/FeatureManager'; // Phase 3
import SystemHealth from '@/features/admin/SuperAdmin/SystemHealth'; // Phase 5

import Modal from '@/shared/ui/Modal'; // Assuming generic Modal exists, or keeping locally if needed for logic reuse

export default function SuperAdmin() {
    const [activeTab, setActiveTab] = useState('dashboard');
    const [tenants, setTenants] = useState([]);
    const [plans, setPlans] = useState([]);
    const [payments, setPayments] = useState([]);
    const [stats, setStats] = useState(null);
    const [messages, setMessages] = useState([]);
    const [notifications, setNotifications] = useState([]);
    const [auditLogs, setAuditLogs] = useState([]);
    const [systemSettings, setSystemSettings] = useState([]);
    const [loading, setLoading] = useState(true);

    // Editing Plan State
    const [editingPlan, setEditingPlan] = useState(null);
    const [editedPlanData, setEditedPlanData] = useState({});

    // Payment Modal State
    const [showPaymentModal, setShowPaymentModal] = useState(null);
    const [paymentForm, setPaymentForm] = useState({ plan_id: '', amount: '', payment_method: 'cash', notes: '' });

    // Notification Form State
    const [notifForm, setNotifForm] = useState({ title: '', content: '', type: 'info', is_global: true, tenant_id: null });

    // Password Reset State
    const [showPasswordResetModal, setShowPasswordResetModal] = useState(null); // {tenantId, tenantName}
    const [tenantUsers, setTenantUsers] = useState([]);
    const [passwordResetForm, setPasswordResetForm] = useState({ user_id: '', new_password: '' });

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            setLoading(true);
            // Cache busting
            const timestamp = new Date().getTime();
            const results = await Promise.allSettled([
                api.get(`/api/v1/admin/tenants?_t=${timestamp}`),
                api.get(`/api/v1/admin/plans?_t=${timestamp}`),
                api.get(`/api/v1/admin/stats?_t=${timestamp}`),
                api.get(`/api/v1/admin/payments?_t=${timestamp}`),
                api.get(`/support/messages?_t=${timestamp}`),
                api.get(`/api/v1/notifications/?_t=${timestamp}`),
                api.get(`/api/v1/admin/audit-logs?_t=${timestamp}`),
                api.get(`/api/v1/admin/settings?_t=${timestamp}`)
            ]);

            const [tenantsRes, plansRes, statsRes, paymentsRes, messagesRes, notificationsRes, auditsRes, settingsRes] = results;

            if (tenantsRes.status === 'fulfilled') setTenants(Array.isArray(tenantsRes.value.data) ? tenantsRes.value.data : []);
            if (plansRes.status === 'fulfilled') setPlans(Array.isArray(plansRes.value.data) ? plansRes.value.data : []);
            if (statsRes.status === 'fulfilled') setStats(statsRes.value.data);
            if (paymentsRes.status === 'fulfilled') setPayments(Array.isArray(paymentsRes.value.data) ? paymentsRes.value.data : []);
            if (messagesRes.status === 'fulfilled') setMessages(messagesRes.value.data);
            if (notificationsRes.status === 'fulfilled') setNotifications(notificationsRes.value.data);
            if (auditsRes.status === 'fulfilled') setAuditLogs(auditsRes.value.data);
            if (settingsRes.status === 'fulfilled') setSystemSettings(settingsRes.value.data);

        } finally {
            setLoading(false);
        }
    };

    const handleSavePlan = async (planId) => {
        try {
            await api.put(`/admin/plans/${planId}`, editedPlanData);
            setEditingPlan(null);
            setEditedPlanData({});
            fetchData();
        } catch (err) {
            alert('فشل التعديل');
        }
    };

    const handleRecordPayment = async () => {
        try {
            await api.post('/api/v1/admin/payments', {
                ...paymentForm,
                tenant_id: showPaymentModal.id
            });
            setShowPaymentModal(null);
            setPaymentForm({ plan_id: '', amount: '', payment_method: 'cash', notes: '' });
            fetchData();
        } catch (err) {
            alert('فشل تسجيل الدفعة');
        }
    };

    const handleSendNotification = async () => {
        if (!notifForm.title || !notifForm.content) return alert('الرجاء تعبئة العنوان والمحتوى');
        try {
            await broadcastNotification(notifForm);
            setNotifForm({ title: '', content: '', type: 'info', is_global: true, tenant_id: null });
            fetchData();
            alert('تم إرسال الإشعار بنجاح');
        } catch (err) {
            alert('فشل إرسال الإشعار');
        }
    };

    const handleDeleteNotification = async (id) => {
        if (!window.confirm('هل أنت متأكد من حذف هذا الإشعار؟')) return;
        try {
            await deleteNotification(id);
            fetchData();
        } catch (err) {
            alert('فشل حذف الإشعار');
        }
    };

    const handleDeleteMessage = async (id) => {
        if (!window.confirm('هل أنت متأكد من حذف هذه الرسالة؟')) return;
        try {
            await deleteSupportMessage(id);
            setMessages(prev => prev.filter(m => m.id !== id));
            alert('تم حذف الرسالة بنجاح');
        } catch (err) {
            alert('فشل حذف الرسالة');
        }
    };

    const handlePlanChange = (e, tenantId) => {
        const newPlanId = parseInt(e.target.value);
        if (!newPlanId) return;
        if (window.confirm('هل أنت متأكد من تغيير الخطة؟ سيتم احتساب المدة الجديدة بدءاً من اليوم.')) {
            api.post(`/admin/tenants/${tenantId}/assign-plan?plan_id=${newPlanId}`)
                .then(() => fetchData())
                .catch(() => alert('فشل تغيير الخطة'));
        }
    };

    const getDaysRemaining = (endDate) => {
        if (!endDate) return null;
        const days = Math.ceil((new Date(endDate) - new Date()) / (1000 * 60 * 60 * 24));
        return days;
    };

    const handleArchiveTenant = async (tenantId) => {
        if (!window.confirm("هل أنت متأكد من أرشفة هذه العيادة؟ ستختفي من القائمة النشطة ويتم تعطيل دخول المستخدمين.")) return;
        try {
            await api.delete(`/admin/tenants/${tenantId}`);
            fetchData();
            alert("تمت الأرشفة بنجاح");
        } catch (error) {
            console.error(error);
            alert("فشلت عملية الأرشفة");
        }
    };






    const handleRestoreTenant = async (tenantId) => {
        if (!window.confirm("هل أنت متأكد من استعادة هذه العيادة؟")) return;
        try {
            await api.post(`/admin/tenants/${tenantId}/restore`);
            fetchData();
            alert("تمت الاستعادة بنجاح");
        } catch (error) {
            console.error(error);
            alert("فشلت عملية الاستعادة");
        }
    };

    // Phase 2: User Management Handlers
    const [globalUsers, setGlobalUsers] = useState([]);
    const [usersLoading, setUsersLoading] = useState(false);

    const handleSearchUsers = async (query) => {
        setUsersLoading(true);
        try {
            // If empty query, empty list or default list? 
            // For performance, maybe default list first 50.
            const res = await api.get(`/api/v1/admin/users?search_query=${query || ''}`);
            setGlobalUsers(Array.isArray(res.data) ? res.data : []);
        } catch (err) {
            console.error(err);
            alert("فشل البحث");
        } finally {
            setUsersLoading(false);
        }
    };

    const handleToggleUserStatus = async (userId, currentStatus) => {
        const action = currentStatus ? "تعطيل" : "تفعيل";
        if (!window.confirm(`هل أنت متأكد من ${action} هذا المستخدم؟`)) return;

        try {
            await api.post(`/api/v1/admin/users/${userId}/toggle-status`);
            // Update local state to reflect change instantly
            setGlobalUsers(prev => Array.isArray(prev) ? prev.map(u =>
                u.id === userId ? { ...u, is_active: !currentStatus } : u
            ) : []);
            alert(`تم ${action} المستخدم بنجاح`);
        } catch (err) {
            console.error(err);
            alert("فشل تغيير حالة المستخدم");
        }
    };

    const handleResetPassword = async (tenantId) => {
        try {
            console.log('[DEBUG] Fetching users for tenant:', tenantId);
            const res = await api.get(`/api/v1/admin/system/tenants/${tenantId}/users`);
            console.log('[DEBUG] API Response:', res.data);

            // Temporary Debug Alert (Version 2)
            alert(`[V2 FIX] Found ${res.data?.users?.length || 0} users. \nFirst User: ${JSON.stringify(res.data?.users?.[0])}`);

            const users = res.data.users || [];
            setTenantUsers(users);

            if (users.length === 0) {
                console.warn('[DEBUG] No users found for tenant:', tenantId);
            }

            const tenant = Array.isArray(tenants) ? tenants.find(t => t.id === tenantId) : null;
            setShowPasswordResetModal({ tenantId, tenantName: tenant?.name || 'العيادة' });
            setPasswordResetForm({ user_id: '', new_password: '' });
        } catch (err) {
            console.error('Error in handleResetPassword:', err);
            alert('فشل تحميل مستخدمي العيادة: ' + (err.response?.data?.detail || err.message));
        }
    };

    const handleSubmitPasswordReset = async () => {
        if (!passwordResetForm.user_id || !passwordResetForm.new_password) {
            return alert('الرجاء اختيار المستخدم وإدخال كلمة المرور الجديدة');
        }
        if (passwordResetForm.new_password.length < 6) {
            return alert('كلمة المرور يجب أن تكون 6 أحرف على الأقل');
        }
        if (!window.confirm('هل أنت متأكد من إعادة تعيين كلمة المرور؟')) return;

        try {
            await api.post(`/api/v1/admin/system/users/${passwordResetForm.user_id}/reset-password`, {
                new_password: passwordResetForm.new_password
            });
            setShowPasswordResetModal(null);
            setPasswordResetForm({ user_id: '', new_password: '' });
            alert('تم إعادة تعيين كلمة المرور بنجاح');
        } catch (err) {
            console.error(err);
            alert('فشل إعادة تعيين كلمة المرور');
        }
    };

    if (loading) return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900">
            <div className="flex flex-col items-center gap-4">
                <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
                <p className="text-slate-500 font-bold animate-pulse">جاري تحميل لوحة التحكم...</p>
            </div>
        </div>
    );

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950 p-6 lg:p-10 font-sans" dir="rtl">
            <div className="max-w-7xl mx-auto space-y-8">

                {/* Header */}
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800">
                    <div className="flex items-center gap-4">
                        <div className="bg-gradient-to-br from-indigo-500 to-purple-600 p-4 rounded-2xl shadow-lg shadow-indigo-500/20 text-white">
                            <ShieldCheck size={32} />
                        </div>
                        <div>
                            <h1 className="text-3xl font-black text-slate-800 dark:text-white">إدارة النظام</h1>
                            <p className="text-slate-500 dark:text-slate-400 font-medium mt-1">نظرة عامة والتحكم الكامل في الاشتراكات</p>
                        </div>
                    </div>
                    <div className="flex flex-wrap items-center justify-start md:justify-end gap-2 bg-slate-100 dark:bg-slate-800 p-2 rounded-2xl w-full md:w-auto">
                        {[
                            { id: 'dashboard', label: 'الرئيسية', icon: LayoutDashboard },
                            { id: 'tenants', label: 'العيادات', icon: Building2 },
                            { id: 'users', label: 'المستخدمين', icon: Users }, // Phase 2
                            { id: 'plans', label: 'الخطط', icon: CalendarRange },
                            { id: 'payments', label: 'المالية', icon: CreditCard },
                            { id: 'messages', label: 'الرسائل', icon: MessageSquare },
                            { id: 'notifications', label: 'الإشعارات', icon: Bell },
                            { id: 'ai_analytics', label: 'AI Analytics', icon: Activity },
                            { id: 'audit_logs', label: 'السجلات', icon: Activity },
                            { id: 'settings', label: 'الإعدادات', icon: Settings },
                            { id: 'security', label: 'الأمان', icon: ShieldCheck },
                            { id: 'features', label: 'المزايا', icon: Puzzle },
                            { id: 'health', label: 'مراقبة النظام', icon: Activity }
                        ].map(tab => (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={`flex items-center gap-2 px-6 py-3 rounded-xl font-bold text-sm transition-all duration-300 ${activeTab === tab.id
                                    ? 'bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-400 shadow-md transform scale-105'
                                    : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 hover:bg-slate-200/50 dark:hover:bg-slate-700/50'
                                    }`}
                            >
                                <tab.icon size={18} />
                                {tab.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Content */}
                <div className="animate-fade-in-up">
                    {/* Dashboard Tab */}
                    {activeTab === 'dashboard' && stats && (
                        <DashboardStats stats={stats} />
                    )}

                    {/* Tenants Tab */}
                    {activeTab === 'tenants' && (
                        <TenantsManager
                            tenants={tenants}
                            plans={plans}
                            handlePlanChange={handlePlanChange}
                            setShowPaymentModal={setShowPaymentModal}
                            setPaymentForm={setPaymentForm}
                            getDaysRemaining={getDaysRemaining}
                            handleArchiveTenant={handleArchiveTenant}
                            handleRestoreTenant={handleRestoreTenant}
                            onResetPassword={handleResetPassword}
                        />
                    )}

                    {/* Global Users Tab (Phase 2) */}
                    {activeTab === 'users' && (
                        <UsersManager
                            users={globalUsers}
                            onSearch={handleSearchUsers}
                            onToggleStatus={handleToggleUserStatus}
                            loading={usersLoading}
                        />
                    )}

                    {/* Plans Tab */}
                    {activeTab === 'plans' && (
                        <PlansManager
                            plans={plans}
                            editingPlan={editingPlan}
                            setEditingPlan={setEditingPlan}
                            editedPlanData={editedPlanData}
                            setEditedPlanData={setEditedPlanData}
                            handleSavePlan={handleSavePlan}
                            onRefresh={fetchData}
                        />
                    )}

                    {/* Payments Tab */}
                    {activeTab === 'payments' && (
                        <PaymentsManager
                            payments={payments}
                            tenants={tenants}
                            plans={plans}
                        />
                    )}

                    {/* Support Messages Tab */}
                    {activeTab === 'messages' && (
                        <SupportInbox
                            messages={messages}
                            setMessages={setMessages}
                            handleDeleteMessage={handleDeleteMessage}
                            fetchData={fetchData}
                        />
                    )}

                    {/* Notifications Tab */}
                    {activeTab === 'notifications' && (
                        <NotificationsManager
                            notifForm={notifForm}
                            setNotifForm={setNotifForm}
                            handleSendNotification={handleSendNotification}
                            notifications={notifications}
                            handleDeleteNotification={handleDeleteNotification}
                            tenants={tenants}
                        />
                    )}

                    {/* Audit Logs Tab */}
                    {activeTab === 'audit_logs' && (
                        <AuditLogViewer logs={auditLogs} />
                    )}

                    {/* AI Analytics Tab (Phase 0+1) */}
                    {activeTab === 'ai_analytics' && (
                        <AIAnalyticsDashboard />
                    )}

                    {/* Settings Tab (Phase 3) */}
                    {activeTab === 'settings' && (
                        <SettingsManager settings={systemSettings} fetchData={fetchData} />
                    )}

                    {/* Security Tab (Phase 3) */}
                    {activeTab === 'security' && (
                        <SecurityPanel />
                    )}

                    {/* Features Tab (Phase 3) */}
                    {activeTab === 'features' && (
                        <FeatureManager tenants={tenants} />
                    )}

                    {/* Operational Health (Phase 5) */}
                    {activeTab === 'health' && (
                        <SystemHealth />
                    )}
                </div>
            </div>

            {/* Global Payment Modal - Kept in main since it needs overlay state */}
            {showPaymentModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-fade-in">
                    <div className="bg-white dark:bg-slate-900 rounded-3xl p-8 w-full max-w-lg shadow-2xl space-y-6">
                        <div className="flex justify-between items-center">
                            <div>
                                <h3 className="text-xl font-bold text-slate-800 dark:text-white">تسجيل دفعة جديدة</h3>
                                <p className="text-slate-500 dark:text-slate-400 text-sm">{showPaymentModal.name}</p>
                            </div>
                            <button
                                onClick={() => setShowPaymentModal(null)}
                                className="p-2 bg-slate-100 dark:bg-slate-800 rounded-full hover:bg-slate-200"
                            >
                                <X size={20} />
                            </button>
                        </div>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-bold text-slate-500 mb-1.5">خطة الاشتراك</label>
                                <select
                                    value={paymentForm.plan_id}
                                    onChange={(e) => {
                                        const pid = parseInt(e.target.value);
                                        const p = plans.find(pl => pl.id === pid);
                                        setPaymentForm({ ...paymentForm, plan_id: pid, amount: p ? p.price : '' });
                                    }}
                                    className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-indigo-500 outline-none font-bold"
                                >
                                    {(plans || []).map(p => (
                                        <option key={p.id} value={p.id}>{p.display_name_ar} ({p.price} ج.م)</option>
                                    ))}
                                </select>
                            </div>

                            <div>
                                <label className="block text-sm font-bold text-slate-500 mb-1.5">المبلغ المدفوع</label>
                                <input
                                    type="number"
                                    value={paymentForm.amount}
                                    onChange={(e) => setPaymentForm({ ...paymentForm, amount: e.target.value })}
                                    className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-indigo-500 outline-none font-bold"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-bold text-slate-500 mb-1.5">وسيلة الدفع</label>
                                <div className="grid grid-cols-3 gap-3">
                                    {[
                                        { id: 'cash', label: 'نقدي', icon: Banknote },
                                        { id: 'bank_transfer', label: 'تحويل', icon: Landmark },
                                        { id: 'credit_card', label: 'بطاقة', icon: CreditCard }
                                    ].map(method => (
                                        <button
                                            key={method.id}
                                            onClick={() => setPaymentForm({ ...paymentForm, payment_method: method.id })}
                                            className={`flex flex-col items-center justify-center gap-2 p-3 rounded-xl border-2 transition-all ${paymentForm.payment_method === method.id
                                                ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600'
                                                : 'border-slate-100 dark:border-slate-800 text-slate-400 hover:border-slate-300'
                                                }`}
                                        >
                                            <method.icon size={20} />
                                            <span className="text-xs font-bold">{method.label}</span>
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <button
                                onClick={handleRecordPayment}
                                className="w-full py-4 bg-emerald-500 hover:bg-emerald-600 text-white rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/20 text-lg hover:scale-[1.02] transition-all"
                            >
                                <PlusCircle size={20} />
                                حفظ العملية
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Password Reset Modal */}
            {showPasswordResetModal && (
                <div key={showPasswordResetModal.tenantId} className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-fade-in">
                    <div className="bg-white dark:bg-slate-900 rounded-3xl p-8 w-full max-w-lg shadow-2xl space-y-6">
                        <div className="flex justify-between items-center">
                            <div>
                                <h3 className="text-xl font-bold text-slate-800 dark:text-white">إعادة تعيين كلمة المرور</h3>
                                <p className="text-slate-500 dark:text-slate-400 text-sm">
                                    {showPasswordResetModal.tenantName}
                                    {passwordResetForm.user_id && (
                                        <span className="text-amber-600 dark:text-amber-400 font-bold mr-1">
                                            {' '}→{' '}
                                            {tenantUsers.find(u => String(u.id) === passwordResetForm.user_id)?.username ||
                                                tenantUsers.find(u => String(u.id) === passwordResetForm.user_id)?.email ||
                                                'مستخدم'}
                                        </span>
                                    )}
                                </p>
                            </div>
                            <button
                                onClick={() => setShowPasswordResetModal(null)}
                                className="p-2 bg-slate-100 dark:bg-slate-800 rounded-full hover:bg-slate-200"
                            >
                                <X size={20} />
                            </button>
                        </div>

                        <div className="space-y-4">
                            {/* VISUAL DEBUGGING - REMOVE AFTER FIX */}
                            <div className="p-4 bg-black text-green-400 font-mono text-xs rounded-xl overflow-auto max-h-40" dir="ltr">
                                <p className="font-bold border-b border-green-800 mb-2">DEBUG V3: API RESPONSE DUMP</p>
                                <p>Tenant ID: {showPasswordResetModal.tenantId}</p>
                                <p>Users Count: {tenantUsers.length}</p>
                                <pre>{JSON.stringify(tenantUsers.slice(0, 3), null, 2)}</pre>
                            </div>

                            <div>
                                <label className="block text-sm font-bold text-slate-500 mb-1.5">المستخدم</label>
                                {tenantUsers.length === 0 ? (
                                    <div className="w-full px-4 py-3 rounded-xl border border-amber-200 bg-amber-50 dark:bg-amber-900/20 dark:border-amber-700 text-amber-700 dark:text-amber-400 text-sm font-bold">
                                        ⚠️ لا يوجد مستخدمين مسجلين لهذه العيادة
                                    </div>
                                ) : (
                                    <select
                                        value={passwordResetForm.user_id}
                                        onChange={(e) => setPasswordResetForm({ ...passwordResetForm, user_id: e.target.value })}
                                        className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-amber-500 outline-none font-bold"
                                    >
                                        <option value="">اختر المستخدم</option>
                                        {tenantUsers.map(u => (
                                            <option key={u.id} value={u.id}>
                                                {u.username || u.email || `مستخدم #${u.id}`} - {u.role}
                                                {!u.is_active && ' [معطل]'}
                                                {u.account_locked_until && ' [مقفل]'}
                                            </option>
                                        ))}
                                    </select>
                                )}
                                {/* Show selected user username prominently */}
                                {passwordResetForm.user_id && (
                                    <div className="mt-2 px-4 py-2 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-700 rounded-xl">
                                        <span className="text-sm text-slate-500">المستخدم المحدد: </span>
                                        <span className="font-bold text-indigo-700 dark:text-indigo-400">
                                            {tenantUsers.find(u => String(u.id) === passwordResetForm.user_id)?.username || 'غير معروف'}
                                        </span>
                                    </div>
                                )}
                            </div>

                            <div>
                                <label className="block text-sm font-bold text-slate-500 mb-1.5">كلمة المرور الجديدة</label>
                                <input
                                    type="text"
                                    value={passwordResetForm.new_password}
                                    onChange={(e) => setPasswordResetForm({ ...passwordResetForm, new_password: e.target.value })}
                                    placeholder="أدخل كلمة المرور الجديدة (6 أحرف على الأقل)"
                                    className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-amber-500 outline-none font-bold"
                                    disabled={tenantUsers.length === 0}
                                />
                                <p className="text-xs text-slate-400 mt-2">💡 سيتم إلغاء قفل الحساب وتفعيله تلقائياً</p>
                            </div>

                            <button
                                onClick={handleSubmitPasswordReset}
                                disabled={tenantUsers.length === 0}
                                className={`w-full py-4 rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg text-lg transition-all ${tenantUsers.length === 0
                                    ? 'bg-slate-300 text-slate-500 cursor-not-allowed'
                                    : 'bg-amber-500 hover:bg-amber-600 text-white shadow-amber-500/20 hover:scale-[1.02]'
                                    }`}
                            >
                                <Key size={20} />
                                إعادة تعيين كلمة المرور
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
