import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { FlaskConical, Plus, Edit2, Trash2, X, Phone, MapPin, Mail, User, Search, Building2, Crown } from 'lucide-react';
import { getLaboratories, createLaboratory, updateLaboratory, deleteLaboratory, getLabOrdersStats } from '../api';
import LabDetailsModal from './LabDetailsModal';
import GlobalLabOrdersModal from './GlobalLabOrdersModal';
export default function Labs() {
    const { t } = useTranslation();
    const [labs, setLabs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [stats, setStats] = useState(null);
    // Modal State
    const [selectedLab, setSelectedLab] = useState(null);
    const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);
    const [isGlobalModalOpen, setIsGlobalModalOpen] = useState(false);
    const [globalModalTitle, setGlobalModalTitle] = useState('');
    const [globalModalStatus, setGlobalModalStatus] = useState('');
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingLab, setEditingLab] = useState(null);
    const [formData, setFormData] = useState({
        name: '',
        phone: '',
        address: '',
        contact_person: '',
        email: '',
        specialties: '',
        notes: ''
    });
    useEffect(() => {
        loadData();
    }, []);
    const loadData = async () => {
        try {
            setLoading(true);
            const [labsRes, statsRes] = await Promise.all([
                getLaboratories(),
                getLabOrdersStats()
            ]);
            setLabs(labsRes.data);
            setStats(statsRes.data);
        } catch (err) {
            console.error('Failed to load labs:', err);
        } finally {
            setLoading(false);
        }
    };
    const handleOpenModal = (lab = null) => {
        if (lab) {
            setEditingLab(lab);
            setFormData({
                name: lab.name || '',
                phone: lab.phone || '',
                address: lab.address || '',
                contact_person: lab.contact_person || '',
                email: lab.email || '',
                specialties: lab.specialties || '',
                notes: lab.notes || ''
            });
        } else {
            setEditingLab(null);
            setFormData({
                name: '',
                phone: '',
                address: '',
                contact_person: '',
                email: '',
                specialties: '',
                notes: ''
            });
        }
        setIsModalOpen(true);
    };
    const handleCloseModal = () => {
        setIsModalOpen(false);
        setEditingLab(null);
    };
    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            if (editingLab) {
                await updateLaboratory(editingLab.id, formData);
            } else {
                await createLaboratory(formData);
            }
            handleCloseModal();
            loadData();
        } catch (err) {
            alert(t('labs.messages.save_error'));
            console.error(err);
        }
    };
    const handleDelete = async (id) => {
        if (!window.confirm(t('labs.actions.confirm_delete'))) return;
        try {
            await deleteLaboratory(id);
            loadData();
        } catch (err) {
            alert(t('labs.messages.delete_error'));
            console.error(err);
        }
    };
    const filteredLabs = labs.filter(lab =>
        lab.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (lab.contact_person && lab.contact_person.toLowerCase().includes(searchQuery.toLowerCase()))
    );
    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent"></div>
            </div>
        );
    }
    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-3">
                        <div className="p-2 bg-purple-100 rounded-xl">
                            <FlaskConical className="text-purple-600" size={24} />
                        </div>
                        {t('labs.title')}
                    </h1>
                    <p className="text-slate-500 text-sm mt-1">{t('labs.subtitle')}</p>
                </div>
                <button
                    onClick={() => handleOpenModal()}
                    className="flex items-center gap-2 px-6 py-3 bg-purple-600 text-white font-bold rounded-xl hover:bg-purple-700 shadow-lg shadow-purple-500/20 transition-all"
                >
                    <Plus size={20} />
                    {t('labs.actions.add_lab')}
                </button>
            </div>
            {/* Stats Cards */}
            {stats && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-white p-4 rounded-xl border border-slate-100 shadow-sm">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-purple-100 rounded-lg">
                                <Building2 className="text-purple-600" size={20} />
                            </div>
                            <div>
                                <p className="text-xs text-slate-500 font-bold">{t('labs.stats.total_labs')}</p>
                                <p className="text-xl font-bold text-slate-800">{stats.total_labs}</p>
                            </div>
                        </div>
                    </div>
                    <div
                        onClick={() => {
                            setGlobalModalTitle(t('labs.stats.pending_orders'));
                            setGlobalModalStatus('pending');
                            setIsGlobalModalOpen(true);
                        }}
                        className="bg-white p-4 rounded-xl border border-slate-100 shadow-sm cursor-pointer hover:shadow-md transition-all hover:border-amber-200"
                    >
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-amber-100 rounded-lg">
                                <Crown className="text-amber-600" size={20} />
                            </div>
                            <div>
                                <p className="text-xs text-slate-500 font-bold">{t('labs.stats.pending_orders')}</p>
                                <p className="text-xl font-bold text-amber-600">{stats.pending_orders}</p>
                            </div>
                        </div>
                    </div>
                    <div
                        onClick={() => {
                            setGlobalModalTitle(t('labs.stats.completed_orders'));
                            setGlobalModalStatus('completed');
                            setIsGlobalModalOpen(true);
                        }}
                        className="bg-white p-4 rounded-xl border border-slate-100 shadow-sm cursor-pointer hover:shadow-md transition-all hover:border-emerald-200"
                    >
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-emerald-100 rounded-lg">
                                <Crown className="text-emerald-600" size={20} />
                            </div>
                            <div>
                                <p className="text-xs text-slate-500 font-bold">{t('labs.stats.completed_orders')}</p>
                                <p className="text-xl font-bold text-emerald-600">{stats.completed_orders}</p>
                            </div>
                        </div>
                    </div>
                    <div className="bg-white p-4 rounded-xl border border-slate-100 shadow-sm">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-blue-100 rounded-lg">
                                <FlaskConical className="text-blue-600" size={20} />
                            </div>
                            <div>
                                <p className="text-xs text-slate-500 font-bold">{t('labs.stats.profit')}</p>
                                <p className="text-xl font-bold text-blue-600">{stats.profit?.toFixed(0)}</p>
                            </div>
                        </div>
                    </div>
                </div>
            )}
            {/* Search */}
            <div className="relative">
                <Search className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400" size={20} />
                <input
                    type="text"
                    placeholder={t('labs.search_placeholder')}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pr-12 pl-4 py-3 bg-white border border-slate-200 rounded-xl outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all"
                />
            </div>
            {/* Labs Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredLabs.map(lab => (
                    <div
                        key={lab.id}
                        onClick={(e) => {
                            // Prevent opening details if clicking edit/delete buttons
                            if (e.target.closest('button')) return;
                            setSelectedLab(lab);
                            setIsDetailsModalOpen(true);
                        }}
                        className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm hover:shadow-md transition-all cursor-pointer hover:border-purple-300 group"
                    >
                        <div className="flex justify-between items-start mb-4">
                            <div className="flex items-center gap-3">
                                <div className="p-3 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-xl text-white">
                                    <FlaskConical size={24} />
                                </div>
                                <div>
                                    <h3 className="font-bold text-slate-800">{lab.name}</h3>
                                    {lab.contact_person && (
                                        <p className="text-sm text-slate-500 flex items-center gap-1">
                                            <User size={12} />
                                            {lab.contact_person}
                                        </p>
                                    )}
                                </div>
                            </div>
                            <div className={`px-2 py-1 rounded-full text-xs font-bold ${lab.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
                                {lab.is_active ? t('labs.active') : t('labs.inactive')}
                            </div>
                        </div>
                        <div className="space-y-2 text-sm text-slate-600 mb-4">
                            {lab.phone && (
                                <div className="flex items-center gap-2">
                                    <Phone size={14} className="text-slate-400" />
                                    <span dir="ltr">{lab.phone}</span>
                                </div>
                            )}
                            {lab.email && (
                                <div className="flex items-center gap-2">
                                    <Mail size={14} className="text-slate-400" />
                                    <span>{lab.email}</span>
                                </div>
                            )}
                            {lab.address && (
                                <div className="flex items-center gap-2">
                                    <MapPin size={14} className="text-slate-400" />
                                    <span className="truncate">{lab.address}</span>
                                </div>
                            )}
                        </div>
                        {lab.specialties && (
                            <div className="flex flex-wrap gap-1 mb-3">
                                {lab.specialties.split(',').map((s, i) => (
                                    <span key={i} className="px-2 py-0.5 bg-purple-50 text-purple-700 text-xs rounded-full font-medium">
                                        {s.trim()}
                                    </span>
                                ))}
                            </div>
                        )}
                        {lab.notes && (
                            <p className="text-xs text-slate-500 bg-slate-50 p-2 rounded-lg mb-4 line-clamp-2">
                                {lab.notes}
                            </p>
                        )}
                        <div className="flex gap-2 pt-3 border-t border-slate-100">
                            <button
                                onClick={() => handleOpenModal(lab)}
                                className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                            >
                                <Edit2 size={16} />
                                {t('labs.actions.edit')}
                            </button>
                            <button
                                onClick={() => handleDelete(lab.id)}
                                className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                            >
                                <Trash2 size={16} />
                                {t('labs.actions.delete')}
                            </button>
                        </div>
                    </div>
                ))}
                {filteredLabs.length === 0 && (
                    <div className="col-span-full py-12 text-center bg-slate-50 rounded-2xl border border-dashed border-slate-200">
                        <FlaskConical size={48} className="mx-auto mb-3 text-slate-300" />
                        <FlaskConical size={48} className="mx-auto mb-3 text-slate-300" />
                        <p className="text-slate-500">{t('labs.empty')}</p>
                        <button
                            onClick={() => handleOpenModal()}
                            className="mt-4 text-purple-600 font-bold hover:underline"
                        >
                            {t('labs.add_new_empty')}
                        </button>
                    </div>
                )}
            </div>
            {/* Add/Edit Modal */}
            {isModalOpen && (
                <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
                    <div className="bg-white w-full max-w-lg rounded-2xl p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="text-xl font-bold text-slate-800">
                                {editingLab ? t('labs.form.edit_title') : t('labs.form.add_title')}
                            </h3>
                            <button
                                onClick={handleCloseModal}
                                className="p-2 hover:bg-slate-100 rounded-lg text-slate-400 hover:text-slate-600 transition-colors"
                            >
                                <X size={20} />
                            </button>
                        </div>
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div>
                                <label className="block text-sm font-bold text-slate-600 mb-1">
                                    {t('labs.form.name')} <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    className="w-full p-3 bg-slate-50 rounded-xl outline-none focus:ring-2 focus:ring-purple-500/20 border border-transparent focus:border-purple-500"
                                    placeholder={t('labs.form.placeholders.name')}
                                    required
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-bold text-slate-600 mb-1">{t('labs.form.phone')}</label>
                                    <input
                                        type="tel"
                                        value={formData.phone}
                                        onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                                        className="w-full p-3 bg-slate-50 rounded-xl outline-none focus:ring-2 focus:ring-purple-500/20 border border-transparent focus:border-purple-500"
                                        placeholder={t('labs.form.placeholders.phone')}
                                        dir="ltr"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-bold text-slate-600 mb-1">{t('labs.form.email')}</label>
                                    <input
                                        type="email"
                                        value={formData.email}
                                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                        className="w-full p-3 bg-slate-50 rounded-xl outline-none focus:ring-2 focus:ring-purple-500/20 border border-transparent focus:border-purple-500"
                                        placeholder={t('labs.form.placeholders.email')}
                                        dir="ltr"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-bold text-slate-600 mb-1">{t('labs.form.address')}</label>
                                <input
                                    type="text"
                                    value={formData.address}
                                    onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                                    className="w-full p-3 bg-slate-50 rounded-xl outline-none focus:ring-2 focus:ring-purple-500/20 border border-transparent focus:border-purple-500"
                                    placeholder={t('labs.form.placeholders.address')}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-bold text-slate-600 mb-1">{t('labs.form.contact_person')}</label>
                                <input
                                    type="text"
                                    value={formData.contact_person}
                                    onChange={(e) => setFormData({ ...formData, contact_person: e.target.value })}
                                    className="w-full p-3 bg-slate-50 rounded-xl outline-none focus:ring-2 focus:ring-purple-500/20 border border-transparent focus:border-purple-500"
                                    placeholder={t('labs.form.placeholders.contact_person')}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-bold text-slate-600 mb-1">{t('labs.form.specialties')}</label>
                                <input
                                    type="text"
                                    value={formData.specialties}
                                    onChange={(e) => setFormData({ ...formData, specialties: e.target.value })}
                                    className="w-full p-3 bg-slate-50 rounded-xl outline-none focus:ring-2 focus:ring-purple-500/20 border border-transparent focus:border-purple-500"
                                    placeholder={t('labs.form.placeholders.specialties')}
                                />
                                <p className="text-xs text-slate-400 mt-1">{t('labs.form.specialties_hint')}</p>
                            </div>
                            <div>
                                <label className="block text-sm font-bold text-slate-600 mb-1">{t('labs.form.notes')}</label>
                                <textarea
                                    value={formData.notes}
                                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                                    className="w-full p-3 bg-slate-50 rounded-xl outline-none focus:ring-2 focus:ring-purple-500/20 border border-transparent focus:border-purple-500 h-24 resize-none"
                                    placeholder={t('labs.form.placeholders.notes')}
                                />
                            </div>
                            <div className="flex gap-3 pt-4">
                                <button
                                    type="button"
                                    onClick={handleCloseModal}
                                    className="flex-1 px-4 py-3 text-slate-600 hover:bg-slate-100 rounded-xl transition-colors font-bold"
                                >
                                    {t('labs.actions.cancel')}
                                </button>
                                <button
                                    type="submit"
                                    className="flex-1 px-4 py-3 bg-purple-600 text-white rounded-xl hover:bg-purple-700 transition-colors font-bold shadow-lg shadow-purple-500/20"
                                >
                                    {editingLab ? t('labs.actions.save') : t('labs.actions.add')}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
            {/* Lab Details Modal */}
            <LabDetailsModal
                lab={selectedLab}
                isOpen={isDetailsModalOpen}
                onClose={() => setIsDetailsModalOpen(false)}
            />
            {/* Global Orders Modal */}
            <GlobalLabOrdersModal
                isOpen={isGlobalModalOpen}
                onClose={() => setIsGlobalModalOpen(false)}
                initialStatus={globalModalStatus}
                title={globalModalTitle}
            />
        </div>
    );
}
