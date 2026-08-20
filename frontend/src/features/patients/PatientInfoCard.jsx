import { useEffect, useMemo, useState } from 'react';
import { Edit2, FileText, Hash, Plus, User as UserIcon, Phone, MapPin } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { getPriceList } from '@/api';

const PriceListBadge = ({ priceListId, t }) => {
    const [name, setName] = useState(null);
    const [isInsurance, setIsInsurance] = useState(false);

    useEffect(() => {
        if (!priceListId) return;
        getPriceList(priceListId)
            .then((res) => {
                setName(res.data.name);
                setIsInsurance(res.data.type === 'insurance');
            })
            .catch(() => setName(t('patientDetails.info_card.not_found')));
    }, [priceListId, t]);

    if (!priceListId) {
        return (
            <span className="inline-flex min-h-7 max-w-full items-center rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-xs font-bold text-slate-500 dark:border-slate-700 dark:bg-slate-800/50">
                {t('patientDetails.info_card.basic_plan')}
            </span>
        );
    }

    return (
        <span className={`inline-flex min-h-7 max-w-full items-center gap-1 rounded-full border px-3 py-1 text-xs font-bold transition-all ${isInsurance
            ? 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-400'
            : 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-900/20 dark:text-blue-400'}`}>
            <span className="min-w-0 truncate">{name || t('common.loading', 'Loading...')}</span>
        </span>
    );
};

function calculateExactAge(dateOfBirth) {
    if (!dateOfBirth) return null;
    const dob = new Date(`${dateOfBirth}T00:00:00`);
    if (Number.isNaN(dob.getTime())) return null;
    const today = new Date();
    let age = today.getFullYear() - dob.getFullYear();
    const hasHadBirthday = today.getMonth() > dob.getMonth()
        || (today.getMonth() === dob.getMonth() && today.getDate() >= dob.getDate());
    if (!hasHadBirthday) age -= 1;
    return Math.max(0, age);
}

const PatientInfoCard = ({ patient, onEdit, onPrescription, onNewAppointment }) => {
    const { t } = useTranslation();
    const computedAge = useMemo(() => {
        if (patient?.date_of_birth && patient?.date_of_birth_precision === 'exact') {
            return calculateExactAge(patient.date_of_birth);
        }
        return patient?.age || null;
    }, [patient?.date_of_birth, patient?.date_of_birth_precision, patient?.age]);

    if (!patient) return null;

    const actionClass = 'inline-flex min-h-11 min-w-0 items-center justify-center gap-2 rounded-xl px-3 py-2.5 text-sm font-bold transition-colors focus:outline-none focus:ring-2 sm:rounded-2xl sm:px-5';

    return (
        <section className="flex min-w-0 flex-col gap-4 rounded-2xl border border-slate-100 bg-white p-3 shadow-sm animate-in fade-in slide-in-from-top-4 duration-500 dark:border-slate-700 dark:bg-slate-800 sm:gap-5 sm:p-5 sm:rounded-3xl lg:flex-row lg:items-center lg:justify-between lg:gap-6 lg:p-6">
            <div className="min-w-0 space-y-2">
                <div className="flex min-w-0 flex-col items-start gap-2 min-[360px]:flex-row min-[360px]:flex-wrap min-[360px]:items-center min-[360px]:gap-3">
                    <h2 className="min-w-0 break-words text-xl font-bold tracking-tight text-slate-800 dark:text-white sm:text-2xl" dir="auto">
                        {patient.name}
                    </h2>
                    <PriceListBadge priceListId={patient.default_price_list_id} t={t} />
                </div>

                <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-2 text-xs font-bold text-slate-500 dark:text-slate-400 sm:gap-x-4 sm:text-sm">
                    <span dir="ltr" className="inline-flex min-h-7 items-center gap-1.5">
                        <Hash size={14} className="shrink-0 text-primary" aria-hidden="true" />
                        <span className="break-all">{patient.file_number || patient.id}</span>
                    </span>
                    <span className="hidden opacity-20 md:block">•</span>
                    <span className="inline-flex min-h-7 items-center gap-1.5">
                        <UserIcon size={14} className="shrink-0 text-primary" aria-hidden="true" />
                        <span>{computedAge !== null ? t('patientDetails.info_card.age_years', { age: computedAge }) : t('patientDetails.info_card.age_unknown')}</span>
                    </span>
                    <span className="hidden opacity-20 md:block">•</span>
                    <span dir="ltr" className="inline-flex min-h-7 max-w-full items-center gap-1.5">
                        <Phone size={14} className="shrink-0 text-primary" aria-hidden="true" />
                        <span className="break-all">{patient.phone || t('patientDetails.info_card.no_phone')}</span>
                    </span>
                    {patient.address && (
                        <>
                            <span className="hidden opacity-20 md:block">•</span>
                            <span className="inline-flex min-w-0 max-w-full items-center gap-1.5" dir="auto">
                                <MapPin size={14} className="shrink-0 text-primary" aria-hidden="true" />
                                <span className="min-w-0 break-words">{patient.address}</span>
                            </span>
                        </>
                    )}
                </div>
            </div>

            <div className="grid w-full min-w-0 grid-cols-1 gap-2 min-[420px]:grid-cols-3 lg:w-auto lg:min-w-fit">
                <button type="button" onClick={onPrescription} className={`${actionClass} border border-teal-100 bg-teal-50 text-teal-700 hover:bg-teal-100 focus:ring-teal-400/40 dark:border-teal-800/50 dark:bg-teal-900/30 dark:text-teal-300 dark:hover:bg-teal-900/50`}>
                    <FileText size={18} className="shrink-0" aria-hidden="true" />
                    <span className="min-w-0 truncate">{t('patientDetails.info_card.prescription')}</span>
                </button>
                <button type="button" onClick={onEdit} className={`${actionClass} border border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100 focus:ring-primary/30 dark:border-slate-600/50 dark:bg-slate-700/50 dark:text-slate-200 dark:hover:bg-slate-700`}>
                    <Edit2 size={18} className="shrink-0" aria-hidden="true" />
                    <span className="min-w-0 truncate">{t('patientDetails.info_card.edit_data')}</span>
                </button>
                <button type="button" onClick={onNewAppointment} className={`${actionClass} bg-primary text-white shadow-medium hover:bg-primary-hover focus:ring-primary/40 focus:ring-offset-2`}>
                    <Plus size={18} className="shrink-0" aria-hidden="true" />
                    <span className="min-w-0 truncate">{t('patientDetails.info_card.new_appointment')}</span>
                </button>
            </div>
        </section>
    );
};

export default PatientInfoCard;
