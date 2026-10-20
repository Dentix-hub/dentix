import { useMemo, useState } from 'react';
import PropTypes from 'prop-types';
import { Trash2, AlertTriangle, Camera, Eye, Plus, FlaskConical, CheckCircle } from 'lucide-react';
import Modal from '@/shared/ui/Modal';
import {
    buildAttachmentUrl,
    getPurposeLabel,
    DiagnosticImageLightbox,
    LinkClinicalAttachmentModal,
} from '@/features/clinical-attachments';
import { isLabRequiredProcedure, mapLabOrderStatus } from '../domain';
import LabHandoffSheet from '@/features/care-sessions/LabHandoffSheet';

export default function ClinicalChartInspector({
    copy,
    title,
    selection,
    toothState,
    workItems = [],
    treatments = [],
    treatmentPlans = [],
    payments = [],
    labOrders = [],
    onRemoveItem = null,
    patientId = null,
    attachments = [],
    attachmentLinks = [],
    activeCareSession = null,
    onCreateAttachmentLink = null,
    onDeleteAttachmentLink = null,
    onOpenLabHandoff = null,
}) {
    const hasSelection = Boolean(selection?.toothKey);
    const toothKey = selection?.toothKey ? String(selection.toothKey) : null;
    const findingsCount = toothState?.findings?.length ?? 0;
    const proceduresCount = toothState?.procedures?.length ?? 0;

    const [pendingRemovalItem, setPendingRemovalItem] = useState(null);
    const [selectedImageForLightbox, setSelectedImageForLightbox] = useState(null);
    const [isLinkModalOpen, setIsLinkModalOpen] = useState(false);
    const [activeLabHandoffItem, setActiveLabHandoffItem] = useState(null);

    const toothImages = useMemo(() => {
        if (!toothKey) return [];
        return (attachmentLinks || []).filter(
            (lnk) =>
                lnk.tooth_key != null &&
                String(lnk.tooth_key) === String(toothKey) &&
                (lnk.file_type?.includes('image') ||
                    lnk.content_type?.includes('image') ||
                    lnk.filename?.match(/\.(png|jpg|jpeg|webp|gif|svg)$/i) ||
                    lnk.file_name?.match(/\.(png|jpg|jpeg|webp|gif|svg)$/i) ||
                    (!lnk.file_type && !lnk.content_type))
        );
    }, [toothKey, attachmentLinks]);

    const activeToothItems = useMemo(() => {
        if (!toothKey) return [];
        const itemsMap = new Map();

        // 1. From workItems
        (workItems || []).forEach((wi) => {
            if (wi.status === 'cancelled' || wi.status === 'superseded' || wi.status === 'entered_in_error') {
                return;
            }
            const targetsThisTooth = (wi.targets || []).filter(
                (t) => String(t.tooth_key || t.toothKey) === toothKey
            );
            if (targetsThisTooth.length > 0 || (wi.tooth_number && String(wi.tooth_number) === toothKey)) {
                const id = wi.id;
                const surfaces = targetsThisTooth.filter((t) => t.surface_code).map((t) => t.surface_code);

                // G12-M10 & G12-M11: Lab status mapping & reflection
                const linkedLab = (labOrders || []).find((lo) => lo.work_item_id === id || lo.id === wi.lab_order_id);
                const labStatus = linkedLab ? mapLabOrderStatus(linkedLab.status) : (wi.lab_status || 'unmapped');
                const isLabReady = labStatus === 'lab_ready' || Boolean(wi.lab_ready);
                const shade = linkedLab?.shade || wi.shade || null;
                const material = linkedLab?.material || wi.material || null;

                itemsMap.set(`wi-${id}`, {
                    id,
                    uniqueKey: `wi-${id}`,
                    sourceType: 'work_item',
                    kind: wi.kind || 'procedure',
                    code: wi.code,
                    name: copy.legend?.[wi.code?.toLowerCase()] || copy[wi.code] || wi.code,
                    status: wi.status,
                    surfaces,
                    notes: wi.notes,
                    labOrderId: linkedLab?.id || wi.lab_order_id || null,
                    labStatus,
                    isLabReady,
                    shade,
                    material,
                    raw: wi,
                });
            }
        });

        // 2. From treatments (legacy / fallback)
        (treatments || []).forEach((tr) => {
            if (tr.status === 'cancelled') return;
            if (String(tr.tooth_number) === toothKey) {
                const id = tr.id;
                const surfaces = Array.isArray(tr.surfaces)
                    ? tr.surfaces
                    : (tr.surface ? tr.surface.split('').filter(Boolean) : []);
                if (!itemsMap.has(`wi-${id}`)) {
                    const linkedLab = (labOrders || []).find((lo) => lo.treatment_id === id || String(lo.tooth_number) === String(toothKey));
                    const labStatus = linkedLab ? mapLabOrderStatus(linkedLab.status) : 'unmapped';
                    const isLabReady = labStatus === 'lab_ready';
                    const shade = linkedLab?.shade || null;
                    const material = linkedLab?.material || null;

                    itemsMap.set(`tr-${id}`, {
                        id,
                        uniqueKey: `tr-${id}`,
                        sourceType: 'treatment',
                        kind: 'treatment',
                        code: tr.procedure || tr.code,
                        name: tr.procedure || tr.code,
                        status: tr.status,
                        surfaces,
                        cost: tr.cost,
                        paid: tr.paid,
                        sessions: tr.sessions,
                        labOrderId: linkedLab?.id || null,
                        labStatus,
                        isLabReady,
                        shade,
                        material,
                        raw: tr,
                    });
                }
            }
        });

        // 3. From toothState visual findings (if not already mapped)
        (toothState?.findings || []).forEach((f, idx) => {
            const id = f.id ?? f.visualId ?? `${toothKey}-finding-${idx}`;
            if (![...itemsMap.values()].some((it) => String(it.id) === String(id) || String(it.uniqueKey) === `wi-${id}`)) {
                const surfaces = (f.targets || []).filter((t) => t.surfaceCode).map((t) => t.surfaceCode);
                itemsMap.set(`vis-${id}`, {
                    id,
                    uniqueKey: `vis-${id}`,
                    sourceType: 'visual_finding',
                    kind: 'finding',
                    code: f.code,
                    name: copy.legend?.[f.code?.toLowerCase()] || copy[f.code] || f.code,
                    status: f.phase || 'active',
                    surfaces,
                    raw: f,
                });
            }
        });

        // 4. From toothState visual procedures (if not already mapped)
        (toothState?.procedures || []).forEach((p, idx) => {
            const id = p.id ?? p.visualId ?? `${toothKey}-proc-${idx}`;
            if (![...itemsMap.values()].some((it) => String(it.id) === String(id) || String(it.uniqueKey) === `wi-${id}` || String(it.uniqueKey) === `tr-${id}`)) {
                const surfaces = (p.targets || []).filter((t) => t.surfaceCode).map((t) => t.surfaceCode);
                const linkedLab = (labOrders || []).find((lo) => lo.work_item_id === id || lo.treatment_id === id || String(lo.tooth_number) === String(toothKey));
                const labStatus = linkedLab ? mapLabOrderStatus(linkedLab.status) : (p.lab_status || (p.isLabReady ? 'lab_ready' : 'unmapped'));
                const isLabReady = labStatus === 'lab_ready' || Boolean(p.isLabReady || p.lab_ready);
                const shade = linkedLab?.shade || p.shade || null;
                const material = linkedLab?.material || p.material || null;

                itemsMap.set(`vis-${id}`, {
                    id,
                    uniqueKey: `vis-${id}`,
                    sourceType: 'visual_procedure',
                    kind: 'procedure',
                    code: p.code,
                    name: copy.legend?.[p.code?.toLowerCase()] || copy[p.code] || p.code,
                    status: p.phase || 'active',
                    surfaces,
                    labOrderId: linkedLab?.id || p.lab_order_id || null,
                    labStatus,
                    isLabReady,
                    shade,
                    material,
                    raw: p,
                });
            }
        });

        return Array.from(itemsMap.values());
    }, [toothKey, workItems, treatments, toothState, copy, labOrders]);

    const inspectConsequences = (item) => {
        const consequences = [];

        // Check if attached to active treatment plan phase
        const linkedPlans = [];
        (treatmentPlans || []).forEach((plan) => {
            if (plan.status === 'cancelled') return;
            (plan.phases || []).forEach((phase) => {
                const hasItem = (phase.items || []).some((pi) => {
                    const piWorkItemId = pi.work_item_id || pi.work_item?.id;
                    if (piWorkItemId && String(piWorkItemId) === String(item.id)) {
                        return true;
                    }
                    if (
                        item.code &&
                        pi.work_item?.code === item.code &&
                        pi.work_item?.targets?.some((t) => String(t.tooth_key || t.toothKey) === toothKey)
                    ) {
                        return true;
                    }
                    return false;
                });
                if (hasItem) {
                    linkedPlans.push({
                        planTitle: plan.title,
                        phaseName: phase.name,
                        planId: plan.id,
                        phaseId: phase.id,
                    });
                }
            });
        });

        if (linkedPlans.length > 0) {
            consequences.push({
                type: 'treatment_plan',
                title: copy.planWarningTitle || 'Attached to Treatment Plan',
                description: `This procedure is attached to active treatment plan: ${linkedPlans.map((p) => `${p.planTitle} (${p.phaseName})`).join(', ')}. Removing it may disrupt the treatment plan phase.`,
                linkedPlans,
            });
        }

        // Check completed sessions or payments
        const linkedPayments = (payments || []).filter(
            (p) => String(p.treatment_id) === String(item.id) || String(p.work_item_id) === String(item.id)
        );
        const paidAmount = Number(item.paid || 0) + linkedPayments.reduce((acc, p) => acc + Number(p.amount || 0), 0);
        const hasCompletedSessions = Number(item.sessions || 0) > 0 || item.status === 'Done' || item.status === 'completed';

        if (paidAmount > 0 || hasCompletedSessions) {
            consequences.push({
                type: 'payment_or_session',
                title: copy.financialWarningTitle || 'Recorded Payments or Completed Sessions',
                description: `This item has recorded financial payments ($${paidAmount}) or completed clinical sessions. Removing it may lead to billing or clinical audit discrepancies.`,
                paidAmount,
                hasCompletedSessions,
            });
        }

        return consequences;
    };

    const handleInitiateRemove = (item) => {
        const consequences = inspectConsequences(item);
        if (consequences.length > 0) {
            setPendingRemovalItem({ item, consequences });
        } else {
            onRemoveItem?.(item);
        }
    };

    const handleConfirmRemoval = () => {
        if (pendingRemovalItem) {
            onRemoveItem?.(pendingRemovalItem.item);
            setPendingRemovalItem(null);
        }
    };

    const isArabic = copy?.localeName === 'العربية';

    return (
        <aside
            aria-label={(title || 'Clinical Chart') + ' - ' + (copy?.inspector || 'Inspector')}
            className="mt-3 rounded-2xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-900/60"
            data-testid="clinical-chart-inspector"
        >
            <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">{copy?.inspector || 'Inspector'}</h3>
                <span className="text-xs font-medium text-slate-500 dark:text-slate-400">{copy?.previewOnly || 'Preview Only'}</span>
            </div>
            <dl aria-live="polite" className="mt-3 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
                <div>
                    <dt className="text-xs text-slate-500 dark:text-slate-400">{copy.selectedTooth}</dt>
                    <dd className="mt-1 font-bold text-slate-900 dark:text-slate-100">{hasSelection ? selection.toothKey : copy.none}</dd>
                </div>
                <div>
                    <dt className="text-xs text-slate-500 dark:text-slate-400">{copy.selectedSurface}</dt>
                    <dd className="mt-1 font-bold text-slate-900 dark:text-slate-100">
                        {selection?.surfaceCodes && selection.surfaceCodes.length > 0
                            ? selection.surfaceCodes.map(code => copy.surfaces?.[code] || code).join(', ')
                            : (selection?.surfaceCode ? (copy.surfaces?.[selection.surfaceCode] || selection.surfaceCode) : copy.none)}
                    </dd>
                </div>
                <div>
                    <dt className="text-xs text-slate-500 dark:text-slate-400">{copy.findings}</dt>
                    <dd className="mt-1 font-bold text-slate-900 dark:text-slate-100">{findingsCount}</dd>
                </div>
                <div>
                    <dt className="text-xs text-slate-500 dark:text-slate-400">{copy.procedures}</dt>
                    <dd className="mt-1 font-bold text-slate-900 dark:text-slate-100">{proceduresCount}</dd>
                </div>
            </dl>

            {hasSelection && (
                <>
                    {/* Active Findings & Procedures Section */}
                    <div className="mt-4 border-t border-slate-200 pt-3 dark:border-slate-800" data-testid="inspector-items-section">
                        <div className="flex items-center justify-between">
                            <h4 className="text-xs font-bold text-slate-700 dark:text-slate-300">
                                {copy.activeItems || 'Active Findings & Procedures'}
                            </h4>
                            <span className="text-xs text-slate-400">
                                ({activeToothItems.length})
                            </span>
                        </div>

                        {activeToothItems.length === 0 ? (
                            <p className="mt-2 text-xs italic text-slate-500 dark:text-slate-400" data-testid="inspector-no-items">
                                {copy.noItemsOnTooth || 'No active findings or procedures on this tooth.'}
                            </p>
                        ) : (
                            <ul className="mt-2 space-y-2" data-testid="inspector-items-list">
                                {activeToothItems.map((item) => (
                                    <li
                                        key={item.uniqueKey}
                                        data-testid={`inspector-item-${item.id}`}
                                        className="flex items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white p-2.5 shadow-sm dark:border-slate-800 dark:bg-slate-900"
                                    >
                                        <div className="min-w-0 flex-1">
                                            <div className="flex flex-wrap items-center gap-1.5">
                                                <span className="text-xs font-bold text-slate-900 dark:text-slate-100">
                                                    {item.name}
                                                </span>
                                                <span
                                                    className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-[10px] font-semibold ${
                                                        item.kind === 'finding'
                                                            ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/50 dark:text-amber-300'
                                                            : 'bg-blue-100 text-blue-800 dark:bg-blue-950/50 dark:text-blue-300'
                                                    }`}
                                                >
                                                    {item.kind === 'finding' ? (copy.findings || 'Finding') : (copy.procedures || 'Procedure')}
                                                </span>
                                                {item.surfaces && item.surfaces.length > 0 && (
                                                    <span className="inline-flex items-center rounded-md bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                                                        {item.surfaces.join('')}
                                                    </span>
                                                )}
                                                {item.isLabReady && (
                                                    <span
                                                        data-testid={`lab-status-badge-${item.id}`}
                                                        className="inline-flex items-center gap-1 rounded-md bg-emerald-100 px-1.5 py-0.5 text-[10px] font-bold text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300"
                                                    >
                                                        <CheckCircle size={10} aria-hidden="true" />
                                                        {copy.labReady || 'Lab Ready'}
                                                    </span>
                                                )}
                                            </div>
                                            {item.status && (
                                                <p className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">
                                                    {copy.status || 'Status'}: {item.status}
                                                </p>
                                            )}
                                            {(item.shade || item.material) && (
                                                <p
                                                    data-testid={`item-shade-material-${item.id}`}
                                                    className="mt-0.5 text-[11px] text-slate-600 dark:text-slate-300"
                                                >
                                                    {item.material && <span className="font-medium">{item.material}</span>}
                                                    {item.material && item.shade && <span> • </span>}
                                                    {item.shade && <span>{copy.shade || 'Shade'}: {item.shade}</span>}
                                                </p>
                                            )}
                                        </div>

                                        <div className="flex items-center gap-1.5 shrink-0">
                                            {item.kind === 'procedure' && isLabRequiredProcedure(item.code) && (
                                                <button
                                                    type="button"
                                                    onClick={() => {
                                                        if (onOpenLabHandoff) onOpenLabHandoff(item);
                                                        setActiveLabHandoffItem(item);
                                                    }}
                                                    aria-label={`Send ${item.name} to Lab`}
                                                    data-testid={`lab-handoff-${item.id}`}
                                                    className="inline-flex min-h-11 shrink-0 items-center justify-center rounded-control border border-teal-300 bg-teal-50 px-2.5 py-1.5 text-xs font-bold text-teal-700 shadow-low transition-colors hover:bg-teal-100 dark:border-teal-800 dark:bg-teal-950/40 dark:text-teal-300 dark:hover:bg-teal-900/60"
                                                >
                                                    <FlaskConical size={14} className="me-1" aria-hidden="true" />
                                                    <span className="hidden sm:inline">{copy.sendToLab || 'Send to Lab'}</span>
                                                </button>
                                            )}

                                            {onRemoveItem && (
                                                <button
                                                    type="button"
                                                    onClick={() => handleInitiateRemove(item)}
                                                    aria-label={`${copy.removeItem || 'Remove'} ${item.name}`}
                                                    data-testid={`remove-item-${item.id}`}
                                                    className="inline-flex min-h-11 min-w-11 shrink-0 items-center justify-center rounded-lg border border-red-200 bg-white px-2.5 py-1.5 text-xs font-bold text-red-600 transition-colors hover:bg-red-50 hover:text-red-700 dark:border-red-900/60 dark:bg-slate-800 dark:text-red-400 dark:hover:bg-red-950/30"
                                                >
                                                    <Trash2 size={15} aria-hidden="true" />
                                                    <span className="ms-1 hidden sm:inline">{copy.removeItem || 'Remove'}</span>
                                                </button>
                                            )}
                                        </div>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </div>

                    {/* Diagnostic Images Section (Slice S24 / G15-M07) */}
                    <div className="mt-4 border-t border-slate-200 pt-3 dark:border-slate-800" data-testid="inspector-images-section">
                        <div className="flex items-center justify-between">
                            <h4 className="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                                <Camera className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
                                <span>{copy.diagnosticImages || 'Diagnostic Images & X-Rays'}</span>
                            </h4>
                            <div className="flex items-center gap-2">
                                <span className="text-xs text-slate-400" data-testid="tooth-images-count">
                                    ({toothImages.length})
                                </span>
                                {attachments.length > 0 && (
                                    <button
                                        type="button"
                                        onClick={() => setIsLinkModalOpen(true)}
                                        data-testid="btn-link-tooth-image"
                                        className="inline-flex items-center gap-1 text-[11px] font-bold text-blue-600 hover:text-blue-700 dark:text-blue-400"
                                    >
                                        <Plus className="h-3 w-3" />
                                        <span>{copy.linkImage || 'Link Image'}</span>
                                    </button>
                                )}
                            </div>
                        </div>

                        {toothImages.length === 0 ? (
                            <p className="mt-2 text-xs italic text-slate-500 dark:text-slate-400" data-testid="inspector-no-images">
                                {copy.noImagesOnTooth || 'No diagnostic images linked to this tooth.'}
                            </p>
                        ) : (
                            <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3" data-testid="tooth-inspector-images">
                                {toothImages.map((img) => (
                                    <div
                                        key={img.id}
                                        data-testid={`tooth-image-thumbnail-${img.id}`}
                                        onClick={() => setSelectedImageForLightbox(img)}
                                        className="group relative aspect-square cursor-pointer overflow-hidden rounded-xl border border-slate-200 bg-slate-100 shadow-sm transition-transform hover:scale-[1.02] dark:border-slate-800 dark:bg-slate-800"
                                    >
                                        <img
                                            src={buildAttachmentUrl(img.file_path)}
                                            alt={img.filename || `Tooth ${toothKey} image`}
                                            className="h-full w-full object-cover"
                                        />
                                        <div className="absolute top-1 start-1">
                                            <span
                                                data-testid={`tooth-image-purpose-${img.id}`}
                                                className="rounded bg-black/75 px-1.5 py-0.5 text-[9px] font-bold text-white backdrop-blur-xs"
                                            >
                                                {getPurposeLabel(img.purpose_code, isArabic)}
                                            </span>
                                        </div>
                                        <div className="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 transition-opacity group-hover:opacity-100">
                                            <Eye className="h-4 w-4 text-white" />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </>
            )}

            {/* Removal Confirmation Consequence Modal */}
            {pendingRemovalItem && (
                <Modal
                    isOpen={Boolean(pendingRemovalItem)}
                    onClose={() => setPendingRemovalItem(null)}
                    title={copy.consequenceModalTitle || 'Warning: Removal Consequences'}
                    className="max-w-md"
                >
                    <div className="space-y-4 p-4" data-testid="consequence-warning-modal">
                        <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/40 dark:text-amber-200">
                            <AlertTriangle size={20} className="mt-0.5 shrink-0 text-amber-600 dark:text-amber-400" aria-hidden="true" />
                            <div className="min-w-0 flex-1">
                                <p className="text-sm font-semibold">
                                    {copy.consequenceModalLead || 'Removing this item will affect existing clinic records:'}
                                </p>
                                <ul className="mt-2 list-disc space-y-1.5 ps-4 text-xs">
                                    {pendingRemovalItem.consequences.map((c, i) => (
                                        <li
                                            key={i}
                                            data-testid={c.type === 'treatment_plan' ? 'consequence-plan-warning' : 'consequence-payment-warning'}
                                        >
                                            <strong className="font-semibold">{c.title}: </strong>
                                            <span>{c.description}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>

                        <p className="text-xs text-slate-500 dark:text-slate-400">
                            {copy.consequenceModalConfirmPrompt || 'Are you sure you want to proceed with removal? This action cannot be undone.'}
                        </p>

                        <div className="flex items-center justify-end gap-3 pt-2">
                            <button
                                type="button"
                                onClick={() => setPendingRemovalItem(null)}
                                data-testid="cancel-consequence-button"
                                className="inline-flex min-h-11 items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                            >
                                {copy.cancel || 'Cancel'}
                            </button>
                            <button
                                type="button"
                                onClick={handleConfirmRemoval}
                                data-testid="confirm-consequence-remove-button"
                                className="inline-flex min-h-11 items-center justify-center rounded-xl bg-red-600 px-4 py-2 text-sm font-bold text-white shadow-sm hover:bg-red-700"
                            >
                                {copy.confirmRemove || 'Confirm Removal'}
                            </button>
                        </div>
                    </div>
                </Modal>
            )}

            {/* Diagnostic Image Lightbox Modal */}
            {selectedImageForLightbox && (
                <DiagnosticImageLightbox
                    isOpen={Boolean(selectedImageForLightbox)}
                    onClose={() => setSelectedImageForLightbox(null)}
                    image={selectedImageForLightbox}
                    isArabic={isArabic}
                />
            )}

            {/* Link Existing Attachment Modal from Tooth Inspector */}
            {isLinkModalOpen && (
                <LinkClinicalAttachmentModal
                    isOpen={isLinkModalOpen}
                    onClose={() => setIsLinkModalOpen(false)}
                    attachment={attachments[0] || null}
                    patientId={patientId}
                    activeCareSession={activeCareSession}
                    workItems={workItems}
                    initialToothKey={toothKey}
                    existingLinks={attachmentLinks}
                    onLinkCreated={onCreateAttachmentLink}
                    onLinkDeleted={onDeleteAttachmentLink}
                    isArabic={isArabic}
                />
            )}

            {/* Chairside Lab Handoff Sheet (Slice S28 / G12-M06) */}
            {activeLabHandoffItem && (
                <LabHandoffSheet
                    isOpen={Boolean(activeLabHandoffItem)}
                    onClose={() => setActiveLabHandoffItem(null)}
                    patientId={patientId}
                    toothKey={toothKey}
                    workItem={activeLabHandoffItem}
                    t={(k, f) => f || k}
                />
            )}
        </aside>
    );
}

ClinicalChartInspector.propTypes = {
    copy: PropTypes.object.isRequired,
    title: PropTypes.string,
    selection: PropTypes.shape({
        toothKey: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
        surfaceCode: PropTypes.string,
        surfaceCodes: PropTypes.arrayOf(PropTypes.string),
    }),
    toothState: PropTypes.shape({
        findings: PropTypes.array,
        procedures: PropTypes.array,
    }),
    workItems: PropTypes.array,
    treatments: PropTypes.array,
    treatmentPlans: PropTypes.array,
    payments: PropTypes.array,
    labOrders: PropTypes.array,
    onRemoveItem: PropTypes.func,
    patientId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    attachments: PropTypes.array,
    attachmentLinks: PropTypes.array,
    activeCareSession: PropTypes.object,
    onCreateAttachmentLink: PropTypes.func,
    onDeleteAttachmentLink: PropTypes.func,
    onOpenLabHandoff: PropTypes.func,
};
