import { useState, useEffect } from 'react';
import { X, Play, Square, AlertCircle, Clock } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { openSession, closeSession, getMaterialStock } from '@/api/inventory';
import LoadingSpinner from '@/shared/ui/LoadingSpinner';
import { useTranslation } from 'react-i18next';
const TrackSessionModal = ({ isOpen, onClose, session, material, stockItem, mode = 'OPEN', onSuccess }) => {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const [selectedStockId, setSelectedStockId] = useState(stockItem?.id || '');
    const [isSubmitting, setIsSubmitting] = useState(false);
    // Fetch batches if we don't have a specific stock item but have material
    const { data: batches, isLoading: isLoadingBatches } = useQuery({
        queryKey: ['material-stock', material?.id],
        queryFn: () => getMaterialStock(material?.id),
        enabled: isOpen && mode === 'OPEN' && !stockItem && !!material?.id,
    });
    useEffect(() => {
        if (stockItem) setSelectedStockId(stockItem.id);
    }, [stockItem]);
    const openMutation = useMutation({
        mutationFn: openSession,
        onSuccess: () => {
            queryClient.invalidateQueries(['active-sessions']);
            if (onSuccess) onSuccess();
            onClose();
        }
    });
    const closeMutation = useMutation({
        mutationFn: (data) => closeSession(session.id, data),
        onSuccess: () => {
            queryClient.invalidateQueries(['active-sessions']);
            queryClient.invalidateQueries(['procedure-weights']);
            if (onSuccess) onSuccess();
            onClose();
        }
    });
    const handleConfirm = async () => {
        setIsSubmitting(true);
        console.log("Starting Confirm...", { mode, selectedStockId });
        try {
            if (mode === 'OPEN') {
                if (!selectedStockId) {
                    alert(t('inventory.track_session.messages.select_error'));
                    return;
                }
                const payload = {
                    stock_item_id: parseInt(selectedStockId),
                    status: 'ACTIVE'
                };
                console.log("Sending Open Payload:", payload);
                await openMutation.mutateAsync(payload);
                alert(t('inventory.track_session.messages.success_open'));
            } else {
                // Close session - no quantity needed, auto-calculates
                await closeMutation.mutateAsync({});
                alert(t('inventory.track_session.messages.success_close'));
            }
        } catch (e) {
            console.error("Operation Failed:", e);
            const res = e.response?.data;
            const msg = res?.error?.message || res?.detail || e.message;
            alert(t('inventory.track_session.messages.error_prefix') + msg);
        } finally {
            setIsSubmitting(false);
        }
    };
    if (!isOpen) return null;
    const isOpenMode = mode === 'OPEN';
    const displayMaterialName = material?.name || material?.material_name || stockItem?.name || stockItem?.material_name || session?.stock_item?.batch?.material?.name || session?.stock_item?.material?.name;
    const unit = material?.unit || session?.stock_item?.batch?.material?.base_unit || session?.stock_item?.material?.base_unit || 'Units';
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className="bg-surface w-full max-w-md rounded-2xl shadow-xl border border-border overflow-hidden">
                <div className={`p-6 border-b border-border flex justify-between items-center ${isOpenMode ? 'bg-green-500/10' : 'bg-red-500/10'}`}>
                    <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg ${isOpenMode ? 'bg-green-500/20 text-green-600' : 'bg-red-500/20 text-red-600'}`}>
                            {isOpenMode ? <Play size={24} /> : <Square size={24} />}
                        </div>
                        <div>
                            <h3 className="text-lg font-bold">{isOpenMode ? t('inventory.track_session.title_open') : t('inventory.track_session.title_close')}</h3>
                            <p className="text-sm opacity-70">
                                {isOpenMode ? t('inventory.track_session.subtitle_open') : t('inventory.track_session.subtitle_close')}
                            </p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-1 hover:bg-black/5 rounded-full"><X size={20} /></button>
                </div>
                <div className="p-6 space-y-6">
                    <div className="text-sm font-medium border-b border-border pb-4">
                        <span className="text-text-secondary">{t('inventory.track_session.material_label')} </span>
                        <span className="font-bold text-lg text-text-primary mr-2">{displayMaterialName}</span>
                    </div>
                    {isOpenMode ? (
                        <div className="space-y-4">
                            <div className="flex items-start gap-3 p-3 bg-background-secondary rounded-lg">
                                <AlertCircle className="text-primary shrink-0 mt-0.5" size={18} />
                                <p className="text-sm text-text-secondary leading-relaxed">
                                    {t('inventory.track_session.info_open')}
                                </p>
                            </div>
                            {!stockItem && (
                                <div>
                                    <label className="block text-sm font-bold mb-2">{t('inventory.track_session.select_batch_label')}</label>
                                    {isLoadingBatches ? <LoadingSpinner size="sm" /> : (
                                        <select
                                            className="w-full p-3 rounded-lg border border-border bg-background"
                                            value={selectedStockId}
                                            onChange={e => setSelectedStockId(e.target.value)}
                                        >
                                            <option value="">{t('inventory.track_session.select_placeholder')}</option>
                                            {batches?.data?.map(b => (
                                                <option key={b.id} value={b.id}>
                                                    {b.warehouse?.name || 'مخزن'} - Batch: {b.batch?.batch_number} (Exp: {b.batch?.expiry_date}) - Qty: {b.quantity}
                                                </option>
                                            ))}
                                        </select>
                                    )}
                                    {batches?.data?.length === 0 && (
                                        <p className="text-red-500 text-sm mt-1">{t('inventory.track_session.empty_stock')}</p>
                                    )}
                                </div>
                            )}
                        </div>
                    ) : (
                        <div className="space-y-4">
                            <div className="flex items-center gap-2 text-sm text-text-secondary mb-4 p-3 bg-red-50 rounded-lg dark:bg-red-900/10">
                                <Clock size={16} />
                                <span>{t('inventory.track_session.opened_since')} </span>
                                <span className="font-mono dir-ltr font-bold">
                                    {session?.opened_at ? new Date(session.opened_at).toLocaleDateString() + ' ' + new Date(session.opened_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '-'}
                                </span>
                            </div>
                            <div className="flex items-start gap-3 p-3 bg-amber-50 rounded-lg dark:bg-amber-900/10">
                                <AlertCircle className="text-amber-600 shrink-0 mt-0.5" size={18} />
                                <p className="text-sm text-text-secondary leading-relaxed">
                                    {t('inventory.track_session.info_close_auto', 'عند إنهاء الجلسة، سيتم حساب الاستهلاك تلقائياً بناءً على الأوزان النسبية للإجراءات.')}
                                </p>
                            </div>
                        </div>
                    )}
                </div>
                <div className="p-4 border-t border-border bg-surface-secondary/30 flex justify-end gap-3">
                    <button onClick={onClose} className="px-4 py-2 rounded-lg font-bold hover:bg-black/5">{t('inventory.track_session.actions.cancel')}</button>
                    <button
                        onClick={handleConfirm}
                        disabled={isSubmitting || (isOpenMode && !selectedStockId)}
                        className={`px-6 py-2 rounded-lg font-bold text-white shadow-lg transition-transform active:scale-95 flex items-center gap-2 ${isOpenMode ? 'bg-green-600 hover:bg-green-700 disabled:bg-green-400' : 'bg-red-600 hover:bg-red-700 disabled:bg-red-400'}`}
                    >
                        {isSubmitting && <LoadingSpinner size="sm" color="white" />}
                        {isOpenMode ? t('inventory.track_session.actions.start') : t('inventory.track_session.actions.end')}
                    </button>
                </div>
            </div>
        </div>
    );
};
export default TrackSessionModal;

