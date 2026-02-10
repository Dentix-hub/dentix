import { Edit2, FileText, Plus, User as UserIcon, Phone, MapPin } from 'lucide-react';
import { useTranslation } from 'react-i18next';

const PatientInfoCard = ({ patient, onEdit, onPrescription, onNewAppointment }) => {
    const { t } = useTranslation();

    if (!patient) return null;

    return (
        <div className="bg-white dark:bg-slate-800 p-6 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700 flex flex-col md:flex-row justify-between md:items-center gap-4">
            <div>
                <div className="flex items-center gap-3">
                    <h2 className="text-2xl font-bold text-slate-800 dark:text-white">{patient.name}</h2>
                    <PriceListBadge priceListId={patient.default_price_list_id} t={t} />
                </div>
                <div className="flex gap-4 text-slate-500 dark:text-slate-400 text-sm mt-1 items-center">
                    <span className="flex items-center gap-1">
                        <UserIcon size={14} />
                        {patient.age ? t('patientDetails.info_card.age_years', { age: patient.age }) : t('patientDetails.info_card.age_unknown')}
                    </span>
                    <span>•</span>
                    <span dir="ltr" className="flex items-center gap-1">
                        <Phone size={14} />
                        {patient.phone || t('patientDetails.info_card.no_phone')}
                    </span>
                </div>
                {patient.address && (
                    <div className="text-slate-500 dark:text-slate-400 text-sm mt-1 flex items-center gap-1">
                        <MapPin size={14} />
                        {patient.address}
                    </div>
                )}
            </div>
            <div className="flex gap-2">
                <button onClick={onPrescription} className="flex items-center gap-2 px-4 py-2 bg-purple-100 dark:bg-purple-900/30 font-bold rounded-lg text-purple-700 dark:text-purple-300 hover:bg-purple-200 dark:hover:bg-purple-900/50 transition-colors">
                    <FileText size={16} /> {t('patientDetails.info_card.prescription')}
                </button>
                <button onClick={onEdit} className="flex items-center gap-2 px-4 py-2 bg-slate-100 dark:bg-slate-700 font-bold rounded-lg text-slate-600 dark:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors">
                    <Edit2 size={16} /> {t('patientDetails.info_card.edit_data')}
                </button>
                <button onClick={onNewAppointment} className="flex items-center gap-2 px-4 py-2 bg-green-500 font-bold rounded-lg text-white hover:bg-green-600 shadow-lg shadow-green-500/20 transition-colors">
                    <Plus size={16} /> {t('patientDetails.info_card.new_appointment')}
                </button>
            </div>
        </div>
    );
};

import { useState, useEffect } from 'react';

const PriceListBadge = ({ priceListId, t }) => {
    const [name, setName] = useState(null);
    const [isInsurance, setIsInsurance] = useState(false);

    useEffect(() => {
        if (!priceListId) return;
        import('../../api').then(({ getPriceList }) => {
            getPriceList(priceListId).then(res => {
                setName(res.data.name);
                setIsInsurance(res.data.type === 'insurance');
            }).catch(() => setName(t('patientDetails.info_card.not_found')));
        });
    }, [priceListId, t]);

    if (!priceListId) return (
        <span className="bg-slate-100 text-slate-500 px-3 py-1 rounded-full text-xs font-bold border border-slate-200">
            {t('patientDetails.info_card.basic_plan')}
        </span>
    );

    return (
        <span className={`px-3 py-1 rounded-full text-xs font-bold border flex items-center gap-1 ${isInsurance
            ? 'bg-amber-50 text-amber-700 border-amber-200'
            : 'bg-blue-50 text-blue-700 border-blue-200'
            }`}>
            {isInsurance ? '🛡️' : '💰'} {name || 'Loading...'}
        </span>
    );
};

export default PatientInfoCard;