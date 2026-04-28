import React, { memo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Trash2, Phone, MapPin, Calendar, Users } from 'lucide-react';
import { Button, SkeletonBox, SkeletonCard, EmptyState } from '@/shared/ui';

const PatientCard = memo(function PatientCard({ patient, onDelete, onNavigate, index, t }) {
    return (
        <div
            onClick={() => onNavigate(patient.id)}
            className="relative rounded-xl border border-border bg-surface hover:bg-surface-hover p-5 shadow-sm hover:shadow-md transition-shadow group cursor-pointer"
        >
            <div className="flex items-start gap-4">
                <div className="flex items-center justify-center w-12 h-12 rounded-full bg-primary/10 text-primary font-bold text-lg shrink-0">
                    {patient.name?.charAt(0)?.toUpperCase()}
                </div>

                <div className="flex-1 min-w-0">
                    <h3 className="text-lg font-semibold text-text-primary truncate">
                        {patient.name}
                    </h3>

                    <div className="mt-2 space-y-1 text-sm text-slate-600">
                        {patient.age && (
                            <div className="flex items-center gap-2">
                                <Calendar className="w-4 h-4" />
                                <span>{t('patientDetails.info_card.age_years', { age: patient.age })}</span>
                            </div>
                        )}
                        {patient.phone && (
                            <div className="flex items-center gap-2">
                                <Phone className="w-4 h-4" />
                                <span dir="ltr">{patient.phone}</span>
                            </div>
                        )}
                        {patient.address && (
                            <div className="flex items-center gap-2">
                                <MapPin className="w-4 h-4" />
                                <span className="truncate">{patient.address}</span>
                            </div>
                        )}
                    </div>
                </div>

                <Button
                    variant="ghost"
                    size="sm"
                    className="opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity text-red-500 hover:text-red-700 hover:bg-red-50"
                    onClick={(e) => {
                        e.stopPropagation();
                        onDelete(patient.id, patient.name);
                    }}
                >
                    <Trash2 className="w-4 h-4" />
                </Button>
            </div>
        </div>
    );
});

export default memo(function PatientTable({ patients, isLoading, onDelete }) {
    const navigate = useNavigate();
    const { t } = useTranslation();

    const handleNavigate = useCallback((id) => {
        navigate(`/patients/${id}`);
    }, [navigate]);

    if (isLoading) {
        return (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {Array.from({ length: 6 }).map((_, i) => (
                    <SkeletonCard key={i} />
                ))}
            </div>
        );
    }

    if (!patients || patients.length === 0) {
        return (
            <EmptyState
                icon={Users}
                title={t('patients.empty_state.title')}
                description={t('patients.empty_state.desc')}
            />
        );
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {patients.map((patient, index) => (
                <PatientCard
                    key={patient.id}
                    patient={patient}
                    index={index}
                    onDelete={onDelete}
                    onNavigate={handleNavigate}
                    t={t}
                />
            ))}
        </div>
    );
});

