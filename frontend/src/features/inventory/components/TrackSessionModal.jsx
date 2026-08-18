import { useState, useEffect } from 'react';
import logger from '@/utils/logger';
import { Play, Square, AlertCircle, Clock } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { openSession, closeSession, getMaterialStock } from '@/api/inventory';
import LoadingSpinner from '@/shared/ui/LoadingSpinner';
import Modal from '@/shared/ui/Modal';
import { useTranslation } from 'react-i18next';

const TrackSessionModal = ({ isOpen, onClose, session, material, stockItem, mode = 'OPEN', onSuccess }) => {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const [selectedStockId, setSelectedStockId] = useState(stockItem?.id || '');
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Fetch batches if we don't have a specific stock item but have material
    const { data: batches = [], isLoading: isLoadingBatches } = useQuery({
        queryKey: ['material-stock', material?.id],
        queryFn: async () => {
            const res = await getMaterialStock(material?.id);
            return Array.isArray(res.data) ? res.data : [];
        },
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
        logger.log("Starting Confirm...", { mode, selectedStockId });
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
                logger.log("Sending Open Payload:", payload);
                await openMutation.mutateAsync(payload);
                alert(t('inventory.track_session.messages.success_open'));
            } else {
                // Close session - no quantity needed, auto-calculates
                await closeMutation.mutateAsync({});
                alert(t('inventory.track_session.messages.success_close'));
            }
        } catch (e) {
            logger.error("Operation Failed:", e);
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
    const dialogTitle = isOpenMode ? t('inventory.track_session.title_open') : t('inventory.track_session.title_close');

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            size="md"
            title={dialogTitle}
            closeLabel={t('common.close', 'Close')}
            closeOnOutside={!isSubmitting}
        >
            <div className="space-y-6">
                <div className={`flex items-start gap-3 rounded-control border border-border p-4 ${isOpenMode ? 'bg-green-500/10' : 'bg-red-500/10'}`}>
                    <div className={`shrink-0 rounded-control p-2 ${isOpenMode ? 'bg-green-500/20 text-green-600' : 'bg-red-500/20 text-red-600'}`}>
                        {isOpenMode ? <Play size={24} aria-hidden="true" /> : <Square size={24} aria-hidden="true" />}
                    </div>
                    <p className="pt-1 text-sm text-text-secondary">
                        {isOpenMode ? t('inventory.track_session.subtitle_open') : t('inventory.track_session.subtitle_close')}
                    </p>
                </div>

                <div className="border-b border-border pb-4 text-sm font-medium">
                    <span className="text-text-secondary">{t('inventory.track_session.material_label')} </span>
                    <span className="me-2 text-lg font-bold text-text-primary">{displayMaterialName}</span>
                </div>

                {isOpenMode ? (
                    <div className="space-y-4">
                        <div className="flex items-start gap-3 rounded-control bg-surface-subtle p-3">
                            <AlertCircle className="mt-0.5 shrink-0 text-primary" size={18} aria-hidden="true" />
                            <p className="text-sm leading-relaxed text-text-secondary">
                                {t('inventory.track_session.info_open')}
                            </p>
                        </div>
                        {!stockItem && (
                            <div>
                                <label htmlFor="track-session-stock-item" className="mb-2 block text-sm font-bold text-text-primary">
                                    {t('inventory.track_session.select_batch_label')}
                                </label>
                                {isLoadingBatches ? <LoadingSpinner size="sm" /> : (
                                    <select
                                        id="track-session-stock-item"
                                        className="w-full rounded-control border border-border bg-surface px-3 py-3 text-text-primary focus-visible:ring-focus"
                                        value={selectedStockId}
                                        onChange={e => setSelectedStockId(e.target.value)}
                                    >
                                        <option value="">{t('inventory.track_session.select_placeholder')}</option>
                                        {batches.map(b => (
                                            <option key={b.id} value={b.id}>
                                                {b.warehouse?.name || 'مخزن'} - Batch: {b.batch?.batch_number} (Exp: {b.batch?.expiry_date}) - Qty: {b.quantity}
                                            </option>
                                        ))}
                                    </select>
                                )}
                                {batches.length === 0 && (
                                    <p className="mt-1 text-sm text-red-500">{t('inventory.track_session.empty_stock')}</p>
                                )}
                            </div>
                        )}
                    </div>
                ) : (
                    <div className="space-y-4">
                        <div className="mb-4 flex items-center gap-2 rounded-control bg-red-50 p-3 text-sm text-text-secondary dark:bg-red-900/10">
                            <Clock size={16} aria-hidden="true" />
                            <span>{t('inventory.track_session.opened_since')} </span>
                            <span className="font-mono font-bold" dir="ltr">
                                {session?.opened_at ? new Date(session.opened_at).toLocaleDateString() + ' ' + new Date(session.opened_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '-'}
                            </span>
                        </div>
                        <div className="flex items-start gap-3 rounded-control bg-amber-50 p-3 dark:bg-amber-900/10">
                            <AlertCircle className="mt-0.5 shrink-0 text-amber-600" size={18} aria-hidden="true" />
                            <p className="text-sm leading-relaxed text-text-secondary">
                                {t('inventory.track_session.info_close_auto', 'عند إنهاء الجلسة، سيتم حساب الاستهلاك تلقائياً بناءً على الأوزان النسبية للإجراءات.')}
                            </p>
                        </div>
                    </div>
                )}

                <div className="flex justify-end gap-3 border-t border-border pt-4">
                    <button
                        type="button"
                        onClick={onClose}
                        disabled={isSubmitting}
                        className="rounded-control px-4 py-2 font-bold text-text-secondary hover:bg-surface-subtle disabled:opacity-50"
                    >
                        {t('inventory.track_session.actions.cancel')}
                    </button>
                    <button
                        type="button"
                        onClick={handleConfirm}
                        disabled={isSubmitting || (isOpenMode && !selectedStockId)}
                        className={`flex items-center gap-2 rounded-control px-6 py-2 font-bold text-white shadow-low transition-transform active:scale-95 disabled:cursor-not-allowed disabled:opacity-60 ${isOpenMode ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'}`}
                    >
                        {isSubmitting && <LoadingSpinner size="sm" color="white" />}
                        {isOpenMode ? t('inventory.track_session.actions.start') : t('inventory.track_session.actions.end')}
                    </button>
                </div>
            </div>
        </Modal>
    );
};

export default TrackSessionModal;
