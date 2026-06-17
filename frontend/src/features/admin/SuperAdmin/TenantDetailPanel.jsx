import { memo, useEffect, useState } from 'react';
import logger from '@/utils/logger';
import { 
    X, 
    Users, 
    Calendar, 
    DollarSign, 
    Clock, 
    Activity, 
    Shield, 
    ExternalLink,
    Mail,
    Globe,
    Phone
} from 'lucide-react';
import { api } from '@/api';
import { format } from 'date-fns';
import { ar } from 'date-fns/locale';

const TenantDetailPanel = memo(function TenantDetailPanel({ tenantId, onClose, onImpersonate }) {
    const [data, setData] = useState(null);
    const [users, setUsers] = useState([]);
    const [selectedUser, setSelectedUser] = useState('');
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!tenantId) return;
        const fetchDetails = async () => {
            try {
                setLoading(true);
                const [detailsRes, usersRes] = await Promise.all([
                    api.get(`/api/v1/admin/tenants/${tenantId}/details`),
                    api.get(`/api/v1/admin/tenants/${tenantId}/users`)
                ]);
                setData(detailsRes.data);
                setUsers(usersRes.data.users || []);
                setSelectedUser('');
            } catch (err) {
                logger.error(err);
            } finally {
                setLoading(false);
            }
        };
        fetchDetails();
    }, [tenantId]);

    if (!tenantId) return null;

    return (
        <div className={`fixed inset-y-0 end-0 w-full max-w-md bg-white dark:bg-slate-900 shadow-2xl z-50 transform transition-transform duration-300 ${tenantId ? 'translate-x-0' : 'translate-x-full'}`}>
            <div className="h-full flex flex-col">
                {/* Header */}
                <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center bg-slate-50 dark:bg-slate-800/50">
                    <div>
                        <h2 className="text-xl font-bold text-slate-800 dark:text-white">تفاصيل العيادة</h2>
                        <p className="text-sm text-slate-500 mt-1">إدارة بيانات وموارد المستأجر</p>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-full transition-colors">
                        <X size={20} />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6 space-y-8 custom-scrollbar">
                    {loading ? (
                        <div className="space-y-6 animate-pulse">
                            <div className="h-32 bg-slate-100 dark:bg-slate-800 rounded-3xl" />
                            <div className="grid grid-cols-2 gap-4">
                                <div className="h-24 bg-slate-100 dark:bg-slate-800 rounded-2xl" />
                                <div className="h-24 bg-slate-100 dark:bg-slate-800 rounded-2xl" />
                            </div>
                        </div>
                    ) : (
                        <>
                            {!data ? (
                                <div className="p-8 text-center text-slate-500 bg-slate-50 dark:bg-slate-800/50 rounded-2xl">
                                    <Activity className="mx-auto mb-3 opacity-20" size={48} />
                                    <p className="font-bold">فشل تحميل البيانات</p>
                                    <p className="text-xs mt-1">تأكد من اتصالك بالخادم أو حاول مرة أخرى</p>
                                </div>
                            ) : (
                                <>
                                    {/* Profile Card */}
                                    <div className="bg-gradient-to-br from-indigo-500 to-teal-600 p-6 rounded-3xl text-white shadow-lg shadow-indigo-500/20">
                                        <h3 className="text-2xl font-bold mb-1">{data.tenant?.name || 'بدون اسم'}</h3>
                                        <p className="text-indigo-100 flex items-center gap-2 text-sm">
                                            <Globe size={14} />
                                            {data.tenant?.domain || 'portal'}.dentix.com
                                        </p>
                                        <div className="mt-6 flex flex-col gap-3">
                                            <select
                                                className="w-full bg-white/20 text-white placeholder-white/50 border border-white/20 rounded-xl px-4 py-2.5 outline-none focus:ring-2 focus:ring-white/50 [&>option]:text-slate-800"
                                                value={selectedUser}
                                                onChange={(e) => setSelectedUser(e.target.value)}
                                            >
                                                <option value="">دخول تلقائي (المدير)</option>
                                                {users.filter(u => u.is_active).map(u => (
                                                    <option key={u.id} value={u.id}>
                                                        {u.username || u.email} ({u.role})
                                                    </option>
                                                ))}
                                            </select>
                                            <div className="flex gap-4">
                                                <button 
                                                    onClick={() => onImpersonate(data.tenant?.id, selectedUser)}
                                                    className="flex-1 bg-white/20 hover:bg-white/30 backdrop-blur-md px-4 py-2.5 rounded-xl text-sm font-bold flex items-center justify-center gap-2 transition-all"
                                                >
                                                    <Shield size={16} />
                                                    دخول للنظام
                                                </button>
                                                <button className="p-2.5 bg-white/10 hover:bg-white/20 backdrop-blur-md rounded-xl transition-all">
                                                    <ExternalLink size={18} />
                                                </button>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Stats Grid */}
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="bg-slate-50 dark:bg-slate-800/40 p-4 rounded-2xl border border-slate-100 dark:border-slate-800">
                                            <Users size={20} className="text-teal-500 mb-2" />
                                            <div className="text-xl font-bold text-slate-800 dark:text-white">{data.stats?.patients_count || 0}</div>
                                            <div className="text-xs text-slate-500">إجمالي المرضى</div>
                                        </div>
                                        <div className="bg-slate-50 dark:bg-slate-800/40 p-4 rounded-2xl border border-slate-100 dark:border-slate-800">
                                            <Calendar size={20} className="text-blue-500 mb-2" />
                                            <div className="text-xl font-bold text-slate-800 dark:text-white">{data.stats?.appointments_count || 0}</div>
                                            <div className="text-xs text-slate-500">المواعيد</div>
                                        </div>
                                        <div className="bg-slate-50 dark:bg-slate-800/40 p-4 rounded-2xl border border-slate-100 dark:border-slate-800">
                                            <DollarSign size={20} className="text-amber-500 mb-2" />
                                            <div className="text-xl font-bold text-slate-800 dark:text-white">{(data.stats?.total_revenue || 0).toLocaleString()}</div>
                                            <div className="text-xs text-slate-500">إيرادات العيادة</div>
                                        </div>
                                        <div className="bg-slate-50 dark:bg-slate-800/40 p-4 rounded-2xl border border-slate-100 dark:border-slate-800">
                                            <Shield size={20} className="text-indigo-500 mb-2" />
                                            <div className="text-xl font-bold text-slate-800 dark:text-white">{data.tenant?.plan || 'trial'}</div>
                                            <div className="text-xs text-slate-500">الخطة الحالية</div>
                                        </div>
                                    </div>

                                    {/* Contact Information */}
                                    <div className="space-y-4">
                                        <h4 className="text-sm font-bold text-slate-400 uppercase tracking-wider">معلومات التواصل</h4>
                                        <div className="space-y-3">
                                            <div className="flex items-center gap-4 p-4 bg-slate-50 dark:bg-slate-800/40 rounded-2xl border border-slate-100 dark:border-slate-800">
                                                <div className="p-2.5 bg-white dark:bg-slate-800 rounded-xl shadow-sm text-indigo-500">
                                                    <Mail size={18} />
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <div className="text-xs text-slate-500 mb-0.5">البريد الإلكتروني</div>
                                                    <div className="text-sm font-bold text-slate-800 dark:text-white truncate">
                                                        {data.tenant?.admin_email || 'غير متوفر'}
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-4 p-4 bg-slate-50 dark:bg-slate-800/40 rounded-2xl border border-slate-100 dark:border-slate-800">
                                                <div className="p-2.5 bg-white dark:bg-slate-800 rounded-xl shadow-sm text-teal-500">
                                                    <Phone size={18} />
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <div className="text-xs text-slate-500 mb-0.5">رقم الهاتف</div>
                                                    <div className="text-sm font-bold text-slate-800 dark:text-white">
                                                        {data.tenant?.contact_phone || 'غير متوفر'}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    {/* More Details */}
                                    <div className="space-y-4">
                                        <h4 className="text-sm font-bold text-slate-400 uppercase tracking-wider">سجل النشاط والتواريخ</h4>
                                        <div className="space-y-3">
                                            <div className="flex items-center justify-between p-4 bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-800">
                                                <div className="flex items-center gap-3">
                                                    <div className="p-2 bg-slate-50 dark:bg-slate-700 rounded-lg text-slate-500">
                                                        <Clock size={16} />
                                                    </div>
                                                    <span className="text-sm font-medium text-slate-600 dark:text-slate-300">تاريخ الانضمام</span>
                                                </div>
                                                <span className="text-sm font-bold text-slate-800 dark:text-white">
                                                    {data.tenant?.created_at ? format(new Date(data.tenant.created_at), 'dd MMM yyyy', { locale: ar }) : '-'}
                                                </span>
                                            </div>
                                            <div className="flex items-center justify-between p-4 bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-800">
                                                <div className="flex items-center gap-3">
                                                    <div className="p-2 bg-slate-50 dark:bg-slate-700 rounded-lg text-slate-500">
                                                        <Activity size={16} />
                                                    </div>
                                                    <span className="text-sm font-medium text-slate-600 dark:text-slate-300">آخر نشاط</span>
                                                </div>
                                                <span className="text-sm font-bold text-slate-800 dark:text-white">
                                                    {data.stats?.last_activity ? format(new Date(data.stats.last_activity), 'dd MMM HH:mm', { locale: ar }) : 'لا يوجد'}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                </>
                            )}
                        </>
                    )}
                </div>

                {/* Footer Actions */}
                <div className="p-6 border-t border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
                    <button 
                        className="w-full py-3 bg-slate-800 dark:bg-slate-700 text-white font-bold rounded-2xl hover:bg-slate-900 transition-colors"
                        onClick={onClose}
                    >
                        إغلاق
                    </button>
                </div>
            </div>
        </div>
    );
});

export default TenantDetailPanel;
