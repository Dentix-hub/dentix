import { Edit2, Trash2 } from 'lucide-react';
import { fdiToPalmer } from '@/utils/toothUtils';
import { useTranslation } from 'react-i18next';

const TreatmentHistory = ({
    history,
    onEdit,
    onDelete,
    onAdd
}) => {
    const { t } = useTranslation();

    return (
        <div className="bg-white rounded-2xl border border-slate-100 overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-300">
            <div className="p-4 border-b border-slate-50 flex justify-between items-center bg-slate-50/50">
                <h3 className="font-bold text-slate-700">{t('patientDetails.treatment_history.title')}</h3>
                <button onClick={onAdd} className="text-primary text-sm font-bold hover:underline">{t('patientDetails.treatment_history.add_manual')}</button>
            </div>
            <div className="overflow-x-auto">
                <table className="w-full text-right align-middle">
                    <thead className="bg-slate-50 text-slate-600 text-sm font-bold uppercase tracking-wider">
                        <tr>
                            <th className="p-4 whitespace-nowrap">{t('patientDetails.treatment_history.date')}</th>
                            <th className="p-4 whitespace-nowrap">{t('patientDetails.treatment_history.tooth')}</th>
                            <th className="p-4 whitespace-nowrap min-w-[150px]">{t('patientDetails.treatment_history.diagnosis')}</th>
                            <th className="p-4 whitespace-nowrap min-w-[150px]">{t('patientDetails.treatment_history.treatment')}</th>
                            <th className="p-4 whitespace-nowrap">{t('patientDetails.treatment_history.details')}</th>
                            <th className="p-4 whitespace-nowrap">{t('patientDetails.treatment_history.actions')}</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-50">
                        {history.map(item => (
                            <tr key={item.id} className="hover:bg-slate-50 transition-colors">
                                <td className="p-4 whitespace-nowrap">{new Date(item.date).toLocaleDateString()}</td>
                                <td className="p-4 font-mono text-slate-500 whitespace-nowrap">{fdiToPalmer(item.tooth_number) || '-'}</td>
                                <td className="p-4 font-bold text-slate-700 whitespace-nowrap">{item.diagnosis}</td>
                                <td className="p-4 whitespace-nowrap">{item.procedure}</td>
                                <td className="p-4 text-sm text-slate-700">
                                    {item.canal_count && <div className="font-bold mb-1 text-blue-700">{t('patientDetails.treatment_history.canal_count')} {item.canal_count}</div>}
                                    {(() => {
                                        try {
                                            const canals = JSON.parse(item.canal_lengths);
                                            if (Array.isArray(canals) && canals.length > 0) {
                                                return (
                                                    <div className="flex flex-wrap gap-2 mt-2">
                                                        {canals.map((c, idx) => (
                                                            <div key={idx} className="flex items-center gap-1 bg-blue-50 border border-blue-200 px-2 py-1 rounded-lg">
                                                                <span className="font-bold text-blue-800">{c.name || t('patientDetails.treatment_history.canal_default_name')}:</span>
                                                                <span className="font-mono text-blue-900 font-bold text-base">{c.length}</span>
                                                                <span className="text-xs text-blue-500">{t('patientDetails.treatment_history.canal_unit')}</span>
                                                            </div>
                                                        ))}
                                                    </div>
                                                );
                                            }
                                            return item.canal_lengths ? <div className="font-bold text-slate-800 bg-yellow-50 p-1 rounded border border-yellow-200">{t('patientDetails.treatment_history.lengths')} {item.canal_lengths}</div> : null;
                                        } catch (e) {
                                            return item.canal_lengths ? <div className="font-bold text-slate-800">{t('patientDetails.treatment_history.lengths')} {item.canal_lengths}</div> : null;
                                        }
                                    })()}
                                    {item.sessions && <div className="mt-2 text-slate-600 bg-slate-50 p-1 rounded block" title={item.sessions}><strong>{t('patientDetails.treatment_history.sessions')}</strong> {item.sessions}</div>}
                                    {item.complications && <div className="mt-1 text-red-600 font-bold bg-red-50 p-1 rounded block" title={item.complications}>⚠ {item.complications}</div>}
                                    {item.notes && <div className="mt-1 text-slate-500 italic text-xs" title={item.notes}>{item.notes}</div>}
                                </td>
                                <td className="p-4 flex gap-2 whitespace-nowrap">
                                    <button onClick={() => onEdit(item)} className="p-2 text-slate-400 hover:text-blue-500 hover:bg-blue-50 rounded-lg"><Edit2 size={16} /></button>
                                    <button onClick={() => onDelete(item.id)} className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg"><Trash2 size={16} /></button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            {history.length === 0 && <div className="p-8 text-center text-slate-400">{t('patientDetails.treatment_history.empty')}</div>}
        </div>
    );
};

export default TreatmentHistory;
