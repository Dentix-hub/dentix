import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Button, Modal } from '@/shared/ui';
import { getMaterials } from '@/api/inventory';
import { getCareSessionMaterialSuggestions, getCareSessionMaterialCost, recordCareSessionMaterials } from '@/api/patients';

const payload = (response) => response?.data?.data ?? response?.data ?? response;

export default function CareSessionMaterialsModal({ patientId, sessionId, workItemId, onClose, t }) {
    const queryClient = useQueryClient();
    const [materialId, setMaterialId] = useState('');
    const [quantity, setQuantity] = useState('1');
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');
    const materials = useQuery({ queryKey: ['inventory-materials'], queryFn: async () => payload(await getMaterials()) });
    const suggestions = useQuery({
        queryKey: ['care-material-suggestions', patientId, workItemId],
        queryFn: async () => payload(await getCareSessionMaterialSuggestions(patientId, workItemId)),
    });
    const usages = useQuery({
        queryKey: ['care-material-usages', patientId, workItemId],
        queryFn: async () => payload(await getCareSessionMaterialCost(patientId, workItemId)),
    });
    const available = Array.isArray(materials.data) ? materials.data : [];
    const recorded = usages.data?.sessions?.find((visit) => visit.care_session_id === sessionId)?.usages || [];
    const recommended = suggestions.data?.suggestions || [];
    const loadError = materials.isError || suggestions.isError || usages.isError;

    const save = async (event) => {
        event.preventDefault();
        if (!materialId || !Number.isFinite(Number(quantity)) || Number(quantity) <= 0) return;
        setSaving(true);
        setError('');
        try {
            await recordCareSessionMaterials(patientId, sessionId, {
                work_item_id: workItemId,
                items: [{ material_id: Number(materialId), quantity: Number(quantity) }],
            });
            await queryClient.invalidateQueries({ queryKey: ['care-material-usages', patientId, workItemId] });
            for (const key of ['inventory-stock', 'stock-summary', 'material-stock', 'warehouse-stock', 'stock-check', 'care-material-suggestions']) {
                queryClient.invalidateQueries({ queryKey: [key] });
            }
            setMaterialId('');
            setQuantity('1');
        } catch (err) {
            const detail = err?.response?.data?.detail;
            setError(detail?.message || (typeof detail === 'string' ? detail : t('care_session.material_error', 'Unable to record materials. Check stock and opened packages.')));
        } finally {
            setSaving(false);
        }
    };

    return <Modal isOpen onClose={onClose} title={t('care_session.materials_btn', 'Materials')} size="md">
        <form onSubmit={save} className="space-y-4" data-testid="care-session-materials">
            <p className="text-sm text-text-secondary">{t('care_session.materials_explicit_use', 'Select the material actually used. Recording usage deducts stock for this procedure and visit.')}</p>
            {recommended.length > 0 && <p className="text-xs text-text-secondary">{t('care_session.suggested_materials', 'Suggestions')}: {recommended.map((item) => item.material_name || item.category_name || item.category_name_ar).filter(Boolean).join(', ')}</p>}
            {loadError && <p role="alert">{t('care_session.material_load_error', 'Unable to load materials or recorded usage. Close and try again.')}</p>}
            <label className="block text-sm">{t('care_session.material', 'Material')}
                <select aria-label={t('care_session.material', 'Material')} value={materialId} onChange={(event) => setMaterialId(event.target.value)} required className="mt-1 w-full rounded-xl border border-border bg-surface p-2">
                    <option value="">{t('common.select', 'Select')}</option>
                    {available.map((item) => <option key={item.id} value={item.id}>{item.name} ({item.base_unit})</option>)}
                </select>
            </label>
            <label className="block text-sm">{t('care_session.material_quantity', 'Quantity used')}
                <input aria-label={t('care_session.material_quantity', 'Quantity used')} type="number" min="0.000001" step="any" value={quantity} onChange={(event) => setQuantity(event.target.value)} required className="mt-1 w-full rounded-xl border border-border bg-surface p-2" />
            </label>
            {error && <p role="alert" className="text-sm text-danger">{error}</p>}
            <Button type="submit" disabled={saving || materials.isPending || loadError}>{saving ? t('common.saving', 'Saving...') : t('care_session.record_material_use', 'Record usage')}</Button>
            <div className="border-t border-border pt-3">
                <h4 className="text-sm font-bold">{t('care_session.recorded_materials', 'Recorded in this visit')}</h4>
                {recorded.map((item) => <p key={item.id} className="text-sm">{item.material_name} — {item.quantity_used ?? t('care_session.open_package_use', 'Open package usage')}</p>)}
                {!usages.isPending && !recorded.length && <p className="text-xs text-text-secondary">{t('care_session.no_material_use', 'No usage recorded yet.')}</p>}
            </div>
        </form>
    </Modal>;
}
