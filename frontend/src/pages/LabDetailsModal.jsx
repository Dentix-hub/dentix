import { useState, useEffect, useCallback } from 'react';
import logger from '@/utils/logger';
import { useTranslation } from 'react-i18next';
import { X, FlaskConical, Plus, AlertCircle, Check } from 'lucide-react';
import { Modal } from '@/shared/ui';
import {
    getLabStats,
    getLabOrders,
    getLabPayments,
    createLabPayment,
    allocateLabPayment,
    deallocateLabPayment,
} from '../api';

const LabDetailsModal = ({ lab, isOpen, onClose, onUpdate }) => {
    const { t } = useTranslation();
    const [activeTab, setActiveTab] = useState('overview'); // overview, orders, payments
    const [stats, setStats] = useState(null);
    const [orders, setOrders] = useState([]);
    const [payments, setPayments] = useState([]);
    const [loading, setLoading] = useState(false);

    // Filters
    const [orderStatus, setOrderStatus] = useState('');
    const [paymentStatusFilter, setPaymentStatusFilter] = useState('all');

    // Payment Form
    const [showPaymentForm, setShowPaymentForm] = useState(false);
    const [paymentData, setPaymentData] = useState({ amount: '', notes: '', method: 'Cash', lab_order_id: null });
    const [selectedOrderForPayment, setSelectedOrderForPayment] = useState(null);

    // Settle Remaining Sheet (One-Tap Settle)
    const [settleSheetOrder, setSettleSheetOrder] = useState(null);
    const [settleSheetData, setSettleSheetData] = useState({ method: 'Cash', notes: '' });
    const [isSubmittingSettle, setIsSubmittingSettle] = useState(false);

    // Allocate Existing Payment Modal
    const [allocateModalPayment, setAllocateModalPayment] = useState(null);
    const [selectedAllocationOrderId, setSelectedAllocationOrderId] = useState('');
    const [isSubmittingAllocate, setIsSubmittingAllocate] = useState(false);

    const labId = lab?.id;

    const loadData = useCallback(async () => {
        if (!labId) return;
        setLoading(true);
        try {
            const [statsRes, ordersRes, paymentsRes] = await Promise.all([
                getLabStats(labId),
                getLabOrders({ laboratory_id: labId }),
                getLabPayments(labId),
            ]);
            setStats(statsRes.data);
            setOrders(ordersRes.data || []);
            setPayments(paymentsRes.data || []);
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
            setOrders(res.data || []);
        } catch (error) {
            logger.error("Failed to filter orders", error);
        }
    }, [labId, orderStatus]);

    useEffect(() => {
        if (isOpen && labId) {
            loadData();
            setActiveTab('overview');
            setOrderStatus('');
            setPaymentStatusFilter('all');
            setShowPaymentForm(false);
            setSettleSheetOrder(null);
            setAllocateModalPayment(null);
        }
    }, [isOpen, labId, loadData]);

    // Reload orders when server-side status filter changes
    useEffect(() => {
        if (activeTab === 'orders' && labId) {
            loadOrders();
        }
    }, [activeTab, labId, loadOrders]);

    const getOrderRemaining = (order) => {
        const cost = Number(order.cost || 0);
        const paid = Number(order.paid_amount || 0);
        return order.remaining_amount != null
            ? Number(order.remaining_amount)
            : Math.max(0, cost - paid);
    };

    const getOrderPaymentStatus = (order) => {
        if (order.status === 'cancelled') return 'cancelled';
        const cost = Number(order.cost || 0);
        const paid = Number(order.paid_amount || 0);
        const remaining = getOrderRemaining(order);
        if (order.payment_status === 'paid' || (cost > 0 && remaining <= 0)) return 'paid';
        if (order.payment_status === 'partial' || paid > 0) return 'partial';
        return 'unpaid';
    };

    const filteredOrders = orders.filter((order) => {
        if (paymentStatusFilter && paymentStatusFilter !== 'all') {
            const status = getOrderPaymentStatus(order);
            if (status !== paymentStatusFilter) return false;
        }
        return true;
    });

    const handleAddPayment = async (e) => {
        e.preventDefault();
        const amt = parseFloat(paymentData.amount);
        if (!amt || amt <= 0) {
            alert(t('labs.details.payments.messages.invalid_amount', 'يرجى إدخال مبلغ صحيح أكبر من الصفر'));
            return;
        }
        if (paymentData.lab_order_id) {
            const targetOrder = orders.find(o => o.id === Number(paymentData.lab_order_id));
            if (targetOrder) {
                const remaining = getOrderRemaining(targetOrder);
                if (amt > remaining) {
                    alert(t('labs.details.payments.messages.overpay', 'المبلغ المدفوع يتجاوز المتبقي للطلب'));
                    return;
                }
            }
        }
        try {
            const payload = {
                amount: amt,
                method: paymentData.method,
                notes: paymentData.notes || undefined,
            };
            if (paymentData.lab_order_id) {
                payload.lab_order_id = Number(paymentData.lab_order_id);
            }
            await createLabPayment(lab.id, payload);
            setPaymentData({ amount: '', notes: '', method: 'Cash', lab_order_id: null });
            setSelectedOrderForPayment(null);
            setShowPaymentForm(false);
            await loadData();
            onUpdate?.();
        } catch (error) {
            const detail = error.response?.data?.detail;
            alert(typeof detail === 'string' ? detail : t('labs.details.payments.messages.add_fail'));
        }
    };

    const handleOpenSettleSheet = (order) => {
        setSettleSheetOrder(order);
        setSettleSheetData({ method: 'Cash', notes: '' });
    };

    const handleConfirmSettle = async (e) => {
        e?.preventDefault();
        if (!settleSheetOrder) return;
        const remaining = getOrderRemaining(settleSheetOrder);
        if (remaining <= 0) return;
        setIsSubmittingSettle(true);
        try {
            await createLabPayment(lab.id, {
                amount: remaining,
                method: settleSheetData.method,
                notes: settleSheetData.notes || undefined,
                lab_order_id: settleSheetOrder.id,
            });
            setSettleSheetOrder(null);
            await loadData();
            onUpdate?.();
        } catch (error) {
            const detail = error.response?.data?.detail;
            alert(typeof detail === 'string' ? detail : t('labs.details.payments.messages.add_fail'));
        } finally {
            setIsSubmittingSettle(false);
        }
    };

    const handleOpenPartialPayment = (order) => {
        const remaining = getOrderRemaining(order);
        setPaymentData({
            amount: remaining > 0 ? String(remaining) : '',
            notes: '',
            method: 'Cash',
            lab_order_id: order.id,
        });
        setSelectedOrderForPayment(order);
        setActiveTab('payments');
        setShowPaymentForm(true);
    };

    const handleOrderSelectChange = (e) => {
        const val = e.target.value;
        if (!val) {
            setPaymentData(prev => ({ ...prev, lab_order_id: null }));
            setSelectedOrderForPayment(null);
        } else {
            const orderId = Number(val);
            const found = orders.find(o => o.id === orderId);
            const remaining = found ? getOrderRemaining(found) : '';
            setPaymentData(prev => ({
                ...prev,
                lab_order_id: orderId,
                amount: remaining ? String(remaining) : prev.amount,
            }));
            setSelectedOrderForPayment(found || null);
        }
    };

    const handleOpenAllocateModal = (payment) => {
        setAllocateModalPayment(payment);
        setSelectedAllocationOrderId('');
    };

    const handleConfirmAllocate = async (e) => {
        e?.preventDefault();
        if (!allocateModalPayment || !selectedAllocationOrderId) return;
        setIsSubmittingAllocate(true);
        try {
            await allocateLabPayment(lab.id, allocateModalPayment.id, Number(selectedAllocationOrderId));
            setAllocateModalPayment(null);
            setSelectedAllocationOrderId('');
            await loadData();
            onUpdate?.();
        } catch (error) {
            const detail = error.response?.data?.detail;
            alert(typeof detail === 'string' ? detail : 'فشل ربط الدفعة بالطلب');
        } finally {
            setIsSubmittingAllocate(false);
        }
    };

    const handleDeallocate = async (payment) => {
        const msg = t('labs.details.payments.confirm_deallocate', 'هل أنت متأكد من إلغاء ربط هذه الدفعة بالطلب؟ ستصبح دفعة على الحساب.');
        if (!window.confirm(msg)) return;
        try {
            await deallocateLabPayment(lab.id, payment.id);
            await loadData();
            onUpdate?.();
        } catch (error) {
            const detail = error.response?.data?.detail;
            alert(typeof detail === 'string' ? detail : 'فشل إلغاء الربط');
        }
    };

    const renderPaymentStatusChip = (order) => {
        const status = getOrderPaymentStatus(order);
        if (status === 'cancelled') {
            return (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold inline-flex items-center bg-slate-100 text-slate-700">
                    {t('labs.details.orders.status_cancelled', 'ملغي')}
                </span>
            );
        }
        if (status === 'paid') {
            return (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold inline-flex items-center bg-emerald-100 text-emerald-700">
                    {t('labs.details.orders.status_paid', 'مدفوع')}
                </span>
            );
        }
        if (status === 'partial') {
            return (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold inline-flex items-center bg-amber-100 text-amber-700">
                    {t('labs.details.orders.status_partial', 'جزئي')}
                </span>
            );
        }
        return (
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold inline-flex items-center bg-rose-100 text-rose-700">
                {t('labs.details.orders.status_unpaid', 'غير مدفوع')}
            </span>
        );
    };

    const renderOrderStatusChip = (order) => {
        const status = order.status;
        if (status === 'completed') {
            return (
                <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                    {t('labs.details.overview.status_completed', 'مكتمل')}
                </span>
            );
        }
        if (status === 'in_progress') {
            return (
                <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
                    {t('labs.details.orders.filter_in_progress', 'جاري التنفيذ')}
                </span>
            );
        }
        if (status === 'cancelled') {
            return (
                <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
                    {t('labs.details.orders.status_cancelled', 'ملغي')}
                </span>
            );
        }
        return (
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
                {t('labs.details.overview.status_pending', 'معلق')}
            </span>
        );
    };

    const eligibleOrdersForAllocation = allocateModalPayment
        ? orders.filter(o => o.status !== 'cancelled' && getOrderRemaining(o) >= Number(allocateModalPayment.amount))
        : [];

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
                    <button onClick={onClose} className="p-2 hover:bg-slate-200 rounded-full transition-colors" aria-label="Close">
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
                                    {/* Unallocated Payments Banner */}
                                    {Number(stats.unallocated_payments_total || 0) > 0 && (
                                        <div
                                            data-testid="unallocated-banner"
                                            className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-amber-900 shadow-sm"
                                        >
                                            <div className="flex items-center gap-3">
                                                <AlertCircle size={22} className="text-amber-600 shrink-0" />
                                                <span className="text-sm font-medium">
                                                    {t(
                                                        'labs.details.overview.unallocated_alert',
                                                        'عندك دفعات على الحساب لسه ما اتربطتش بحالات: {{amount}}',
                                                        { amount: stats.unallocated_payments_total }
                                                    )}
                                                </span>
                                            </div>
                                            <button
                                                type="button"
                                                onClick={() => setActiveTab('payments')}
                                                className="px-3.5 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-bold transition-colors shrink-0 shadow-sm"
                                            >
                                                {t('labs.details.overview.view_unallocated', 'عرض المدفوعات')}
                                            </button>
                                        </div>
                                    )}

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
                                </div>
                            )}

                            {/* ORDERS TAB */}
                            {activeTab === 'orders' && (
                                <div className="space-y-4 animate-in slide-in-from-bottom-2 fade-in duration-300">
                                    {/* Dual Filters */}
                                    <div className="flex flex-wrap gap-2 mb-4">
                                        <select
                                            aria-label={t('labs.details.orders.filter_all', 'كل الحالات')}
                                            className="p-2 border rounded-lg text-sm bg-white focus:ring-2 focus:ring-teal-500 outline-none"
                                            value={orderStatus}
                                            onChange={(e) => setOrderStatus(e.target.value)}
                                        >
                                            <option value="">{t('labs.details.orders.filter_all', 'كل الحالات')}</option>
                                            <option value="pending">{t('labs.details.orders.filter_pending', 'معلق (Pending)')}</option>
                                            <option value="in_progress">{t('labs.details.orders.filter_in_progress', 'جاري التنفيذ (In Progress)')}</option>
                                            <option value="completed">{t('labs.details.orders.filter_completed', 'مكتمل (Completed)')}</option>
                                        </select>

                                        <select
                                            aria-label={t('labs.details.orders.filter_payment_all', 'كل حالات السداد')}
                                            className="p-2 border rounded-lg text-sm bg-white focus:ring-2 focus:ring-teal-500 outline-none"
                                            value={paymentStatusFilter}
                                            onChange={(e) => setPaymentStatusFilter(e.target.value)}
                                        >
                                            <option value="all">{t('labs.details.orders.filter_payment_all', 'كل حالات السداد')}</option>
                                            <option value="unpaid">{t('labs.details.orders.filter_payment_unpaid', 'غير مدفوع')}</option>
                                            <option value="partial">{t('labs.details.orders.filter_payment_partial', 'جزئي')}</option>
                                            <option value="paid">{t('labs.details.orders.filter_payment_paid', 'مدفوع')}</option>
                                        </select>
                                    </div>

                                    {/* Mobile Cards (below md) */}
                                    <div className="block md:hidden space-y-3" data-testid="orders-cards-mobile">
                                        {filteredOrders.map((order) => {
                                            const paid = Number(order.paid_amount || 0);
                                            const cost = Number(order.cost || 0);
                                            const remaining = getOrderRemaining(order);
                                            const isCancelled = order.status === 'cancelled';

                                            return (
                                                <div
                                                    key={order.id}
                                                    data-testid={`order-card-${order.id}`}
                                                    className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-3"
                                                >
                                                    {/* Top row: Patient + Work + Chips */}
                                                    <div className="flex justify-between items-start gap-2">
                                                        <div>
                                                            <div className="font-bold text-slate-800 text-base">{order.patient_name}</div>
                                                            <div className="text-xs text-slate-500 mt-0.5">
                                                                <span className="font-medium text-slate-700">{order.work_type}</span>
                                                                {order.material && <span> • {order.material}</span>}
                                                                {order.shade && <span> ({order.shade})</span>}
                                                                {order.tooth_number && <span> • #{order.tooth_number}</span>}
                                                            </div>
                                                        </div>
                                                        <div className="flex flex-wrap gap-1 justify-end shrink-0">
                                                            {renderOrderStatusChip(order)}
                                                            {renderPaymentStatusChip(order)}
                                                        </div>
                                                    </div>

                                                    {/* 3-cell Row: Cost / Paid / Remaining */}
                                                    <div className="grid grid-cols-3 gap-2 bg-slate-50 rounded-lg p-2.5 text-center text-xs border border-slate-100">
                                                        <div>
                                                            <div className="text-slate-500 font-medium mb-0.5">{t('labs.details.orders.table.cost', 'التكلفة')}</div>
                                                            <div className="font-bold text-slate-800 font-mono text-sm">{cost}</div>
                                                        </div>
                                                        <div>
                                                            <div className="text-slate-500 font-medium mb-0.5">{t('labs.details.orders.table.paid', 'المدفوع')}</div>
                                                            <div className="font-bold text-emerald-600 font-mono text-sm">{paid}</div>
                                                        </div>
                                                        <div>
                                                            <div className="text-slate-500 font-medium mb-0.5">{t('labs.details.orders.table.remaining', 'المتبقي')}</div>
                                                            <div className="font-bold text-amber-600 font-mono text-sm">{remaining}</div>
                                                        </div>
                                                    </div>

                                                    {/* Date */}
                                                    <div className="text-[11px] text-slate-400">
                                                        {t('labs.details.orders.table.date', 'التاريخ')}: {new Date(order.order_date).toLocaleDateString('ar-EG')}
                                                    </div>

                                                    {/* Buttons */}
                                                    {!isCancelled && remaining > 0 && (
                                                        <div className="grid grid-cols-2 gap-2 pt-1">
                                                            <button
                                                                type="button"
                                                                onClick={() => handleOpenSettleSheet(order)}
                                                                className="w-full py-2 px-3 bg-teal-600 hover:bg-teal-700 text-white rounded-lg text-xs font-bold transition-colors shadow-sm flex items-center justify-center gap-1.5"
                                                            >
                                                                <Check size={14} />
                                                                {t('labs.details.orders.settle_remaining', 'سدّدت المتبقي')}
                                                            </button>
                                                            <button
                                                                type="button"
                                                                onClick={() => handleOpenPartialPayment(order)}
                                                                className="w-full py-2 px-3 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-bold transition-colors flex items-center justify-center gap-1.5 border border-slate-200"
                                                            >
                                                                {t('labs.details.orders.partial_payment', 'دفعة جزئية')}
                                                            </button>
                                                        </div>
                                                    )}
                                                </div>
                                            );
                                        })}
                                        {filteredOrders.length === 0 && (
                                            <div className="p-8 text-center text-slate-500 bg-white rounded-xl border">
                                                {t('labs.details.orders.table.empty', 'لا توجد طلبات')}
                                            </div>
                                        )}
                                    </div>

                                    {/* Desktop Table (md+) */}
                                    <div className="hidden md:block bg-white rounded-xl border shadow-sm overflow-x-auto">
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
                                                {filteredOrders.map((order) => {
                                                    const paid = Number(order.paid_amount || 0);
                                                    const cost = Number(order.cost || 0);
                                                    const remaining = getOrderRemaining(order);
                                                    const isCancelled = order.status === 'cancelled';

                                                    return (
                                                        <tr key={order.id} className="hover:bg-slate-50/50">
                                                            <td className="p-3 font-bold text-slate-700">{order.patient_name}</td>
                                                            <td className="p-3">
                                                                <div className="font-medium">{order.work_type}</div>
                                                                <div className="text-xs text-slate-500">{order.material} {order.shade && `(${order.shade})`}</div>
                                                            </td>
                                                            <td className="p-3">
                                                                <div className="flex flex-col gap-1 items-start">
                                                                    {renderOrderStatusChip(order)}
                                                                    {renderPaymentStatusChip(order)}
                                                                </div>
                                                            </td>
                                                            <td className="p-3 font-mono">{cost}</td>
                                                            <td className="p-3 font-mono text-emerald-600 font-medium">{paid}</td>
                                                            <td className="p-3 font-mono text-amber-600 font-bold">{remaining}</td>
                                                            <td className="p-3 text-slate-500">{new Date(order.order_date).toLocaleDateString('ar-EG')}</td>
                                                            <td className="p-3 text-center">
                                                                {!isCancelled && remaining > 0 && (
                                                                    <div className="flex items-center justify-center gap-1.5">
                                                                        <button
                                                                            type="button"
                                                                            onClick={() => handleOpenSettleSheet(order)}
                                                                            className="px-2.5 py-1 text-xs font-bold bg-teal-600 text-white hover:bg-teal-700 rounded-lg transition-colors shadow-sm"
                                                                        >
                                                                            {t('labs.details.orders.settle_remaining', 'سدّدت المتبقي')}
                                                                        </button>
                                                                        <button
                                                                            type="button"
                                                                            onClick={() => handleOpenPartialPayment(order)}
                                                                            className="px-2.5 py-1 text-xs font-bold bg-slate-100 text-slate-700 hover:bg-slate-200 rounded-lg transition-colors border border-slate-200"
                                                                        >
                                                                            {t('labs.details.orders.partial_payment', 'دفعة جزئية')}
                                                                        </button>
                                                                    </div>
                                                                )}
                                                            </td>
                                                        </tr>
                                                    );
                                                })}
                                                {filteredOrders.length === 0 && (
                                                    <tr>
                                                        <td colSpan="8" className="p-8 text-center text-slate-500">{t('labs.details.orders.table.empty', 'لا توجد طلبات')}</td>
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

                                    {/* Payment Form */}
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

                                            {/* Order select dropdown */}
                                            <div>
                                                <label htmlFor="lab-payment-order-select" className="block text-xs font-bold text-indigo-800 mb-1">
                                                    {t('labs.details.payments.form.order_label', 'الطلب')}
                                                </label>
                                                <select
                                                    id="lab-payment-order-select"
                                                    value={paymentData.lab_order_id || ''}
                                                    onChange={handleOrderSelectChange}
                                                    className="w-full p-2 rounded border focus:ring-2 focus:ring-indigo-500 outline-none text-xs bg-white"
                                                >
                                                    <option value="">{t('labs.details.payments.form.unallocated_option', 'على الحساب (غير مخصص)')}</option>
                                                    {orders
                                                        .filter(o => o.status !== 'cancelled' && getOrderRemaining(o) > 0)
                                                        .map(o => {
                                                            const rem = getOrderRemaining(o);
                                                            return (
                                                                <option key={o.id} value={o.id}>
                                                                    {o.work_type} — {o.patient_name} — {t('labs.details.orders.table.remaining', 'متبقي')} {rem}
                                                                </option>
                                                            );
                                                        })}
                                                </select>
                                            </div>

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
                                                        className="w-full p-2 rounded border focus:ring-2 focus:ring-indigo-500 outline-none bg-white text-xs"
                                                        required
                                                    />
                                                </div>
                                                <div>
                                                    <label className="block text-xs font-bold text-indigo-800 mb-1">{t('labs.details.payments.form.method')}</label>
                                                    <select
                                                        value={paymentData.method}
                                                        onChange={(e) => setPaymentData({ ...paymentData, method: e.target.value })}
                                                        className="w-full p-2 rounded border focus:ring-2 focus:ring-indigo-500 outline-none bg-white text-xs"
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
                                                        className="w-full p-2 rounded border focus:ring-2 focus:ring-indigo-500 outline-none bg-white text-xs"
                                                    />
                                                </div>
                                            </div>
                                            <button type="submit" className="w-full py-2 bg-indigo-600 text-white font-bold rounded-lg hover:bg-indigo-700 text-xs">
                                                {t('labs.details.payments.form.submit')}
                                            </button>
                                        </form>
                                    )}

                                    {/* Mobile Cards (below md) */}
                                    <div className="block md:hidden space-y-3" data-testid="payments-cards-mobile">
                                        {payments.map((payment) => {
                                            const linkedOrder = payment.lab_order_id
                                                ? orders.find(o => o.id === payment.lab_order_id)
                                                : null;
                                            const pDate = payment.date || payment.created_at;
                                            const pMethod = payment.method || payment.payment_method || 'Cash';

                                            return (
                                                <div
                                                    key={payment.id}
                                                    data-testid={`payment-card-${payment.id}`}
                                                    className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-2.5"
                                                >
                                                    <div className="flex justify-between items-center">
                                                        <span className="text-lg font-bold text-emerald-600 font-mono">
                                                            {payment.amount}
                                                        </span>
                                                        <span className="text-xs text-slate-500">
                                                            {pDate ? new Date(pDate).toLocaleDateString('ar-EG') : '-'}
                                                        </span>
                                                    </div>

                                                    <div className="flex items-center justify-between text-xs text-slate-600">
                                                        <span className="bg-slate-100 px-2 py-0.5 rounded text-slate-700 font-medium">{pMethod}</span>
                                                        {payment.notes && <span className="text-slate-500 italic max-w-[200px] truncate">{payment.notes}</span>}
                                                    </div>

                                                    <div className="pt-2 border-t border-slate-100 flex items-center justify-between gap-2">
                                                        <div className="text-xs">
                                                            {linkedOrder ? (
                                                                <div className="flex items-center gap-1 font-medium text-slate-700">
                                                                    <span className="text-teal-600 font-bold">{linkedOrder.work_type}</span>
                                                                    <span>({linkedOrder.patient_name})</span>
                                                                </div>
                                                            ) : payment.lab_order_id ? (
                                                                <span className="font-mono text-slate-500">#{payment.lab_order_id}</span>
                                                            ) : (
                                                                <span className="text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full text-xs font-semibold">
                                                                    {t('labs.details.payments.on_account', 'على الحساب')}
                                                                </span>
                                                            )}
                                                        </div>

                                                        {/* Actions: Allocate or Deallocate */}
                                                        {payment.lab_order_id ? (
                                                            <button
                                                                type="button"
                                                                onClick={() => handleDeallocate(payment)}
                                                                className="px-2.5 py-1 text-xs font-bold text-rose-600 bg-rose-50 hover:bg-rose-100 rounded-lg transition-colors border border-rose-200 shrink-0"
                                                            >
                                                                {t('labs.details.payments.deallocate_button', 'إلغاء الربط')}
                                                            </button>
                                                        ) : (
                                                            <button
                                                                type="button"
                                                                onClick={() => handleOpenAllocateModal(payment)}
                                                                className="px-2.5 py-1 text-xs font-bold text-teal-700 bg-teal-50 hover:bg-teal-100 rounded-lg transition-colors border border-teal-200 shrink-0"
                                                            >
                                                                {t('labs.details.payments.allocate_button', 'ربط بطلب')}
                                                            </button>
                                                        )}
                                                    </div>
                                                </div>
                                            );
                                        })}
                                        {payments.length === 0 && (
                                            <div className="p-8 text-center text-slate-500 bg-white rounded-xl border">
                                                {t('labs.details.payments.table.empty', 'لا توجد مدفوعات مسجلة')}
                                            </div>
                                        )}
                                    </div>

                                    {/* Desktop Table (md+) */}
                                    <div className="hidden md:block bg-white rounded-xl border shadow-sm overflow-x-auto">
                                        <table className="w-full text-sm text-right">
                                            <thead className="bg-slate-50 border-b text-slate-500">
                                                <tr>
                                                    <th className="p-3 font-medium">{t('labs.details.payments.table.date')}</th>
                                                    <th className="p-3 font-medium">{t('labs.details.payments.table.amount')}</th>
                                                    <th className="p-3 font-medium">{t('labs.details.payments.table.method')}</th>
                                                    <th className="p-3 font-medium">{t('labs.details.payments.table.linked_order', 'الطلب المرتبط')}</th>
                                                    <th className="p-3 font-medium">{t('labs.details.payments.table.notes')}</th>
                                                    <th className="p-3 font-medium text-center">{t('labs.details.orders.table.actions', 'إجراءات')}</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y">
                                                {payments.map(payment => {
                                                    const linkedOrder = payment.lab_order_id
                                                        ? orders.find(o => o.id === payment.lab_order_id)
                                                        : null;
                                                    const pDate = payment.date || payment.created_at;
                                                    const pMethod = payment.method || payment.payment_method || 'Cash';

                                                    return (
                                                        <tr key={payment.id} className="hover:bg-slate-50/50">
                                                            <td className="p-3 text-slate-600">{pDate ? new Date(pDate).toLocaleDateString('ar-EG') : '-'}</td>
                                                            <td className="p-3 font-bold text-emerald-600">{payment.amount}</td>
                                                            <td className="p-3 text-slate-500">{pMethod}</td>
                                                            <td className="p-3 text-xs">
                                                                {linkedOrder ? (
                                                                    <span className="font-medium text-slate-700">
                                                                        {linkedOrder.work_type} ({linkedOrder.patient_name})
                                                                    </span>
                                                                ) : payment.lab_order_id ? (
                                                                    <span className="font-mono text-slate-500">#{payment.lab_order_id}</span>
                                                                ) : (
                                                                    <span className="text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full text-xs font-semibold">
                                                                        {t('labs.details.payments.on_account', 'على الحساب')}
                                                                    </span>
                                                                )}
                                                            </td>
                                                            <td className="p-3 text-slate-500 text-xs">{payment.notes || '-'}</td>
                                                            <td className="p-3 text-center">
                                                                {payment.lab_order_id ? (
                                                                    <button
                                                                        type="button"
                                                                        onClick={() => handleDeallocate(payment)}
                                                                        className="px-2.5 py-1 text-xs font-bold text-rose-600 bg-rose-50 hover:bg-rose-100 rounded-lg transition-colors border border-rose-200"
                                                                    >
                                                                        {t('labs.details.payments.deallocate_button', 'إلغاء الربط')}
                                                                    </button>
                                                                ) : (
                                                                    <button
                                                                        type="button"
                                                                        onClick={() => handleOpenAllocateModal(payment)}
                                                                        className="px-2.5 py-1 text-xs font-bold text-teal-700 bg-teal-50 hover:bg-teal-100 rounded-lg transition-colors border border-teal-200"
                                                                    >
                                                                        {t('labs.details.payments.allocate_button', 'ربط بطلب')}
                                                                    </button>
                                                                )}
                                                            </td>
                                                        </tr>
                                                    );
                                                })}
                                                {payments.length === 0 && (
                                                    <tr>
                                                        <td colSpan="6" className="p-8 text-center text-slate-500">{t('labs.details.payments.table.empty')}</td>
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

            {/* Settle Remaining Confirm Sheet / Modal */}
            {settleSheetOrder && (
                <Modal
                    isOpen={!!settleSheetOrder}
                    onClose={() => setSettleSheetOrder(null)}
                    title={t('labs.details.orders.settle_sheet.title', 'سداد المتبقي للطلب')}
                    size="sm"
                    mobileVariant="sheet"
                >
                    <div className="space-y-4">
                        <p className="text-xs text-slate-500 -mt-2">
                            {settleSheetOrder.work_type} — {settleSheetOrder.patient_name}
                        </p>

                        <div className="bg-teal-50 border border-teal-100 p-3.5 rounded-xl text-center">
                            <div className="text-xs text-teal-700 font-medium mb-1">
                                {t('labs.details.orders.settle_sheet.amount_label', 'المبلغ المسدد')}
                            </div>
                            <div className="text-2xl font-bold text-teal-800 font-mono">
                                {getOrderRemaining(settleSheetOrder)}
                            </div>
                        </div>

                        <form onSubmit={handleConfirmSettle} className="space-y-3">
                            <div>
                                <label htmlFor="settle-sheet-method" className="block text-xs font-bold text-slate-700 mb-1">
                                    {t('labs.details.orders.settle_sheet.method_label', 'طريقة الدفع')}
                                </label>
                                <select
                                    id="settle-sheet-method"
                                    value={settleSheetData.method}
                                    onChange={(e) => setSettleSheetData(prev => ({ ...prev, method: e.target.value }))}
                                    className="w-full p-2.5 rounded-lg border text-xs bg-white focus:ring-2 focus:ring-teal-500 outline-none"
                                >
                                    <option>Cash</option>
                                    <option>Bank Transfer</option>
                                    <option>Cheque</option>
                                    <option>Vodafone Cash</option>
                                </select>
                            </div>

                            <div>
                                <label htmlFor="settle-sheet-notes" className="block text-xs font-bold text-slate-700 mb-1">
                                    {t('labs.details.orders.settle_sheet.notes_label', 'ملاحظات (اختياري)')}
                                </label>
                                <input
                                    id="settle-sheet-notes"
                                    type="text"
                                    value={settleSheetData.notes}
                                    onChange={(e) => setSettleSheetData(prev => ({ ...prev, notes: e.target.value }))}
                                    placeholder={t('labs.details.payments.form.notes', 'ملاحظات')}
                                    className="w-full p-2.5 rounded-lg border text-xs focus:ring-2 focus:ring-teal-500 outline-none"
                                />
                            </div>

                            <div className="flex gap-2 pt-2">
                                <button
                                    type="submit"
                                    disabled={isSubmittingSettle}
                                    className="flex-1 py-2.5 px-4 bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white rounded-lg text-xs font-bold transition-colors shadow-sm"
                                >
                                    {isSubmittingSettle ? '...' : t('labs.details.orders.settle_sheet.confirm', 'تأكيد السداد')}
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setSettleSheetOrder(null)}
                                    className="py-2.5 px-4 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-bold transition-colors"
                                >
                                    {t('labs.details.orders.settle_sheet.cancel', 'إلغاء')}
                                </button>
                            </div>
                        </form>
                    </div>
                </Modal>
            )}

            {/* Allocate Payment Modal */}
            {allocateModalPayment && (
                <Modal
                    isOpen={!!allocateModalPayment}
                    onClose={() => setAllocateModalPayment(null)}
                    title={t('labs.details.payments.allocate_modal.title', 'ربط الدفعة بطلب معمل')}
                    size="sm"
                    mobileVariant="sheet"
                >
                    <div className="space-y-4">
                        <div className="bg-slate-50 p-3 rounded-xl text-xs space-y-1 border border-slate-100">
                            <div className="text-slate-500">
                                {t('labs.details.payments.table.amount', 'المبلغ')}:{' '}
                                <span className="font-bold text-emerald-600 font-mono text-sm">{allocateModalPayment.amount}</span>
                            </div>
                            <div className="text-slate-500">
                                {t('labs.details.payments.table.method', 'الطريقة')}:{' '}
                                <span className="font-medium text-slate-700">{allocateModalPayment.method || allocateModalPayment.payment_method || 'Cash'}</span>
                            </div>
                            {allocateModalPayment.notes && (
                                <div className="text-slate-500">
                                    {t('labs.details.payments.table.notes', 'ملاحظات')}:{' '}
                                    <span className="text-slate-700">{allocateModalPayment.notes}</span>
                                </div>
                            )}
                        </div>

                        <div>
                            <label htmlFor="allocate-order-select" className="block text-xs font-bold text-slate-700 mb-1">
                                {t('labs.details.payments.allocate_modal.select_order_label', 'اختر الطلب المراد ربط الدفعة به')}
                            </label>
                            {eligibleOrdersForAllocation.length === 0 ? (
                                <p className="text-xs text-rose-600 bg-rose-50 p-3 rounded-lg border border-rose-200">
                                    {t('labs.details.payments.allocate_modal.no_eligible_orders', 'لا توجد طلبات مؤهلة (متبقيها أكبر أو يساوي مبلغ الدفعة)')}
                                </p>
                            ) : (
                                <select
                                    id="allocate-order-select"
                                    value={selectedAllocationOrderId}
                                    onChange={(e) => setSelectedAllocationOrderId(e.target.value)}
                                    className="w-full p-2.5 rounded-lg border text-xs bg-white focus:ring-2 focus:ring-teal-500 outline-none"
                                >
                                    <option value="">-- {t('labs.details.payments.allocate_modal.select_order_label', 'اختر الطلب')} --</option>
                                    {eligibleOrdersForAllocation.map(o => {
                                        const rem = getOrderRemaining(o);
                                        return (
                                            <option key={o.id} value={o.id}>
                                                {o.work_type} — {o.patient_name} — {t('labs.details.orders.table.remaining', 'متبقي')} {rem}
                                            </option>
                                        );
                                    })}
                                </select>
                            )}
                        </div>

                        <div className="flex gap-2 pt-2">
                            <button
                                type="button"
                                onClick={handleConfirmAllocate}
                                disabled={!selectedAllocationOrderId || isSubmittingAllocate}
                                className="flex-1 py-2.5 px-4 bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white rounded-lg text-xs font-bold transition-colors shadow-sm"
                            >
                                {isSubmittingAllocate ? '...' : t('labs.details.payments.allocate_modal.confirm', 'تأكيد الربط')}
                            </button>
                            <button
                                type="button"
                                onClick={() => setAllocateModalPayment(null)}
                                className="py-2.5 px-4 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-bold transition-colors"
                            >
                                {t('labs.details.payments.allocate_modal.cancel', 'إلغاء')}
                            </button>
                        </div>
                    </div>
                </Modal>
            )}
        </div>
    );
};

export default LabDetailsModal;
