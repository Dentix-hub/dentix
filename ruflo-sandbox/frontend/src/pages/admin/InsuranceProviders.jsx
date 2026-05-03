import { useState, useEffect } from 'react';
import {
    getInsuranceProviders,
    createInsuranceProvider,
    updateInsuranceProvider,
    deactivateInsuranceProvider
} from '../../api';
import {
    BuildingOfficeIcon,
    PlusIcon,
    PencilSquareIcon,
    TrashIcon,
    PhoneIcon,
    EnvelopeIcon
} from '@heroicons/react/24/outline';
import { useTranslation } from 'react-i18next';
export default function InsuranceProviders() {
    const { t } = useTranslation();
    const [providers, setProviders] = useState([]);
    const [loading, setLoading] = useState(true);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingProvider, setEditingProvider] = useState(null);
    // Form State
    const [formData, setFormData] = useState({
        name: '',
        code: '',
        contact_email: '',
        contact_phone: '',
        address: '',
        notes: ''
    });
    useEffect(() => {
        fetchProviders();
    }, []);
    const fetchProviders = async () => {
        try {
            setLoading(true);
            const response = await getInsuranceProviders();
            setProviders(response.data || []);
        } catch (error) {
            console.error("Error fetching providers:", error);
        } finally {
            setLoading(false);
        }
    };
    const handleOpenModal = (provider = null) => {
        if (provider) {
            setEditingProvider(provider);
            setFormData({
                name: provider.name,
                code: provider.code || '',
                contact_email: provider.contact_email || '',
                contact_phone: provider.contact_phone || '',
                address: provider.address || '', // Note: API might not return address in list view, check API
                notes: provider.notes || ''
            });
        } else {
            setEditingProvider(null);
            setFormData({
                name: '',
                code: '',
                contact_email: '',
                contact_phone: '',
                address: '',
                notes: ''
            });
        }
        setIsModalOpen(true);
    };
    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            if (editingProvider) {
                await updateInsuranceProvider(editingProvider.id, formData);
            } else {
                await createInsuranceProvider(formData);
            }
            setIsModalOpen(false);
            fetchProviders();
        } catch (error) {
            console.error("Error saving provider:", error);
            alert("Error saving provider. Please check inputs.");
        }
    };
    const handleDelete = async (id) => {
        if (window.confirm("Are you sure you want to deactivate this provider?")) {
            try {
                await deactivateInsuranceProvider(id);
                fetchProviders();
            } catch (error) {
                console.error("Error deactivating:", error);
                alert(error.response?.data?.detail || "فشل حذف/تعطيل شركة التأمين");
            }
        }
    };
    if (loading) return <div className="p-8 text-center">{t('common.loading')}</div>;
    return (
        <div className="p-6">
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h1 className="text-2xl font-bold flex items-center gap-2">
                        <BuildingOfficeIcon className="w-8 h-8 text-blue-600" />
                        {t('insurance.title')}
                    </h1>
                    <p className="text-gray-500 mt-1">{t('insurance.subtitle')}</p>
                </div>
                <button
                    onClick={() => handleOpenModal()}
                    className="bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-blue-700"
                >
                    <PlusIcon className="w-5 h-5" />
                    {t('insurance.add_btn')}
                </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {providers.map((provider) => (
                    <div key={provider.id} className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
                        <div className="flex justify-between items-start mb-4">
                            <div className="bg-blue-50 p-3 rounded-lg">
                                <BuildingOfficeIcon className="w-8 h-8 text-blue-600" />
                            </div>
                            <div className="flex gap-2">
                                <button
                                    onClick={() => handleOpenModal(provider)}
                                    className="p-1 text-gray-400 hover:text-blue-600"
                                >
                                    <PencilSquareIcon className="w-5 h-5" />
                                </button>
                                <button
                                    onClick={() => handleDelete(provider.id)}
                                    className="p-1 text-gray-400 hover:text-red-500"
                                >
                                    <TrashIcon className="w-5 h-5" />
                                </button>
                            </div>
                        </div>
                        <h3 className="text-lg font-bold mb-1">{provider.name}</h3>
                        {provider.code && <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">{t('insurance.code')}: {provider.code}</span>}
                        <div className="mt-4 space-y-2 text-sm text-gray-600">
                            {provider.contact_phone && (
                                <div className="flex items-center gap-2">
                                    <PhoneIcon className="w-4 h-4" />
                                    <span>{provider.contact_phone}</span>
                                </div>
                            )}
                            {provider.contact_email && (
                                <div className="flex items-center gap-2">
                                    <EnvelopeIcon className="w-4 h-4" />
                                    <span>{provider.contact_email}</span>
                                </div>
                            )}
                        </div>
                        <div className="mt-4 pt-4 border-t border-gray-100 flex justify-between items-center text-sm">
                            <span className="text-gray-500">{t('insurance.price_lists_count')}</span>
                            <span className="font-semibold bg-blue-50 text-blue-600 px-2 py-1 rounded-full">
                                {provider.price_lists_count}
                            </span>
                        </div>
                    </div>
                ))}
            </div>
            {/* Modal */}
            {isModalOpen && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-xl shadow-xl w-full max-w-lg overflow-hidden">
                        <div className="p-6 border-b border-gray-100">
                            <h2 className="text-xl font-bold">
                                {editingProvider ? t('insurance.edit_title') : t('insurance.add_title')}
                            </h2>
                        </div>
                        <form onSubmit={handleSubmit} className="p-6 space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">{t('insurance.company_name')}</label>
                                <input
                                    type="text"
                                    required
                                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 outline-none"
                                    value={formData.name}
                                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">{t('insurance.code')}</label>
                                    <input
                                        type="text"
                                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-left"
                                        value={formData.code}
                                        onChange={e => setFormData({ ...formData, code: e.target.value })}
                                        placeholder="EX: ALLIANZ-EG"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">{t('insurance.phone')}</label>
                                    <input
                                        type="tel"
                                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-left"
                                        value={formData.contact_phone}
                                        onChange={e => setFormData({ ...formData, contact_phone: e.target.value })}
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">{t('insurance.email')}</label>
                                <input
                                    type="email"
                                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-left"
                                    value={formData.contact_email}
                                    onChange={e => setFormData({ ...formData, contact_email: e.target.value })}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">{t('insurance.address')}</label>
                                <textarea
                                    className="w-full border border-gray-300 rounded-lg px-3 py-2 h-20"
                                    value={formData.address}
                                    onChange={e => setFormData({ ...formData, address: e.target.value })}
                                />
                            </div>
                            <div className="flex gap-3 mt-8">
                                <button
                                    type="button"
                                    onClick={() => setIsModalOpen(false)}
                                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
                                >
                                    {t('insurance.cancel')}
                                </button>
                                <button
                                    type="submit"
                                    className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                                >
                                    {t('insurance.save')}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}

