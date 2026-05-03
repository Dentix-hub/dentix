import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Save, Plus, Trash2, Printer } from 'lucide-react';
import { getSavedMedications, saveMedication, deleteSavedMedication, updateTenantSettings, getTenantSettings } from '@/api';
export default function RxSettings({ setMessage }) {
    const { t } = useTranslation();
    const [headerInfo, setHeaderInfo] = useState({
        doctor_name: '',
        doctor_title: '',
        clinic_address: '',
        clinic_phone: ''
    });
    const [medications, setMedications] = useState([]);
    const [newMed, setNewMed] = useState({ name: '', default_dose: '', notes: '' });
    const [loading, setLoading] = useState(false);
    useEffect(() => {
        loadData();
    }, []);
    const loadData = async () => {
        try {
            const [settingsRes, medsRes] = await Promise.all([
                getTenantSettings(),
                getSavedMedications()
            ]);
            // Populate header info if exists
            setHeaderInfo({
                doctor_name: settingsRes.data.doctor_name || '',
                doctor_title: settingsRes.data.doctor_title || '',
                clinic_address: settingsRes.data.clinic_address || '',
                clinic_phone: settingsRes.data.clinic_phone || ''
            });
            setMedications(medsRes.data);
        } catch (err) {
            console.error(err);
        }
    };
    const handleSaveHeader = async () => {
        setLoading(true);
        try {
            await updateTenantSettings(headerInfo);
            setMessage({ type: 'success', text: 'تم حفظ إعدادات الروشتة' });
        } catch (err) {
            setMessage({ type: 'error', text: 'فشل الحفظ' });
        } finally {
            setLoading(false);
        }
    };
    const handleAddMedication = async (e) => {
        e.preventDefault();
        if (!newMed.name) return;
        try {
            const res = await saveMedication(newMed);
            setMedications([...medications, res.data]);
            setNewMed({ name: '', default_dose: '', notes: '' });
            setMessage({ type: 'success', text: 'تم إضافة الدواء' });
        } catch (err) {
            setMessage({ type: 'error', text: err.response?.data?.detail || 'فشل الإضافة' });
        }
    };
    const handleDeleteMed = async (id) => {
        if (!window.confirm('هل أنت متأكد من الحذف؟')) return;
        try {
            await deleteSavedMedication(id);
            setMedications(medications.filter(m => m.id !== id));
            setMessage({ type: 'success', text: 'تم الحذف' });
        } catch (err) {
            setMessage({ type: 'error', text: 'فشل الحذف' });
        }
    };
    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Header Settings Section */}
            <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-white/5 p-6 shadow-sm">
                <div className="flex items-center gap-3 mb-6">
                    <div className="w-10 h-10 rounded-xl bg-indigo-100 dark:bg-indigo-500/10 flex items-center justify-center text-indigo-600">
                        <Printer size={20} />
                    </div>
                    <div>
                        <h3 className="text-lg font-bold text-slate-800 dark:text-white">{t('rx_settings.title')}</h3>
                        <p className="text-sm text-slate-500">{t('rx_settings.subtitle')}</p>
                    </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">{t('rx_settings.doctor_name')}</label>
                        <input
                            type="text"
                            value={headerInfo.doctor_name}
                            onChange={(e) => setHeaderInfo({ ...headerInfo, doctor_name: e.target.value })}
                            placeholder={t('rx_settings.doctor_name')}
                            className="w-full p-3 bg-slate-50 dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 outline-none focus:border-indigo-500 transition-colors"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">{t('rx_settings.doctor_title')}</label>
                        <input
                            type="text"
                            value={headerInfo.doctor_title}
                            onChange={(e) => setHeaderInfo({ ...headerInfo, doctor_title: e.target.value })}
                            placeholder={t('rx_settings.doctor_title')}
                            className="w-full p-3 bg-slate-50 dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 outline-none focus:border-indigo-500 transition-colors"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">{t('rx_settings.address')}</label>
                        <input
                            type="text"
                            value={headerInfo.clinic_address}
                            onChange={(e) => setHeaderInfo({ ...headerInfo, clinic_address: e.target.value })}
                            placeholder={t('rx_settings.address')}
                            className="w-full p-3 bg-slate-50 dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 outline-none focus:border-indigo-500 transition-colors"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">{t('rx_settings.phone')}</label>
                        <input
                            type="text"
                            dir="ltr"
                            value={headerInfo.clinic_phone}
                            onChange={(e) => setHeaderInfo({ ...headerInfo, clinic_phone: e.target.value })}
                            placeholder="010xxxxxxx"
                            className="w-full p-3 bg-slate-50 dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 outline-none focus:border-indigo-500 transition-colors text-right"
                        />
                    </div>
                </div>
                <div className="mt-6 flex justify-end">
                    <button
                        onClick={handleSaveHeader}
                        disabled={loading}
                        className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2 rounded-xl font-bold flex items-center gap-2 transition-all shadow-lg shadow-indigo-500/20"
                    >
                        <Save size={18} />
                        {t('rx_settings.save')}
                    </button>
                </div>
            </div>
            {/* Saved Medications Section */}
            <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-white/5 p-6 shadow-sm">
                <div className="flex items-center gap-3 mb-6">
                    <div className="w-10 h-10 rounded-xl bg-emerald-100 dark:bg-emerald-500/10 flex items-center justify-center text-emerald-600">
                        <Plus size={20} />
                    </div>
                    <div>
                        <h3 className="text-lg font-bold text-slate-800 dark:text-white">{t('rx_settings.saved_meds')}</h3>
                        <p className="text-sm text-slate-500">{t('rx_settings.saved_meds_subtitle')}</p>
                    </div>
                </div>
                {/* Add Form */}
                <form onSubmit={handleAddMedication} className="bg-slate-50 dark:bg-slate-900/50 p-4 rounded-xl mb-6 grid grid-cols-1 md:grid-cols-4 gap-4 items-end border border-slate-200 dark:border-slate-700">
                    <div className="md:col-span-1">
                        <label className="block text-xs font-bold text-slate-500 mb-1">{t('rx_settings.med_name')}</label>
                        <input
                            type="text"
                            required
                            dir="ltr"
                            value={newMed.name}
                            onChange={(e) => setNewMed({ ...newMed, name: e.target.value })}
                            className="w-full p-2 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-600 outline-none focus:border-emerald-500 text-left"
                            placeholder={t('rx_settings.plac_name')}
                        />
                    </div>
                    <div className="md:col-span-1">
                        <label className="block text-xs font-bold text-slate-500 mb-1">{t('rx_settings.dose')}</label>
                        <input
                            type="text"
                            value={newMed.default_dose}
                            onChange={(e) => setNewMed({ ...newMed, default_dose: e.target.value })}
                            className="w-full p-2 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-600 outline-none focus:border-emerald-500"
                            placeholder={t('rx_settings.plac_dose')}
                        />
                    </div>
                    <div className="md:col-span-1">
                        <label className="block text-xs font-bold text-slate-500 mb-1">{t('rx_settings.notes')}</label>
                        <input
                            type="text"
                            value={newMed.notes}
                            onChange={(e) => setNewMed({ ...newMed, notes: e.target.value })}
                            className="w-full p-2 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-600 outline-none focus:border-emerald-500"
                            placeholder={t('rx_settings.plac_notes')}
                        />
                    </div>
                    <button
                        type="submit"
                        className="bg-emerald-500 hover:bg-emerald-600 text-white p-2 rounded-lg font-bold flex items-center justify-center gap-2 transition-colors h-[42px]"
                    >
                        <Plus size={18} />
                        {t('rx_settings.add_btn')}
                    </button>
                </form>
                {/* List */}
                <div className="overflow-x-auto">
                    <table className="w-full text-right">
                        <thead>
                            <tr className="border-b border-slate-100 dark:border-slate-700 text-slate-500 text-sm">
                                <th className="pb-3 pr-2 text-left">{t('rx_settings.table.name')}</th>
                                <th className="pb-3 px-2">{t('rx_settings.table.dose')}</th>
                                <th className="pb-3 px-2">{t('rx_settings.table.notes')}</th>
                                <th className="pb-3 pl-2 w-20"></th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                            {medications.length === 0 ? (
                                <tr>
                                    <td colSpan="4" className="py-8 text-center text-slate-400">{t('rx_settings.table.empty')}</td>
                                </tr>
                            ) : (
                                medications.map(med => (
                                    <tr key={med.id} className="group hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">
                                        <td className="py-3 pr-2 font-bold text-slate-800 dark:text-slate-200 text-left" dir="ltr">{med.name}</td>
                                        <td className="py-3 px-2 text-slate-600 dark:text-slate-400">{med.default_dose}</td>
                                        <td className="py-3 px-2 text-slate-500 text-sm">{med.notes}</td>
                                        <td className="py-3 pl-2 text-left">
                                            <button
                                                onClick={() => handleDeleteMed(med.id)}
                                                className="text-red-400 hover:text-red-500 p-1 rounded-lg hover:bg-red-50 dark:hover:bg-red-500/10 transition-colors opacity-0 group-hover:opacity-100"
                                            >
                                                <Trash2 size={16} />
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}

