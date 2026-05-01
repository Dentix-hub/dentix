import React, { useState, useEffect, useMemo } from 'react';
import { Edit2, FileText, Plus, User as UserIcon, Phone, MapPin } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { getPriceList } from '@/api';

const PriceListBadge = ({ priceListId, t }) => {
    const [name, setName] = useState(null);
    const [isInsurance, setIsInsurance] = useState(false);

    useEffect(() => {
        if (!priceListId) return;
        
        getPriceList(priceListId)
            .then(res => {
                setName(res.data.name);
                setIsInsurance(res.data.type === 'insurance');
            })
            .catch(() => setName(t('patientDetails.info_card.not_found')));
    }, [priceListId, t]);

    if (!priceListId) return (
        <span className="bg-slate-100 dark:bg-slate-800/50 text-slate-500 px-3 py-1 rounded-full text-xs font-bold border border-slate-200 dark:border-slate-700">
            {t('patientDetails.info_card.basic_plan')}
        </span>
    );

    return (
        <span className={`px-3 py-1 rounded-full text-xs font-bold border flex items-center gap-1 transition-all ${isInsurance
            ? 'bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-800'
            : 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400 border-blue-200 dark:border-blue-800'
            }`}>
            {isInsurance ? '🛡️' : '💰'} {name || t('common.loading', 'Loading...')}
        </span>
    );
};

const PatientInfoCard = ({ patient, onEdit, onPrescription, onNewAppointment }) => {
    const { t } = useTranslation();

    const computedAge = useMemo(() => {
        if (!patient?.date_of_birth) return patient?.age;
        return Math.floor((new Date() - new Date(patient.date_of_birth)) / 31557600000);
    }, [patient?.date_of_birth, patient?.age]);

    if (!patient) return null;

    return (
        <div className="bg-white dark:bg-slate-800 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-700 flex flex-col lg:flex-row justify-between lg:items-center gap-6 animate-in fade-in slide-in-from-top-4 duration-500">
            <div className="space-y-1">
                <div className="flex items-center gap-3 flex-wrap">
                    <h2 className="text-2xl font-black text-slate-800 dark:text-white tracking-tight">{patient.name}</h2>
                    <PriceListBadge priceListId={patient.default_price_list_id} t={t} />
                </div>
                <div className="flex flex-wrap gap-x-4 gap-y-2 text-slate-500 dark:text-slate-400 text-sm font-bold items-center">
                    <span className="flex items-center gap-1.5">
                        <UserIcon size={14} className="text-primary" />
                        {computedAge ? t('patientDetails.info_card.age_years', { age: computedAge }) : t('patientDetails.info_card.age_unknown')}
                    </span>
                    <span className="opacity-20 hidden md:block">•</span>
                    <span dir="ltr" className="flex items-center gap-1.5">
                        <Phone size={14} className="text-primary" />
                        {patient.phone || t('patientDetails.info_card.no_phone')}
                    </span>
                    {patient.address && (
                        <>
                            <span className="opacity-20 hidden md:block">•</span>
                            <div className="flex items-center gap-1.5">
                                <MapPin size={14} className="text-primary" />
                                {patient.address}
                            </div>
                        </>
                    )}
                </div>
            </div>
            
            <div className="flex flex-wrap gap-3">
                <button 
                    onClick={onPrescription} 
                    className="flex items-center gap-2 px-5 py-2.5 bg-teal-50 dark:bg-teal-900/30 font-black rounded-2xl text-teal-700 dark:text-teal-300 hover:bg-teal-100 dark:hover:bg-teal-900/50 transition-all active:scale-95 border border-teal-100 dark:border-teal-800/50"
                >
                    <FileText size={18} /> {t('patientDetails.info_card.prescription')}
                </button>
                <button 
                    onClick={onEdit} 
                    className="flex items-center gap-2 px-5 py-2.5 bg-slate-50 dark:bg-slate-700/50 font-black rounded-2xl text-slate-600 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 transition-all active:scale-95 border border-slate-200 dark:border-slate-600/50"
                >
                    <Edit2 size={18} /> {t('patientDetails.info_card.edit_data')}
                </button>
                <button 
                    onClick={onNewAppointment} 
                    className="flex items-center gap-2 px-6 py-2.5 bg-primary font-black rounded-2xl text-white hover:bg-primary-hover shadow-lg shadow-primary/20 transition-all active:scale-95"
                >
                    <Plus size={18} /> {t('patientDetails.info_card.new_appointment')}
                </button>
            </div>
        </div>
    );
};

export default PatientInfoCard;
