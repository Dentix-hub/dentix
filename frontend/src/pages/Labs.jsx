import { useEffect, useMemo, useState } from 'react';
import logger from '@/utils/logger';
import { useTranslation } from 'react-i18next';
import {
    FlaskConical,
    Plus,
    Edit2,
    Trash2,
    Phone,
    MapPin,
    Mail,
    User,
    Search,
    Building2,
    Crown,
    Home
} from 'lucide-react';
import {
    getLaboratories,
    createLaboratory,
    updateLaboratory,
    deleteLaboratory,
    getLabOrdersStats
} from '../api';
import LabDetailsModal from './LabDetailsModal';
import GlobalLabOrdersModal from './GlobalLabOrdersModal';
import { Modal, PageHeader } from '@/shared/ui';

const emptyForm = {
    name: '',
    phone: '',
    address: '',
    contact_person: '',
    email: '',
    specialties: '',
    notes: ''
};

export default function Labs() {
    const { t } = useTranslation();
    const [labs, setLabs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [stats, setStats] = useState(null);
    const [selectedLab, setSelectedLab] = useState(null);
    const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);
    const [isGlobalModalOpen, setIsGlobalModalOpen] = useState(false);
    const [globalModalTitle, setGlobalModalTitle] = useState('');
    const [globalModalStatus, setGlobalModalStatus] = useState('');
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingLab, setEditingLab] = useState(null);
    const [formData, setFormData] = useState(emptyForm);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            setLoading(true);
            const [labsRes, statsRes] = await Promise.allSettled([
                getLaboratories(),
                getLabOrdersStats()
            ]);

            if (labsRes.status === 'fulfilled') {
                setLabs(Array.isArray(labsRes.value.data) ? labsRes.value.data : []);
            } else {
                logger.error('Failed to load labs:', labsRes.reason);
            }

            if (statsRes.status === 'fulfilled') {
                setStats(statsRes.value.data);
            } else {
                logger.warn('Failed to load lab stats (likely permission issue):', statsRes.reason);
            }
        } catch (error) {
            logger.error('Critical error loading labs data:', error);
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
            setFormData(emptyForm);
        }
        setIsModalOpen(true);
    };

    const handleCloseModal = () => {
        if (saving) return;
        setIsModalOpen(false);
        setEditingLab(null);
    };

    const handleSubmit = async (event) => {
        event.preventDefault();
        try {
            setSaving(true);
            if (editingLab) await updateLaboratory(editingLab.id, formData);
            else await createLaboratory(formData);
            setIsModalOpen(false);
            setEditingLab(null);
            await loadData();
        } catch (error) {
            alert(t('labs.messages.save_error'));
            logger.error(error);
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async (id) => {
        if (!window.confirm(t('labs.actions.confirm_delete'))) return;
        try {
            await deleteLaboratory(id);
            await loadData();
        } catch (error) {
            alert(t('labs.messages.delete_error'));
            logger.error(error);
        }
    };

    const openGlobalOrders = (status, title) => {
        setGlobalModalTitle(title);
        setGlobalModalStatus(status);
        setIsGlobalModalOpen(true);
    };

    const filteredLabs = useMemo(() => {
        const query = searchQuery.trim().toLowerCase();
        return labs.filter(lab =>
            lab.name?.toLowerCase().includes(query)
            || lab.contact_person?.toLowerCase().includes(query)
            || lab.phone?.toLowerCase().includes(query)
        );
    }, [labs, searchQuery]);

    if (loading) {
        return (
            <div className="flex min-h-[50dvh] items-center justify-center">
                <div className="h-12 w-12 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            </div>
        );
    }

    return (
        <div className="min-w-0 space-y-5 pb-8 sm:space-y-6 sm:pb-12">
            <PageHeader
                title={t('labs.title')}
                subtitle={t('labs.subtitle')}
                icon={FlaskConical}
                breadcrumbs={[
                    { label: t('nav.home', 'Home'), icon: Home, path: '/' },
                    { label: t('labs.title') }
                ]}
                actions={
                    <button
                        type="button"
                        onClick={() => handleOpenModal()}
                        className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 font-bold text-white shadow-medium transition-colors hover:bg-indigo-700 sm:w-auto sm:px-6 sm:rounded-2xl"
                    >
                        <Plus size={20} aria-hidden="true" />
                        <span>{t('labs.actions.add_lab')}</span>
                    </button>
                }
            />

            {stats && (
                <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
                    <StatCard
                        label={t('labs.stats.total_labs')}
                        value={stats.total_labs}
                        icon={Building2}
                        iconClass="bg-teal-100 text-teal-600 dark:bg-teal-900/30 dark:text-teal-300"
                    />
                    <StatCard
                        label={t('labs.stats.pending_orders')}
                        value={stats.pending_orders}
                        icon={Crown}
                        iconClass="bg-amber-100 text-amber-600 dark:bg-amber-900/30 dark:text-amber-300"
                        valueClass="text-amber-600 dark:text-amber-300"
                        onClick={() => openGlobalOrders('pending', t('labs.stats.pending_orders'))}
                    />
                    <StatCard
                        label={t('labs.stats.completed_orders')}
                        value={stats.completed_orders}
                        icon={Crown}
                        iconClass="bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-300"
                        valueClass="text-emerald-600 dark:text-emerald-300"
                        onClick={() => openGlobalOrders('completed', t('labs.stats.completed_orders'))}
                    />
                    <StatCard
                        label={t('labs.stats.profit')}
                        value={stats.profit?.toFixed?.(0) ?? stats.profit ?? 0}
                        icon={FlaskConical}
                        iconClass="bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-300"
                        valueClass="text-blue-600 dark:text-blue-300"
                    />
                </div>
            )}

            <div className="relative min-w-0">
                <Search className="pointer-events-none absolute end-3 top-1/2 -translate-y-1/2 text-slate-500 sm:end-4" size={20} aria-hidden="true" />
                <input
                    type="search"
                    placeholder={t('labs.search_placeholder')}
                    value={searchQuery}
                    onChange={event => setSearchQuery(event.target.value)}
                    className="min-h-11 w-full rounded-xl border border-slate-200 bg-white py-2.5 ps-3 pe-11 outline-none transition-all focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 dark:border-slate-700 dark:bg-slate-900 sm:ps-4 sm:pe-12 sm:py-3"
                />
            </div>

            <div className="grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2 md:gap-4 lg:grid-cols-3">
                {filteredLabs.map(lab => (
                    <article key={lab.id} className="min-w-0 rounded-2xl border border-slate-100 bg-white p-3 shadow-sm transition-shadow hover:shadow-md dark:border-slate-800 dark:bg-slate-900 sm:p-5">
                        <button
                            type="button"
                            onClick={() => {
                                setSelectedLab(lab);
                                setIsDetailsModalOpen(true);
                            }}
                            className="w-full min-w-0 text-start"
                            aria-label={`${t('labs.title')}: ${lab.name}`}
                        >
                            <div className="mb-3 flex min-w-0 items-start gap-3 sm:mb-4">
                                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-teal-500 to-indigo-600 text-white">
                                    <FlaskConical size={22} aria-hidden="true" />
                                </div>
                                <div className="min-w-0 flex-1">
                                    <h3 className="break-words font-bold text-slate-800 dark:text-white" dir="auto">{lab.name}</h3>
                                    {lab.contact_person && (
                                        <p className="mt-1 flex min-w-0 items-center gap-1 text-sm text-slate-500 dark:text-slate-400">
                                            <User size={12} className="shrink-0" aria-hidden="true" />
                                            <span className="min-w-0 truncate" dir="auto">{lab.contact_person}</span>
                                        </p>
                                    )}
                                </div>
                                <span className={`shrink-0 rounded-full px-2 py-1 text-[11px] font-bold ${lab.is_active ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300' : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'}`}>
                                    {lab.is_active ? t('labs.active') : t('labs.inactive')}
                                </span>
                            </div>

                            <div className="mb-3 min-w-0 space-y-2 text-sm text-slate-600 dark:text-slate-300 sm:mb-4">
                                {lab.phone && (
                                    <span className="flex min-w-0 items-center gap-2">
                                        <Phone size={14} className="shrink-0 text-slate-500" aria-hidden="true" />
                                        <span dir="ltr" className="break-all">{lab.phone}</span>
                                    </span>
                                )}
                                {lab.email && (
                                    <span className="flex min-w-0 items-center gap-2">
                                        <Mail size={14} className="shrink-0 text-slate-500" aria-hidden="true" />
                                        <span className="min-w-0 break-all" dir="ltr">{lab.email}</span>
                                    </span>
                                )}
                                {lab.address && (
                                    <span className="flex min-w-0 items-start gap-2">
                                        <MapPin size={14} className="mt-0.5 shrink-0 text-slate-500" aria-hidden="true" />
                                        <span className="min-w-0 break-words" dir="auto">{lab.address}</span>
                                    </span>
                                )}
                            </div>

                            {lab.specialties && (
                                <div className="mb-3 flex min-w-0 flex-wrap gap-1.5">
                                    {lab.specialties.split(',').filter(Boolean).map((specialty, index) => (
                                        <span key={`${specialty}-${index}`} className="rounded-full bg-teal-50 px-2 py-1 text-xs font-medium text-teal-700 dark:bg-teal-900/20 dark:text-teal-300">
                                            {specialty.trim()}
                                        </span>
                                    ))}
                                </div>
                            )}
                            {lab.notes && (
                                <p className="mb-3 line-clamp-2 break-words rounded-lg bg-slate-50 p-2 text-xs text-slate-500 dark:bg-slate-800 dark:text-slate-400 sm:mb-4" dir="auto">{lab.notes}</p>
                            )}
                        </button>

                        <div className="grid grid-cols-2 gap-2 border-t border-slate-100 pt-3 dark:border-slate-800">
                            <button
                                type="button"
                                onClick={() => handleOpenModal(lab)}
                                className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm font-bold text-slate-600 transition-colors hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                            >
                                <Edit2 size={16} aria-hidden="true" />
                                {t('labs.actions.edit')}
                            </button>
                            <button
                                type="button"
                                onClick={() => handleDelete(lab.id)}
                                className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm font-bold text-red-500 transition-colors hover:bg-red-50 dark:hover:bg-red-950/30"
                            >
                                <Trash2 size={16} aria-hidden="true" />
                                {t('labs.actions.delete')}
                            </button>
                        </div>
                    </article>
                ))}

                {filteredLabs.length === 0 && (
                    <div className="col-span-full rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-10 text-center dark:border-slate-700 dark:bg-slate-900 sm:py-12">
                        <FlaskConical size={44} className="mx-auto mb-3 text-slate-300" aria-hidden="true" />
                        <p className="text-slate-500">{t('labs.empty')}</p>
                        <button
                            type="button"
                            onClick={() => handleOpenModal()}
                            className="mt-3 inline-flex min-h-11 items-center justify-center rounded-xl px-4 font-bold text-teal-600 transition-colors hover:bg-teal-50 dark:hover:bg-teal-950/20"
                        >
                            {t('labs.add_new_empty')}
                        </button>
                    </div>
                )}
            </div>

            <Modal
                isOpen={isModalOpen}
                onClose={handleCloseModal}
                title={editingLab ? t('labs.form.edit_title') : t('labs.form.add_title')}
                size="lg"
                closeOnOutside={!saving}
            >
                <form onSubmit={handleSubmit} className="min-w-0 space-y-4">
                    <LabField label={t('labs.form.name')} required>
                        <input
                            type="text"
                            value={formData.name}
                            onChange={event => setFormData({ ...formData, name: event.target.value })}
                            className="min-h-11 w-full rounded-xl border border-border bg-background px-3 py-2.5 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20"
                            placeholder={t('labs.form.placeholders.name')}
                            required
                            autoComplete="organization"
                        />
                    </LabField>

                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                        <LabField label={t('labs.form.phone')}>
                            <input
                                type="tel"
                                inputMode="tel"
                                value={formData.phone}
                                onChange={event => setFormData({ ...formData, phone: event.target.value })}
                                className="min-h-11 w-full rounded-xl border border-border bg-background px-3 py-2.5 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20"
                                placeholder={t('labs.form.placeholders.phone')}
                                dir="ltr"
                                autoComplete="tel"
                            />
                        </LabField>
                        <LabField label={t('labs.form.email')}>
                            <input
                                type="email"
                                value={formData.email}
                                onChange={event => setFormData({ ...formData, email: event.target.value })}
                                className="min-h-11 w-full rounded-xl border border-border bg-background px-3 py-2.5 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20"
                                placeholder={t('labs.form.placeholders.email')}
                                dir="ltr"
                                autoComplete="email"
                            />
                        </LabField>
                    </div>

                    <LabField label={t('labs.form.address')}>
                        <input
                            type="text"
                            value={formData.address}
                            onChange={event => setFormData({ ...formData, address: event.target.value })}
                            className="min-h-11 w-full rounded-xl border border-border bg-background px-3 py-2.5 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20"
                            placeholder={t('labs.form.placeholders.address')}
                            autoComplete="street-address"
                        />
                    </LabField>

                    <LabField label={t('labs.form.contact_person')}>
                        <input
                            type="text"
                            value={formData.contact_person}
                            onChange={event => setFormData({ ...formData, contact_person: event.target.value })}
                            className="min-h-11 w-full rounded-xl border border-border bg-background px-3 py-2.5 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20"
                            placeholder={t('labs.form.placeholders.contact_person')}
                            autoComplete="name"
                        />
                    </LabField>

                    <LabField label={t('labs.form.specialties')} hint={t('labs.form.specialties_hint')}>
                        <input
                            type="text"
                            value={formData.specialties}
                            onChange={event => setFormData({ ...formData, specialties: event.target.value })}
                            className="min-h-11 w-full rounded-xl border border-border bg-background px-3 py-2.5 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20"
                            placeholder={t('labs.form.placeholders.specialties')}
                        />
                    </LabField>

                    <LabField label={t('labs.form.notes')}>
                        <textarea
                            value={formData.notes}
                            onChange={event => setFormData({ ...formData, notes: event.target.value })}
                            className="min-h-24 w-full resize-y rounded-xl border border-border bg-background px-3 py-2.5 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20"
                            placeholder={t('labs.form.placeholders.notes')}
                        />
                    </LabField>

                    <div className="sticky bottom-0 z-10 -mx-3 grid grid-cols-1 gap-2 border-t border-border bg-surface-elevated px-3 pb-[max(0.25rem,env(safe-area-inset-bottom))] pt-3 min-[360px]:grid-cols-2 sm:-mx-4 sm:px-4">
                        <button
                            type="button"
                            onClick={handleCloseModal}
                            disabled={saving}
                            className="min-h-11 rounded-xl px-4 py-2 font-bold text-text-secondary transition-colors hover:bg-surface-hover disabled:opacity-50"
                        >
                            {t('labs.actions.cancel')}
                        </button>
                        <button
                            type="submit"
                            disabled={saving}
                            className="min-h-11 rounded-xl bg-teal-600 px-4 py-2 font-bold text-white shadow-medium transition-colors hover:bg-teal-700 disabled:opacity-50"
                        >
                            {saving ? t('common.saving', 'Saving...') : editingLab ? t('labs.actions.save') : t('labs.actions.add')}
                        </button>
                    </div>
                </form>
            </Modal>

            <LabDetailsModal
                lab={selectedLab}
                isOpen={isDetailsModalOpen}
                onClose={() => setIsDetailsModalOpen(false)}
            />
            <GlobalLabOrdersModal
                isOpen={isGlobalModalOpen}
                onClose={() => setIsGlobalModalOpen(false)}
                initialStatus={globalModalStatus}
                title={globalModalTitle}
            />
        </div>
    );
}

function StatCard({ label, value, icon: Icon, iconClass, valueClass = 'text-slate-800 dark:text-white', onClick }) {
    const content = (
        <>
            <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${iconClass}`}>
                <Icon size={19} aria-hidden="true" />
            </span>
            <span className="min-w-0">
                <span className="block break-words text-[11px] font-bold text-slate-500 dark:text-slate-400 sm:text-xs">{label}</span>
                <strong className={`mt-0.5 block break-words text-lg font-bold sm:text-xl ${valueClass}`}>{value}</strong>
            </span>
        </>
    );

    if (onClick) {
        return (
            <button
                type="button"
                onClick={onClick}
                className="flex min-h-24 min-w-0 items-center gap-2 rounded-xl border border-slate-100 bg-white p-3 text-start shadow-sm transition-[box-shadow,border-color] hover:border-primary/30 hover:shadow-md dark:border-slate-800 dark:bg-slate-900 sm:gap-3 sm:p-4"
            >
                {content}
            </button>
        );
    }

    return (
        <div className="flex min-h-24 min-w-0 items-center gap-2 rounded-xl border border-slate-100 bg-white p-3 shadow-sm dark:border-slate-800 dark:bg-slate-900 sm:gap-3 sm:p-4">
            {content}
        </div>
    );
}

function LabField({ label, required = false, hint, children }) {
    return (
        <div className="min-w-0">
            <label className="mb-1 block text-sm font-bold text-text-secondary">
                {label}{required && <span className="ms-1 text-red-500">*</span>}
            </label>
            {children}
            {hint && <p className="mt-1 break-words text-xs text-text-muted">{hint}</p>}
        </div>
    );
}
