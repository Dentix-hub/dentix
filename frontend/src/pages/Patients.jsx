import React, { useState, useMemo, memo, useCallback } from 'react';
import { Search, Plus, User, Trash2, Users, UserPlus, Activity, Phone, MapPin, Calendar, Clock } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { createPatient, deletePatient, searchPatients, getUsers } from '@/api';
import { usePatients } from '@/hooks/usePatients';
import { useAuth } from '@/auth/useAuth';
import PatientScanner from '@/features/patients/PatientScanner';
import { Skeleton, EmptyState, Modal, Button, Input, toast, Badge } from '@/shared/ui';

export default function Patients() {
    const navigate = useNavigate();
    const { t } = useTranslation();

    // Use cached patients data from React Query
    const { data: patients = [], isLoading: loading, refetch } = usePatients();

    const [search, setSearch] = useState('');
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [isScannerOpen, setIsScannerOpen] = useState(false);

    const { user } = useAuth();
    const [doctors, setDoctors] = useState([]);

    // New Patient State
    const [newPatient, setNewPatient] = useState({
        name: '',
        age: '',
        phone: '',
        address: '',
        medical_history: '',
        assigned_doctor_id: ''
    });
    const [suggestions, setSuggestions] = useState([]);
    const [searchTimeoutState, setSearchTimeoutState] = useState(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Fetch Doctors if Admin or Staff
    React.useEffect(() => {
        const fetchDoctors = async () => {
            try {
                // If the user is a doctor, they can assign to themselves by default
                // But we still list other doctors in case they want to assign to a colleague
                const res = await getUsers({ role: 'doctor' });
                setDoctors(res.data);

                // Auto-set assigned_doctor_id if current user is a doctor
                if (user?.role === 'doctor') {
                    setNewPatient(prev => ({ ...prev, assigned_doctor_id: user.id }));
                }
            } catch (err) {
                console.error("Failed to fetch doctors", err);
            }
        };
        if (isModalOpen) fetchDoctors();
    }, [isModalOpen, user]);

    // Modern Vibrant Card Colors - keeping this logic as it adds nice variety
    const cardColors = [
        {
            bg: "bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-slate-800/50 dark:to-slate-900/50",
            border: "border-blue-100 dark:border-blue-900/20",
            text: "text-blue-600 dark:text-blue-400",
            accent: "from-blue-500 to-indigo-600"
        },
        {
            bg: "bg-gradient-to-br from-purple-50 to-fuchsia-50 dark:from-slate-800/50 dark:to-slate-900/50",
            border: "border-purple-100 dark:border-purple-900/20",
            text: "text-purple-600 dark:text-purple-400",
            accent: "from-purple-500 to-fuchsia-600"
        },
        {
            bg: "bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-slate-800/50 dark:to-slate-900/50",
            border: "border-emerald-100 dark:border-emerald-900/20",
            text: "text-emerald-600 dark:text-emerald-400",
            accent: "from-emerald-500 to-teal-600"
        },
        {
            bg: "bg-gradient-to-br from-amber-50 to-orange-50 dark:from-slate-800/50 dark:to-slate-900/50",
            border: "border-amber-100 dark:border-amber-900/20",
            text: "text-amber-600 dark:text-amber-400",
            accent: "from-amber-500 to-orange-600"
        },
        {
            bg: "bg-gradient-to-br from-rose-50 to-pink-50 dark:from-slate-800/50 dark:to-slate-900/50",
            border: "border-rose-100 dark:border-rose-900/20",
            text: "text-rose-600 dark:text-rose-400",
            accent: "from-rose-500 to-pink-600"
        }
    ];

    // cardColors array stays the same...

    // Derived Stats
    const stats = useMemo(() => {
        const total = patients.length;
        const newThisMonth = patients.filter(p => {
            if (!p.created_at) return false;
            const date = new Date(p.created_at);
            const now = new Date();
            return date.getMonth() === now.getMonth() && date.getFullYear() === now.getFullYear();
        }).length;
        const active = Math.floor(total * 0.7); // Mock logic kept
        return { total, newThisMonth, active };
    }, [patients]);

    const handleDeletePatient = useCallback(async (id, name) => {
        if (!window.confirm(t('patients.delete_confirm', { name }))) {
            return;
        }
        const toastId = toast.loading(t('common.loading'));
        try {
            await deletePatient(id);
            toast.success(t('patients.delete_success'), { id: toastId });
            refetch(); // Refetch from cache
        } catch (err) {
            toast.error(t('patients.delete_error'), { id: toastId });
        }
    }, [refetch, t]);

    const handleCreatePatient = async (e) => {
        e.preventDefault();
        if (!newPatient.name || !newPatient.phone) {
            toast.error(t('patients.form.name_placeholder') + ' ' + t('common.and') + ' ' + t('patients.form.phone_label')); // Fallback simplistic validation message
            return;
        }

        setIsSubmitting(true);
        const toastId = toast.loading(t('common.loading'));

        try {
            // Check duplicates
            const res = await searchPatients(newPatient.phone);
            const duplicates = res.data;
            const exactMatch = duplicates.find(p => p.phone === newPatient.phone && p.name === newPatient.name);
            if (exactMatch) {
                toast.error(t('patients.form.duplicate_error'), { id: toastId });
                setIsSubmitting(false);
                return;
            }
            // Logic for phone match warning could be a confirm dialog or toast action, keeping simple for now
        } catch (err) {
            console.error("Error checking duplicates", err);
        }

        try {
            await createPatient({
                name: newPatient.name,
                age: parseInt(newPatient.age) || 0,
                phone: newPatient.phone,
                address: newPatient.address || '',
                medical_history: newPatient.medical_history || '',
                assigned_doctor_id: newPatient.assigned_doctor_id || null,
                notes: ''
            });
            toast.success(t('patients.form.submit_btn'), { id: toastId });
            setIsModalOpen(false);
            setNewPatient({
                name: '',
                age: '',
                phone: '',
                address: '',
                medical_history: '',
                assigned_doctor_id: user?.role === 'doctor' ? user.id : ''
            });
            setSuggestions([]);
            setSearch('');
            refetch(); // Refetch from cache
        } catch (err) {
            console.error(err);
            const msg = err.response?.data?.detail || t('patients.delete_error'); // Reusing generic error
            toast.error(msg, { id: toastId });
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleInputChange = (field, value) => {
        setNewPatient(prev => ({ ...prev, [field]: value }));

        if (['name', 'phone'].includes(field)) {
            if (searchTimeoutState) clearTimeout(searchTimeoutState);

            if (!value || value.length < 2) {
                setSuggestions([]);
                return;
            }

            const timeoutId = setTimeout(async () => {
                try {
                    const res = await searchPatients(value);
                    setSuggestions(res.data);
                } catch (err) {
                    console.error(err);
                }
            }, 300);
            setSearchTimeoutState(timeoutId);
        }
    };

    const handleScanComplete = (data) => {
        setNewPatient(prev => ({
            ...prev,
            name: data.name || prev.name,
            age: data.age || prev.age,
            phone: data.phone || prev.phone,
            address: data.address || prev.address
        }));
        toast.success(t('patients.form.scan_success'));
    };

    const filteredPatients = patients.filter(p =>
        p.name.includes(search) || p.phone.includes(search)
    );

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700 min-h-screen pb-20">
            {/* Header Section */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                <div>
                    <h2 className="text-4xl font-black text-text-primary tracking-tight flex items-center gap-3">
                        <Users className="text-primary" size={40} />
                        {t('patients.title')}
                    </h2>
                    <p className="text-text-secondary mt-2 text-lg font-medium">{t('patients.subtitle')}</p>
                </div>
                <Button
                    size="lg"
                    onClick={() => setIsModalOpen(true)}
                    className="shadow-xl shadow-primary/25"
                >
                    <Plus size={20} className="mr-2" />
                    {t('patients.add_new')}
                </Button>
            </div>

            {/* Stats Bar */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <StatCard
                    label={t('patients.stats_total')}
                    value={stats.total}
                    icon={Users}
                    color="text-blue-600"
                    bg="bg-blue-50 dark:bg-blue-900/20"
                    loading={loading}
                />
                <StatCard
                    label={t('patients.stats_new_month')}
                    value={stats.newThisMonth}
                    icon={UserPlus}
                    color="text-emerald-600"
                    bg="bg-emerald-50 dark:bg-emerald-900/20"
                    loading={loading}
                />
                <StatCard
                    label={t('patients.stats_active')}
                    value={stats.active}
                    icon={Activity}
                    color="text-violet-600"
                    bg="bg-violet-50 dark:bg-violet-900/20"
                    loading={loading}
                />
            </div>

            {/* Search Bar */}
            <div className="sticky top-20 z-30 bg-surface/80 backdrop-blur-xl p-4 rounded-3xl border border-border shadow-lg shadow-slate-200/50 dark:shadow-black/20 transitiion-all">
                <Input
                    placeholder={t('patients.search_placeholder')}
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    icon={Search}
                    className="border-none bg-background focus:ring-0 text-lg py-3"
                    containerClassName="w-full"
                />
            </div>

            {/* Patients Grid Virtualized */}
            <div className="flex-1 min-h-[500px]">
                {loading ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {Array.from({ length: 6 }).map((_, i) => <Skeleton.Card key={i} />)}
                    </div>
                ) : filteredPatients.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pb-20">
                        {filteredPatients.map((patient, index) => {
                            const theme = cardColors[index % cardColors.length];
                            return (
                                <div
                                    key={patient.id}
                                    onClick={() => navigate(`/patients/${patient.id}`)}
                                    className={`group ${theme.bg} rounded-[2rem] p-6 border ${theme.border} shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300 relative overflow-hidden cursor-pointer h-[180px]`}
                                >
                                    {/* Card Background Decoration */}
                                    <div className={`absolute top-0 right-0 w-32 h-32 bg-gradient-to-br ${theme.accent} opacity-10 rounded-bl-[4rem] group-hover:opacity-20 transition-all`} />

                                    <div className="relative z-10 flex flex-col h-full justify-between">
                                        <div className="flex justify-between items-start">
                                            <div className="flex items-center gap-3">
                                                <div className={`w-12 h-12 flex-shrink-0 rounded-2xl bg-gradient-to-br ${theme.accent} flex items-center justify-center text-white text-lg font-black shadow-lg shadow-black/5`}>
                                                    {patient.name.charAt(0)}
                                                </div>
                                                <div className="min-w-0">
                                                    <h3 className={`text-base font-black ${theme.text} group-hover:brightness-110 transition-all truncate`} title={patient.name}>{patient.name}</h3>
                                                    <div className="flex items-center gap-2 text-text-secondary text-xs mt-1">
                                                        <Calendar size={12} />
                                                        <span className="font-bold">{patient.age} سنة</span>
                                                    </div>
                                                </div>
                                            </div>
                                            <button
                                                onClick={(e) => { e.stopPropagation(); handleDeletePatient(patient.id, patient.name); }}
                                                className="p-1.5 text-text-secondary hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-xl transition-all"
                                            >
                                                <Trash2 size={16} />
                                            </button>
                                        </div>

                                        <div className="space-y-1.5">
                                            <div className="flex items-center gap-2 p-2 bg-surface/50 rounded-xl backdrop-blur-sm">
                                                <Phone size={14} className={theme.text} />
                                                <span className="font-bold text-text-primary text-xs" dir="ltr">{patient.phone}</span>
                                            </div>
                                            {patient.address && (
                                                <div className="flex items-center gap-2 p-2 bg-surface/50 rounded-xl backdrop-blur-sm">
                                                    <MapPin size={14} className={theme.text} />
                                                    <span className="font-bold text-text-primary text-[10px] truncate">{patient.address}</span>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                ) : (
                    <EmptyState
                        icon={Users}
                        title={t('patients.empty_state.title')}
                        description={t('patients.empty_state.desc')}
                        action={
                            <Button onClick={() => setIsModalOpen(true)}>
                                <Plus size={18} className="mr-2" /> {t('patients.add_new')}
                            </Button>
                        }
                    />
                )}
            </div>

            {/* Add Patient Modal */}
            <Modal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                title={t('patients.add_new')}
                size="lg"
            >
                <form onSubmit={handleCreatePatient} className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <Input
                            label={t('patients.form.name_label')}
                            placeholder={t('patients.form.name_placeholder')}
                            value={newPatient.name}
                            onChange={(e) => handleInputChange('name', e.target.value)}
                            containerClassName="md:col-span-2"
                        />
                        <Input
                            label={t('patients.form.age_label')}
                            type="number"
                            placeholder="مثال: 25"
                            value={newPatient.age}
                            onChange={(e) => handleInputChange('age', e.target.value)}
                        />
                        <Input
                            label={t('patients.form.phone_label')}
                            type="tel"
                            placeholder="01xxxxxxxxx"
                            value={newPatient.phone}
                            onChange={(e) => handleInputChange('phone', e.target.value)}
                            dir="ltr"
                            className="text-right"
                        />
                        <Input
                            label={t('patients.form.address_label')}
                            placeholder={t('patients.form.address_placeholder')}
                            value={newPatient.address}
                            onChange={(e) => handleInputChange('address', e.target.value)}
                            containerClassName="md:col-span-2"
                        />

                        {/* Doctor Assignment Dropdown */}
                        <div className="md:col-span-2 space-y-1.5">
                            <label className="block text-sm font-bold text-text-secondary">
                                {t('patients.form.doctor_label')}
                            </label>
                            <select
                                value={newPatient.assigned_doctor_id || ''}
                                onChange={(e) => handleInputChange('assigned_doctor_id', e.target.value)}
                                className="w-full rounded-xl border border-border bg-input text-text-primary p-2.5 outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                            >
                                <option value="">{t('patients.form.doctor_select')}</option>
                                {doctors.map(doc => (
                                    <option key={doc.id} value={doc.id}>
                                        د. {doc.username}
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div className="md:col-span-2 space-y-3 pt-2 border-t border-border">
                            <label className="text-sm font-black text-text-secondary flex items-center gap-2">
                                <Activity size={16} />
                                {t('patients.form.medical_history')}
                            </label>
                            <div className="flex flex-wrap gap-2">
                                {['لا يوجد', 'سكري', 'ضغط دم', 'أزمة قلبية', 'حساسية', 'سيولة دم', 'فيروس سي', 'غدة درقية', 'حمل/رضاعة', 'تدخين'].map(condition => (
                                    <button
                                        key={condition}
                                        type="button"
                                        onClick={() => {
                                            let current = newPatient.medical_history ? newPatient.medical_history.split('، ') : [];
                                            current = current.map(c => c.trim()).filter(c => c && c !== 'لا يوجد');

                                            if (condition === 'لا يوجد') {
                                                setNewPatient(prev => ({ ...prev, medical_history: 'لا يوجد' }));
                                                return;
                                            }
                                            if (current.includes(condition)) {
                                                current = current.filter(c => c !== condition);
                                            } else {
                                                current.push(condition);
                                            }
                                            setNewPatient(prev => ({ ...prev, medical_history: current.length ? current.join('، ') : '' }));
                                        }}
                                        className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all border ${(newPatient.medical_history || '').includes(condition)
                                            ? 'bg-rose-500 text-white border-rose-500'
                                            : 'bg-surface text-text-secondary border-border hover:border-rose-300'
                                            }`}
                                    >
                                        {condition}
                                    </button>
                                ))}
                            </div>
                            <Input
                                placeholder={t('patients.form.other_notes')}
                                value={newPatient.medical_history}
                                onChange={(e) => handleInputChange('medical_history', e.target.value)}
                            />
                        </div>

                        {suggestions.length > 0 && (
                            <div className="md:col-span-2 bg-amber-50 dark:bg-amber-900/20 p-4 rounded-2xl border border-amber-200 dark:border-amber-700/50">
                                <h4 className="text-amber-800 dark:text-amber-400 font-bold mb-3 text-sm">
                                    {t('patients.form.duplicate_warning')}
                                </h4>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-32 overflow-y-auto custom-scrollbar">
                                    {suggestions.map(s => (
                                        <div key={s.id} className="flex justify-between text-sm bg-surface p-2 rounded-lg border border-border">
                                            <span className="font-bold text-text-primary">{s.name}</span>
                                            <span className="text-text-secondary" dir="ltr">{s.phone}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>

                    <div className="flex gap-4 pt-4">
                        <Button
                            variant="ghost"
                            type="button"
                            onClick={() => setIsModalOpen(false)}
                            className="flex-1"
                        >
                            {t('patients.form.cancel_btn')}
                        </Button>
                        <Button
                            type="submit"
                            isLoading={isSubmitting}
                            className="flex-[2]"
                        >
                            {t('patients.form.submit_btn')}
                        </Button>
                    </div>
                </form>
            </Modal>

            {isScannerOpen && (
                <PatientScanner
                    onScanComplete={handleScanComplete}
                    onClose={() => setIsScannerOpen(false)}
                />
            )}
        </div>
    );
}

// Memoized StatCard to prevent re-renders
const StatCard = memo(({ label, value, icon: Icon, color, bg, loading }) => (
    <div className="bg-surface p-6 rounded-3xl border border-border shadow-sm flex items-center gap-4">
        {loading ? (
            <Skeleton.Box width="3.5rem" height="3.5rem" rounded="2xl" />
        ) : (
            <div className={`w-14 h-14 rounded-2xl ${bg} ${color} flex items-center justify-center`}>
                <Icon size={28} />
            </div>
        )}
        <div>
            {loading ? (
                <>
                    <Skeleton.Box width="80px" height="12px" className="mb-2" />
                    <Skeleton.Box width="40px" height="24px" />
                </>
            ) : (
                <>
                    <p className="text-text-secondary font-bold text-sm">{label}</p>
                    <p className="text-3xl font-black text-text-primary">{value}</p>
                </>
            )}
        </div>
    </div>
));

StatCard.displayName = 'StatCard';
