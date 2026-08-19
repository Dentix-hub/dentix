import { memo } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Archive, CalendarPlus, ExternalLink, Phone, RefreshCw, SearchX, UserRound, Users, MessageCircle } from 'lucide-react';
import { Button, SkeletonBox } from '@/shared/ui';
import { useAuth } from '@/auth/useAuth';

function whatsappHref(phone) {
    if (!phone) return null;
    const digits = String(phone).replace(/\D/g, '');
    if (!digits) return null;
    const international = digits.startsWith('00')
        ? digits.slice(2)
        : digits.startsWith('0')
            ? `20${digits.slice(1)}`
            : digits;
    return `https://wa.me/${international}`;
}

function PatientIdentity({ patient }) {
    return (
        <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-sm font-extrabold text-primary">
                {patient.name?.trim()?.charAt(0)?.toUpperCase() || '?'}
            </div>
            <div className="min-w-0 flex-1">
                <Link
                    to={`/patients/${patient.id}`}
                    className="block break-words font-bold leading-snug text-text-primary hover:text-primary focus:outline-none focus:underline md:truncate"
                    dir="auto"
                >
                    {patient.name}
                </Link>
                <span className="text-xs text-text-muted" dir="ltr">#{patient.file_number || patient.id}</span>
            </div>
        </div>
    );
}

function RowActions({ patient, canArchive, onArchive, align = 'end' }) {
    const { t } = useTranslation();
    const waHref = whatsappHref(patient.phone);
    return (
        <div className={`flex flex-wrap items-center gap-1 ${align === 'start' ? 'justify-start' : 'justify-end'}`}>
            {patient.phone && (
                <a href={`tel:${patient.phone}`} className="flex h-9 w-9 items-center justify-center rounded-lg text-text-muted hover:bg-surface-hover hover:text-primary focus:outline-none focus:ring-2 focus:ring-primary/30" aria-label={t('patients.call_patient')}>
                    <Phone className="h-4 w-4" />
                </a>
            )}
            {waHref && (
                <a href={waHref} target="_blank" rel="noreferrer" className="flex h-9 w-9 items-center justify-center rounded-lg text-text-muted hover:bg-surface-hover hover:text-primary focus:outline-none focus:ring-2 focus:ring-primary/30" aria-label={t('patients.whatsapp_patient')}>
                    <MessageCircle className="h-4 w-4" />
                </a>
            )}
            <Link to={`/appointments?patient_id=${patient.id}`} className="flex h-9 w-9 items-center justify-center rounded-lg text-text-muted hover:bg-surface-hover hover:text-primary focus:outline-none focus:ring-2 focus:ring-primary/30" aria-label={t('patients.new_appointment')}>
                <CalendarPlus className="h-4 w-4" />
            </Link>
            <Link to={`/patients/${patient.id}`} className="flex h-9 w-9 items-center justify-center rounded-lg text-text-muted hover:bg-surface-hover hover:text-primary focus:outline-none focus:ring-2 focus:ring-primary/30" aria-label={t('patients.open_patient')}>
                <ExternalLink className="h-4 w-4" />
            </Link>
            {canArchive && (
                <button type="button" onClick={() => onArchive(patient.id, patient.name)} className="flex h-9 w-9 items-center justify-center rounded-lg text-text-muted hover:bg-amber-50 hover:text-amber-700 focus:outline-none focus:ring-2 focus:ring-amber-400/40 dark:hover:bg-amber-950/30" aria-label={t('patients.archive_patient')}>
                    <Archive className="h-4 w-4" />
                </button>
            )}
        </div>
    );
}

function LoadingRows() {
    return (
        <div className="space-y-2 p-4">
            {Array.from({ length: 7 }).map((_, index) => (
                <SkeletonBox key={index} height="4rem" className="rounded-xl" />
            ))}
        </div>
    );
}

export default memo(function PatientTable({ patients, isLoading, isError, searchQuery, onRetry, onArchive, onAdd, hasNextPage, isFetchingNextPage, onLoadMore }) {
    const { t } = useTranslation();
    const { user } = useAuth();
    const canArchive = ['admin', 'super_admin'].includes(user?.role);

    if (isLoading) return <LoadingRows />;

    if (isError) {
        return (
            <div className="flex min-h-64 flex-col items-center justify-center gap-3 p-8 text-center">
                <RefreshCw className="h-8 w-8 text-red-500" />
                <h3 className="font-bold text-text-primary">{t('patients.load_error')}</h3>
                <p className="max-w-md text-sm text-text-muted">{t('patients.load_error_hint')}</p>
                <Button variant="secondary" onClick={onRetry}>{t('common.retry')}</Button>
            </div>
        );
    }

    if (!patients?.length) {
        const searching = Boolean(searchQuery);
        return (
            <div className="flex min-h-72 flex-col items-center justify-center gap-3 p-8 text-center">
                <div className="rounded-2xl bg-primary/10 p-4 text-primary">
                    {searching ? <SearchX className="h-8 w-8" /> : <Users className="h-8 w-8" />}
                </div>
                <h3 className="text-lg font-bold text-text-primary">
                    {searching ? t('patients.no_search_results') : t('patients.empty_state.title')}
                </h3>
                <p className="max-w-lg text-sm text-text-muted">
                    {searching ? t('patients.no_search_results_hint') : t('patients.empty_state.desc')}
                </p>
                <Button onClick={onAdd}>{t('patients.add_new')}</Button>
            </div>
        );
    }

    return (
        <>
            <div className="hidden overflow-x-auto md:block">
                <table className="w-full border-collapse text-start">
                    <thead className="bg-surface-hover/60 text-xs uppercase tracking-wide text-text-muted">
                        <tr>
                            <th scope="col" className="px-5 py-3 text-start">{t('patients.patient')}</th>
                            <th scope="col" className="px-5 py-3 text-start">{t('patients.file_number')}</th>
                            <th scope="col" className="px-5 py-3 text-start">{t('patients.form.age_label')}</th>
                            <th scope="col" className="px-5 py-3 text-start">{t('patients.form.phone_label')}</th>
                            <th scope="col" className="px-5 py-3 text-start">{t('patients.assigned_doctor')}</th>
                            <th scope="col" className="px-5 py-3 text-end">{t('common.actions')}</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                        {patients.map((patient) => (
                            <tr key={patient.id} className="transition-colors hover:bg-surface-hover/40">
                                <td className="px-5 py-3"><PatientIdentity patient={patient} /></td>
                                <td className="px-5 py-3 text-sm font-semibold text-text-secondary"><span dir="ltr">#{patient.file_number || patient.id}</span></td>
                                <td className="px-5 py-3 text-sm text-text-secondary">{patient.age ? t('patientDetails.info_card.age_years', { age: patient.age }) : '—'}</td>
                                <td className="px-5 py-3 text-sm text-text-secondary"><span dir="ltr">{patient.phone || '—'}</span></td>
                                <td className="px-5 py-3 text-sm text-text-secondary">{patient.assigned_doctor_name || '—'}</td>
                                <td className="px-5 py-3"><RowActions patient={patient} canArchive={canArchive} onArchive={onArchive} /></td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            <div className="divide-y divide-border md:hidden">
                {patients.map((patient) => (
                    <article key={patient.id} className="p-4">
                        <PatientIdentity patient={patient} />
                        <div className="mt-3 ms-[3.25rem] flex flex-wrap gap-x-4 gap-y-1 text-xs text-text-muted">
                            {patient.age ? <span>{t('patientDetails.info_card.age_years', { age: patient.age })}</span> : null}
                            {patient.phone ? <span dir="ltr">{patient.phone}</span> : null}
                            {patient.assigned_doctor_name ? <span className="inline-flex items-center gap-1"><UserRound className="h-3 w-3" />{patient.assigned_doctor_name}</span> : null}
                        </div>
                        <div className="mt-2 ms-[3.25rem] border-t border-border/60 pt-2">
                            <RowActions patient={patient} canArchive={canArchive} onArchive={onArchive} align="start" />
                        </div>
                    </article>
                ))}
            </div>

            {hasNextPage && (
                <div className="border-t border-border p-4 text-center">
                    <Button variant="secondary" onClick={onLoadMore} isLoading={isFetchingNextPage}>
                        {t('patients.load_more')}
                    </Button>
                </div>
            )}
        </>
    );
});
