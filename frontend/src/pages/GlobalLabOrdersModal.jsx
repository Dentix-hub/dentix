import { useState, useEffect } from 'react';
import logger from '@/utils/logger';
import { X, FlaskConical, Search } from 'lucide-react';
import { getLabOrders } from '../api';
const GlobalLabOrdersModal = ({ isOpen, onClose, initialStatus = '', title = '' }) => {
    const [orders, setOrders] = useState([]);
    const [loading, setLoading] = useState(false);
    const [statusFilter, setStatusFilter] = useState(initialStatus);
    const [searchQuery, setSearchQuery] = useState('');
    useEffect(() => {
        if (isOpen) {
            setStatusFilter(initialStatus);
            loadOrders(initialStatus);
        }
    }, [isOpen, initialStatus]);
    const loadOrders = async (status) => {
        setLoading(true);
        try {
            const res = await getLabOrders({ status: status || undefined });
            setOrders(res.data);
        } catch (error) {
            logger.error("Failed to load global orders", error);
        } finally {
            setLoading(false);
        }
    };
    const handleFilterChange = (status) => {
        setStatusFilter(status);
        loadOrders(status);
    };
    const filteredOrders = orders.filter(order =>
        (order.patient_name?.toLowerCase() || '').includes(searchQuery.toLowerCase()) ||
        (order.laboratory_name?.toLowerCase() || '').includes(searchQuery.toLowerCase())
    );
    if (!isOpen) return null;
    return (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-surface-elevated text-text-primary border border-border dark:bg-slate-900 dark:text-slate-100 w-full max-w-4xl rounded-2xl shadow-2xl max-h-[90vh] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="p-6 bg-slate-50 dark:bg-slate-800/80 border-b border-border flex justify-between items-center">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-teal-100 dark:bg-teal-950/70 rounded-xl text-teal-600 dark:text-teal-400">
                            <FlaskConical size={24} />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">{title || 'طلبات المعامل'}</h2>
                            <div className="text-sm text-slate-500 dark:text-slate-400">
                                {filteredOrders.length} طلب
                            </div>
                        </div>
                    </div>
                    <button type="button" onClick={onClose} className="p-2 text-slate-600 hover:bg-slate-200 dark:text-slate-300 dark:hover:bg-slate-700 rounded-full transition-colors">
                        <X size={20} />
                    </button>
                </div>
                {/* Filters */}
                <div className="p-4 border-b border-border flex gap-4 bg-white dark:bg-slate-900">
                    <div className="relative flex-1">
                        <Search className="absolute end-3 top-1/2 -translate-y-1/2 text-slate-500 dark:text-slate-400" size={16} />
                        <input
                            type="text"
                            placeholder="بحث باسم المريض أو المعمل..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full pe-10 ps-4 py-2 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 rounded-lg border border-slate-200 dark:border-slate-700 outline-none focus:ring-2 focus:ring-teal-500/20"
                        />
                    </div>
                    <select
                        className="p-2 border border-slate-200 dark:border-slate-700 rounded-lg text-sm bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 outline-none focus:ring-2 focus:ring-teal-500/20"
                        value={statusFilter}
                        onChange={(e) => handleFilterChange(e.target.value)}
                    >
                        <option value="">كل الحالات</option>
                        <option value="pending">معلق (Pending)</option>
                        <option value="in_progress">جاري التنفيذ</option>
                        <option value="completed">مكتمل (Completed)</option>
                    </select>
                </div>
                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6 bg-slate-50/50 dark:bg-slate-950/40">
                    {loading ? (
                        <div className="flex justify-center py-12"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600"></div></div>
                    ) : (
                        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
                            <table className="w-full text-sm text-right">
                                <thead className="bg-slate-50 dark:bg-slate-800/80 border-b border-border text-slate-600 dark:text-slate-300">
                                    <tr>
                                        <th className="p-3 font-medium">المعمل</th>
                                        <th className="p-3 font-medium">المريض</th>
                                        <th className="p-3 font-medium">العمل</th>
                                        <th className="p-3 font-medium">الحالة</th>
                                        <th className="p-3 font-medium">التكلفة</th>
                                        <th className="p-3 font-medium">تاريخ الطلب</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-border">
                                    {filteredOrders.map(order => (
                                        <tr key={order.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/50">
                                            <td className="p-3 font-bold text-indigo-600 dark:text-indigo-400">{order.laboratory_name}</td>
                                            <td className="p-3 font-medium text-slate-700 dark:text-slate-200">{order.patient_name}</td>
                                            <td className="p-3">
                                                <div className="font-medium text-slate-800 dark:text-slate-100">{order.work_type}</div>
                                                <div className="text-xs text-slate-500 dark:text-slate-400">{order.material} {order.shade && `(${order.shade})`}</div>
                                            </td>
                                            <td className="p-3">
                                                <span className={`px-2 py-1 rounded text-xs font-bold 
                                                    ${order.status === 'completed' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300' :
                                                        order.status === 'pending' ? 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300' :
                                                            'bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300'}`}>
                                                    {order.status}
                                                </span>
                                            </td>
                                            <td className="p-3 font-mono">{order.cost} ج.م</td>
                                            <td className="p-3 text-slate-500 dark:text-slate-400">{new Date(order.order_date).toLocaleDateString('ar-EG')}</td>
                                        </tr>
                                    ))}
                                    {filteredOrders.length === 0 && (
                                        <tr>
                                            <td colSpan="6" className="p-8 text-center text-slate-500 dark:text-slate-400">لا توجد طلبات</td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
export default GlobalLabOrdersModal;

