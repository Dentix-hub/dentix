import { useState, useEffect } from 'react';
import { getMaterials, getProcedureWeights, setProcedureWeight, deleteProcedureWeight } from '@/api/inventory';
import * as api from '@/api';
import { Package, X, Search, Plus, Edit2, Trash2 } from 'lucide-react';
const ProceduresMaterialsModal = ({ isOpen, onClose, procedure }) => {
    const [materials, setMaterials] = useState([]);
    const [weights, setWeights] = useState([]);
    const [loading, setLoading] = useState(false);
    // Form state
    const [selectedMaterial, setSelectedMaterial] = useState('');
    const [amount, setAmount] = useState(1);
    useEffect(() => {
        if (isOpen && procedure) {
            loadData();
        }
    }, [isOpen, procedure]);
    const loadData = async () => {
        setLoading(true);
        try {
            const [matRes, weightRes] = await Promise.all([
                getMaterials(),
                getProcedureWeights({ procedure_id: procedure.id })
            ]);
            setMaterials(matRes.data);
            setWeights(weightRes.data);
        } catch (err) {
            console.error("Failed to load inventory data", err);
        } finally {
            setLoading(false);
        }
    };
    const handleAdd = async () => {
        if (!selectedMaterial || amount <= 0) return;
        try {
            await setProcedureWeight({
                procedure_name: procedure.name, // API uses name currently
                material_id: parseInt(selectedMaterial),
                weight: parseFloat(amount)
            });
            loadData();
            setSelectedMaterial('');
            setAmount(1);
        } catch (err) {
            alert('فشل إضافة المادة');
        }
    };
    const handleDelete = async (weightId) => {
        if (!window.confirm('هل أنت متأكد من إزالة هذه المادة من الإجراء؟')) return;
        try {
            await deleteProcedureWeight(weightId);
            loadData();
        } catch (err) {
            alert('فشل حذف المادة');
        }
    };
    if (!isOpen) return null;
    return (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4 backdrop-blur-sm animate-in fade-in">
            <div className="bg-white dark:bg-slate-800 w-full max-w-2xl rounded-3xl p-6 shadow-2xl scale-100 animate-in zoom-in-95 duration-200 flex flex-col">
                <div className="flex justify-between items-center mb-6">
                    <div>
                        <h3 className="text-xl font-bold text-slate-800 dark:text-white">إدارة مواد: {procedure?.name}</h3>
                        <p className="text-sm text-slate-500">تكوين المواد المستهلكة لهذا الإجراء</p>
                    </div>
                    <button onClick={onClose}><X /></button>
                </div>
                <div className="space-y-4 animate-in fade-in slide-in-from-left-4">
                    <div className="flex gap-2 items-end bg-slate-50 dark:bg-slate-900/50 p-4 rounded-xl border border-slate-100 dark:border-slate-700">
                        <div className="flex-1">
                            <label className="text-xs font-bold mb-1 block text-slate-600 dark:text-slate-400">المادة</label>
                            <select
                                value={selectedMaterial}
                                onChange={e => setSelectedMaterial(e.target.value)}
                                className="w-full p-2 rounded-lg border bg-white dark:bg-slate-800 dark:border-slate-600"
                            >
                                <option value="">اختر مادة...</option>
                                {materials.map(m => (
                                    <option key={m.id} value={m.id}>{m.name} ({m.base_unit})</option>
                                ))}
                            </select>
                        </div>
                        <div className="w-24">
                            <label className="text-xs font-bold mb-1 block text-slate-600 dark:text-slate-400">الكمية</label>
                            <input
                                type="number" step="0.1"
                                value={amount}
                                onChange={e => setAmount(e.target.value)}
                                className="w-full p-2 rounded-lg border text-center bg-white dark:bg-slate-800 dark:border-slate-600"
                            />
                        </div>
                        <button
                            onClick={handleAdd}
                            disabled={!selectedMaterial}
                            className="bg-indigo-600 text-white p-2.5 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
                        >
                            <Plus size={20} />
                        </button>
                    </div>
                    {/* List */}
                    <div className="space-y-2">
                        {weights.length === 0 ? (
                            <div className="text-center py-8 text-slate-400">لا توجد مواد مرتبطة بهذا الإجراء</div>
                        ) : weights.map(w => {
                            const mat = materials.find(m => m.id === w.material_id);
                            return (
                                <div key={w.id} className="flex justify-between items-center p-3 bg-white dark:bg-slate-800 border dark:border-slate-700 rounded-xl shadow-sm">
                                    <div className="flex items-center gap-3">
                                        <div className="p-2 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 rounded-lg"><Package size={18} /></div>
                                        <div>
                                            <div className="font-bold dark:text-slate-200">{mat?.name || 'مادة غير معروفة'}</div>
                                            <div className="text-xs text-slate-500">يخصم: {w.weight} {mat?.base_unit}</div>
                                        </div>
                                    </div>
                                    <button onClick={() => handleDelete(w.id)} className="text-xs text-red-500 hover:align-baseline hover:text-red-700">حذف</button>
                                </div>
                            );
                        })}
                    </div>
                    <div className="bg-blue-50 dark:bg-blue-900/20 p-3 rounded-lg text-xs text-blue-700 dark:text-blue-300 mt-4">
                        💡 لتحليل التكلفة واستهلاك المواد (Coverage)، انتقل إلى قسم <b>التحليلات الذكية</b>.
                    </div>
                </div>
                <div className="pt-4 border-t dark:border-slate-700 mt-6">
                    <button onClick={onClose} className="w-full py-3 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 font-bold rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600">إغلاق</button>
                </div>
            </div>
        </div>
    );
};
const ProceduresSettings = ({ setMessage }) => {
    const [procedures, setProcedures] = useState([]);
    const [isProcLoading, setIsProcLoading] = useState(false);
    const [isProcModalOpen, setIsProcModalOpen] = useState(false);
    const [editingProc, setEditingProc] = useState(null);
    const [newProc, setNewProc] = useState({ name: '', price: '' });
    const [procSearch, setProcSearch] = useState('');
    // Material Modal State
    const [materialModal, setMaterialModal] = useState({ open: false, procedure: null });
    useEffect(() => {
        loadProcedures();
    }, []);
    const loadProcedures = async () => {
        setIsProcLoading(true);
        try {
            const res = await api.getProcedures();
            setProcedures(res.data);
        } catch (err) {
            console.error(err);
        } finally {
            setIsProcLoading(false);
        }
    };
    const handleSaveProcedure = async (e) => {
        e.preventDefault();
        try {
            const payload = {
                name: newProc.name,
                price: parseFloat(newProc.price) || 0
            };
            if (editingProc) {
                await api.updateProcedure(editingProc.id, payload);
            } else {
                await api.createProcedure(payload);
            }
            setIsProcModalOpen(false);
            setNewProc({ name: '', price: '' });
            setEditingProc(null);
            loadProcedures();
            setMessage({ type: 'success', text: editingProc ? 'تم تعديل الإجراء بنجاح' : 'تم إضافة الإجراء بنجاح' });
            setTimeout(() => setMessage(null), 3000);
        } catch (err) {
            setMessage({ type: 'error', text: 'حدث خطأ أثناء الحفظ' });
        }
    };
    const handleDeleteProcedure = async (id) => {
        if (!window.confirm('هل أنت متأكد من حذف هذا الإجراء؟')) return;
        try {
            await api.deleteProcedure(id);
            loadProcedures();
            setMessage({ type: 'success', text: 'تم حذف الإجراء بنجاح' });
            setTimeout(() => setMessage(null), 3000);
        } catch (err) {
            setMessage({ type: 'error', text: 'فشل الحذف' });
        }
    };
    const openEditProc = (proc) => {
        setEditingProc(proc);
        setNewProc({ name: proc.name, price: proc.price });
        setIsProcModalOpen(true);
    };
    const filteredProcedures = procedures.filter(p => p.name.toLowerCase().includes(procSearch.toLowerCase()));
    return (
        <div className="space-y-6">
            <div className="flex justify-between gap-4">
                <div className="relative flex-1">
                    <Search className="absolute right-4 top-3.5 text-slate-400" size={20} />
                    <input
                        type="text"
                        placeholder="بحث عن إجراء..."
                        className="w-full p-3 pr-12 bg-slate-50 dark:bg-slate-900/50 rounded-xl border border-slate-200 outline-none focus:border-indigo-500 font-bold"
                        value={procSearch}
                        onChange={(e) => setProcSearch(e.target.value)}
                    />
                </div>
                <button
                    onClick={() => {
                        setEditingProc(null);
                        setNewProc({ name: '', price: '' });
                        setIsProcModalOpen(true);
                    }}
                    className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-bold hover:bg-indigo-700 transition flex items-center gap-2"
                >
                    <Plus size={20} />
                    إضافة
                </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {isProcLoading ? (
                    <div className="col-span-2 text-center py-10 text-slate-500">جاري التحميل...</div>
                ) : filteredProcedures.map(proc => (
                    <div key={proc.id} className="group p-4 bg-slate-50 dark:bg-slate-900/30 rounded-xl border border-slate-100 dark:border-white/5 flex justify-between items-center hover:bg-white dark:hover:bg-slate-800 transition-colors shadow-sm hover:shadow-md">
                        <div>
                            <h4 className="font-bold text-slate-800 dark:text-white">{proc.name}</h4>
                            <p className="text-indigo-600 font-bold mt-1">{proc.price} ج.م</p>
                        </div>
                        <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button
                                onClick={() => setMaterialModal({ open: true, procedure: proc })}
                                className="p-2 text-slate-500 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg"
                                title="المواد المستهلكة"
                            >
                                <Package size={18} />
                            </button>
                            <button onClick={() => openEditProc(proc)} className="p-2 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg"><Edit2 size={18} /></button>
                            <button onClick={() => handleDeleteProcedure(proc.id)} className="p-2 text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-lg"><Trash2 size={18} /></button>
                        </div>
                    </div>
                ))}
            </div>
            {/* Proc Modal */}
            {isProcModalOpen && (
                <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4 backdrop-blur-sm animate-in fade-in">
                    <div className="bg-white dark:bg-slate-800 w-full max-w-md rounded-3xl p-8 shadow-2xl scale-100 animate-in zoom-in-95 duration-200">
                        <h3 className="text-2xl font-bold mb-6 text-slate-800 dark:text-white">{editingProc ? 'تعديل الخدمة' : 'إضافة خدمة جديدة'}</h3>
                        <form onSubmit={handleSaveProcedure} className="space-y-5">
                            <div>
                                <label className="text-sm font-bold text-slate-600 dark:text-slate-400 mb-2 block">اسم الخدمة</label>
                                <input
                                    value={newProc.name}
                                    onChange={e => setNewProc({ ...newProc, name: e.target.value })}
                                    className="w-full p-4 bg-slate-50 dark:bg-slate-900 rounded-xl outline-none border focus:border-indigo-500 font-bold"
                                    required
                                />
                            </div>
                            <div>
                                <label className="text-sm font-bold text-slate-600 dark:text-slate-400 mb-2 block">السعر (ج.م)</label>
                                <input
                                    value={newProc.price}
                                    onChange={e => setNewProc({ ...newProc, price: e.target.value })}
                                    type="number"
                                    className="w-full p-4 bg-slate-50 dark:bg-slate-900 rounded-xl outline-none border focus:border-indigo-500 font-bold"
                                    required
                                />
                            </div>
                            <div className="flex gap-3 mt-8">
                                <button type="button" onClick={() => setIsProcModalOpen(false)} className="flex-1 py-3 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-xl font-bold text-slate-600 transition">إلغاء</button>
                                <button type="submit" className="flex-1 py-3 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 font-bold shadow-lg shadow-indigo-500/20 transition">حفظ</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
            {/* Materials Modal */}
            <ProceduresMaterialsModal
                isOpen={materialModal.open}
                onClose={() => setMaterialModal({ ...materialModal, open: false })}
                procedure={materialModal.procedure}
            />
        </div>
    );
};
export default ProceduresSettings;

