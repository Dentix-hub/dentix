import { useState, useEffect } from 'react';
import { X, Save, Plus, Scale, Brain } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getProcedureWeights, setProcedureWeight } from '@/api/inventory';
import { useProcedures } from '@/shared/context/ProceduresContext';
import LoadingSpinner from '@/shared/ui/LoadingSpinner';
import { useTranslation } from 'react-i18next';
const SmartLearningModal = ({ isOpen, onClose, material }) => {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const { procedures: allProcedures } = useProcedures();
    const [weights, setWeights] = useState([]);
    const [newProcName, setNewProcName] = useState('');
    const [newProcWeight, setNewProcWeight] = useState(1.0);
    const [isAdding, setIsAdding] = useState(false);
    const [editingId, setEditingId] = useState(null);
    // Fetch existing weights
    const { data: existingWeights, isLoading: isLoadingWeights } = useQuery({
        queryKey: ['procedure-weights', material?.id],
        queryFn: () => getProcedureWeights(material?.id),
        enabled: !!material?.id,
    });
    useEffect(() => {
        if (existingWeights?.data) {
            setWeights(existingWeights.data);
        } else if (existingWeights) {
            setWeights(existingWeights);
        }
    }, [existingWeights]);
    const mutation = useMutation({
        mutationFn: setProcedureWeight,
        onSuccess: () => {
            queryClient.invalidateQueries(['procedure-weights', material?.id]);
            setIsAdding(false);
            setEditingId(null);
            setNewProcName('');
            setNewProcWeight(1.0);
        }
    });
    const handleAdd = async (procName, weight) => {
        await mutation.mutateAsync({
            procedure_name: procName,
            material_id: material.id,
            weight: parseFloat(weight)
        });
    };
    const handleUpdate = async (item, newWeight) => {
        if (!newWeight || isNaN(newWeight)) return;
        await mutation.mutateAsync({
            procedure_name: item.procedure?.name || item.procedure_name, // Backend needs name to find ID
            material_id: material.id,
            weight: parseFloat(newWeight)
        });
    };
    if (!isOpen || !material) return null;
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className="bg-surface w-full max-w-2xl rounded-2xl shadow-2xl border border-border flex flex-col max-h-[90vh]">
                {/* Header */}
                <div className="p-6 border-b border-border flex justify-between items-center bg-primary/5">
                    <div className="flex items-center gap-3">
                        <div className="p-3 bg-primary/10 rounded-xl">
                            <Brain className="text-primary" size={24} />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-text-primary">{t('inventory.smart_learning.title')}</h2>
                            <p className="text-sm text-text-secondary">{t('inventory.smart_learning.subtitle', { name: material.name })}</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-black/5 rounded-full text-text-secondary transition-colors">
                        <X size={24} />
                    </button>
                </div>
                {/* Body */}
                <div className="p-6 overflow-y-auto flex-1 space-y-6">
                    <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-xl text-sm text-blue-800 dark:text-blue-200 flex gap-3 items-start">
                        <Scale size={20} className="mt-0.5 shrink-0" />
                        <div>
                            <p className="font-bold mb-1">{t('inventory.smart_learning.help_title')}</p>
                            <p>{t('inventory.smart_learning.help_desc')}</p>
                            <p className="mt-1 opacity-80">{t('inventory.smart_learning.help_note')}</p>
                        </div>
                    </div>
                    {isLoadingWeights ? <LoadingSpinner /> : (
                        <div className="border border-border rounded-xl overflow-hidden">
                            <table className="w-full text-right">
                                <thead className="bg-background-secondary border-b border-border">
                                    <tr>
                                        <th className="px-4 py-3 text-sm font-bold text-text-secondary">{t('inventory.smart_learning.table.procedure')}</th>
                                        <th className="px-4 py-3 text-sm font-bold text-text-secondary">{t('inventory.smart_learning.table.weight')}</th>
                                        <th className="px-4 py-3 text-sm font-bold text-text-secondary">{t('inventory.smart_learning.table.average')}</th>
                                        <th className="px-4 py-3 text-sm font-bold text-text-secondary">{t('inventory.smart_learning.table.edit')}</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-border bg-surface">
                                    {weights.length === 0 && !isAdding && (
                                        <tr>
                                            <td colSpan="4" className="px-4 py-8 text-center text-text-secondary">
                                                {t('inventory.smart_learning.empty')}
                                            </td>
                                        </tr>
                                    )}
                                    {weights.map((w) => {
                                        const isEditing = editingId === w.id;
                                        return (
                                            <tr key={w.id} className="group hover:bg-surface-hover transition-colors">
                                                <td className="px-4 py-3 font-medium">
                                                    {w.procedure?.name || w.procedure_name || `ID: ${w.procedure_id}`}
                                                </td>
                                                <td className="px-4 py-3">
                                                    {isEditing ? (
                                                        <input
                                                            type="number"
                                                            step="0.01"
                                                            min="0.01"
                                                            className="w-20 p-1 rounded border border-primary outline-none text-center"
                                                            defaultValue={w.weight}
                                                            onKeyDown={(e) => {
                                                                if (e.key === 'Enter') handleUpdate(w, e.currentTarget.value);
                                                            }}
                                                            onBlur={(e) => handleUpdate(w, e.currentTarget.value)}
                                                            autoFocus
                                                        />
                                                    ) : (
                                                        <span className="inline-block px-2 py-1 bg-primary/10 text-primary rounded-lg font-bold">
                                                            {w.weight}x
                                                        </span>
                                                    )}
                                                </td>
                                                <td className="px-4 py-3 font-mono text-sm text-text-secondary dir-ltr">
                                                    {w.current_average_usage > 0 ? `${w.current_average_usage.toFixed(3)} ${material.unit || 'units'}` : '-'}
                                                </td>
                                                <td className="px-4 py-3">
                                                    {isEditing ? (
                                                        <button onClick={() => setEditingId(null)} className="text-xs text-slate-500 hover:text-slate-700">{t('inventory.smart_learning.actions.cancel')}</button>
                                                    ) : (
                                                        <div className="flex gap-2">
                                                            <button
                                                                onClick={() => setEditingId(w.id)}
                                                                className="text-xs text-primary hover:underline"
                                                            >
                                                                {t('inventory.smart_learning.actions.edit')}
                                                            </button>
                                                            <button
                                                                onClick={() => {
                                                                    if (confirm(t('inventory.smart_learning.delete_confirm'))) mutation.mutate({ procedure_name: w.procedure?.name || w.procedure_name, material_id: material.id, weight: 0 }); // 0/Delete logic needed
                                                                    // For now, setting to 0 might be equivalent to delete in backend or we need Delete API
                                                                    // Current backend `setProcedureWeight` updates or creates. 
                                                                    // To delete, we probably need a dedicated delete or handle 0/null.
                                                                    // Assuming update for now.
                                                                }}
                                                                className="text-xs text-red-500 hover:underline"
                                                            >
                                                                {t('inventory.smart_learning.actions.delete')}
                                                            </button>
                                                        </div>
                                                    )}
                                                </td>
                                            </tr>
                                        );
                                    })}
                                    {/* Add Row */}
                                    {isAdding && (
                                        <tr className="bg-primary/5">
                                            <td className="px-4 py-3">
                                                <select
                                                    className="w-full p-2 rounded-lg border border-border bg-surface"
                                                    value={newProcName}
                                                    onChange={e => setNewProcName(e.target.value)}
                                                >
                                                    <option value="">{t('inventory.smart_learning.select_placeholder')}</option>
                                                    {allProcedures
                                                        ?.filter(p => !weights.some(w => w.procedure_id === p.id || w.procedure?.id === p.id))
                                                        .map(p => (
                                                            <option key={p.id} value={p.name}>{p.name}</option>
                                                        ))}
                                                </select>
                                            </td>
                                            <td className="px-4 py-3">
                                                <input
                                                    type="number" step="0.01" min="0.01"
                                                    className="w-20 p-2 rounded-lg border border-border bg-surface text-center"
                                                    value={newProcWeight}
                                                    onChange={e => setNewProcWeight(e.target.value)}
                                                />
                                            </td>
                                            <td className="px-4 py-3 text-center">-</td>
                                            <td className="px-4 py-3">
                                                <button
                                                    onClick={() => handleAdd(newProcName, newProcWeight)} // Renamed handleSave to handleAdd for clarity
                                                    disabled={!newProcName}
                                                    className="p-2 bg-primary text-white rounded-lg hover:bg-primary-600 disabled:opacity-50"
                                                >
                                                    <Save size={16} />
                                                </button>
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    )}
                    {!isAdding && (
                        <button
                            onClick={() => setIsAdding(true)}
                            className="w-full py-3 border-2 border-dashed border-border rounded-xl flex items-center justify-center gap-2 text-text-secondary hover:text-primary hover:border-primary hover:bg-primary/5 transition-all"
                        >
                            <Plus size={20} />
                            <span>{t('inventory.smart_learning.add_button')}</span>
                        </button>
                    )}
                </div>
                {/* Footer */}
                <div className="p-6 border-t border-border bg-surface-secondary/30 flex justify-end">
                    <button
                        onClick={onClose}
                        className="px-6 py-2 bg-white border border-border text-text-primary rounded-lg font-bold hover:bg-gray-50 transition-colors"
                    >
                        {t('inventory.smart_learning.actions.close')}
                    </button>
                </div>
            </div>
        </div>
    );
};
export default SmartLearningModal;
