import { useState, useEffect } from 'react';
import { Plus, Trash2, DollarSign, TrendingUp, TrendingDown, Calendar } from 'lucide-react';
import { getExpenses, createExpense, deleteExpense, getFinancialStats } from '../api';
import { getTodayStr } from '../utils/toothUtils';
import { useTranslation } from 'react-i18next';
export default function Expenses() {
    const { t } = useTranslation();
    const [expenses, setExpenses] = useState([]);
    const [stats, setStats] = useState({ total_received: 0, total_expenses: 0, net_profit: 0 });
    const [loading, setLoading] = useState(true);
    const [isModalOpen, setIsModalOpen] = useState(false);
    // Form
    const [newItem, setNewItem] = useState({ item_name: '', cost: '', category: 'General', date: getTodayStr(), notes: '' });
    useEffect(() => {
        loadData();
    }, []);
    const loadData = async () => {
        try {
            setLoading(true);
            const [eRes, sRes] = await Promise.all([
                getExpenses(),
                getFinancialStats()
            ]);
            setExpenses(eRes.data);
            setStats(sRes.data);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };
    const handleCreate = async () => {
        if (!newItem.item_name || !newItem.cost) return alert(t('billing.alerts.enter_item_cost'));
        try {
            await createExpense({ ...newItem, cost: parseFloat(newItem.cost) });
            setIsModalOpen(false);
            setNewItem({ item_name: '', cost: '', category: 'General', date: getTodayStr(), notes: '' });
            loadData();
        } catch (err) {
            alert(t('billing.expenses_page.create_fail'));
        }
    };
    const handleDelete = async (id) => {
        if (!confirm(t('billing.alerts.delete_expense_confirm'))) return;
        try {
            await deleteExpense(id);
            loadData();
        } catch (err) {
            console.error(err);
        }
    };
    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <div className="flex flex-col md:flex-row justify-between items-end gap-4">
                <div>
                    <h2 className="text-2xl font-bold text-slate-800">{t('billing.expenses_page.title')}</h2>
                    <p className="text-slate-500">{t('billing.expenses_page.subtitle')}</p>
                </div>
                <button
                    onClick={() => setIsModalOpen(true)}
                    className="flex items-center gap-2 px-6 py-3 bg-red-500 text-white font-bold rounded-xl hover:bg-red-600 shadow-lg shadow-red-500/30 transition-all"
                >
                    <Plus size={20} /> {t('billing.expenses_page.add_button')}
                </button>
            </div>
            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 relative overflow-hidden">
                    <div className="relative z-10">
                        <p className="text-slate-500 font-bold mb-1">{t('billing.stats.total_income')}</p>
                        <h3 className="text-3xl font-bold text-emerald-600">{stats.total_received.toLocaleString()}</h3>
                    </div>
                    <TrendingUp className="absolute left-4 bottom-4 text-emerald-100" size={60} />
                </div>
                <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 relative overflow-hidden">
                    <div className="relative z-10">
                        <p className="text-slate-500 font-bold mb-1">{t('billing.stats.total_expenses')}</p>
                        <h3 className="text-3xl font-bold text-red-500">{stats.total_expenses.toLocaleString()}</h3>
                    </div>
                    <TrendingDown className="absolute left-4 bottom-4 text-red-100" size={60} />
                </div>
                <div className={`p-6 rounded-2xl shadow-sm border relative overflow-hidden ${stats.net_profit >= 0 ? 'bg-gradient-to-br from-blue-500 to-blue-600 border-blue-400 text-white' : 'bg-red-50 border-red-200 text-red-600'}`}>
                    <div className="relative z-10">
                        <p className={`font-bold mb-1 ${stats.net_profit >= 0 ? 'text-blue-100' : 'text-red-400'}`}>{t('billing.stats.net_profit')}</p>
                        <h3 className="text-3xl font-bold">{stats.net_profit.toLocaleString()}</h3>
                    </div>
                    <DollarSign className={`absolute left-4 bottom-4 ${stats.net_profit >= 0 ? 'text-white/20' : 'text-red-200'}`} size={60} />
                </div>
            </div>
            {/* Expenses Table */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-right">
                        <thead className="bg-slate-50 text-slate-600 font-bold text-sm">
                            <tr>
                                <th className="p-4 whitespace-nowrap">{t('billing.expenses.item')}</th>
                                <th className="p-4 whitespace-nowrap">{t('billing.expenses.category')}</th>
                                <th className="p-4 whitespace-nowrap">{t('billing.expenses.date')}</th>
                                <th className="p-4 whitespace-nowrap">{t('billing.expenses.cost')}</th>
                                <th className="p-4 whitespace-nowrap">{t('billing.expenses_page.notes')}</th>
                                <th className="p-4 whitespace-nowrap">{t('billing.expenses.actions')}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-50">
                            {expenses.map(exp => (
                                <tr key={exp.id} className="hover:bg-slate-50 transition-colors">
                                    <td className="p-4 font-bold text-slate-800">{exp.item_name}</td>
                                    <td className="p-4">
                                        <span className="px-3 py-1 bg-slate-100 text-slate-600 rounded-lg text-xs font-bold">{exp.category}</span>
                                    </td>
                                    <td className="p-4 text-slate-500 text-sm flex items-center gap-2">
                                        <Calendar size={14} />
                                        {new Date(exp.date).toLocaleDateString()}
                                    </td>
                                    <td className="p-4 font-bold text-red-500">{exp.cost.toLocaleString()}</td>
                                    <td className="p-4 text-slate-500 text-sm max-w-[200px] truncate">{exp.notes || '-'}</td>
                                    <td className="p-4">
                                        <button onClick={() => handleDelete(exp.id)} className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg"><Trash2 size={16} /></button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                {expenses.length === 0 && <div className="p-12 text-center text-slate-400">{t('billing.expenses_page.empty')}</div>}
            </div>
            {/* Modal */}
            {isModalOpen && (
                <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
                    <div className="bg-white w-full max-w-md rounded-2xl p-6 shadow-2xl animate-in zoom-in duration-200">
                        <h3 className="text-xl font-bold mb-4 text-slate-800">{t('billing.expenses.modal_title')}</h3>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-bold text-slate-700 mb-1">{t('billing.expenses.item')}</label>
                                <input
                                    value={newItem.item_name}
                                    onChange={e => setNewItem({ ...newItem, item_name: e.target.value })}
                                    placeholder={t('billing.expenses.placeholder')}
                                    className="w-full p-3 bg-slate-50 rounded-xl border border-slate-200 outline-none focus:border-primary transition-colors"
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-bold text-slate-700 mb-1">{t('billing.expenses.cost')}</label>
                                    <input
                                        type="number"
                                        value={newItem.cost}
                                        onChange={e => setNewItem({ ...newItem, cost: e.target.value })}
                                        className="w-full p-3 bg-slate-50 rounded-xl border border-slate-200 outline-none focus:border-primary transition-colors"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-bold text-slate-700 mb-1">{t('billing.expenses.category')}</label>
                                    <select
                                        value={newItem.category}
                                        onChange={e => setNewItem({ ...newItem, category: e.target.value })}
                                        className="w-full p-3 bg-slate-50 rounded-xl border border-slate-200 outline-none focus:border-primary transition-colors"
                                    >
                                        <option value="General">{t('billing.expenses.categories.general')}</option>
                                        <option value="Materials">{t('billing.expenses.categories.materials')}</option>
                                        <option value="Salaries">{t('billing.expenses.categories.salaries')}</option>
                                        <option value="Rent">{t('billing.expenses.categories.rent')}</option>
                                        <option value="Utilities">{t('billing.expenses.categories.utilities')}</option>
                                        <option value="Maintenance">{t('billing.expenses.categories.maintenance')}</option>
                                    </select>
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-bold text-slate-700 mb-1">{t('billing.expenses.date')}</label>
                                <input
                                    type="date"
                                    value={newItem.date}
                                    onChange={e => setNewItem({ ...newItem, date: e.target.value })}
                                    className="w-full p-3 bg-slate-50 rounded-xl border border-slate-200 outline-none focus:border-primary transition-colors"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-bold text-slate-700 mb-1">{t('billing.expenses_page.notes')}</label>
                                <textarea
                                    value={newItem.notes}
                                    onChange={e => setNewItem({ ...newItem, notes: e.target.value })}
                                    className="w-full p-3 bg-slate-50 rounded-xl border border-slate-200 outline-none focus:border-primary transition-colors h-24 resize-none"
                                />
                            </div>
                            <div className="flex justify-end gap-3 mt-6">
                                <button onClick={() => setIsModalOpen(false)} className="px-4 py-2 hover:bg-slate-100 rounded-lg font-bold text-slate-500">{t('common.cancel')}</button>
                                <button onClick={handleCreate} className="px-6 py-2 bg-primary text-white font-bold rounded-lg hover:bg-sky-600 shadow-lg shadow-primary/20">{t('common.save')}</button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
