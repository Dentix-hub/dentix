import { useState, useEffect, useCallback } from 'react';
import logger from '@/utils/logger';
import { useTranslation } from 'react-i18next';
import { X, FlaskConical, Plus } from 'lucide-react';
import { getLabStats, getLabOrders, getLabPayments, createLabPayment } from '../api';
const LabDetailsModal = ({ lab, isOpen, onClose }) => {
    const { t } = useTranslation();
    const [activeTab, setActiveTab] = useState('overview'); // overview, orders, payments
    const [stats, setStats] = useState(null);
    const [orders, setOrders] = useState([]);
    const [payments, setPayments] = useState([]);
    const [loading, setLoading] = useState(false);
    // Order filters
    const [orderStatus, setOrderStatus] = useState('');
    // Payment Form
    const [showPaymentForm, setShowPaymentForm] = useState(false);
    const [paymentData, setPaymentData] = useState({ amount: '', notes: '', method: 'Cash', lab_order_id: null });
    const [selectedOrderForPayment, setSelectedOrderForPayment] = useState(null);
    const labId = lab?.id;
    const loadData = useCallback(async () => {
        if (!labId) return;
        setLoading(true);
        try {
            const [statsRes, ordersRes, paymentsRes] = await Promise.all([
                getLabStats(labId),
                getLabOrders({ laboratory_id: labId }),
                getLabPayments(labId)
            ]);
            setStats(statsRes.data);
            setOrders(ordersRes.data);
            setPayments(paymentsRes.data);
        } catch (error) {
            logger.error("Failed to load lab details", error);
        } finally {
            setLoading(false);
        }
    }, [labId]);
    const loadOrders = useCallback(async () => {
        if (!labId) return;
        try {
            const res = await getLabOrders({ laboratory_id: labId, status: orderStatus || undefined });
            setOrders(res.data);
        } catch (error) {
            logger.error("Failed to filter orders", error);
        }
    }, [labId, orderStatus]);
    useEffect(() => {
        if (isOpen && labId) {
            loadData();
            setActiveTab('overview');
            setOrderStatus('');
            setShowPaymentForm(false);
        }
    }, [isOpen, labId, loadData]);
    // Reload orders when filter changes
    useEffect(() => {
        if (activeTab === 'orders' && labId) {
            loadOrders();
        }
    }, [activeTab, labId, loadOrders]);
    const handleAddPayment = async (e) => {
        e.preventDefault();
        const amt = parseFloat(paymentData.amount);
        if (!amt || amt <= 0) return;
        try {
            const payload = {
                amount: amt,
                method: paymentData.method,
                notes: paymentData.notes || undefined,
            };
            if (paymentData.lab_order_id) {
                payload.lab_order_id = paymentData.lab_order_id;
            }
            await createLabPayment(lab.id, payload);
            setPaymentData({ amount: '', notes: '', method: 'Cash', lab_order_id: null });
            setSelectedOrderForPayment(null);
            setShowPaymentForm(false);
            loadData(); // Reload all to update balance and orders
        } catch (error) {
            const detail = error.response?.data?.detail;
            alert(typeof detail === 'string' ? detail : t('labs.details.payments.messages.add_fail'));
        }
    };

    const handleOpenPayOrder = (order) => {
        const cost = Number(order.cost || 0);
        const paid = Number(order.paid_amount || 0);
        const rem = order.remaining_amount != null
            ? Number(order.remaining_amount)
            : Math.max(0, cost - paid);
        setPaymentData({
            amount: rem > 0 ? String(rem) : '',
            notes: '',
            method: 'Cash',
            lab_order_id: order.id,
        });
        setSelectedOrderForPayment(order);
        setActiveTab('payments');
        setShowPaymentForm(true);
    };
    if (!isOpen || !lab) return null;
    return (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white w-full max-w-4xl rounded-2xl shadow-2xl max-h-[90vh] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="p-6 bg-slate-50 border-b flex justify-between items-center">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-teal-100 rounded-xl text-teal-600">
                            <FlaskConical size={24} />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-slate-800">{lab.name}</h2>
                            <div className="flex gap-3 text-sm text-slate-500">
                                {lab.phone && <span>{lab.phone}</span>}
                                {lab.contact_person && <span>• {lab.contact_person}</span>}
                            </div>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-slate-200 rounded-full transition-colors">
                        <X size={20} className="text-slate-500" />
                    </button>
                </div>
                {/* Tabs */}
                <div className="flex border-b px-6 bg-white shrink-0">
                    <button
                        onClick={() => setActiveTab('overview')}
                        className={`px-4 py-3 text-sm font-bold border-b-2 transition-colors ${activeTab === 'overview' ? 'border-teal-600 text-teal-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
                    >
                        {t('labs.details.tabs.overview')}
                    </button>
                    <button
                        onClick={() => setActiveTab('orders')}
                        className={`px-4 py-3 text-sm font-bold border-b-2 transition-colors ${activeTab === 'orders' ? 'border-teal-600 text-teal-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
                    >
                        {t('labs.details.tabs.orders')} ({stats?.total_orders || 0})
                    </button>
                    <button
                        onClick={() => setActiveTab('payments')}
                        className={`px-4 py-3 text-sm font-bold border-b-2 transition-colors ${activeTab === 'payments' ? 'border-teal-600 text-teal-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
                    >
                        {t('labs.details.tabs.payments')}
                    </button>
                </div>
                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6 bg-slate-50/50">
                    {loading && !stats ? (
                        <div className="flex justify-center py-12"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600"></div></div>
                    ) : (
                        <>
                            {/* OVERVIEW TAB */}
                            {activeTab === 'overview' && stats && (
                                <div className="space-y-6 animate-in slide-in-from-bottom-2 fade-in duration-300">
                                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                        <div className="bg-white p-4 rounded-xl border shadow-sm">
                                            <div className="text-sm text-slate-500 mb-1">{t('labs.details.overview.total_cost')}</div>
                                            <div className="text-2xl font-bold text-slate-800">{stats.total_cost}</div>
                                        </div>
                                        <div className="bg-white p-4 rounded-xl border shadow-sm">
                                            <div className="text-sm text-slate-500 mb-1">{t('labs.details.overview.paid')}</div>
                                            <div className="text-2xl font-bold text-emerald-600">{stats.total_paid}</div>
                                        </div>
                                        <div className={`bg-white p-4 rounded-xl border shadow-sm ${stats.balance > 0 ? 'border-red-200 bg-red-50' : 'border-emerald-200 bg-emerald-50'}`}>
                                            <div className="text-sm text-slate-500 mb-1">
                                                {stats.balance < 0
                                                    ? t('labs.details.overview.clinic_credit', 'رصيد لصالح العيادة')
                                                    : t('labs.details.overview.balance', 'المستحق للمعمل (مديونية)')}
                                            </div>
                                            <div className={`text-2xl font-bold ${stats.balance > 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                                                {stats.balance < 0 ? Math.abs(stats.balance) : stats.balance}
                                            </div>
                                        </div>
                                        <div className="bg-white p-4 rounded-xl border shadow-sm">
                                            <div className="text-sm text-slate-500 mb-1">{t('labs.details.overview.order_status')}</div>
                                            <div className="flex gap-2 text-sm mt-1">
                                                <span className="bg-amber-100 text-amber-700 px-2 py-0.5 rounded text-xs font-bold">{stats.pending_orders} {t('labs.details.overview.status_pending')}</span>
                                                <span className="bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded text-xs font-bold">{stats.completed_orders} {t('labs.details.overview.status_completed')}</span>
                                            </div>
                                        </div>
                                    </div>
                                    {/* Recent Activity placeholder could go here */}
                                </div>
                            )}
                            {/* ORDERS TAB */}
                            {activeTab === 'orders' && (
                                <div className="space-y-4 animate-in slide-in-from-bottom-2 fade-in duration-300">
                                    <div className="flex gap-2 mb-4">
                                        <select
                                            className="p-2 border rounded-lg text-sm bg-white"
                                            value={orderStatus}
                                            onChange={(e) => setOrderStatus(e.target.value)}
                                        >
                                            <option value="">{t('labs.details.orders.filter_all')}</option>
                                            <option value="pending">{t('labs.details.orders.filter_pending')}</option>
                                            <option value="in_progress">{t('labs.details.orders.filter_in_progress')}</option>
                                            <option value="completed">{t('labs.details.orders.filter_completed')}</option>
                                        </select>
                                    </div>
                                    <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
                                        <table className="w-full text-sm text-right">
                                            <thead className="bg-slate-50 border-b text-slate-500">
                                                <tr>
                                                    <th className="p-3 font-medium">{t('labs.details.orders.table.patient', 'المريض')}</th>
                                                    <th className="p-3 font-medium">{t('labs.details.orders.table.work', 'العمل')}</th>
                                                    <th className="p-3 font-medium">{t('labs.details.orders.table.status', 'الحالة')}</th>
                                                    <th className="p-3 font-medium">{t('labs.details.orders.table.cost', 'التكلفة')}</th>
                                                    <th className="p-3 font-medium">{t('labs.details.orders.table.paid', 'المدفوع')}</th>
                                                    <th className="p-3 font-medium">{t('labs.details.orders.table.remaining', 'المتبقي')}</th>
                                                    <th className="p-3 font-medium">{t('labs.details.orders.table.date', 'التاريخ')}</th>
                                                    <th className="p-3 font-medium text-center">{t('labs.details.orders.table.actions', 'إجراءات')}</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y">
                                                {orders.map((order) => {
                                                    const paid = Number(order.paid_amount || 0);
                                                    const cost = Number(order.cost || 0);
                                                    const remaining = order.remaining_amount != null
                                                        ? Number(order.remaining_amount)
                                                        : Math.max(0, cost - paid);
                                                    const isCancelled = order.status === 'cancelled';
                                                    const isPaid = order.payment_status === 'paid' || (cost > 0 && remaining <= 0);
                                                    const isPartial = order.payment_status === 'partial' || paid > 0;

                                                    return (
                                                        <tr key={order.id} className="hover:bg-slate-50/50">
                                                            <td className="p-3 font-bold text-slate-700">{order.patient_name}</td>
                                                            <td className="p-3">
                                                                <div className="font-medium">{order.work_type}</div>
                                                                <div className="text-xs text-slate-500">{order.material} {order.shade && `(${order.shade})`}</div>
                                                            </td>
                                                            <td className="p-3">
                                                                <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold inline-flex items-center ${
                                                                    isCancelled
                                                                        ? 'bg-slate-100 text-slate-700'
                                                                        : isPaid
                                                                            ? 'bg-emerald-100 text-emerald-700'
                                                                            : isPartial
                                                                                ? 'bg-amber-100 text-amber-700'
                                                                                : 'bg-rose-100 text-rose-700'
                                                                }`}>
                                                                    {isCancelled
                                                                        ? t('labs.details.orders.status_cancelled', 'ملغي')
                                                                        : isPaid
                                                                            ? t('labs.details.orders.status_paid', 'مدفوع')
                                                                            : isPartial
                                                                                ? t('labs.details.orders.status_partial', 'جزئي')
                                                                                : t('labs.details.orders.status_unpaid', 'غير مدفوع')}
                                                                </span>
                                                            </td>
                                                            <td className="p-3 font-mono">{cost}</td>
                                                            <td className="p-3 font-mono text-emerald-600 font-medium">{paid}</td>
                                                            <td className="p-3 font-mono text-amber-600 font-bold">{remaining}</td>
                                                            <td className="p-3 text-slate-500">{new Date(order.order_date).toLocaleDateString('ar-EG')}</td>
                                                            <td className="p-3 text-center">
                                                                {!isCancelled && remaining > 0 && (
                                                                    <button
                                                                        type="button"
                                                                        onClick={() => handleOpenPayOrder(order)}
                                                                        className="px-2.5 py-1 text-xs font-bold bg-teal-50 text-teal-700 hover:bg-teal-100 rounded-lg transition-colors border border-teal-200"
                                                                    >
                                                                        {t('labs.details.orders.record_payment', 'تسجيل دفعة')}
                                                                    </button>
                                                                )}
                                                            </td>
                                                        </tr>
                                                    );
                                                })}
                                                {orders.length === 0 && (
                                                    <tr>
                                                        <td colSpan="8" className="p-8 text-center text-slate-500">{t('labs.details.orders.table.empty')}</td>
                                                    </tr>
                                                )}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            )}
                            {/* PAYMENTS TAB */}
                            {activeTab === 'payments' && (
                                <div className="space-y-4 animate-in slide-in-from-bottom-2 fade-in duration-300">
                                    <div className="flex justify-between items-center mb-4">
                                        <h3 className="font-bold text-slate-700">{t('labs.details.payments.title')}</h3>
                                        <button
                                            onClick={() => setShowPaymentForm(!showPaymentForm)}
                                            className="flex items-center gap-2 px-3 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm font-bold"
                                        >
                                            <Plus size={16} />
                                            {showPaymentForm ? t('labs.details.payments.cancel_button') : t('labs.details.payments.add_button')}
                                        </button>
                                    </div>
                                    {showPaymentForm && (
                                        <form onSubmit={handleAddPayment} className="bg-indigo-50 p-4 rounded-xl mb-4 border border-indigo-100 animate-in fade-in slide-in-from-top-2 space-y-3">
                                            {paymentData.lab_order_id && (
                                                <div className="flex items-center justify-between bg-white/80 p-2.5 rounded-lg border border-indigo-200 text-xs">
                                                    <span className="font-bold text-indigo-900">
                                                        {t('labs.details.payments.allocated_to_order', 'دفعة مخصصة للطلب')}: #{paymentData.lab_order_id}
                                                        {selectedOrderForPayment ? ` — ${selectedOrderForPayment.work_type} (${selectedOrderForPayment.patient_name})` : ''}
                                                    </span>
                                                    <button
                                                        type="button"
                                                        onClick={() => {
                                                            setPaymentData((prev) => ({ ...prev, lab_order_id: null }));
                                                            setSelectedOrderForPayment(null);
                                                        }}
                                                        className="text-indigo-600 hover:underline font-bold text-[11px]"
                                                    >
                                                        {t('labs.details.payments.clear_allocation', 'إلغاء التخصيص (على الحساب)')}
                                                    </button>
                                                </div>
                                            )}
                                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
                                                <div>
                                                    <label htmlFor="lab-payment-amount" className="block text-xs font-bold text-indigo-800 mb-1">{t('labs.details.payments.form.amount')}</label>
                                                    <input
                                                        id="lab-payment-amount"
                                                        type="number"
                                                        step="0.01"
                                                        min="0.01"
                                                        value={paymentData.amount}
                                                        onChange={(e) => setPaymentData({ ...paymentData, amount: e.target.value })}
                                                        className="w-full p-2 rounded border focus:ring-2 focus:ring-indigo-500 outline-none"
                                                        required
                                                    />
                                                </div>
                                                <div>
                                                    <label className="block text-xs font-bold text-indigo-800 mb-1">{t('labs.details.payments.form.method')}</label>
                                                    <select
                                                        value={paymentData.method}
                                                        onChange={(e) => setPaymentData({ ...paymentData, method: e.target.value })}
                                                        className="w-full p-2 rounded border focus:ring-2 focus:ring-indigo-500 outline-none"
                                                    >
                                                        <option>Cash</option>
                                                        <option>Bank Transfer</option>
                                                        <option>Cheque</option>
                                                        <option>Vodafone Cash</option>
                                                    </select>
                                                </div>
                                                <div>
                                                    <label className="block text-xs font-bold text-indigo-800 mb-1">{t('labs.details.payments.form.notes')}</label>
                                                    <input
                                                        type="text"
                                                        value={paymentData.notes}
                                                        onChange={(e) => setPaymentData({ ...paymentData, notes: e.target.value })}
                                                        className="w-full p-2 rounded border focus:ring-2 focus:ring-indigo-500 outline-none"
                                                    />
                                                </div>
                                            </div>
                                            <button type="submit" className="w-full py-2 bg-indigo-600 text-white font-bold rounded-lg hover:bg-indigo-700">
                                                {t('labs.details.payments.form.submit')}
                                            </button>
                                        </form>
                                    )}
                                    <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
                                        <table className="w-full text-sm text-right">
                                            <thead className="bg-slate-50 border-b text-slate-500">
                                                <tr>
                                                    <th className="p-3 font-medium">{t('labs.details.payments.table.date')}</th>
                                                    <th className="p-3 font-medium">{t('labs.details.payments.table.amount')}</th>
                                                    <th className="p-3 font-medium">{t('labs.details.payments.table.method')}</th>
                                                    <th className="p-3 font-medium">{t('labs.details.payments.table.linked_order', 'الطلب المرتبط')}</th>
                                                    <th className="p-3 font-medium">{t('labs.details.payments.table.notes')}</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y">
                                                {payments.map(payment => {
                                                    const linkedOrder = payment.lab_order_id
                                                        ? orders.find(o => o.id === payment.lab_order_id)
                                                        : null;
                                                    return (
                                                        <tr key={payment.id} className="hover:bg-slate-50/50">
                                                            <td className="p-3 text-slate-600">{new Date(payment.date).toLocaleDateString('ar-EG')}</td>
                                                            <td className="p-3 font-bold text-emerald-600">{payment.amount}</td>
                                                            <td className="p-3 text-slate-500">{payment.method}</td>
                                                            <td className="p-3 text-xs">
                                                                {linkedOrder ? (
                                                                    <span className="font-medium text-slate-700">
                                                                        {linkedOrder.work_type} ({linkedOrder.patient_name})
                                                                    </span>
                                                                ) : payment.lab_order_id ? (
                                                                    <span className="font-mono text-slate-500">#{payment.lab_order_id}</span>
                                                                ) : (
                                                                    <span className="text-slate-400 italic">
                                                                        {t('labs.details.payments.on_account', 'على الحساب')}
                                                                    </span>
                                                                )}
                                                            </td>
                                                            <td className="p-3 text-slate-500 text-xs">{payment.notes || '-'}</td>
                                                        </tr>
                                                    );
                                                })}
                                                {payments.length === 0 && (
                                                    <tr>
                                                        <td colSpan="5" className="p-8 text-center text-slate-500">{t('labs.details.payments.table.empty')}</td>
                                                    </tr>
                                                )}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>
        </div>
    );
};
export default LabDetailsModal;
