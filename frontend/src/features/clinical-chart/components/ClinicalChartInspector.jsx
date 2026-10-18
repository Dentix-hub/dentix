import { useMemo, useState } from 'react';
import { Trash2, AlertTriangle } from 'lucide-react';
import Modal from '@/shared/ui/Modal';

export default function ClinicalChartInspector({
    copy,
    title,
    selection,
    toothState,
    workItems = [],
    treatments = [],
    treatmentPlans = [],
    payments = [],
    onRemoveItem = null,
}) {
    const hasSelection = Boolean(selection?.toothKey);
    const toothKey = selection?.toothKey ? String(selection.toothKey) : null;
    const findingsCount = toothState?.findings?.length ?? 0;
    const proceduresCount = toothState?.procedures?.length ?? 0;

    const [pendingRemovalItem, setPendingRemovalItem] = useState(null);

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
                        raw: tr,
                    });
                }
            }
        });

        // 3. From toothState visual findings (if not already mapped)
        (toothState?.findings || []).forEach((f, idx) => {
            const id = f.visualId || `${toothKey}-finding-${idx}`;
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
            const id = p.visualId || `${toothKey}-proc-${idx}`;
            if (![...itemsMap.values()].some((it) => String(it.id) === String(id) || String(it.uniqueKey) === `wi-${id}` || String(it.uniqueKey) === `tr-${id}`)) {
                const surfaces = (p.targets || []).filter((t) => t.surfaceCode).map((t) => t.surfaceCode);
                itemsMap.set(`vis-${id}`, {
                    id,
                    uniqueKey: `vis-${id}`,
                    sourceType: 'visual_procedure',
                    kind: 'procedure',
                    code: p.code,
                    name: copy.legend?.[p.code?.toLowerCase()] || copy[p.code] || p.code,
                    status: p.phase || 'active',
                    surfaces,
                    raw: p,
                });
            }
        });

        return Array.from(itemsMap.values());
    }, [toothKey, workItems, treatments, toothState, copy]);

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

    return (
        <aside
            aria-label={title + ' - ' + copy.inspector}
            className="mt-3 rounded-2xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-900/60"
            data-testid="clinical-chart-inspector"
        >
            <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">{copy.inspector}</h3>
                <span className="text-xs font-medium text-slate-500 dark:text-slate-400">{copy.previewOnly}</span>
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
                                        </div>
                                        {item.status && (
                                            <p className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">
                                                {copy.status || 'Status'}: {item.status}
                                            </p>
                                        )}
                                    </div>

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
                                </li>
                            ))}
                        </ul>
                    )}
                </div>
            )}

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
        </aside>
    );
}
