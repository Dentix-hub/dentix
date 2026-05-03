import { useState, useEffect } from 'react';
import { FlaskConical, CheckCircle, Clock, AlertCircle, Plus, Edit2, Trash2, X } from 'lucide-react';
import { getPatientLabOrders, getLaboratories, createLabOrder, updateLabOrder, deleteLabOrder } from '@/api';
import { useTranslation } from 'react-i18next';
const LabOrdersTab = ({ patientId }) => {
    const { t } = useTranslation();
    const [labOrders, setLabOrders] = useState([]);
    const [laboratories, setLaboratories] = useState([]);
    const [loading, setLoading] = useState(false);
    // Modal State
    const [isLabOrderModalOpen, setIsLabOrderModalOpen] = useState(false);
    const [editingLabOrder, setEditingLabOrder] = useState(null);
    const initialLabOrder = { laboratory_id: '', work_type: '', tooth_number: '', shade: '', material: '', cost: '', price_to_patient: '', notes: '' };
    const [newLabOrder, setNewLabOrder] = useState(initialLabOrder);
    useEffect(() => {
        if (patientId) {
            loadData();
        }
    }, [patientId]);
    const loadData = async () => {
        setLoading(true);
        try {
            const [ordersRes, labsRes] = await Promise.all([
                getPatientLabOrders(patientId),
                getLaboratories()
            ]);
            setLabOrders(ordersRes.data);
            setLaboratories(labsRes.data);
        } catch (err) {
            console.error("Failed to load lab data", err);
        } finally {
            setLoading(false);
        }
    };
    const handleDeleteLabOrder = async (orderId) => {
        if (!window.confirm(t('patientDetails.lab_orders.confirm_delete'))) return;
        try {
            await deleteLabOrder(orderId);
            loadData();
        } catch (err) {
            alert(t('patientDetails.lab_orders.delete_failed'));
        }
    };
    const handleSaveLabOrder = async () => {
        if (!newLabOrder.laboratory_id || !newLabOrder.work_type) {
            alert(t('patientDetails.lab_orders.validation_error'));
            return;
        }
        try {
            const orderData = {
                patient_id: parseInt(patientId),
                laboratory_id: parseInt(newLabOrder.laboratory_id),
                work_type: newLabOrder.work_type,
                tooth_number: newLabOrder.tooth_number,
                shade: newLabOrder.shade,
                material: newLabOrder.material,
                cost: parseFloat(newLabOrder.cost) || 0,
                price_to_patient: parseFloat(newLabOrder.price_to_patient) || 0,
                notes: newLabOrder.notes
            };
            if (editingLabOrder) {
                orderData.status = newLabOrder.status;
                await updateLabOrder(editingLabOrder.id, orderData);
            } else {
                await createLabOrder(orderData);
            }
            setIsLabOrderModalOpen(false);
            setNewLabOrder(initialLabOrder);
            setEditingLabOrder(null);
            loadData();
        } catch (err) {
            alert(t('patientDetails.lab_orders.save_error'));
            console.error(err);
        }
    };
    if (loading && labOrders.length === 0) return <div className="p-10 text-center">Loading...</div>;
    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-300">
            {/* Lab Stats */}
            <div className="grid grid-cols-3 gap-4">
                <div className="bg-white p-4 rounded-xl border border-slate-100 shadow-sm">
                    <p className="text-xs text-slate-500 font-bold uppercase mb-1">{t('patientDetails.lab_orders.stats.total_orders')}</p>
                    <p className="text-2xl font-bold text-slate-800">{labOrders.length}</p>
                </div>
                <div className="bg-white p-4 rounded-xl border border-slate-100 shadow-sm">
                    <p className="text-xs text-slate-500 font-bold uppercase mb-1">{t('patientDetails.lab_orders.stats.prosthetics_cost')}</p>
                    <p className="text-2xl font-bold text-teal-600">
                        {labOrders.reduce((acc, curr) => acc + (curr.price_to_patient || 0), 0)}
                    </p>
                </div>
                <div className="bg-white p-4 rounded-xl border border-slate-100 shadow-sm">
                    <p className="text-xs text-slate-500 font-bold uppercase mb-1">{t('patientDetails.lab_orders.stats.pending')}</p>
                    <p className="text-2xl font-bold text-amber-600">
                        {labOrders.filter(o => o.status === 'pending' || o.status === 'in_progress').length}
                    </p>
                </div>
            </div>
            {/* Lab Orders List */}
            <div className="bg-white rounded-2xl border border-slate-100 overflow-hidden">
                <div className="p-4 border-b border-slate-50 flex justify-between items-center bg-slate-50/50">
                    <h3 className="font-bold text-slate-700 flex items-center gap-2">
                        <FlaskConical size={20} className="text-teal-600" />
                        {t('patientDetails.lab_orders.title')}
                    </h3>
                    <button
                        onClick={() => {
                            setEditingLabOrder(null);
                            setNewLabOrder(initialLabOrder);
                            setIsLabOrderModalOpen(true);
                        }}
                        className="flex items-center gap-2 text-teal-600 text-sm font-bold hover:underline"
                    >
                        <Plus size={16} /> {t('patientDetails.lab_orders.add_order')}
                    </button>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-right">
                        <thead className="bg-slate-50 text-slate-600 text-sm font-bold">
                            <tr>
                                <th className="p-4">{t('patientDetails.lab_orders.table.date')}</th>
                                <th className="p-4">{t('patientDetails.lab_orders.table.lab')}</th>
                                <th className="p-4">{t('patientDetails.lab_orders.table.work_type')}</th>
                                <th className="p-4">{t('patientDetails.lab_orders.table.tooth')}</th>
                                <th className="p-4">{t('patientDetails.lab_orders.table.shade')}</th>
                                <th className="p-4">{t('patientDetails.lab_orders.table.status')}</th>
                                <th className="p-4">{t('patientDetails.lab_orders.table.price')}</th>
                                <th className="p-4">{t('patientDetails.lab_orders.table.actions')}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {labOrders.map(order => (
                                <tr key={order.id} className="border-t border-slate-50 hover:bg-slate-50 transition-colors">
                                    <td className="p-4 whitespace-nowrap">{new Date(order.order_date).toLocaleDateString()}</td>
                                    <td className="p-4 font-bold text-slate-700 whitespace-nowrap">{order.laboratory_name}</td>
                                    <td className="p-4 whitespace-nowrap">
                                        <span className="bg-teal-50 text-teal-700 px-2 py-1 rounded-lg text-sm font-medium">{order.work_type}</span>
                                        {order.material && <span className="text-slate-400 text-xs ml-1">({order.material})</span>}
                                    </td>
                                    <td className="p-4 font-bold text-slate-600 whitespace-nowrap">{order.tooth_number || '-'}</td>
                                    <td className="p-4 whitespace-nowrap">{order.shade || '-'}</td>
                                    <td className="p-4 whitespace-nowrap">
                                        <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-bold ${order.status === 'completed' ? 'bg-emerald-100 text-emerald-700' :
                                            order.status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                                                order.status === 'try_in' ? 'bg-indigo-100 text-indigo-700' :
                                                    order.status === 'cancelled' ? 'bg-red-100 text-red-700' :
                                                        'bg-amber-100 text-amber-700'
                                            }`}>
                                            {order.status === 'completed' && <><CheckCircle size={12} /> {t('patientDetails.lab_orders.status.completed')}</>}
                                            {order.status === 'in_progress' && <><Clock size={12} /> {t('patientDetails.lab_orders.status.in_progress')}</>}
                                            {order.status === 'try_in' && <><Clock size={12} /> {t('patientDetails.lab_orders.status.try_in')}</>}
                                            {order.status === 'pending' && <><Clock size={12} /> {t('patientDetails.lab_orders.status.pending')}</>}
                                            {order.status === 'cancelled' && <><AlertCircle size={12} /> {t('patientDetails.lab_orders.status.cancelled')}</>}
                                        </span>
                                    </td>
                                    <td className="p-4 font-bold text-teal-600 whitespace-nowrap">{order.price_to_patient}</td>
                                    <td className="p-4 flex gap-2 whitespace-nowrap">
                                        <button
                                            onClick={() => {
                                                setEditingLabOrder(order);
                                                setNewLabOrder({
                                                    laboratory_id: order.laboratory_id,
                                                    work_type: order.work_type,
                                                    tooth_number: order.tooth_number || '',
                                                    shade: order.shade || '',
                                                    material: order.material || '',
                                                    cost: order.cost,
                                                    price_to_patient: order.price_to_patient,
                                                    notes: order.notes || '',
                                                    status: order.status
                                                });
                                                setIsLabOrderModalOpen(true);
                                            }}
                                            className="p-2 text-slate-400 hover:text-blue-500 hover:bg-blue-50 rounded-lg"
                                        >
                                            <Edit2 size={16} />
                                        </button>
                                        <button
                                            onClick={() => handleDeleteLabOrder(order.id)}
                                            className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg"
                                        >
                                            <Trash2 size={16} />
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                {labOrders.length === 0 && (
                    <div className="p-12 text-center text-slate-400">
                        <FlaskConical size={48} className="mx-auto mb-3 opacity-20" />
                        <p>{t('patientDetails.lab_orders.empty')}</p>
                        <button
                            onClick={() => {
                                setEditingLabOrder(null);
                                setNewLabOrder(initialLabOrder);
                                setIsLabOrderModalOpen(true);
                            }}
                            className="mt-4 text-teal-600 font-bold hover:underline"
                        >
                            {t('patientDetails.lab_orders.add_empty')}
                        </button>
                    </div>
                )}
            </div>
            {/* Lab Order Modal */}
            {isLabOrderModalOpen && (
                <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
                    <div className="bg-white w-full max-w-lg rounded-2xl p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                                <FlaskConical className="text-teal-600" size={24} />
                                {editingLabOrder ? t('patientDetails.lab_orders.modal.title_edit') : t('patientDetails.lab_orders.modal.title_add')}
                            </h3>
                            <button onClick={() => setIsLabOrderModalOpen(false)} className="p-2 hover:bg-slate-100 rounded-lg">
                                <X size={20} />
                            </button>
                        </div>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-bold text-slate-600 mb-1">
                                    {t('patientDetails.lab_orders.modal.lab_label')} <span className="text-red-500">*</span>
                                </label>
                                <select
                                    value={newLabOrder.laboratory_id}
                                    onChange={e => setNewLabOrder({ ...newLabOrder, laboratory_id: e.target.value })}
                                    className="w-full p-3 bg-slate-50 rounded-xl outline-none focus:ring-2 focus:ring-teal-500/20 border border-transparent focus:border-teal-500"
                                    required
                                >
                                    <option value="">{t('patientDetails.lab_orders.modal.lab_placeholder')}</option>
                                    {laboratories.map(lab => (
                                        <option key={lab.id} value={lab.id}>{lab.name}</option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-bold text-slate-600 mb-1">
                                    {t('patientDetails.lab_orders.modal.work_type')} <span className="text-red-500">*</span>
                                </label>
                                <select
                                    value={newLabOrder.work_type}
                                    onChange={e => setNewLabOrder({ ...newLabOrder, work_type: e.target.value })}
                                    className="w-full p-3 bg-slate-50 rounded-xl outline-none focus:ring-2 focus:ring-teal-500/20 border border-transparent focus:border-teal-500"
                                    required
                                >
                                    <option value="">{t('patientDetails.lab_orders.modal.work_type_placeholder')}</option>
                                    <option value="Crown">{t('patientDetails.lab_orders.modal.work_types.crown')}</option>
                                    <option value="Bridge">{t('patientDetails.lab_orders.modal.work_types.bridge')}</option>
                                    <option value="Veneer">{t('patientDetails.lab_orders.modal.work_types.veneer')}</option>
                                    <option value="Inlay">{t('patientDetails.lab_orders.modal.work_types.inlay')}</option>
                                    <option value="Onlay">{t('patientDetails.lab_orders.modal.work_types.onlay')}</option>
                                    <option value="Denture">{t('patientDetails.lab_orders.modal.work_types.denture')}</option>
                                    <option value="Partial Denture">{t('patientDetails.lab_orders.modal.work_types.partial_denture')}</option>
                                    <option value="Implant Crown">{t('patientDetails.lab_orders.modal.work_types.implant_crown')}</option>
                                    <option value="Other">{t('patientDetails.lab_orders.modal.work_types.other')}</option>
                                </select>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-bold text-slate-600 mb-1">{t('patientDetails.lab_orders.modal.tooth_label')}</label>
                                    <input
                                        type="text"
                                        value={newLabOrder.tooth_number}
                                        onChange={e => setNewLabOrder({ ...newLabOrder, tooth_number: e.target.value })}
                                        className="w-full p-3 bg-slate-50 rounded-xl outline-none focus:ring-2 focus:ring-teal-500/20 border border-transparent focus:border-teal-500"
                                        placeholder={t('patientDetails.lab_orders.modal.tooth_placeholder')}
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-bold text-slate-600 mb-1">{t('patientDetails.lab_orders.modal.shade_label')}</label>
                                    <input
                                        type="text"
                                        value={newLabOrder.shade}
                                        onChange={e => setNewLabOrder({ ...newLabOrder, shade: e.target.value })}
                                        className="w-full p-3 bg-slate-50 rounded-xl outline-none focus:ring-2 focus:ring-teal-500/20 border border-transparent focus:border-teal-500"
                                        placeholder={t('patientDetails.lab_orders.modal.shade_placeholder')}
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-bold text-slate-600 mb-1">{t('patientDetails.lab_orders.modal.material_label')}</label>
                                <select
                                    value={newLabOrder.material}
                                    onChange={e => setNewLabOrder({ ...newLabOrder, material: e.target.value })}
                                    className="w-full p-3 bg-slate-50 rounded-xl outline-none focus:ring-2 focus:ring-teal-500/20 border border-transparent focus:border-teal-500"
                                >
                                    <option value="">{t('patientDetails.lab_orders.modal.material_placeholder')}</option>
                                    <option value="Zirconia">{t('patientDetails.lab_orders.modal.materials.zirconia')}</option>
                                    <option value="E-max">{t('patientDetails.lab_orders.modal.materials.emax')}</option>
                                    <option value="PFM">{t('patientDetails.lab_orders.modal.materials.pfm')}</option>
                                    <option value="Full Metal">{t('patientDetails.lab_orders.modal.materials.full_metal')}</option>
                                    <option value="Acrylic">{t('patientDetails.lab_orders.modal.materials.acrylic')}</option>
                                    <option value="Composite">{t('patientDetails.lab_orders.modal.materials.composite')}</option>
                                    <option value="Other">{t('patientDetails.lab_orders.modal.materials.other')}</option>
                                </select>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-bold text-slate-600 mb-1">{t('patientDetails.lab_orders.modal.cost_label')}</label>
                                    <input
                                        type="number"
                                        value={newLabOrder.cost}
                                        onChange={e => setNewLabOrder({ ...newLabOrder, cost: e.target.value })}
                                        className="w-full p-3 bg-slate-50 rounded-xl outline-none focus:ring-2 focus:ring-teal-500/20 border border-transparent focus:border-teal-500"
                                        placeholder="0"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-bold text-slate-600 mb-1">{t('patientDetails.lab_orders.modal.price_label')}</label>
                                    <input
                                        type="number"
                                        value={newLabOrder.price_to_patient}
                                        onChange={e => setNewLabOrder({ ...newLabOrder, price_to_patient: e.target.value })}
                                        className="w-full p-3 bg-slate-50 rounded-xl outline-none focus:ring-2 focus:ring-teal-500/20 border border-transparent focus:border-teal-500"
                                        placeholder="0"
                                    />
                                </div>
                            </div>
                            {editingLabOrder && (
                                <div>
                                    <label className="block text-sm font-bold text-slate-600 mb-1">{t('patientDetails.lab_orders.modal.status_label')}</label>
                                    <select
                                        value={newLabOrder.status}
                                        onChange={e => setNewLabOrder({ ...newLabOrder, status: e.target.value })}
                                        className="w-full p-3 bg-slate-50 rounded-xl outline-none focus:ring-2 focus:ring-teal-500/20 border border-transparent focus:border-teal-500"
                                    >
                                        <option value="pending">{t('patientDetails.lab_orders.status.pending')}</option>
                                        <option value="in_progress">{t('patientDetails.lab_orders.status.in_progress')}</option>
                                        <option value="try_in">{t('patientDetails.lab_orders.status.try_in')}</option>
                                        <option value="completed">{t('patientDetails.lab_orders.status.completed')}</option>
                                        <option value="cancelled">{t('patientDetails.lab_orders.status.cancelled')}</option>
                                    </select>
                                </div>
                            )}
                            <div>
                                <label className="block text-sm font-bold text-slate-600 mb-1">{t('patientDetails.lab_orders.modal.notes_label')}</label>
                                <textarea
                                    value={newLabOrder.notes}
                                    onChange={e => setNewLabOrder({ ...newLabOrder, notes: e.target.value })}
                                    className="w-full p-3 bg-slate-50 rounded-xl outline-none focus:ring-2 focus:ring-teal-500/20 border border-transparent focus:border-teal-500 h-20 resize-none"
                                    placeholder={t('patientDetails.lab_orders.modal.notes_placeholder')}
                                />
                            </div>
                            <div className="flex gap-3 pt-4">
                                <button
                                    onClick={() => setIsLabOrderModalOpen(false)}
                                    className="flex-1 px-4 py-3 text-slate-600 hover:bg-slate-100 rounded-xl transition-colors font-bold"
                                >
                                    {t('patientDetails.lab_orders.modal.cancel')}
                                </button>
                                <button
                                    onClick={handleSaveLabOrder}
                                    className="flex-1 px-4 py-3 bg-teal-600 text-white rounded-xl hover:bg-teal-700 transition-colors font-bold shadow-lg shadow-teal-500/20"
                                >
                                    {editingLabOrder ? t('patientDetails.lab_orders.modal.save_edit') : t('patientDetails.lab_orders.modal.save_add')}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
export default LabOrdersTab;

