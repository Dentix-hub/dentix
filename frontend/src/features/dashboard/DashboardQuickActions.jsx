import React from 'react';
import { Plus, Calendar, Wallet, FileText } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

const ActionButton = ({ icon: Icon, label, onClick, colorClass }) => (
    <button
        onClick={onClick}
        className={`flex flex-col items-center justify-center p-6 rounded-3xl transition-all duration-300 hover:scale-[1.02] active:scale-95 border border-slate-100 dark:border-slate-700/50 shadow-sm hover:shadow-md ${colorClass}`}
    >
        <div className="w-14 h-14 rounded-2xl bg-white/20 backdrop-blur-md flex items-center justify-center mb-3 shadow-inner">
            <Icon size={28} className="text-white" />
        </div>
        <span className="font-black text-white tracking-tight">{label}</span>
    </button>
);

const DashboardQuickActions = ({ onAddPatient, onRecordPayment }) => {
    const { t } = useTranslation();
    const navigate = useNavigate();

    const actions = [
        {
            icon: Plus,
            label: t('dashboard.actions.add_patient'),
            onClick: onAddPatient,
            colorClass: 'bg-gradient-to-br from-primary to-primary-700'
        },
        {
            icon: Calendar,
            label: t('dashboard.actions.new_appointment'),
            onClick: () => navigate('/appointments'),
            colorClass: 'bg-gradient-to-br from-teal-500 to-cyan-600'
        },
        {
            icon: Wallet,
            label: t('dashboard.actions.record_payment'),
            onClick: onRecordPayment,
            colorClass: 'bg-gradient-to-br from-emerald-500 to-emerald-700'
        },
        {
            icon: FileText,
            label: t('dashboard.actions.create_rx'),
            onClick: () => navigate('/patients'),
            colorClass: 'bg-gradient-to-br from-amber-500 to-orange-600'
        }
    ];

    return (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {actions.map((action, index) => (
                <ActionButton key={index} {...action} />
            ))}
        </div>
    );
};

export default DashboardQuickActions;
