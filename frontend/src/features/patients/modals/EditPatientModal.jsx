import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { getUsers } from '@/api';
import PriceListSelector from '@/shared/ui/PriceListSelector';

export default function EditPatientModal({ isOpen, onClose, onSave, initialData }) {
    const { t } = useTranslation();
    const [formData, setFormData] = useState({});
    const [doctors, setDoctors] = useState([]);

    useEffect(() => {
        if (isOpen && initialData) {
            setFormData({
                name: initialData.name,
                age: initialData.age,
                phone: initialData.phone,
                address: initialData.address,
                default_price_list_id: initialData.default_price_list_id,
                assigned_doctor_id: initialData.assigned_doctor_id
            });
        }
    }, [isOpen, initialData]);

    // Fetch doctors for the edit modal
    useEffect(() => {
        if (isOpen) {
            getUsers({ role: 'doctor' })
                .then(res => setDoctors(res.data))
                .catch(err => console.error("Failed to fetch doctors", err));
        }
    }, [isOpen]);

    const handleSubmit = (e) => {
        e.preventDefault();
        onSave(formData);
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
            <div className="bg-white w-full max-w-lg rounded-2xl p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
                <h3 className="text-xl font-bold mb-4">{t('patient_details.edit_modal.title')}</h3>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <input
                        value={formData.name || ''}
                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                        className="w-full p-3 bg-slate-50 rounded-xl outline-none border focus:border-primary"
                        placeholder={t('patients.form.name_label')}
                    />
                    <div className="grid grid-cols-2 gap-4">
                        <input
                            value={formData.age || ''}
                            onChange={(e) => setFormData({ ...formData, age: e.target.value })}
                            className="w-full p-3 bg-slate-50 rounded-xl outline-none border focus:border-primary"
                            placeholder={t('patients.form.age_label')}
                        />
                        <input
                            value={formData.phone || ''}
                            onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                            className="w-full p-3 bg-slate-50 rounded-xl outline-none border focus:border-primary"
                            placeholder={t('patients.form.phone_label')}
                        />
                    </div>
                    <input
                        value={formData.address || ''}
                        onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                        className="w-full p-3 bg-slate-50 rounded-xl outline-none border focus:border-primary"
                        placeholder={t('patients.form.address_label')}
                    />

                    {/* Price List Selector */}
                    <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                        <label className="block text-sm font-bold text-slate-700 mb-2">{t('patient_details.edit_modal.price_list_label')}</label>
                        <PriceListSelector
                            value={formData.default_price_list_id ?? ''}
                            onChange={(val) => setFormData(prev => ({ ...prev, default_price_list_id: val }))}
                        />
                        <p className="text-xs text-slate-400 mt-1">{t('patient_details.edit_modal.price_list_hint')}</p>
                    </div>

                    {/* Doctor Assignment */}
                    <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                        <label className="block text-sm font-bold text-slate-700 mb-2">{t('patient_details.edit_modal.doctor_label')}</label>
                        <select
                            value={formData.assigned_doctor_id || ''}
                            onChange={(e) => setFormData({ ...formData, assigned_doctor_id: e.target.value })}
                            className="w-full p-3 bg-white rounded-xl outline-none border border-gray-200 focus:border-blue-500"
                        >
                            <option value="">{t('patient_details.edit_modal.doctor_select')}</option>
                            {doctors.map(doc => (
                                <option key={doc.id} value={doc.id}>
                                    د. {doc.username}
                                </option>
                            ))}
                        </select>
                        <p className="text-xs text-slate-400 mt-1">{t('patient_details.edit_modal.doctor_hint')}</p>
                    </div>

                    <div className="flex justify-end gap-3">
                        <button type="button" onClick={onClose} className="px-4 py-2 hover:bg-slate-100 rounded-lg">{t('common.cancel')}</button>
                        <button type="submit" className="px-6 py-2 bg-primary text-white rounded-lg">{t('common.save')}</button>
                    </div>
                </form>
            </div>
        </div>
    );
}
