import { useState, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import PropTypes from 'prop-types';
import { invalidatePatientClinicalQueries } from '@/features/patients/utils/invalidatePatientClinicalQueries';
import {
    FlaskConical,
    Calendar,
    FileText,
    CheckCircle2,
    ShieldCheck,
    AlertCircle,
    Building2,
    Layers,
    Palette,
} from 'lucide-react';
import Modal from '@/shared/ui/Modal';
import { getLaboratories, dispatchLabHandoff } from '@/api/labs';

const COMMON_SHADES = ['A1', 'A2', 'A3', 'A3.5', 'B1', 'B2', 'BL1'];
const COMMON_MATERIALS = ['Zirconia', 'E-Max', 'PFM (Porcelain)', 'PMMA (Temp)', 'Titanium'];

/**
 * One-Tap Lab Handoff Sheet (Slice S28 / G12-M06, G12-M08, G12-M09, G12-M16).
 * Chairside dialog pre-populating patient, tooth, procedure code, and doctor for quick lab dispatch.
 * Decouples lab price from synthetic treatment creation: creates ZERO duplicate treatment rows (R06).
 */
export default function LabHandoffSheet({
    isOpen,
    onClose,
    patientId,
    patientName = '',
    workItem = null,
    toothKey = '',
    doctorName = '',
    onSuccess = null,
    t = (k, f) => f || k,
}) {
    const queryClient = useQueryClient();
    const [laboratories, setLaboratories] = useState([]);
    const [loadingLabs, setLoadingLabs] = useState(false);
    const [selectedLabId, setSelectedLabId] = useState('');
    const [workType, setWorkType] = useState('');
    const [toothNumber, setToothNumber] = useState('');
    const [shade, setShade] = useState('A2');
    const [customShade, setCustomShade] = useState('');
    const [material, setMaterial] = useState('Zirconia');
    const [customMaterial, setCustomMaterial] = useState('');
    const [deliveryDate, setDeliveryDate] = useState('');
    const [cost, setCost] = useState('0');
    const [priceToPatient, setPriceToPatient] = useState('0');
    const [notes, setNotes] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [errorMessage, setErrorMessage] = useState('');
    const [successOrder, setSuccessOrder] = useState(null);

    // Initial pre-population
    useEffect(() => {
        if (!isOpen) return;

        // Resolve tooth number
        let initialTooth = toothKey || '';
        if (!initialTooth && workItem?.targets?.length) {
            initialTooth = workItem.targets
                .map((t) => t.tooth_key || t.toothKey)
                .filter(Boolean)
                .join(', ');
        }
        setToothNumber(initialTooth);

        // Resolve work type
        const initialWorkType =
            workItem?.code === 'PROS_CROWN'
                ? 'Crown Restoration'
                : workItem?.code === 'PROS_BRIDGE'
                  ? 'Fixed Bridge'
                  : workItem?.code === 'IMPLANT_CROWN'
                    ? 'Implant Crown'
                    : workItem?.code === 'PROS_DENTURE'
                      ? 'Removable Denture'
                      : workItem?.title || workItem?.code || 'Prosthetic Lab Work';
        setWorkType(initialWorkType);

        // Resolve default delivery date (7 days from now)
        const d = new Date();
        d.setDate(d.getDate() + 7);
        setDeliveryDate(d.toISOString().slice(0, 10));

        // Reset state
        setSuccessOrder(null);
        setErrorMessage('');

        // Fetch labs
        setLoadingLabs(true);
        getLaboratories()
            .then((res) => {
                const labs = res?.data?.data || res?.data || [];
                setLaboratories(labs);
                if (labs.length > 0) {
                    setSelectedLabId((prev) => prev || String(labs[0].id));
                }
            })
            .catch(() => {
                setErrorMessage(t('lab_handoff.failed_load_labs', 'Failed to load dental laboratories list.'));
            })
            .finally(() => {
                setLoadingLabs(false);
            });
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isOpen, workItem, toothKey]);

    const activeShade = customShade.trim() || shade;
    const activeMaterial = customMaterial.trim() || material;

    const handleSubmit = async (e) => {
        if (e) e.preventDefault();
        if (!selectedLabId) {
            setErrorMessage(t('lab_handoff.error_select_lab', 'Please select a laboratory.'));
            return;
        }

        setSubmitting(true);
        setErrorMessage('');

        const payload = {
            laboratory_id: parseInt(selectedLabId, 10),
            work_type: workType || 'Prosthetic Work',
            tooth_number: toothNumber || null,
            shade: activeShade || null,
            material: activeMaterial || null,
            cost: parseFloat(cost) || 0,
            price_to_patient: parseFloat(priceToPatient) || 0,
            delivery_date: deliveryDate ? new Date(deliveryDate).toISOString() : null,
            notes: notes.trim() || null,
        };

        try {
            const workItemId = workItem?.id || workItem?.work_item_id;
            const res = await dispatchLabHandoff(patientId, workItemId, payload);
            const orderData = res?.data?.data || res?.data;
            setSuccessOrder(orderData);
            if (queryClient && patientId) {
                invalidatePatientClinicalQueries(queryClient, patientId);
            }
            if (onSuccess) {
                onSuccess(orderData);
            }
        } catch (err) {
            const detail =
                err?.response?.data?.detail ||
                err?.message ||
                t('lab_handoff.error_submitting', 'Failed to dispatch lab handoff.');
            setErrorMessage(detail);
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={t('lab_handoff.modal_title', 'Chairside Lab Handoff (1-Tap)')}
            size="lg"
        >
            <div className="space-y-4 text-xs text-slate-700 dark:text-slate-300" data-testid="lab-handoff-sheet">
                {/* Header Information Banner */}
                <div className="flex items-start justify-between rounded-card border border-teal-200 bg-teal-50/70 p-3 dark:border-teal-900/50 dark:bg-teal-950/20">
                    <div className="flex items-center gap-2.5">
                        <div className="flex h-9 w-9 items-center justify-center rounded-control bg-teal-600 text-white shadow-low">
                            <FlaskConical className="h-5 w-5" aria-hidden="true" />
                        </div>
                        <div>
                            <div className="flex items-center gap-2">
                                <span className="font-bold text-teal-950 dark:text-teal-200">
                                    {patientName ? `${patientName} · ` : ''}
                                    {doctorName ? `Dr. ${doctorName} · ` : ''}
                                    Tooth {toothNumber || 'General'}
                                </span>
                                <span className="rounded-pill bg-teal-200/80 px-2 py-0.5 text-[10px] font-bold text-teal-900 dark:bg-teal-900/70 dark:text-teal-200">
                                    {workType}
                                </span>
                            </div>
                            <p className="mt-0.5 text-[11px] text-teal-800 dark:text-teal-300">
                                {t('lab_handoff.quick_handoff_subtitle', 'Instant chairside dispatch linked to Clinical Work Item')}
                                {workItem?.id ? ` #${workItem.id}` : ''}
                            </p>
                        </div>
                    </div>
                    <div className="hidden sm:flex items-center gap-1 rounded-pill border border-emerald-300 bg-emerald-100/70 px-2 py-1 text-[10px] font-semibold text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300">
                        <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
                        <span>{t('lab_handoff.no_double_billing', '0 Duplicate Billing (R06)')}</span>
                    </div>
                </div>

                {/* Error Banner */}
                {errorMessage && (
                    <div
                        className="flex items-center gap-2 rounded-card border border-rose-200 bg-rose-50 p-3 text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/30 dark:text-rose-300"
                        data-testid="lab-handoff-error"
                    >
                        <AlertCircle className="h-4 w-4 shrink-0 text-rose-600" aria-hidden="true" />
                        <span>{errorMessage}</span>
                    </div>
                )}

                {/* Success Banner */}
                {successOrder && (
                    <div
                        className="space-y-2 rounded-card border border-emerald-300 bg-emerald-50 p-4 text-emerald-900 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-200"
                        data-testid="lab-handoff-success"
                    >
                        <div className="flex items-center gap-2 font-bold text-sm">
                            <CheckCircle2 className="h-5 w-5 text-emerald-600" aria-hidden="true" />
                            <span>{t('lab_handoff.success_title', 'Lab Order Dispatched Successfully!')}</span>
                        </div>
                        <p className="text-xs">
                            {t(
                                'lab_handoff.success_detail',
                                `Lab Order #${successOrder.id} linked to Work Item #${successOrder.work_item_id || workItem?.id}. Zero duplicate treatment charges created.`,
                                { orderId: successOrder.id, workItemId: successOrder.work_item_id || workItem?.id }
                            )}
                        </p>
                        <div className="flex justify-end pt-2">
                            <button
                                type="button"
                                onClick={onClose}
                                className="rounded-control bg-emerald-600 px-4 py-1.5 font-bold text-white shadow-low hover:bg-emerald-700"
                            >
                                {t('common.done', 'Done')}
                            </button>
                        </div>
                    </div>
                )}

                {!successOrder && (
                    <form onSubmit={handleSubmit} className="space-y-3.5">
                        {/* Laboratory Selector */}
                        <div className="space-y-1">
                            <label className="block font-semibold text-slate-800 dark:text-slate-200">
                                <span className="flex items-center gap-1.5">
                                    <Building2 className="h-3.5 w-3.5 text-teal-600" aria-hidden="true" />
                                    {t('lab_handoff.laboratory_label', 'Select Dental Laboratory')}
                                    <span className="text-rose-500">*</span>
                                </span>
                            </label>
                            {loadingLabs ? (
                                <div className="p-2 text-xs text-slate-500">Loading laboratories...</div>
                            ) : (
                                <select
                                    value={selectedLabId}
                                    onChange={(e) => setSelectedLabId(e.target.value)}
                                    data-testid="lab-select"
                                    className="w-full rounded-control border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800 shadow-low focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                                    required
                                >
                                    <option value="">{t('lab_handoff.choose_lab', '-- Select Laboratory --')}</option>
                                    {laboratories.map((lab) => (
                                        <option key={lab.id} value={lab.id}>
                                            {lab.name} {lab.phone ? `(${lab.phone})` : ''}
                                        </option>
                                    ))}
                                </select>
                            )}
                        </div>

                        {/* Tooth & Work Type */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            <div className="space-y-1">
                                <label className="block font-semibold text-slate-800 dark:text-slate-200">
                                    {t('lab_handoff.tooth_number', 'Tooth Number')}
                                </label>
                                <input
                                    type="text"
                                    value={toothNumber}
                                    onChange={(e) => setToothNumber(e.target.value)}
                                    data-testid="tooth-number-input"
                                    placeholder="e.g. 21"
                                    className="w-full rounded-control border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800 shadow-low focus:border-teal-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                                />
                            </div>
                            <div className="space-y-1">
                                <label className="block font-semibold text-slate-800 dark:text-slate-200">
                                    {t('lab_handoff.work_type', 'Prescription / Work Type')}
                                </label>
                                <input
                                    type="text"
                                    value={workType}
                                    onChange={(e) => setWorkType(e.target.value)}
                                    data-testid="work-type-input"
                                    placeholder="e.g. Crown Restoration"
                                    className="w-full rounded-control border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800 shadow-low focus:border-teal-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                                    required
                                />
                            </div>
                        </div>

                        {/* Shade Selection (Quick Chips + Custom) */}
                        <div className="space-y-1.5 rounded-card border border-slate-200 bg-slate-50/60 p-2.5 dark:border-slate-800 dark:bg-slate-900/40">
                            <label className="block font-semibold text-slate-800 dark:text-slate-200">
                                <span className="flex items-center gap-1.5">
                                    <Palette className="h-3.5 w-3.5 text-teal-600" aria-hidden="true" />
                                    {t('lab_handoff.shade_label', 'Shade Selection')}
                                </span>
                            </label>
                            <div className="flex flex-wrap items-center gap-1.5" data-testid="shade-chips">
                                {COMMON_SHADES.map((s) => {
                                    const isSelected = !customShade && shade === s;
                                    return (
                                        <button
                                            key={s}
                                            type="button"
                                            onClick={() => {
                                                setShade(s);
                                                setCustomShade('');
                                            }}
                                            className={`rounded-pill px-2.5 py-1 text-xs font-bold transition-colors ${
                                                isSelected
                                                    ? 'bg-teal-600 text-white shadow-low'
                                                    : 'border border-slate-300 bg-white text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300'
                                            }`}
                                        >
                                            {s}
                                        </button>
                                    );
                                })}
                                <input
                                    type="text"
                                    value={customShade}
                                    onChange={(e) => setCustomShade(e.target.value)}
                                    placeholder={t('lab_handoff.custom_shade', 'Other shade...')}
                                    data-testid="custom-shade-input"
                                    className="h-7 w-28 rounded-control border border-slate-300 bg-white px-2 text-xs text-slate-800 focus:border-teal-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                                />
                            </div>
                        </div>

                        {/* Material Selection (Quick Chips + Custom) */}
                        <div className="space-y-1.5 rounded-card border border-slate-200 bg-slate-50/60 p-2.5 dark:border-slate-800 dark:bg-slate-900/40">
                            <label className="block font-semibold text-slate-800 dark:text-slate-200">
                                <span className="flex items-center gap-1.5">
                                    <Layers className="h-3.5 w-3.5 text-teal-600" aria-hidden="true" />
                                    {t('lab_handoff.material_label', 'Material')}
                                </span>
                            </label>
                            <div className="flex flex-wrap items-center gap-1.5" data-testid="material-chips">
                                {COMMON_MATERIALS.map((m) => {
                                    const isSelected = !customMaterial && material === m;
                                    return (
                                        <button
                                            key={m}
                                            type="button"
                                            onClick={() => {
                                                setMaterial(m);
                                                setCustomMaterial('');
                                            }}
                                            className={`rounded-pill px-2.5 py-1 text-xs font-bold transition-colors ${
                                                isSelected
                                                    ? 'bg-teal-600 text-white shadow-low'
                                                    : 'border border-slate-300 bg-white text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300'
                                            }`}
                                        >
                                            {m}
                                        </button>
                                    );
                                })}
                                <input
                                    type="text"
                                    value={customMaterial}
                                    onChange={(e) => setCustomMaterial(e.target.value)}
                                    placeholder={t('lab_handoff.custom_material', 'Other material...')}
                                    data-testid="custom-material-input"
                                    className="h-7 w-32 rounded-control border border-slate-300 bg-white px-2 text-xs text-slate-800 focus:border-teal-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                                />
                            </div>
                        </div>

                        {/* Delivery Date & Pricing */}
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                            <div className="space-y-1">
                                <label className="block font-semibold text-slate-800 dark:text-slate-200">
                                    <span className="flex items-center gap-1">
                                        <Calendar className="h-3.5 w-3.5 text-teal-600" aria-hidden="true" />
                                        {t('lab_handoff.delivery_date', 'Expected Delivery')}
                                    </span>
                                </label>
                                <input
                                    type="date"
                                    value={deliveryDate}
                                    onChange={(e) => setDeliveryDate(e.target.value)}
                                    data-testid="delivery-date-input"
                                    className="w-full rounded-control border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800 shadow-low focus:border-teal-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                                />
                            </div>
                            <div className="space-y-1">
                                <label className="block font-semibold text-slate-800 dark:text-slate-200">
                                    {t('lab_handoff.lab_cost', 'Lab Cost')}
                                </label>
                                <input
                                    type="number"
                                    step="0.01"
                                    min="0"
                                    value={cost}
                                    onChange={(e) => setCost(e.target.value)}
                                    data-testid="cost-input"
                                    className="w-full rounded-control border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800 shadow-low focus:border-teal-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                                />
                            </div>
                            <div className="space-y-1">
                                <label className="block font-semibold text-slate-800 dark:text-slate-200">
                                    {t('lab_handoff.patient_price', 'Patient Price (Info)')}
                                </label>
                                <input
                                    type="number"
                                    step="0.01"
                                    min="0"
                                    value={priceToPatient}
                                    onChange={(e) => setPriceToPatient(e.target.value)}
                                    data-testid="price-patient-input"
                                    className="w-full rounded-control border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800 shadow-low focus:border-teal-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                                />
                            </div>
                        </div>

                        {/* Special Instructions */}
                        <div className="space-y-1">
                            <label className="block font-semibold text-slate-800 dark:text-slate-200">
                                <span className="flex items-center gap-1">
                                    <FileText className="h-3.5 w-3.5 text-teal-600" aria-hidden="true" />
                                    {t('lab_handoff.notes_label', 'Instructions to Lab Technician')}
                                </span>
                            </label>
                            <textarea
                                value={notes}
                                onChange={(e) => setNotes(e.target.value)}
                                rows={2}
                                data-testid="notes-input"
                                placeholder={t(
                                    'lab_handoff.notes_placeholder',
                                    'e.g. Subgingival margin on buccal, check contact with tooth 22...'
                                )}
                                className="w-full rounded-control border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800 shadow-low focus:border-teal-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                            />
                        </div>

                        {/* Actions */}
                        <div className="flex items-center justify-end gap-2.5 pt-2">
                            <button
                                type="button"
                                onClick={onClose}
                                disabled={submitting}
                                data-testid="cancel-lab-handoff"
                                className="rounded-control border border-slate-300 bg-white px-4 py-2 font-semibold text-slate-700 shadow-low hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                            >
                                {t('common.cancel', 'Cancel')}
                            </button>
                            <button
                                type="submit"
                                disabled={submitting || loadingLabs || !selectedLabId}
                                data-testid="submit-lab-handoff"
                                className="inline-flex items-center gap-2 rounded-control bg-teal-600 px-5 py-2 font-bold text-white shadow-low hover:bg-teal-700 disabled:opacity-50"
                            >
                                <FlaskConical className="h-4 w-4" aria-hidden="true" />
                                <span>
                                    {submitting
                                        ? t('lab_handoff.submitting', 'Dispatching...')
                                        : t('lab_handoff.submit_button', 'Send to Lab (1-Tap)')}
                                </span>
                            </button>
                        </div>
                    </form>
                )}
            </div>
        </Modal>
    );
}

LabHandoffSheet.propTypes = {
    isOpen: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    patientId: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
    patientName: PropTypes.string,
    workItem: PropTypes.object,
    toothKey: PropTypes.string,
    doctorName: PropTypes.string,
    onSuccess: PropTypes.func,
    t: PropTypes.func,
};
