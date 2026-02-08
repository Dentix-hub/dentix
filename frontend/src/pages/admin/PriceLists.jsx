
import React, { useState, useEffect } from 'react';
import {
    getPriceLists,
    createPriceList,
    updatePriceList,
    deactivatePriceList,
    getInsuranceProviders,
    getPriceList,
    addPriceListItem,
    getProcedures
} from '../../api';
import {
    CurrencyDollarIcon,
    PlusIcon,
    PencilSquareIcon,
    TrashIcon,
    ListBulletIcon,
    ShieldCheckIcon,
    XMarkIcon
} from '@heroicons/react/24/outline';
import { useTranslation } from 'react-i18next';

const PriceListEditor = ({ priceListId, onClose }) => {
    const { t } = useTranslation();
    const [listDetails, setListDetails] = useState(null);
    const [procedures, setProcedures] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');

    useEffect(() => {
        loadData();
    }, [priceListId]);

    const loadData = async () => {
        setLoading(true);
        try {
            const [listRes, procRes] = await Promise.all([
                getPriceList(priceListId),
                getProcedures()
            ]);
            setListDetails(listRes.data);
            setProcedures(procRes.data || []);
        } catch (error) {
            console.error("Error loading details:", error);
        } finally {
            setLoading(false);
        }
    };

    const handlePriceUpdate = async (procId, price) => {
        try {
            await addPriceListItem(priceListId, {
                procedure_id: procId,
                price: parseFloat(price),
                discount_percent: 0 // Optional: Add discount support
            });
            // Update local state without reload
            setListDetails(prev => {
                const existingItemIndex = prev.items.findIndex(i => i.procedure_id === procId);
                const newItem = { procedure_id: procId, price: parseFloat(price) };

                const newItems = [...prev.items];
                if (existingItemIndex >= 0) {
                    newItems[existingItemIndex] = { ...newItems[existingItemIndex], ...newItem };
                } else {
                    newItems.push(newItem);
                }
                return { ...prev, items: newItems };
            });
        } catch (error) {
            console.error("Error updating price:", error);
            alert("Failed to update price");
        }
    };

    if (loading) return <div className="p-8 text-center">Loading Editor...</div>;

    const filteredProcedures = procedures.filter(p =>
        p.name.toLowerCase().includes(searchTerm.toLowerCase())
    );

    return (
        <div className="fixed inset-0 bg-white z-50 flex flex-col">
            <div className="p-6 border-b flex justify-between items-center bg-gray-50">
                <div>
                    <h2 className="text-xl font-bold flex items-center gap-2">
                        <PencilSquareIcon className="w-6 h-6 text-blue-600" />
                        {t('settings.price_lists.editor.title')} {listDetails?.name}
                    </h2>
                    <p className="text-sm text-gray-500">
                        {listDetails?.type === 'insurance' && t('settings.price_lists.editor.coverage_info', { coverage: listDetails.coverage_percent, copay: listDetails.copay_percent })}
                    </p>
                </div>
                <button onClick={onClose} className="p-2 hover:bg-gray-200 rounded-full">
                    <XMarkIcon className="w-6 h-6" />
                </button>
            </div>

            <div className="flex-1 overflow-hidden flex flex-col p-6 max-w-5xl mx-auto w-full">
                <div className="mb-4">
                    <input
                        type="search"
                        placeholder={t('settings.price_lists.editor.search_placeholder')}
                        className="w-full border p-3 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 outline-none"
                        value={searchTerm}
                        onChange={e => setSearchTerm(e.target.value)}
                    />
                </div>

                <div className="flex-1 overflow-y-auto border rounded-xl shadow-sm">
                    <table className="w-full text-right">
                        <thead className="bg-gray-50 text-gray-700 sticky top-0">
                            <tr>
                                <th className="p-4">{t('settings.price_lists.editor.table.service_name')}</th>
                                <th className="p-4 w-32">{t('settings.price_lists.editor.table.base_price')}</th>
                                <th className="p-4 w-40">{t('settings.price_lists.editor.table.list_price')}</th>
                                <th className="p-4 w-32"></th>
                            </tr>
                        </thead>
                        <tbody className="divide-y">
                            {filteredProcedures.map(proc => {
                                const item = listDetails?.items?.find(i => i.procedure_id === proc.id);
                                const price = item ? item.price : '';

                                return (
                                    <tr key={proc.id} className="hover:bg-gray-50">
                                        <td className="p-4 font-medium">{proc.name}</td>
                                        <td className="p-4 text-gray-500">{proc.price}</td>
                                        <td className="p-4">
                                            <input
                                                type="number"
                                                className="w-full border rounded px-3 py-1 text-left focus:ring-2 focus:ring-blue-500 outline-none"
                                                placeholder={proc.price} // Default placeholder
                                                defaultValue={price}
                                                onBlur={(e) => {
                                                    const val = e.target.value;
                                                    if (val && parseFloat(val) !== price) {
                                                        handlePriceUpdate(proc.id, val);
                                                    }
                                                }}
                                            />
                                        </td>
                                        <td className="p-4 text-sm text-gray-400">
                                            {item && <span className="text-green-600">{t('settings.price_lists.editor.table.saved')}</span>}
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default function PriceLists() {
    const { t } = useTranslation();
    const [priceLists, setPriceLists] = useState([]);
    const [insuranceProviders, setInsuranceProviders] = useState([]);
    const [loading, setLoading] = useState(true);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingList, setEditingList] = useState(null); // For metadata editing
    const [editingItemsListId, setEditingItemsListId] = useState(null); // For items editing (full screen)

    const [formData, setFormData] = useState({
        name: '',
        type: 'cash',
        insurance_provider_id: '',
        coverage_percent: 100,
        copay_percent: 0,
        copay_fixed: 0,
        is_default: false
    });

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            setLoading(true);
            const [listsRes, providersRes] = await Promise.all([
                getPriceLists(),
                getInsuranceProviders()
            ]);
            setPriceLists(listsRes.data || []);
            setInsuranceProviders(providersRes.data || []);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    const handleOpenModal = (list = null) => {
        if (list) {
            setEditingList(list);
            // Fetch full details (lazy usually, but here we might need fetching if lists doesn't include details)
            // Lists from API: id, name, type, is_default, is_active.
            // We need full details for modal. Let's assume we fetch details or reset form logic.
            // For now, simpler logic:
            setFormData({
                name: list.name,
                type: list.type,
                insurance_provider_id: '', // Need to fetch detailed info if not in list
                coverage_percent: 100, // Should fetch real values
                copay_percent: 0,
                copay_fixed: 0,
                is_default: list.is_default
            });
            // We should ideally fetch details here if we allow editing metadata
            // We should ideally fetch details here if we allow editing metadata
            getPriceList(list.id).then(response => {
                const details = response.data;
                setFormData({
                    name: details.name,
                    type: details.type,
                    insurance_provider_id: details.insurance_provider_id ? parseInt(details.insurance_provider_id) : '',
                    coverage_percent: details.coverage_percent,
                    copay_percent: details.copay_percent,
                    copay_fixed: details.copay_fixed || 0,
                    is_default: details.is_default
                });
            });
        } else {
            setEditingList(null);
            setFormData({
                name: '',
                type: 'cash',
                insurance_provider_id: '',
                coverage_percent: 100,
                copay_percent: 0,
                copay_fixed: 0,
                is_default: false
            });
        }
        setIsModalOpen(true);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            const payload = { ...formData };
            if (payload.type === 'cash') {
                payload.insurance_provider_id = null;
            }
            if (payload.insurance_provider_id === '') payload.insurance_provider_id = null;

            // Type conversion
            payload.coverage_percent = parseFloat(payload.coverage_percent) || 0;
            payload.copay_percent = parseFloat(payload.copay_percent) || 0;
            payload.copay_fixed = parseFloat(payload.copay_fixed) || 0;

            // Date handling
            if (payload.effective_from === '') payload.effective_from = null;
            if (payload.effective_to === '') payload.effective_to = null;

            if (editingList) {
                await updatePriceList(editingList.id, payload);
            } else {
                await createPriceList(payload);
            }
            setIsModalOpen(false);
            fetchData();
        } catch (error) {
            console.error(error);
            alert("Error saving price list");
        }
    };

    const handleDeactivateList = async (list) => {
        if (!window.confirm(`هل أنت متأكد من تعطيل قائمة الأسعار: ${list.name} ؟`)) return;
        try {
            await deactivatePriceList(list.id);
            fetchData();
        } catch (error) {
            console.error(error);
            alert(error.response?.data?.detail || "فشل تعطيل قائمة الأسعار");
        }
    };

    if (loading) return <div>Loading...</div>;

    return (
        <div className="p-6 relative">
            {editingItemsListId && (
                <PriceListEditor
                    priceListId={editingItemsListId}
                    onClose={() => setEditingItemsListId(null)}
                />
            )}

            <div className="flex justify-between items-center mb-6">
                <div>
                    <h1 className="text-2xl font-bold flex items-center gap-2">
                        <ListBulletIcon className="w-8 h-8 text-green-600" />
                        {t('settings.price_lists.title')}
                    </h1>
                    <p className="text-gray-500 mt-1">{t('settings.price_lists.subtitle')}</p>
                </div>
                <button
                    onClick={() => handleOpenModal()}
                    className="bg-green-600 text-white px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-green-700"
                >
                    <PlusIcon className="w-5 h-5" />
                    {t('settings.price_lists.add_btn')}
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {priceLists.map((list) => (
                    <div key={list.id} className={`p-6 rounded-xl shadow-sm border transition-shadow ${list.is_default ? 'border-green-300 bg-green-50/50' : 'border-gray-100 bg-white hover:shadow-md'}`}>
                        <div className="flex justify-between items-start mb-4">
                            <div className={`p-3 rounded-lg ${list.type === 'insurance' ? 'bg-purple-50 text-purple-600' : 'bg-green-50 text-green-600'}`}>
                                {list.type === 'insurance' ? <ShieldCheckIcon className="w-8 h-8" /> : <CurrencyDollarIcon className="w-8 h-8" />}
                            </div>
                            <div className="flex gap-2">
                                <button
                                    onClick={() => setEditingItemsListId(list.id)}
                                    className="px-3 py-1 bg-blue-50 text-blue-600 text-xs rounded-full hover:bg-blue-100 font-medium"
                                >
                                    {t('settings.price_lists.edit_prices')}
                                </button>
                                <button
                                    onClick={() => handleOpenModal(list)}
                                    className="p-1 text-gray-400 hover:text-blue-600"
                                >
                                    <PencilSquareIcon className="w-5 h-5" />
                                </button>
                                <button
                                    onClick={() => {
                                        if (list.is_default) {
                                            alert(t('settings.price_lists.cannot_deactivate_default'));
                                            return;
                                        }
                                        handleDeactivateList(list);
                                    }}
                                    className={`p-1 ${list.is_default ? 'text-gray-200 cursor-not-allowed' : 'text-gray-400 hover:text-red-500'}`}
                                    title={list.is_default ? t('settings.price_lists.cannot_deactivate_default') : t('settings.price_lists.deactivate_confirm')}
                                >
                                    <TrashIcon className="w-5 h-5" />
                                </button>
                            </div>
                        </div>

                        <h3 className="text-lg font-bold mb-1 flex items-center gap-2">
                            {list.name}
                            {list.is_default && <span className="text-[10px] bg-green-100 text-green-700 px-2 py-0.5 rounded-full">{t('settings.price_lists.default_badge')}</span>}
                        </h3>
                        <p className="text-sm text-gray-500">
                            {list.type === 'insurance' ? t('settings.price_lists.insurance_list') : t('settings.price_lists.cash_list')}
                        </p>

                        {!list.is_active && (
                            <div className="mt-4 text-center bg-red-50 text-red-600 py-1 text-xs rounded">
                                {t('settings.price_lists.inactive')}
                            </div>
                        )}
                    </div>
                ))}
            </div>

            {/* Modal for Metadata */}
            {isModalOpen && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-40 p-4">
                    <div className="bg-white rounded-xl shadow-xl w-full max-w-lg overflow-hidden">
                        <div className="p-6 border-b border-gray-100">
                            <h2 className="text-xl font-bold">
                                {editingList ? t('settings.price_lists.edit_modal_title') : t('settings.price_lists.add_modal_title')}
                            </h2>
                        </div>

                        <form onSubmit={handleSubmit} className="p-6 space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">{t('settings.price_lists.list_name')}</label>
                                <input
                                    type="text"
                                    required
                                    className="w-full border border-gray-300 rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-green-500"
                                    value={formData.name}
                                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                                    placeholder={t('settings.price_lists.list_name_placeholder')}
                                />
                            </div>

                            <div className="flex gap-4">
                                <div className="flex-1">
                                    <label className="block text-sm font-medium text-gray-700 mb-1">{t('settings.price_lists.type')}</label>
                                    <select
                                        className="w-full border border-gray-300 rounded-lg px-3 py-2"
                                        value={formData.type}
                                        onChange={e => setFormData({ ...formData, type: e.target.value })}
                                    >
                                        <option value="cash">{t('settings.price_lists.type_cash')}</option>
                                        <option value="insurance">{t('settings.price_lists.type_insurance')}</option>
                                    </select>
                                </div>

                                {formData.type === 'insurance' && (
                                    <div className="flex-1">
                                        <label className="block text-sm font-medium text-gray-700 mb-1">{t('settings.price_lists.insurance_provider')}</label>
                                        <select
                                            className="w-full border border-gray-300 rounded-lg px-3 py-2"
                                            value={formData.insurance_provider_id}
                                            onChange={e => setFormData({ ...formData, insurance_provider_id: e.target.value })}
                                            required={formData.type === 'insurance'}
                                        >
                                            <option value="">{t('settings.price_lists.select_provider')}</option>
                                            {insuranceProviders.map(p => (
                                                <option key={p.id} value={p.id}>{p.name}</option>
                                            ))}
                                        </select>
                                    </div>
                                )}
                            </div>

                            {formData.type === 'insurance' && (
                                <div className="grid grid-cols-2 gap-4 bg-purple-50 p-4 rounded-lg">
                                    <div>
                                        <label className="block text-xs font-bold text-gray-600 mb-1">{t('settings.price_lists.coverage_percent')}</label>
                                        <input
                                            type="number"
                                            className="w-full border border-gray-300 rounded px-2 py-1"
                                            value={formData.coverage_percent}
                                            onChange={e => setFormData({ ...formData, coverage_percent: parseFloat(e.target.value) })}
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-xs font-bold text-gray-600 mb-1">{t('settings.price_lists.copay_percent')}</label>
                                        <input
                                            type="number"
                                            className="w-full border border-gray-300 rounded px-2 py-1"
                                            value={formData.copay_percent}
                                            onChange={e => setFormData({ ...formData, copay_percent: parseFloat(e.target.value) })}
                                        />
                                    </div>
                                </div>
                            )}

                            <label className="flex items-center gap-2 cursor-pointer mt-2">
                                <input
                                    type="checkbox"
                                    checked={formData.is_default}
                                    onChange={e => setFormData({ ...formData, is_default: e.target.checked })}
                                    className="w-4 h-4 text-green-600 rounded"
                                />
                                <span className="text-sm font-medium">{t('settings.price_lists.set_default')}</span>
                            </label>

                            <div className="flex gap-3 mt-8">
                                <button
                                    type="button"
                                    onClick={() => setIsModalOpen(false)}
                                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
                                >
                                    {t('settings.price_lists.cancel')}
                                </button>
                                <button
                                    type="submit"
                                    className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                                >
                                    {t('settings.price_lists.save')}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
